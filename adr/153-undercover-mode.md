# ADR-153: Undercover Mode — Toolkit Internal Leak Prevention

## Status

Proposed

## Date

2026-03-31

## Context

Claude Code's `undercover.ts` (~90 lines) injects a system prompt section specifically for
Anthropic employees working on internal repositories. When `USER_TYPE === 'ant'`, the injected
text instructs the model not to leak internal Anthropic information (internal tool names, ADR
numbers, internal team structures, unpublished API details) into commits, PR descriptions, or
any output that might end up in a public repository. The feature is gated on user type to avoid
burdening non-employee users with irrelevant restrictions.

The design principle: when working in contexts where internal information must not surface, the
model needs an explicit reminder that its internal knowledge is in scope for leakage, even in
apparently innocuous actions like writing commit messages.

### Our Analogous Problem

Our toolkit has its own "internal" vocabulary: agent names (`python-general-engineer`,
`golang-general-engineer`), skill names (`go-patterns`, `systematic-debugging`), ADR numbers
(`ADR-141`, `ADR-152`), hook names (`afk-mode.py`, `cache-break-detector.py`), and internal
patterns (`UserPromptSubmit`, `PostToolUse`, `additionalContext`).

When our agents work on **external user repositories** — the user's own Go service, Python
backend, React frontend — they sometimes reference these toolkit internals in output that
collaborators will see:

- Commit messages: "Fix bug per ADR-141 cache analysis recommendations"
- PR descriptions: "Resolved via systematic-debugging skill"
- Code comments: "# Injected by instruction-reminder.py hook"
- Issue comments: "The auto-plan-detector flagged this"

These references are confusing to collaborators who are not toolkit users. They make PRs look
like they were written by a tool, not a person. They leak information about the operator's
internal development workflow.

### The Toolkit Repo vs. External Repo Distinction

The leak problem only exists when working in **external repositories**. When working in this
toolkit's own repository (`claude-code-toolkit`), referencing ADRs, hooks, and skill names is
correct and expected — those are the actual subjects of discussion.

The key gate: **is the current working directory inside the toolkit repository?**

If yes: toolkit-internal references are appropriate. No injection needed.
If no: toolkit-internal references are inappropriate for user-facing output. Inject the
undercover directive.

### Repository Classification

We need a reliable way to determine if we are inside the toolkit repo vs. an external repo. Two
signals:

1. **Git remote origin URL**: the toolkit repo has a known remote (e.g.,
   `github.com/notque/claude-code-toolkit` or similar). Any repo without that remote is external.
2. **Directory path**: the toolkit is typically installed at `~/.claude/` or a known path.
   If the working directory is not under the known toolkit path, it is external.
3. **`pyproject.toml` / `CLAUDE.md` identity**: the toolkit's own `CLAUDE.md` has a distinctive
   header. If the project's `CLAUDE.md` matches the toolkit template, it is the toolkit repo.

The `scripts/classify-repo.py` script (new) handles this classification, following the router
pattern: scripts do deterministic work, LLMs orchestrate.

### Scope of the Injection

The undercover directive should cover output that becomes visible to external collaborators:

- Commit messages
- PR titles and descriptions
- Branch names (partially — branch names that reference internal concepts)
- Code comments (use judgment — inline comments are usually fine, but comments that reference
  our internal systems are not)
- Issue body text
- Any text that will be committed to the external repository

It should **not** restrict:

- The model's internal reasoning or tool calls
- Instructions passed between agents
- Responses in the Claude Code chat window (these are private to the user)
- References used internally to decide what to do (the model can think about ADR-141 even if
  it should not write "per ADR-141" in a commit message)

### Cache Stability

Like AFK mode, the undercover directive is a session-level characteristic: either we are in
the toolkit repo or we are not. The session starts in a directory; the classification runs once
at session start via `UserPromptSubmit` and the result is cached in a session-scoped file.

The injected directive is static text — identical on every turn if we are in an external repo.
Cache-stable.

## Decision

