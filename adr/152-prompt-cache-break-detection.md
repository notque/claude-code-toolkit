# ADR-152: Prompt Cache Break Detection

## Status

Proposed

## Date

2026-03-31

## Context

Claude Code's `src/services/api/promptCacheBreakDetection.ts` implements explicit tracking of
prompt cache stability. Before each API call it records pre-call state: system prompt hash, tool
schema hashes, model identifier, beta header set, and cache TTL configuration. After the call
completes it compares the actual `cache_read_input_tokens` against the expected value. When
`cache_read_tokens` drops more than 5% relative to the prior call, with a minimum token floor
of 2,000 tokens, it records a cache break event with an explanation of which component changed.

### Why Cache Breaks Are Expensive

The Anthropic API caches the system prompt prefix. When the cache is warm (cache hit), input
tokens cost approximately 1/10 of normal — cache reads are charged at $0.30/Mtok vs. $3.00/Mtok
for a full cache miss on claude-sonnet. For sessions with 10KB+ system prompts, a cache miss
costs ~$0.0015 more per turn. Across a long session with 100 turns, this is $0.15 in additional
cost from a single cache break. Multiplied across developer sessions, the cost accumulates.

More practically: cache hits make sessions feel faster. The API returns faster when it reads from
cache vs. reprocessing the full system prompt.

### Our Hook Injection Problem

Our toolkit injects approximately 20KB of context per turn across multiple `UserPromptSubmit`
hooks:

| Hook | Approximate tokens | Stability |
|------|--------------------|-----------|
| `userprompt-datetime-inject.py` | ~10 tokens | Stable (date only changes once per day) |
| `afk-mode.py` | ~150 tokens | Stable (static per session) |
| `instruction-reminder.py` | ~200 tokens | Stable (static content) |
| `auto-plan-detector.py` | ~50 tokens | Varies (depends on task detection) |
| Future hooks | Unknown | Unknown |

Any hook whose output changes between turns breaks the prompt cache for that turn. Even a
single-character change in `additionalContext` causes the cache fingerprint to shift, invalidating
the cached prefix and forcing a full recompute.

We currently have no visibility into when cache breaks happen, which hook caused them, or how
frequently they occur. We are flying blind on a cost and performance metric that directly affects
the value of our hook investment.

### What Claude Code Records

Claude Code's `promptCacheBreakDetection.ts` captures:

- **Pre-call state**: `systemPromptHash`, `toolSchemaHash`, `model`, `betaHeaders`,
  `cacheTtl`
- **Post-call comparison**: actual `cache_read_input_tokens` from API response
- **Break detection**: if `cache_read_tokens < (prior_cache_read_tokens * 0.95)` and
  `prior_cache_read_tokens > 2000`, record a break
- **Break explanation**: which hash changed (system prompt vs. tool schema vs. model)

The 5% threshold and 2,000-token floor are calibration values — small fluctuations below the
floor are noise; a 5%+ drop with large context is a genuine break.

### What We Can Observe from Hooks

Claude Code's hook API exposes API response data in `PostToolUse` events when the tool is a
model-calling tool. However, we cannot directly observe `cache_read_input_tokens` from a
`PostToolUse` event — that data is in the API response, not the tool result.

The alternative is to observe the injected content itself. Each `UserPromptSubmit` hook's output
is the potential source of a cache break. If we record what each hook injected on the prior turn
and compare it to this turn, we can detect hook-level cache instability even without API response
data.

This is an approximation of Claude Code's approach: instead of comparing `cache_read_tokens`
(which requires API response access), we compare injection content hashes. If injection content
is identical turn-over-turn, the cache should be stable (assuming no other changes). If it
differs, we know which hook's output changed.

### The learning.db Opportunity

We already write to `learning.db` (SQLite) from multiple hooks. A `cache_breaks` table can
accumulate per-session break events: timestamp, session_id, hook_name, prior_hash, new_hash,
estimated_break_cost_tokens. This gives us the analysis capability to identify which hooks are
cache-unstable and prioritize fixing them.

## Decision

Create `hooks/cache-break-detector.py`, a `UserPromptSubmit` hook that tracks injection content
hashes across turns and logs changes to `learning.db`. When a hook output changes between turns,
record a break event. Periodically report break frequency per hook to surface the most expensive
instability sources.

### Detection Approach

