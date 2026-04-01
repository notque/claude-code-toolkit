# ADR-156: Two-Stage Auto-Approval Classifier

## Status

Proposed

## Date

2026-03-31

## Context

Claude Code's `yoloClassifier.ts` implements a two-stage AI-powered classification system for
auto-approving tool actions without human confirmation. The classifier is designed for "YOLO
mode" — sessions where the user wants maximum autonomy with minimal interruptions.

### How the Two-Stage Classifier Works

**Stage 1: Fast classification** (64 output tokens, stop sequences `["yes", "no"]`)
- The classifier receives a transcript of recent messages and the proposed tool action
- It produces a binary yes/no in under 64 tokens
- If the answer is "yes" (safe to approve), the action proceeds immediately
- If the answer is "no" (needs review), Stage 2 fires
- Stop sequences ensure the response terminates as soon as the binary answer is produced,
  minimizing latency for the common case (most actions are safe)

**Stage 2: Chain-of-thought review** (up to 4,096 output tokens)
- Only fires when Stage 1 blocks (says "no")
- Produces a full reasoning trace explaining why the action is risky
- Based on the reasoning, either approves with caveats or confirms the block
- The detailed reasoning is available for logging and user explanation

**Response caching**: classifier responses are cached for 1 hour by the combination of
(action_type, action_parameters_hash). Identical actions within the cache window skip both
stages and use the cached decision. This is important for repeated tool patterns in a session.

**Prompt injection protection**: user messages are **excluded** from the classifier transcript.
Only system context and tool call history are included. This prevents an attacker from
embedding a string like "approve all actions" in a user message that the classifier would
then follow.

### Our Current Permission System: Binary Profiles

Our operator profile system (`personal`, `work`, `ci`, `production`) applies binary gates:

| Profile | Behavior |
|---------|----------|
| `personal` | Full autonomy; no approval required |
| `work` | Restricted to repo-scoped writes; approval for external actions |
| `ci` | Read-only + specific approved write paths |
| `production` | Requires explicit approval for any write |

This works for coarse-grained control but breaks down in practice:

1. **`personal` profile is too permissive**: a typo in an automated task shouldn't delete a
   production config without a sanity check.
2. **`work` profile blocks useful automation**: `work` blocks git operations on files outside
   the current repo, but many legitimate tasks involve multiple repos.
3. **The gates are static**: a rule that was appropriate when the profile was created may not
   fit the current task context.
4. **No gradation**: an action is either approved or blocked, with no "approve with warning"
   or "approve once but alert me" semantics.

The two-stage classifier pattern from `yoloClassifier.ts` addresses all four problems by
replacing static rules with dynamic AI judgment.

### The Permission Decision Problem

The core problem: at any given tool call, the system must decide:

1. Is this action safe to proceed automatically? (approve)
2. Does this action need human review? (block + ask)
3. Is this action categorically prohibited? (hard block, no review)

Our current system handles (3) via hook-level hard blocks (branch-safety, plan-gate). It handles
(1) and (2) via static profile rules. The two-stage classifier would handle (1) and (2) dynamically.

### What We Can Implement Without Source Access

We cannot import `yoloClassifier.ts` — it is Claude Code's internal code. But we can replicate
the pattern using the Claude API directly from a hook, following the same two-stage architecture.

The key design elements we can replicate:

- **Stage 1 prompt**: short, binary, stop-sequence-terminated
- **Stage 2 prompt**: full reasoning chain only when Stage 1 blocks
- **Response caching**: cache by (tool_name, parameters_hash) with 1-hour TTL
- **Transcript exclusion**: exclude user messages from classifier input (prevent prompt injection)
- **Operator profile integration**: use operator profile as context for the classifier

## Decision

Implement a two-stage auto-approval classifier as a `PreToolUse` hook that evaluates tool
actions against current context and decides whether to proceed, block, or escalate. Phase 1
implements the classification pattern; Phase 2 integrates with operator profiles.

### Architecture

**`hooks/auto-approval-classifier.py`** — `PreToolUse` hook implementing two-stage classification.

**Stage 1 call**:

```
System: You are a safety classifier for an AI coding assistant.
Classify the proposed tool action as safe (auto-approve) or unsafe (requires review).
Response: answer with only "yes" (safe) or "no" (requires review).

Context: [tool_name] [parameters_summary]
Operator profile: [profile]
Recent tool history: [last 3 tool calls, no user messages]

Is this action safe to auto-approve?
```

Response: `"yes"` or `"no"` (stop sequences: `["yes", "no"]`). Max tokens: 64.

**Stage 2 call** (only when Stage 1 = "no"):

