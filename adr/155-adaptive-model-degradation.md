# ADR-155: Adaptive Model Degradation on Rate Limits

## Status

Proposed

## Date

2026-03-31

## Context

Claude Code's `src/services/api/withRetry.ts` implements intelligent rate-limit handling beyond
simple exponential backoff. When a 429 (rate limit) or 529 (overloaded) response arrives with
a `retry-after` header greater than 20 seconds, the retry logic shifts strategy:

1. **Model fallback**: if the session is using a fast/preview model, downgrade to a standard
   model for subsequent calls. This preserves the prompt cache (same model family, different
   speed tier) while reducing per-request cost and potentially hitting a less-saturated model
   endpoint.
2. **Extended patience in unattended sessions**: for unattended/automated sessions, retry up to
   6 hours (not the interactive default of ~5 minutes) with 5-minute maximum backoff intervals
   between attempts, plus keep-alive yields to prevent session timeout.
3. **Keep-alive**: during long waits, emit keep-alive signals to prevent the terminal from
   disconnecting the session.

The design reflects a real operational pattern: when you are rate-limited in an automated
session that started at 11pm, you do not want the session to die — you want it to wait patiently
and resume when the rate limit clears, possibly on a less-burdened model.

### Our Rate Limit Exposure

Our toolkit triggers rate limits in two primary scenarios:

**Parallel agent dispatches**: when the `/do` router dispatches 3-5 subagents simultaneously or
when a research pipeline launches parallel research streams, each agent is making independent API
calls. If these overlap, we hit organizational rate limits quickly. A single parallel dispatch
with 5 agents at claude-opus can saturate the per-minute token limit in seconds.

**Long research sessions**: a research pipeline with 10 subagents over 2 hours consumes a large
fraction of the hourly limit. As the session progresses, subsequent agents hit the limit even
when individual requests are well-sized.

We currently have no rate-limit strategy beyond the default Claude Code retry. We do not:
- Log rate limit events
- Adapt model selection based on rate limit signals
- Extend patience in AFK mode sessions
- Alert the user when a long rate limit wait is beginning

### The Available Hook Signals

`PostToolUse` events fire after each tool execution, including when a tool fails. Rate limit
errors surface in the tool result content as HTTP error responses. The signal is detectable:

```json
{
  "tool_name": "...",
  "tool_result": {
    "is_error": true,
    "content": "Error: 429 Too Many Requests..."
  }
}
```

Or in some cases:
```
anthropic.RateLimitError: 429 {"error": {"type": "rate_limit_error", ...}}
```

The `retry-after` value may appear in the error content if it is surfaced through the SDK.

### What We Can Do from Hook Context

We cannot change the model mid-session from a hook — model selection is a session-level parameter.
What we can do from a hook:

1. **Log the event** to `learning.db` for later analysis of rate limit frequency and timing.
2. **Inject advisory context** suggesting the model reduce parallel work or wait before launching
   additional subagents.
3. **Signal AFK mode patience** — if `CLAUDE_AFK_MODE=always` or AFK mode is active, inject a
   continuation directive that tells the model to wait and retry rather than erroring out.
4. **Suggest model downgrade** in the injected context — the model can change its own behavior
   for subsequent agent dispatches if it is advised to prefer sonnet over opus for non-critical
   subtasks.

The model-downgrade suggestion is the most actionable: the model can choose which model to
request for subagent tasks. If rate-limited on opus, it can dispatch subsequent subagents with
`model: sonnet` in the Task tool parameters (where the tool supports this).

### The learning.db Opportunity

Rate limit events are worth tracking across sessions. A `rate_limit_events` table reveals:
- Which times of day rate limits occur most frequently
- Which task types tend to trigger them (parallel dispatches vs. long sessions)
- Whether AFK mode sessions experience more rate limits (due to running overnight)

This data improves future session planning: schedule parallel dispatches for off-peak hours,
batch sequential rather than parallel for large opus tasks.

## Decision

Create `hooks/rate-limit-advisor.py`, a `PostToolUse` hook that detects rate limit errors,
logs them to `learning.db`, and injects advisory context suggesting adaptive behavior for
subsequent requests.

### Detection

Scan `tool_result.content` for rate limit signatures:

| Pattern | Signal |
|---------|--------|
| `429` in error content | Standard rate limit |
| `529` in error content | Overloaded (treat same as rate limit) |
| `RateLimitError` | SDK-level rate limit exception |
| `rate_limit_error` | Anthropic error type string |
| `overloaded_error` | Anthropic overloaded error |
| `Too Many Requests` | HTTP status text |