**Phase 1: Content hashing**

Each `UserPromptSubmit` hook produces `additionalContext`. The cache-break detector runs
**last** among `UserPromptSubmit` hooks (via `settings.json` ordering) and receives the
aggregated context at that point. It hashes the full `additionalContext` payload and compares
against the stored hash from the prior turn.

Wait — the hook API does not give a hook access to other hooks' outputs. Each hook runs
independently and produces its own `additionalContext`. There is no aggregated view available
to a hook.

**Revised approach: Per-hook output files**

Each monitored hook writes its output hash to a temp file at execution time:
`/tmp/claude-hook-{hook_name}-{session_pid}.hash`

The cache-break detector reads all known hook output files, compares to prior-turn stored hashes
(persisted in `/tmp/claude-cache-state-{session_pid}.json`), logs any changes to `learning.db`,
and writes updated hashes for the next turn.

This requires each monitored hook to write its hash. However, modifying every existing hook is
invasive. A lighter approach: the cache-break detector itself hashes its own context view and
logs to `learning.db` as a baseline. The per-hook hash approach can be added incrementally as
hooks are updated.

**Phase 1 (simpler)**: Cache-break detector hashes its own injected content per turn. Since it
is the last `UserPromptSubmit` hook, its injection is a function of session-stable content only.
If *its own* output changes between turns, that signals something in the pipeline changed.

**Phase 2 (full)**: Each hook writes its output hash to a temp file. The cache-break detector
reads all files and reports per-hook stability.

Ship Phase 1 first. Phase 2 is a follow-on.

### Schema: `learning.db` Table

```sql
CREATE TABLE IF NOT EXISTS cache_breaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_pid INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    hook_name TEXT NOT NULL DEFAULT 'aggregate',
    prior_hash TEXT,
    new_hash TEXT NOT NULL,
    estimated_tokens_affected INTEGER,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);
```

The `estimated_tokens_affected` column is populated when token counts are derivable from the
changed content (content length × 0.25 tokens/char as approximation).

### Break Threshold

Log a break event when the hash differs from the prior turn. Do not attempt to replicate Claude
Code's 5% token-drop threshold — we do not have API response token counts. Hash equality is a
binary signal: either the injected content is identical or it is not.

The threshold for *alerting* (injecting a warning into the next prompt) is configurable:
`CLAUDE_CACHE_BREAK_WARN_THRESHOLD` (default: 3 breaks in 5 turns). Below this, breaks are
silently logged. Above this, the hook injects a brief advisory into `additionalContext`.

### Advisory Injection

When the break threshold is exceeded, inject:

```
<cache-stability-advisory>
Prompt cache breaks detected (3 in last 5 turns). Hook injection is unstable.
Check learning.db cache_breaks table for details.
</cache-stability-advisory>
```

This is advisory only — it does not change model behavior, just gives the model awareness that
context injection is unstable, which may help it understand why tool results seem inconsistent.

### Session-Scoped State File

`/tmp/claude-cache-state-{session_pid}.json`:

```json
{
  "session_pid": 12345,
  "turn_number": 7,
  "prior_hash": "sha256:abc123",
  "break_count_recent": 2,
  "last_break_turn": 5
}
```

Written atomically (write to `.tmp`, rename to final path) to avoid partial-read races.

## Affected Files

| File | Action | Purpose |
|------|--------|---------|
| `hooks/cache-break-detector.py` | Create | Hash tracking and break logging |
| `learning.db` | Migrate | Add `cache_breaks` table |
| `.claude/settings.json` | Modify | Register hook last in `UserPromptSubmit` handlers |

## Alternatives Considered

### A. Parse Claude Code logs for cache token data

Claude Code may write cache hit/miss data to its own log files. Parsing those logs would give
us the actual API-level token data rather than an approximation.

**Rejected because**: Claude Code log format is undocumented and changes between versions. Parsing
internal logs creates a fragile dependency on undocumented behavior. Our hash approximation is
sufficient for the primary use case (identifying unstable hooks).

### B. Instrument API calls directly via a proxy

Route our API calls through a local proxy that logs request/response data including cache token
counts.

**Rejected because**: this requires non-trivial infrastructure changes and is outside the scope
of the hook API. The hash approximation provides 80% of the value with none of the infrastructure
complexity.