Create `hooks/undercover-mode.py`, a `UserPromptSubmit` hook that detects whether the current
session is operating in an external repository (not the toolkit repo) and injects a directive
preventing toolkit-internal references from appearing in user-visible output.

Create `scripts/classify-repo.py` to provide deterministic repository classification logic.

### Detection Logic

On first `UserPromptSubmit` event:

1. Run `scripts/classify-repo.py` with the current working directory.
2. Script returns `internal` (toolkit repo) or `external` (any other repo).
3. Cache result in `/tmp/claude-repo-type-{session_pid}.txt`.

On subsequent turns: read cache file, skip classification.

**Classification heuristics in `scripts/classify-repo.py`**:

Priority order (first match wins):

1. `CLAUDE_REPO_TYPE` env var is set to `internal` or `external` → use it directly (escape hatch)
2. Check `git remote get-url origin` for the toolkit repo remote URL → `internal`
3. Check if `$HOME/.claude/` is an ancestor of `cwd` → `internal`
4. Check if `CLAUDE.md` in the repo root contains the toolkit-specific identity marker
   (`"claude-code-toolkit"` in the first 10 lines) → `internal`
5. Default → `external`

### Injected Directive

When in an external repository, inject:

```
<undercover-mode>
You are working in an external repository. Do not reference toolkit-internal concepts in
any output that will be visible to external collaborators:
- Commit messages, PR titles/descriptions, branch names, issue comments
- Code comments that will be committed

Toolkit internals that must not appear in external output: agent names
(python-general-engineer, golang-general-engineer, etc.), skill names
(go-patterns, systematic-debugging, etc.), hook names (afk-mode.py, etc.),
ADR numbers, and implementation details of the toolkit itself.

Use plain language. If you made a decision, describe it in terms of the code and the
problem — not in terms of which toolkit component influenced the decision.
</undercover-mode>
```

### Environment Variable Override

| Variable | Values | Effect |
|----------|--------|--------|
| `CLAUDE_REPO_TYPE` | `internal`, `external` | Override auto-detection |
| `CLAUDE_UNDERCOVER_MODE` | `off` | Disable undercover injection entirely |

`CLAUDE_UNDERCOVER_MODE=off` is the escape hatch for users who want to keep toolkit references
even in external repos (e.g., a user who is actively building on top of the toolkit and wants
their collaborators to understand the context).

### Classification Caching

The classification result is expensive to re-compute if it requires a subprocess call to git.
Cache the result in `/tmp/claude-repo-type-{session_pid}.txt` (single line: `internal` or
`external`). The file is created on first hook execution and read on all subsequent turns.

This is safe because the working directory does not change during a Claude Code session. If the
user changes directory inside the session, the session may be in a different repo — but this
edge case is rare enough to ignore in Phase 1.

## Affected Files

| File | Action | Purpose |
|------|--------|---------|
| `hooks/undercover-mode.py` | Create | Detection and injection |
| `scripts/classify-repo.py` | Create | Deterministic repo classification |
| `.claude/settings.json` | Modify | Register hook in `UserPromptSubmit` handlers |

## Alternatives Considered

### A. Detect "external repo" from git config rather than path

Check `git config --get remote.origin.url` and compare to the known toolkit remote.

**Included as primary heuristic**: this is the most reliable signal. The path-based and
`CLAUDE.md`-based checks are fallbacks for users who have the toolkit installed locally without
a git remote configured.

### B. Inject the directive always (both external and internal)

Apply undercover mode to all sessions, even the toolkit repo.

**Rejected because**: inside the toolkit, referencing ADRs and hooks in commits is correct and
expected. Injecting undercover mode inside the toolkit would suppress legitimate references.
The value is precisely the contextual distinction between internal and external.

### C. Filter output post-generation rather than pre-prompting

After the model produces a commit message or PR description, run a filter that removes toolkit
references before presenting to the user.

**Rejected because**: post-generation filtering is fragile (regex-based removal may corrupt the
surrounding text), introduces latency, and does not address the underlying issue of the model
generating internal references that the user then has to review. Pre-prompting prevents the
problem at the source.

### D. Maintain an allowlist of "safe-to-mention" toolkit concepts

