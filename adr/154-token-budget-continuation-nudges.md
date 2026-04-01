# ADR-154: Token Budget Continuation Nudges

## Status

Proposed

## Date

2026-03-31

## Context

Claude Code's `src/query/tokenBudget.ts` implements a per-turn token budget tracking system.
The `checkTokenBudget()` function monitors cumulative token consumption across a session. When
the system detects that the model is consuming tokens at a rate that suggests diminishing output
quality — short responses, summary language, hedging phrases — it injects a continuation nudge
message into the context. The feature gate is `TOKEN_BUDGET` in `query.ts`.

The nudge message instructs the model that budget remains and it should continue with substantive
work rather than wrapping up. This counteracts a known model behavior: under certain context
conditions (very long sessions, many prior tool calls, large accumulated context), the model
will start producing summary-style output and offering "let me know if you need more" closers
rather than continuing to execute the task.

### The Premature Completion Problem in Our Toolkit

Our agents — particularly research agents, code review agents, and multi-step implementers —
exhibit the same pattern Claude Code's `tokenBudget.ts` was designed to address. The model
reaches a certain point in a long session and begins wrapping up work that is not actually
complete:

**Research agents**: produce a 3-paragraph summary when the task required a 10-section report.
Conclude with "I hope this overview is helpful" rather than continuing to the next section.

**Code review agents**: complete 3 of 8 files and offer "I've covered the key areas — let me
know if you'd like me to continue." The task was a full-repo review.

**Implementation agents**: write a partial implementation and note "You'll need to add tests and
error handling" rather than writing them.

The pattern has a consistent signature:
- Response length drops significantly compared to prior turns
- Summary/closing language appears ("in summary", "to recap", "let me know if")
- The model offers to continue rather than continuing
- The task objectives are not yet met

### Why This Happens

The model's training creates a tendency toward graceful completion. When context is long and
many tokens have been consumed, the model interprets this as a signal to "wind down." This is
appropriate in conversational contexts (where the user may indeed want a summary) but
counterproductive in agentic task execution (where the task is the objective, not the token count).

Claude Code's token budget nudge addresses this by injecting an explicit signal: "you have budget
remaining, keep going." Our toolkit has no equivalent.

### Detection Approach

We cannot directly observe the model's internal token consumption from a `PostToolUse` hook.
What we can observe is the model's output patterns in tool results and in the conversation flow.

Two complementary detection signals:

**Signal 1: Short tool-result output with closing language**
A `PostToolUse` event where the tool result contains less than a threshold word count AND
contains closing language patterns. The closing language patterns are the most reliable signal:

| Pattern | Signal |
|---------|--------|
| `let me know if you need` | Offering to continue |
| `I hope this (overview\|summary\|analysis)` | Closing language |
| `feel free to ask` | Invitation to re-prompt |
| `in summary,` / `to summarize,` / `to recap,` | Summary framing |
| `would you like me to (continue\|proceed\|go further)` | Explicit wrap-up offer |
| `I've covered the (main\|key\|primary)` | Partial-completion framing |

**Signal 2: Response word count drop**
If the current response is < 40% of the rolling average of the prior 3 responses, the model
may be compressing. This is a weaker signal (valid short responses exist) and should be combined
with Signal 1 for higher confidence.

The detection runs in a `PostToolUse` hook on the model's response text, which is available
in the tool result for text-producing tools.

### The Nudge Injection

When the hook detects a premature completion pattern, it injects into the next turn's
`additionalContext` (via `UserPromptSubmit` hook, reading a signal file set by `PostToolUse`):

```
<continuation-nudge>
You have budget remaining. Continue with the next step.
If the task is not yet complete, proceed without asking for confirmation.
Do not summarize or wrap up unless all task objectives are met.
</continuation-nudge>
```

This is a single-turn injection — it fires once, not persistently. After the model has been
nudged, the injection is cleared. If the model responds with substantive work, the pattern does
not re-fire. If it responds with another wrap-up attempt, the hook may fire again (up to a
configurable maximum of 3 nudges per task).

