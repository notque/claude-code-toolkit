# ADR-151: Magic Docs — Dynamic Documentation Injection

## Status

Proposed

## Date

2026-03-31

## Context

Claude Code includes a "magic docs" capability where the model can dynamically fetch library and
framework documentation and inject it into context when working with unfamiliar APIs. The system
prompt instructs the model that it can use WebFetch with documentation-specific prompts against
official documentation sites (docs.python.org, pkg.go.dev, docs.rs, MDN, etc.). Results are
condensed and cached to avoid re-fetching identical docs within a session.

### The Problem in Our Toolkit

Our agents regularly work with libraries they do not deeply know. A Python agent may encounter an
unfamiliar third-party package; a Go agent may hit a less common stdlib package; a research agent
may need to understand a CLI tool's flags. In each case, the model either hallucinates API details
or produces correct but generic output that misses library-specific idioms.

The gap is not capability — Claude can use WebFetch — it is *activation*. Without an explicit
system-level prompt telling the model to fetch documentation when uncertain, it defaults to
pattern-matching from training data. That data may be stale (library at v0.8 when v2.0 is current)
or sparse (niche library with minimal training representation).

### What Claude Code Does Internally

The system prompt section that enables magic docs tells the model:

1. When you encounter an import or API call you are uncertain about, fetch the official docs before
   proceeding.