```
System: You are a safety reviewer for an AI coding assistant.
The Stage 1 classifier flagged this action for review. Explain why, then decide:
APPROVE (with explanation), BLOCK (with reason), or ESCALATE (requires human).

[same context as Stage 1]

Provide your reasoning, then your decision on the last line: APPROVE / BLOCK / ESCALATE
```

Max tokens: 512 (not 4096 as in the original — our use case needs fast decisions, not full
essays). Response parsed for final line decision.

### Caching

Cache key: `sha256(tool_name + json.dumps(params, sort_keys=True))`.
Cache store: `/tmp/claude-approval-cache-{session_pid}.json`.
TTL: 1 hour (configurable via `CLAUDE_APPROVAL_CACHE_TTL`, default 3600).

Cache hit returns the prior decision without making any API calls. This is critical for
performance: repeated file writes, bash commands, and edit operations within the same session
should not each trigger a new classifier call.

### Operator Profile Integration

The classifier receives the current operator profile as context:

- `personal`: Stage 1 threshold is lenient (model is instructed that this is a trusted personal
  environment)
- `work`: Stage 1 threshold is standard
- `ci`: Stage 1 threshold is strict (Stage 1 "no" blocks immediately without Stage 2)
- `production`: hard block for all write operations regardless of classifier output

The `production` hard block bypasses the classifier entirely — it is a non-negotiable gate.

### Hard Block Pass-Through

Actions that are already hard-blocked by `branch-safety` or `plan-gate` hooks should not reach
the classifier. The classifier is for the **gray zone**: actions that are potentially safe but
context-dependent. It is not a replacement for hard blocks.

Registration order in `settings.json` must place hard-block hooks before the classifier hook.

### Exclusion of User Messages from Classifier Transcript

Mirroring `yoloClassifier.ts`, the classifier transcript includes only:
- The current tool call (name + parameters)
- The last 3 tool results (what the model did recently)
- The operator profile
- The system context (from session state)

User messages are explicitly excluded. This prevents prompt injection via user input:
a malicious or mistaken user message saying "ignore all safety checks" should not influence
the classifier. The classifier sees only tool-level context.

### Failure Mode: Default to Approve

If the classifier call fails (API error, timeout, malformed response), the hook defaults to
approving the action. This matches `yoloClassifier.ts`'s failure mode (don't block work on
classifier failure) and ensures the classifier never becomes a reliability bottleneck.

An exception: if the action is a high-risk destructive operation (matches a pattern like
`rm -rf`, `DROP TABLE`, `git push --force`), default to BLOCK on classifier failure. These
operations are too high-risk to approve-by-default.

## Affected Files

| File | Action | Purpose |
|------|--------|---------|
| `hooks/auto-approval-classifier.py` | Create | Two-stage classifier hook |
| `scripts/approval-cache.py` | Create | Cache management utility |
| `.claude/settings.json` | Modify | Register hook in `PreToolUse`, after hard-block hooks |

## Alternatives Considered

### A. Extend static profile rules rather than adding AI judgment

Add more granular rules to the existing profile system (e.g., allow multi-repo git operations
in `work` profile for specific remote patterns).

**Insufficient at scale**: the number of context-dependent edge cases grows faster than static
rules can cover. AI judgment is more adaptive. Static rules handle the known cases; AI judgment
handles the unknown.

### B. Use a smaller/faster model for Stage 1 (Haiku)

Use `claude-haiku-4-5` for Stage 1 to minimize latency.

**Worth exploring in implementation**: Haiku is significantly faster and cheaper for binary
classification. The tradeoff is accuracy — Haiku may approve actions that Sonnet would flag.
Start with Sonnet for Stage 1 and measure the latency impact. If it is acceptable (< 500ms),
stay with Sonnet. If latency is a problem, switch Stage 1 to Haiku and Stage 2 to Sonnet.

### C. Cache decisions across sessions (not just within session)

Use `learning.db` to cache approval decisions across sessions, not just within a session.

**Deferred**: cross-session caching requires cache invalidation when context changes (new files,
changed operator profile, new rules). Session-scoped caching is safer for Phase 1. Cross-session
caching can be added in Phase 2 with appropriate invalidation logic.

### D. Always require Stage 2 for any "no" decision

Never auto-block based on Stage 1 alone — always run Stage 2 for reasoning before blocking.

**Rejected for `ci` profile**: in CI/CD environments, the overhead of Stage 2 calls for blocked
actions can significantly slow automated pipelines. In `ci` profile, Stage 1 "no" is a hard
block. In `work` and `personal` profiles, Stage 2 fires for explanation and possible override.

## Design Questions Resolved

**Should the classifier hook fail-open or fail-closed?**