Some toolkit concepts (like git branches or conventional commits) are fine to mention. Build
an allowlist so only truly internal concepts are suppressed.

**Deferred**: an allowlist requires maintenance as the toolkit grows. Start with a broad
restriction and tune based on observed false positives.

## Design Questions Resolved

**Should undercover mode also suppress ADR references in code comments?**

Yes for external repos, but with nuance: a code comment that says `# see ADR-141` in the
toolkit repo is fine. The same comment committed to a user's application repo would expose
toolkit internals. The directive covers all "output visible to external collaborators" which
includes code comments that will be committed.

**What if the user explicitly asks the agent to mention an ADR in a commit message?**

Undercover mode is advisory, not a hard block. The model will follow explicit user instructions.
The directive reduces the *default* behavior of spontaneously referencing internals, but the
user retains full control.

**Should classification run at session start or on every prompt?**

At session start (first UserPromptSubmit), with result cached. Classification involves a
subprocess call and file system check — unnecessary to repeat on every turn.

## Consequences

### Positive

- External collaborators see clean, context-free commit messages and PR descriptions
- Toolkit users' development workflow is not exposed through agent output
- The pattern mirrors a known best practice from Claude Code's own `undercover.ts`
- Cache-stable: static injection when active, zero tokens when in toolkit repo

### Negative / Risks

**False classification (internal repo detected as external)**: if the toolkit git remote is
not the expected URL (user forked and renamed), the classification may misfire.

Mitigation: `CLAUDE_REPO_TYPE=internal` override. Additionally, the toolkit's own `CLAUDE.md`
identity check serves as a fallback.

**Over-suppression**: the model may apply the directive too broadly and avoid mentioning even
innocuous things like "fixed linting per project conventions." The directive should be tuned
to focus on toolkit-specific nouns (agent names, skill names, ADR numbers) not all meta-references.

**Subprocess latency on first turn**: `git remote get-url origin` is a subprocess call. It
adds ~10-20ms on first turn. Acceptable given it runs only once per session.

## Implementation Notes

**`scripts/classify-repo.py` interface**:

```bash
python3 scripts/classify-repo.py [--cwd /path/to/repo]
# stdout: "internal" or "external"
# exit code: 0 always
```

Deterministic, no LLM calls, fast enough to run in hook context.

**Deploy order** (per established protocol):

1. Create `scripts/classify-repo.py` in repo.
2. Create `hooks/undercover-mode.py` in repo.
3. Sync to `~/.claude/` via `python3 scripts/sync-to-user-claude.py`.
4. Test from an external repo: `python3 ~/.claude/hooks/undercover-mode.py < /dev/null` exits 0
   and stdout contains the `<undercover-mode>` block.
5. Test from toolkit repo: exits 0 and stdout contains no `<undercover-mode>` block.
6. Register in `.claude/settings.json` only after both tests pass.

## Validation Requirements

Before merging:

1. Run hook from a non-toolkit directory: `<undercover-mode>` block injected.
2. Run hook from toolkit directory: no injection.
3. `CLAUDE_REPO_TYPE=internal` from external directory: no injection.
4. `CLAUDE_REPO_TYPE=external` from toolkit directory: injection fires.
5. `CLAUDE_UNDERCOVER_MODE=off`: no injection regardless of directory.
6. Classification cached: second run does not call git (sub-5ms execution after first run).
7. No crash if `git` is not installed (classify-repo.py falls back to path-based check).

## Effort Estimate

**Low** — similar scope to AFK mode (`hooks/afk-mode.py`). The classify-repo.py script is
new but straightforward. Primary implementation risk is getting the classification heuristics
right across varied installation configurations. Estimated 1-2 hours.

## References

- `hooks/afk-mode.py` — reference hook for `UserPromptSubmit` injection pattern
- ADR-143 — AFK mode; cache-stability analysis applies here
- Claude Code source: `undercover.ts` — original implementation reference (~90 lines,
  `USER_TYPE === 'ant'` gate)
- `scripts/classify-repo.py` — new script to be created per this ADR
- `.claude/settings.json` — hook registration reference