### Two-Hook Architecture

This feature requires two hooks working in concert:

- **`PostToolUse` hook (`continuation-nudge-detector.py`)**: detects wrap-up patterns in model
  output, writes a signal file if detected
- **`UserPromptSubmit` hook (`continuation-nudge-injector.py`)**: reads the signal file; if set,
  injects the nudge and clears the signal file

The signal file is `/tmp/claude-nudge-pending-{session_pid}.json`:

```json
{
  "pending": true,
  "trigger_pattern": "let me know if you need",
  "trigger_turn": 12,
  "nudge_count": 1
}
```

The `UserPromptSubmit` hook reads this file on each turn. If `pending: true`, inject the nudge
and set `pending: false`. If `pending: false` or file does not exist, no injection.

Alternatively, implement as a single hook that both detects and injects — but the detection
happens post-tool-use and the injection must happen pre-prompt. The signal file decoupling is
necessary because `PostToolUse` and `UserPromptSubmit` are separate events.

## Decision

Implement token budget continuation nudges as a two-hook system:
1. **`hooks/continuation-nudge-detector.py`** — `PostToolUse` hook detecting wrap-up patterns
2. **`hooks/continuation-nudge-injector.py`** — `UserPromptSubmit` hook reading signal and
   injecting nudge

The implementation targets research agents and review agents as the primary beneficiaries.

### Nudge Limit

Maximum 3 nudges per session (configurable via `CLAUDE_MAX_NUDGES`, default 3). After the limit
is reached, the injector stops firing even if the detector continues to flag patterns. This
prevents nudge loops on tasks that genuinely require follow-up questions.

The limit resets per-task if the toolkit implements a task boundary signal. In Phase 1, it resets
never (lifetime per session). Phase 2 can add task-boundary reset when task tracking is
implemented.

### Confidence Threshold

The detector only sets the signal file when confidence is high:

- **High confidence (fire)**: closing language pattern match + response < 60% of rolling average
- **Medium confidence (skip)**: closing language pattern match only, response not short
- **Low confidence (skip)**: only length drop, no closing language

In Phase 1, only fire on high confidence. False positives (nudging a model that was correctly
summarizing) are more disruptive than false negatives (not nudging a model that stopped early).

### Agent Profile Integration

The research agent profile and review agent profiles should have an explicit directive:

```
Complete all task objectives before summarizing. Do not offer to continue — continue.
```

The nudge hook reinforces this directive when the model drifts. The combination of upfront
directive + reactive nudge provides defense in depth.

## Affected Files

| File | Action | Purpose |
|------|--------|---------|
| `hooks/continuation-nudge-detector.py` | Create | PostToolUse pattern detection |
| `hooks/continuation-nudge-injector.py` | Create | UserPromptSubmit injection on signal |
| `.claude/settings.json` | Modify | Register both hooks |

## Alternatives Considered

### A. Single hook that detects and injects simultaneously

Combine detection and injection in a `PostToolUse` hook that modifies the next user message
directly rather than via a signal file.

**Rejected because**: the hook API does not allow a `PostToolUse` hook to inject content into
the next user prompt. The `UserPromptSubmit` injection mechanism is the correct channel for
pre-prompt context. The two-hook architecture is required by the API design.

### B. Modify agent system prompts instead of using hooks

Add "complete all objectives before summarizing" to every agent's system prompt.

**Included as defense-in-depth** (not instead of the hook). The directive is useful but
insufficient alone — the model can still drift on very long sessions. The reactive hook catches
drift that the upfront directive does not prevent.

### C. Track token counts directly via API response headers

Claude API responses include `X-Cache-Read-Input-Tokens` headers. Parse these to implement
genuine token budget tracking.

**Rejected because**: hook API does not expose HTTP response headers. The pattern-detection
approach is the only mechanism available in hook context.

### D. Use a more aggressive nudge (inject task description again)