2. Use WebFetch with a documentation-targeting prompt (e.g., "Extract the API reference for
   function X from this page").
3. Cache the result in session context to avoid re-fetching the same page.
4. Condense fetched docs to the relevant section rather than dumping full HTML.

The WebFetch tool is then called with URLs like `https://pkg.go.dev/some/package` or
`https://docs.python.org/3/library/something.html` and a prompt that extracts the relevant
function signatures, parameter descriptions, and return types.

### The Activation Gap in Our Toolkit

Our agents do not have this instruction. They know WebFetch exists but have no standing directive
to use it when encountering uncertain APIs. The result is agents that silently hallucinate rather
than fetch-and-verify.

The second gap is caching. Even if an agent decides to fetch docs, there is no mechanism to
avoid re-fetching the same URL later in a session. This matters because our research agents can
trigger 20+ tool calls per task; fetching the same docs repeatedly wastes both tokens and latency.

### Why a Hook Is the Right Layer

A `PostToolUse` hook that monitors tool results for API-uncertainty signals (import errors,
`AttributeError`, `undefined symbol`, `no field named`) can detect the moment the model needs
documentation and inject it before the next prompt. This is reactive — triggered by failure —
and complements the proactive pattern (agents invoking a skill explicitly).

A skill-based approach (agents invoke `/magic-docs` explicitly) handles the proactive case: an
agent writing code for an unfamiliar library requests docs before writing, not after failing.

Both patterns are needed. The hook handles failure recovery; the skill handles proactive fetching.

### Caching Strategy

Session-scoped caching via a temp file (`/tmp/magic-docs-cache-{session_id}.json`) avoids
re-fetching. Cache keys are normalized URLs (lowercased, fragment stripped). TTL is session
lifetime — no cross-session persistence needed since doc versions may change between sessions.

A simple JSON map `{url: {fetched_at, content, token_count}}` is sufficient. The cache file is
cleaned up at session end by the `Stop` event hook.

### Cache Stability Impact

The magic docs hook injects fetched documentation into `additionalContext`. Unlike static
injections (AFK mode, datetime), doc content varies per session. This means:

- First fetch for a URL: cache miss, WebFetch call, content injected, prompt cache breaks for
  that turn (expected cost: one-time)
- Subsequent turns referencing the same docs: content already in context from prior injection;
  no re-injection needed if the content is already in the conversation history

The hook should inject docs **once** per URL per session, not on every subsequent turn. The
`PostToolUse` hook checks whether the URL was already injected this session before re-injecting.

## Decision

Implement magic docs as two complementary components:

1. **`hooks/magic-docs-injector.py`** — a `PostToolUse` hook that detects API uncertainty signals
   in tool results and injects relevant documentation proactively
2. **`skills/magic-docs/SKILL.md`** — an explicit invocation skill for agents to request
   documentation before writing code against unfamiliar APIs

The hook handles reactive recovery (after errors); the skill handles proactive fetching (before
writing).

### Hook Design: `magic-docs-injector.py`

**Trigger**: `PostToolUse` on `Bash`, `Edit`, `Write` tool events.

**Detection patterns** (scan tool result output for):

| Pattern | Signal |
|---------|--------|
| `ImportError: No module named` | Python import unknown |
| `ModuleNotFoundError` | Python import unknown |
| `AttributeError: ... has no attribute` | Python API mismatch |
| `cannot find package` | Go import unknown |
| `undefined: ` | Go symbol unknown |
| `no field named` | Go struct field unknown |
| `TypeError: ... is not a function` | JS/TS API mismatch |

**On match**:
1. Extract the library/package name from the error message.
2. Construct the documentation URL based on detected language (Go → `pkg.go.dev`, Python →
   `docs.python.org` or PyPI, JS/TS → MDN or npm).
3. Check session cache (`/tmp/magic-docs-cache-{pid}.json`). If URL already fetched this session,
   skip.
4. Call WebFetch with: `"Extract the API reference, function signatures, and key usage examples
   from this documentation page. Be concise — 200-400 tokens maximum."`
5. Store result in session cache.
6. Inject the condensed docs as `additionalContext`.

**Fallback**: if URL construction fails or WebFetch returns an error, emit nothing. Never block
the tool chain on a failed doc fetch.

### Skill Design: `skills/magic-docs/SKILL.md`

Explicit invocation pattern for agents:

```
/magic-docs <library-or-package-name> [language]
```

The skill:
1. Identifies the appropriate documentation URL for the named library.
2. Checks session cache.
3. Fetches and condenses if not cached.
4. Returns the condensed API reference to the invoking agent.

Agents in the Python, Go, and TypeScript engineering profiles should have a directive in their
system prompt to invoke `/magic-docs` when writing against unfamiliar imports.

### URL Construction Rules

| Language | Pattern | Example |
|----------|---------|---------|
| Go | `https://pkg.go.dev/{import-path}` | `pkg.go.dev/github.com/spf13/cobra` |
| Python stdlib | `https://docs.python.org/3/library/{module}.html` | `docs.python.org/3/library/asyncio.html` |
| Python third-party | `https://pypi.org/project/{package}/` then follow docs link | PyPI project page |
| JavaScript/TypeScript | `https://developer.mozilla.org/en-US/docs/Web/API/{Interface}` | MDN |
| npm package | `https://www.npmjs.com/package/{package}` | npm page |
| Rust | `https://docs.rs/{crate}` | `docs.rs/tokio` |

URL construction is heuristic — the hook should try the primary URL and fall back gracefully if
WebFetch fails.

## Affected Files

| File | Action | Purpose |
|------|--------|---------|
| `hooks/magic-docs-injector.py` | Create | PostToolUse detection and injection |
| `skills/magic-docs/SKILL.md` | Create | Explicit invocation skill |
| `.claude/settings.json` | Modify | Register hook in `PostToolUse` handlers |

## Alternatives Considered

### A. Always fetch docs at session start for all imported packages

Pre-fetch documentation for all imports visible in the current workspace at session start. This
provides docs before they are needed.

**Rejected because**: most sessions never encounter errors for the majority of imports. Pre-fetching
all imports wastes tokens and latency for docs that will never be consulted. The on-demand model
is more efficient.

### B. Maintain a persistent cross-session doc cache

Cache documentation in SQLite (alongside `learning.db`) for reuse across sessions.

**Deferred**: cross-session caching requires cache invalidation strategy (library versions change).
Session-scoped cache is simpler and avoids stale doc problems. If the overhead of repeated
fetches across sessions proves significant, promote to `learning.db`.

### C. Hook only on explicit tool error exit codes

Trigger only when Bash tools exit non-zero.

**Rejected because**: many API mismatches do not produce non-zero exits — a Python script may run
successfully but call a deprecated method that still works. Pattern matching on output content is
more comprehensive than exit-code gating.

### D. Embed a local documentation index

Maintain a local index of popular library docs, avoiding WebFetch entirely.

**Rejected because**: the index would be stale immediately and require maintenance. The live-fetch
model is simpler and always current.

## Design Questions Resolved

**Should the hook inject docs on every matching turn or just once per URL per session?**

Once per URL per session. After the first injection, the docs are in the conversation context and
the model can reference them. Re-injecting on every subsequent turn wastes tokens and breaks
prompt cache.

**Should the skill be invocable by the model itself, or only by human users?**

Both. Agents in the Python/Go/TypeScript profiles should have an explicit directive: "If you are
about to write code using an import you are uncertain about, invoke `/magic-docs <package>` first."
Human users can also invoke it directly.

**What if the documentation page is very large (10,000+ tokens)?**

The WebFetch prompt explicitly requests condensed output (200-400 tokens). Claude Code's own magic
docs feature uses similar condensation prompts. The hook should additionally truncate any injected
content to 500 tokens hard maximum to prevent a single doc fetch from destabilizing the context.

**Does this interact with the prompt cache break detection ADR (ADR-152)?**

Yes. Doc injection breaks the prompt cache for the turn it fires. ADR-152's hook will log this
break. The two hooks are complementary: ADR-152 provides observability; ADR-151 is one of the
known cache-break sources that observability will reveal.

## Consequences

### Positive

- Agents produce correct API usage on first attempt rather than hallucinating and requiring
  correction
- Error recovery is faster: API errors are met with immediate doc injection rather than manual
  lookup
- Library version drift is handled: fetched docs reflect the current version, not training data
- Explicit `/magic-docs` skill gives agents a self-service mechanism for proactive documentation
  fetching

### Negative / Risks

**WebFetch latency**: doc fetches add latency to the turn where they fire. For fast interactive
sessions, a 1-2 second fetch may be noticeable.

Mitigation: the hook only fires on error patterns, which are already slow turns (error diagnosis
is happening regardless). The latency is acceptable in context.

**False positives in detection patterns**: the pattern match may trigger on non-error output that
coincidentally contains "no field named" or similar strings.

Mitigation: require patterns to appear in stderr-adjacent context (within 5 lines of an error
marker) rather than anywhere in output. Tune detection patterns based on observed false positive
rate after deployment.

**Doc pages that require JavaScript rendering**: some library docs (React, Svelte) render via JS
and are not accessible to plain WebFetch.

Mitigation: fall back to npm or PyPI landing page if the primary docs URL returns empty or
minimal content. Log the failure in session cache to avoid retrying.

**Token overhead**: doc injections are larger than typical hook injections (200-500 tokens vs.
the ~150 tokens of AFK mode or ~200 tokens of instruction-reminder). However, they fire only
when needed, not on every turn, keeping the aggregate cost bounded.

## Implementation Notes

**URL normalization** for cache keying: lowercase the URL, strip fragments and query parameters,
strip trailing slash. This ensures `pkg.go.dev/foo/bar` and `pkg.go.dev/foo/bar/` are the same
cache key.

**Session ID for cache file**: use `os.getpid()` as the session identifier — the hook process is
spawned fresh each turn, but the PID of the Claude Code process is stable per session. Pass it
as an environment variable `CLAUDE_SESSION_PID` if available; fall back to parent PID via
`os.getppid()`.

**Deploy order** (per established protocol — deploy file BEFORE registering in settings.json):

1. Create `hooks/magic-docs-injector.py` in repo.
2. Run `python3 scripts/sync-to-user-claude.py` to sync to `~/.claude/hooks/`.
3. Verify that a simulated error event triggers doc injection:
   `echo '{"tool_name":"Bash","tool_result":{"output":"ImportError: No module named requests"}}' | python3 ~/.claude/hooks/magic-docs-injector.py`
4. Verify that non-error output produces no injection.
5. Only after steps 3-4 pass, register in `.claude/settings.json`.

## Validation Requirements

Before merging:

1. Simulate a Python `ImportError` event; hook fires and injects condensed docs.
2. Simulate a Go `cannot find package` event; hook fires and injects pkg.go.dev content.
3. Simulate clean tool output; hook produces no injection.
4. Second event for the same URL within a session; hook reads from cache and does not call WebFetch.
5. WebFetch failure (simulated via unreachable URL); hook exits 0 with no injection (no crash).
6. Execution time for cache-hit path: under 5ms.
7. Injected content is under 500 tokens for any real documentation page.

## Effort Estimate

**Medium** — two components (hook + skill), URL heuristics require per-language testing, cache
management adds statefulness beyond simpler hooks. Estimated 2-3 hours of implementation and
testing across Go, Python, and TypeScript error patterns.

## References

- `hooks/lib/hook_utils.py` — `context_output()`, `empty_output()` protocol
- ADR-141 — prompt cache stability; doc injection is a known cache-break source
- ADR-152 — prompt cache break detection; will surface magic-docs-caused breaks
- Claude Code source: system prompt section enabling WebFetch for documentation lookup
- `hooks/afk-mode.py` — reference hook for `PostToolUse` implementation pattern
- `.claude/settings.json` — hook registration reference