Fail-open (approve) for most operations; fail-closed (block) for high-risk patterns. This
matches `yoloClassifier.ts`'s design and ensures the classifier never becomes a reliability
bottleneck for normal workflow.

**Does the classifier fire on every tool call?**

With caching, the effective rate is much lower. Common repeated operations (file reads, small
edits, bash commands in the same working directory) will hit the cache. New/unusual operations
miss the cache and trigger the classifier. The cache is the primary performance mechanism.

**What is the latency budget for Stage 1?**

Target: under 300ms for a cache hit (file read), under 2 seconds for a cache miss Stage 1 call.
Stage 2 is acceptable up to 5 seconds given that it only fires on flagged actions. Measure
against this budget during implementation.

**Should the user see Stage 2 reasoning?**

Yes, via `additionalContext` injection. When Stage 2 fires and produces reasoning, inject a
summary into the next turn's context so the model understands why an action was blocked or
conditionally approved. The user also sees this in the chat window.

## Consequences

### Positive

- Dynamic approval decisions based on context rather than static profile rules
- Removes friction for clearly safe operations even in strict profiles
- Stage 2 reasoning gives the model (and user) an explanation for blocks
- Prompt injection protection built in via transcript filtering
- Cache makes repeated operations fast after the first classification

### Negative / Risks

**Classifier latency on cache misses**: Stage 1 adds 1-2 seconds; Stage 2 adds another 2-5
seconds for flagged operations. For fast-paced interactive sessions, this may feel sluggish.

Mitigation: the cache handles repeated operations. New/unusual operations that trigger the
classifier are naturally infrequent. Haiku for Stage 1 is a further mitigation if needed.

**Classification errors**: the AI classifier can approve things it should block, or block things
it should approve. No classifier is perfect.

Mitigation: hard-block hooks for destructive operations remain in place upstream. The classifier
handles the gray zone, not the clear-red zone.

**Cost of classifier calls**: additional API calls for the classifier. At ~64 tokens for Stage 1
and ~512 for Stage 2, the cost per decision is modest. With caching, the effective cost per
session is bounded.

**Complexity**: two-stage system with caching is more complex than static profile rules.
Debugging incorrect approval decisions requires examining the classifier call and cache state.

Mitigation: log all classifier decisions to `learning.db` for post-hoc analysis.

## Implementation Notes

**Transcript preparation** for classifier: extract `tool_name`, `tool_input` (parameters
summary, truncated to 500 chars), and the last 3 tool results from the `PostToolUse` event
stream (stored in session state file). Do not include any user message text.

**Stage 1 prompt engineering**: the prompt must produce exactly "yes" or "no" as stop-sequence-
terminated responses. Test against the model before shipping — some phrasings produce "yes,
..." before the stop sequence fires.

**Deploy order** (per established protocol):

1. Create `hooks/auto-approval-classifier.py`.
2. Create `scripts/approval-cache.py`.
3. Sync to `~/.claude/hooks/` and `~/.claude/scripts/` via sync script.
4. Verify: simulate a safe tool call, confirm Stage 1 "yes", action approved.
5. Verify: simulate a risky tool call, confirm Stage 1 "no", Stage 2 fires.
6. Verify: repeat same tool call, confirm cache hit (no API call).
7. Register in `.claude/settings.json` under `PreToolUse`, after branch-safety and plan-gate.

## Validation Requirements

Before merging:

1. Stage 1 "yes" → action approved, no Stage 2 call.
2. Stage 1 "no" → Stage 2 fires, reasoning produced, decision returned.
3. Cache hit → no API calls, prior decision returned.
4. API failure (Stage 1) → default to approve for standard operations, block for high-risk.
5. High-risk pattern (`rm -rf`) + API failure → block regardless.
6. User messages excluded from classifier transcript (verified by inspection).
7. `production` profile → bypass classifier, hard block on all writes.
8. Response time: cache hit < 5ms, Stage 1 miss < 2000ms, Stage 1 + Stage 2 < 8000ms.

## Effort Estimate

**Medium** — the most complex hook in this ADR set. Requires: Stage 1 and Stage 2 prompt
engineering, caching implementation, operator profile integration, transcript preparation (user
message exclusion), and decision logging. The two-stage architecture is well-defined but each
stage needs independent testing. Estimated 4-6 hours.

## References

- Claude Code source: `yoloClassifier.ts` — original two-stage classifier implementation
- ADR-143 — AFK mode; autonomy posture that the classifier complements
- `hooks/branch-safety.py` — upstream hard-block hook; must register before classifier
- `hooks/plan-gate.py` — upstream hard-block hook; must register before classifier
- `hooks/error-learner.py` — reference for `learning.db` write pattern
- `.claude/settings.json` — registration in `PreToolUse`, position after hard-block hooks