### C. Store hashes in SQLite from the start (skip temp files)

Use `learning.db` for all state rather than temp files, eliminating the `/tmp` state file.

**Deferred**: SQLite writes from hooks require locking coordination if multiple hooks write
concurrently. Temp files are simpler for session-scoped state. The `learning.db` write (for break
events) is append-only with no contention.

### D. Only track the instruction-reminder hook (known cache-stable baseline)

Rather than tracking all hooks, only monitor `instruction-reminder.py` since it is the largest
injection and has a known cache-stability design (ADR-142).

**Rejected as sole approach because**: the value of cache break detection is identifying
*unexpected* instability, which by definition comes from hooks we have not analyzed yet. Monitoring
only known-stable hooks provides no new information.

## Design Questions Resolved

**Should the hook modify its own injection based on detected breaks?**

No in Phase 1. The hook logs and optionally injects an advisory. Behavioral modification (e.g.,
suppressing unstable hook output) is a Phase 2 consideration after we have data on break patterns.

**What is the right session_pid approach?**

`os.getppid()` — the parent process is the Claude Code session process, which persists for the
session lifetime. This is more reliable than `os.getpid()` which changes each hook invocation.

**Does this hook itself need to be cache-stable?**

Yes. The hook's advisory injection (`<cache-stability-advisory>`) must only fire when the break
threshold is exceeded, not on every turn. When threshold is not exceeded, the hook produces no
injection — zero tokens added, perfectly cache-stable.

## Consequences

### Positive

- First-time visibility into prompt cache break frequency and source
- `learning.db` accumulates data for analysis across sessions: which hooks are most unstable,
  which session types have the most breaks
- Advisory injection gives the model awareness of injection instability without requiring human
  monitoring
- Low implementation cost (single hook + one table migration)

### Negative / Risks

**False stability signal**: if two different hook contents happen to produce the same hash
(hash collision), a genuine cache break would go undetected. SHA-256 collision probability is
negligible for our use case.

**Per-turn temp file I/O**: reading and writing a JSON state file on every turn adds latency.
The file is small (< 500 bytes) and the I/O is sequential. Expected overhead: under 2ms.

**Chicken-and-egg with Phase 2**: the full per-hook visibility requires modifying every hook to
write its output hash. This is invasive and will be done incrementally. Phase 1 provides
aggregate visibility only; per-hook attribution comes later.

## Implementation Notes

**Deploy order** (per established protocol):

1. Create `hooks/cache-break-detector.py` in repo.
2. Run migration to add `cache_breaks` table to `learning.db`.
3. Sync to `~/.claude/hooks/` via `python3 scripts/sync-to-user-claude.py`.
4. Verify: `python3 ~/.claude/hooks/cache-break-detector.py < /dev/null` exits 0 with no injection.
5. Register last in `UserPromptSubmit` section of `.claude/settings.json`.

**Registration position**: this hook must run **last** among `UserPromptSubmit` hooks so it
captures the final aggregated state of all prior hook injections for the turn.

## Validation Requirements

Before merging:

1. First turn: no prior hash exists, no break logged, state file created with current hash.
2. Second turn with identical injection context: no break logged.
3. Third turn with modified injection (simulate by changing an env var that affects another hook):
   break logged to `learning.db`.
4. After 3 breaks in 5 turns: advisory injection fires.
5. After 2 more stable turns: advisory does not fire (count resets or decays).
6. Execution time: under 5ms for state file read + write + SQLite insert.
7. Crash safety: corrupted state file causes hook to start fresh (no crash, no injection).

## Effort Estimate

**Low** — single hook, one SQLite table migration, no external dependencies. Hash comparison and
file I/O are straightforward. Phase 1 can ship in under 2 hours. Phase 2 (per-hook attribution)
is a follow-on.

## References

- `hooks/lib/hook_utils.py` — injection protocol
- ADR-141 — prompt cache stability analysis; establishes why cache breaks matter
- ADR-142 — instruction-reminder optimization; first explicit cache-stability analysis in toolkit
- ADR-143 — AFK mode; example of a cache-stable hook with static injection
- Claude Code source: `src/services/api/promptCacheBreakDetection.ts` — original implementation
- `hooks/error-learner.py` — reference for `learning.db` write pattern
- `.claude/settings.json` — hook registration; this hook must be last in `UserPromptSubmit`