On match: log to `learning.db`, inject advisory, set session flag.

### Advisory Injection

When rate limit detected, inject via `additionalContext`:

```
<rate-limit-advisory>
Rate limit encountered. Adapt remaining work:
- Prefer claude-sonnet-4-5 over claude-opus for non-critical subtasks
- Reduce parallel agent dispatches — run sequentially if the task allows
- If in AFK mode: wait and retry rather than failing; the session will resume when limits clear
- Log: rate limit at turn {N}, estimated wait unknown
</rate-limit-advisory>
```

The injection is a one-time signal per rate-limit event (not on every subsequent turn). A session
flag `/tmp/claude-rate-limit-{session_pid}.json` tracks whether the advisory is still "fresh":

```json
{
  "active": true,
  "first_hit_turn": 7,
  "hit_count": 2,
  "last_hit_timestamp": "2026-03-31T14:22:00Z"
}
```

The `UserPromptSubmit` hook clears `active: false` after injecting the advisory once. If another
rate limit occurs in the same session, `active` is set to `true` again.

This requires a second hook (`rate-limit-injector.py`) following the same two-hook pattern as
the continuation nudge (ADR-154). Alternatively, the advisory can be injected directly from
the `PostToolUse` hook if that hook's output is surfaced to the next prompt — check whether
`PostToolUse` `additionalContext` propagates to the subsequent `UserPromptSubmit` context or
only to the current tool result handling.

If `PostToolUse` `additionalContext` reaches the model's next prompt, a single hook suffices.
If not, the two-hook pattern is required. This implementation detail must be confirmed against
the Claude Code hook API documentation before finalizing.

### Schema: `learning.db` Table

```sql
CREATE TABLE IF NOT EXISTS rate_limit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_pid INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    error_type TEXT NOT NULL,
    tool_name TEXT,
    retry_after_seconds INTEGER,
    afk_mode_active INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);
```

`afk_mode_active` is read from the AFK mode session state to correlate rate limits with AFK
sessions vs. interactive sessions.

### AFK Mode Extended Patience

When `afk_mode_active = 1` and a rate limit is detected, inject an additional directive:

```
<rate-limit-patience>
AFK mode is active. Rate limit encountered. Wait for the limit to clear and retry.
Do not exit or report failure — continue the task when API access resumes.
This may take several minutes. Proceed when ready.
</rate-limit-patience>
```