Re-inject the full task description as the nudge rather than a brief continuation directive.

**Deferred**: re-injecting the full task is more effective but risks destabilizing the prompt
cache (the task description is not static text). Phase 1 uses a static nudge. Phase 2 can
experiment with task-description re-injection if Pattern 1 is insufficient.

## Design Questions Resolved

**Should the nudge fire if the model has actually completed the task?**

The hook detects wrap-up language, not task completion. If the model correctly summarizes
because the task is done, the "high confidence" threshold (requiring both closing language AND
a response length drop) should not fire — completed work tends to be substantive in length even
when summarizing. The length floor provides the distinction.

**Does the nudge interact with AFK mode?**

Complementary. AFK mode tells the model to work autonomously; the nudge tells it to keep going.
Both can be active simultaneously with no conflict.

**What is the maximum nudge injection size?**

The nudge text above is approximately 40 tokens. Cache-stable (static text, identical each time
it fires). Well within the acceptable overhead range.

## Consequences

### Positive

- Research and review agents complete their full task scope rather than stopping early
- Users spend less time re-prompting with "please continue" or "please finish the review"
- Complements AFK mode: autonomous sessions are less likely to stall on incomplete work
- Low false-positive risk due to high-confidence threshold requiring both linguistic and length signals

### Negative / Risks

**Nudging a correct summary**: if the model correctly summarizes at the end of a completed task,
the detector may misfire. The high-confidence threshold mitigates this but does not eliminate it.

Mitigation: expose `CLAUDE_MAX_NUDGES=0` as a per-session disable for users who find the
nudging intrusive.

**Nudge loop**: the model produces wrap-up language, gets nudged, produces more wrap-up language,
gets nudged again. The 3-nudge limit prevents infinite loops.

**Pattern match on legitimate output**: a report that genuinely contains a "In summary" section
header may trigger the detector. Require the closing pattern to appear near the end of the
response (last 20% of content) to reduce false positives on mid-response section headers.

## Implementation Notes

**Rolling average calculation**: maintain a JSON state file with the last 3 response word counts.
Update on each `PostToolUse` event. Use this for the length drop signal.

**Closing language scan position**: scan only the last 20% of the response text for closing
language patterns. A report section that says "In summary" at the start of a legitimate summary
section should not trigger; the same phrase at the very end of a response after all work is
described should.

**Deploy order** (per established protocol):

1. Create both hook files in repo.
2. Sync to `~/.claude/hooks/` via sync script.
3. Verify detector: simulate a wrap-up tool result, confirm signal file is created.
4. Verify injector: with signal file present, confirm nudge injection fires and clears signal.
5. Verify injector: with no signal file, confirm no injection.
6. Register both hooks in `.claude/settings.json`.

## Validation Requirements

Before merging:

1. Detector fires on high-confidence wrap-up pattern (closing language + short response).
2. Detector does not fire on medium-confidence (closing language only, normal length).
3. Injector fires when signal file is present, clears signal after injection.
4. Injector does not fire when signal file is absent.
5. Nudge limit (3) is respected — no injection after limit reached.
6. Both hooks exit 0 on malformed input.
7. Each hook executes in under 10ms.

## Effort Estimate

**Low** — two lightweight hooks with file-based coordination. Pattern matching is straightforward
regex. The primary design complexity (two-hook architecture) is already resolved. Estimated 2-3
hours including tuning the detection patterns against real agent outputs.

## References

- Claude Code source: `src/query/tokenBudget.ts` — original implementation
- Claude Code source: `query.ts` — `TOKEN_BUDGET` feature gate
- `hooks/afk-mode.py` — reference for `UserPromptSubmit` injection pattern
- ADR-143 — AFK mode; the autonomous posture this hook reinforces
- ADR-141 — cache stability; nudge injection must be cache-stable (static text)
- `.claude/settings.json` — registration reference; detector in `PostToolUse`, injector in
  `UserPromptSubmit`