This replicates the "retry up to 6 hours" behavior from `withRetry.ts` at the prompt level:
the model is told to be patient rather than fail. (The actual retry is handled by Claude Code's
built-in retry logic; this injection addresses the model's behavioral posture during the wait.)

### Model Degradation Suggestion

The advisory includes a preference suggestion for subsequent subagent dispatches. The model
cannot be forced to change its own model parameter, but advising it to prefer sonnet for
non-critical work is actionable: agents invoked via Task tool can specify model preferences,
and the research coordinator can choose lighter models for summary/synthesis tasks.

The specific suggestion: when rate-limited on opus, use sonnet for:
- Summary and synthesis tasks (breadth-first research aggregation)
- Simple code generation (< 50 LOC)
- Format conversion (JSON → YAML, markdown restructuring)
- Status checks and health verification

Keep opus for:
- Complex architectural decisions
- Novel algorithm design
- Cross-file refactoring with subtle dependencies
- Security analysis

This guidance is included in the advisory injection.

## Affected Files

| File | Action | Purpose |
|------|--------|---------|
| `hooks/rate-limit-advisor.py` | Create | Detection, logging, and advisory injection |
| `learning.db` | Migrate | Add `rate_limit_events` table |
| `.claude/settings.json` | Modify | Register hook in `PostToolUse` handlers |

## Alternatives Considered

### A. Automatic model switching via settings.json

Use `settings.json` to configure fallback models, letting Claude Code handle the switch
transparently.

**Investigated**: Claude Code does implement model fallback in `withRetry.ts`, but this is
gated on the session's model tier configuration and `retry-after` duration. We cannot easily
configure this from settings.json in a way that replicates the internal logic.

**Approach taken**: advisory injection is the available mechanism from hook context. Automatic
model switching remains a future possibility if Claude Code exposes configuration for it.

### B. Implement a rate-limit-aware task scheduler

Before dispatching parallel agents, check current rate limit state and queue tasks to avoid
triggering the limit.

**Deferred as Phase 2**: requires tracking aggregate token consumption per minute, which is
not directly available in hook context. Phase 1 (reactive: detect and log rate limits after
they occur) is the foundation. Phase 2 (proactive: avoid them before they occur) can build
on the `rate_limit_events` data.

### C. Alert the user immediately when rate-limited

Pop a notification or write to stderr when a rate limit is detected.

**Included indirectly**: the advisory injection is visible to the user in the chat context.
A separate notification mechanism would require OS-level integration (not in hook scope).

### D. Only log; do not inject advisory

Keep the hook minimal — log to `learning.db` but do not inject advisory context.

**Rejected as sole approach**: the value of the advisory injection is that it changes the model's
immediate behavior (prefer lighter models, reduce parallelism). Logging alone provides data but
no reactive benefit. Both logging and injection are included.

## Design Questions Resolved

**Should the advisory be injected on every turn after a rate limit, or only once?**

Once per rate-limit event. The advisory is a signal about current conditions, not a standing
instruction. After the model has adjusted (using sonnet instead of opus, sequentializing agents),
the advisory is stale. Clear it after the first injection.

**Does this interact with the continuation nudge (ADR-154)?**

Both hooks write signal files and use injectors. They are independent — a rate limit and a
premature completion could occur at the same time. Both signals can coexist in `additionalContext`
without conflict. The model handles multiple advisory blocks correctly.

**What if there is no `retry-after` header surfaced in the error?**

The advisory still fires based on the error type detection alone. The `retry_after_seconds`
column in the DB allows null. The advisory does not include a specific wait time if it is unknown.

## Consequences

### Positive

- Rate limit events are logged for session-level and cross-session analysis
- Model gets explicit guidance to adapt (lighter models, sequential dispatch) after rate limiting
- AFK mode sessions receive patience directives to continue rather than fail
- `learning.db` data enables future proactive scheduling (avoid peak rate-limit times)

### Negative / Risks

**Advisory injection breaks prompt cache**: a rate-limit advisory injected mid-session introduces
a change to `additionalContext` that breaks the prompt cache for that turn. However, rate limits
already indicate the session is in a disrupted state — cache stability is less critical than
adaptive behavior at that moment.

**Model may not follow model-degradation suggestion**: the advisory suggests preferring sonnet,
but the model may dispatch subsequent opus agents anyway if its task judgment overrides the
suggestion. The advisory is advisory, not a hard constraint. Over time, if the pattern proves
ineffective, a hard constraint (via operator profile rules) can be introduced.

**Rate limit false positive**: a 429 from a non-rate-limit cause (auth error, quota exceeded for
a different reason) may trigger the advisory. The detection patterns are broad. False positives
are low-cost (an unnecessary advisory injection) and acceptable in Phase 1.

## Implementation Notes

**Session flag file atomicity**: write the JSON flag file atomically (write to `.tmp`, rename)
to prevent race conditions if multiple hooks read simultaneously.

**learning.db migration**: add the `rate_limit_events` table to the same migration script as
the `cache_breaks` table from ADR-152. Both are new tables requiring a schema migration.

**Deploy order** (per established protocol):

1. Create `hooks/rate-limit-advisor.py`.
2. Run DB migration to add `rate_limit_events` table.
3. Sync to `~/.claude/hooks/` via sync script.
4. Verify: simulate a rate-limit error event; confirm DB write and advisory injection.
5. Verify: simulate non-error tool result; confirm no injection.
6. Register in `.claude/settings.json` under `PostToolUse`.

## Validation Requirements

Before merging:

1. Rate limit error (429) detected: DB row written, advisory injected.
2. Overloaded error (529) detected: same behavior as 429.
3. Non-error tool result: no DB write, no injection.
4. AFK mode active + rate limit: both advisory and patience directive injected.
5. Second rate limit in same session: DB row added, advisory re-fires (not suppressed).
6. `rate_limit_events` table created if not present (idempotent migration).
7. Hook exits 0 on all code paths including DB write failure.

## Effort Estimate

**Low** — single hook, pattern detection via regex, SQLite append, static advisory text. The
two-hook pattern (if `PostToolUse` additionalContext does not propagate) adds complexity but
follows the established pattern from ADR-154. Estimated 2 hours including DB migration.

## References

- Claude Code source: `src/services/api/withRetry.ts` — model fallback and extended retry logic
- ADR-154 — continuation nudge; establishes two-hook signal-file pattern
- ADR-143 — AFK mode; patience directive complements AFK posture
- `hooks/error-learner.py` — reference for `learning.db` write pattern
- ADR-152 — cache break detection; rate limit advisories are a known cache-break source
- `.claude/settings.json` — registration under `PostToolUse`
