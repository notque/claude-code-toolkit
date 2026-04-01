# ADR-157: Debug Prompt Dumping

## Status

Proposed

## Date

2026-03-31

## Context

Claude Code contains an internal debug feature (Ant-only, gated on a build-time feature flag)
that writes the fully assembled system prompt to `~/.config/claude/dump-prompts/` on each turn.
The dump includes everything the model receives in the system prompt position: the base system
prompt, all feature-flag-injected sections, the tool schema list, and any `additionalContext`
injections from hooks. The feature is enabled per-session via a feature gate.

The motivation for this feature inside Anthropic: when debugging unexpected model behavior,
engineers need to see the *actual* prompt the model received, not the prompt they *think* the
model received. The assembled prompt can differ significantly from the intent due to feature
flags, conditional injections, beta headers, and SDK serialization.

### Our Analogous Problem

We inject approximately 20KB of content per turn across multiple `UserPromptSubmit` hooks:
AFK mode directives, datetime context, agent usage reminders, duplication prevention guards,
auto-plan detection, and (after the ADRs in this set are implemented) cache break advisories,
rate limit advisories, continuation nudges, and undercover mode directives.

Despite this, we have no visibility into what the model actually receives. When behavior is
unexpected, we cannot answer:

- Did the AFK mode injection fire? (The model is behaving interactively despite AFK=always)
- Did the instruction-reminder inject correctly? (The model is ignoring agent routing rules)
- Why did the model reference an internal ADR number in a commit message? (Undercover mode
  should have prevented this)
- Is the auto-plan-detector producing a different plan detection result than expected?
- Is a new hook conflicting with an existing one?

Without prompt dumps, every debugging session starts with hypothesis-driven guessing. We add
print statements, check environment variables, re-read hook code, and ultimately still cannot
confirm what the model saw on that specific turn.

### The Prompt Dump Would Show

A prompt dump for a typical turn would reveal:

```
=== PROMPT DUMP: turn-007, 2026-03-31T14:22:00Z ===
=== SYSTEM PROMPT ===
[Base system prompt from Claude Code: ~2000 tokens]

=== ADDITIONAL CONTEXT (from hooks) ===
[afk-mode injection if active]
[datetime injection]
[instruction-reminder blocks]
[auto-plan-detector output if task detected]
[cache break advisory if threshold exceeded]
[rate limit advisory if applicable]
[undercover mode directive if external repo]
[continuation nudge if wrap-up detected]

=== TOOL SCHEMAS ===
[Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Task, ...]

=== MESSAGES ===
[user: ...]
[assistant: ...]
```

This structure makes it immediately clear which hooks fired, what they injected, and whether
the assembled context matches the expected configuration.

### What We Can Capture from Hook Context

We cannot dump the base system prompt — that is assembled inside Claude Code and not accessible
from hooks. What we can capture:

1. **Our hook injections**: each `UserPromptSubmit` hook produces `additionalContext`. We can
   write each hook's output to a dump directory.
2. **Injection order**: by writing hooks' outputs as numbered files, we preserve the order in
   which they were assembled.
3. **Turn number and timestamp**: for correlating dump files with model behavior.
4. **Hook execution time**: useful for performance debugging.

This gives us visibility into 100% of what *we* inject, even if not the base Claude Code system
prompt.

### Cache Stability Intersection

Prompt dumps are a debugging tool. They should not affect normal operation. The mechanism must
not inject any content into the model's context (it should observe, not modify). The dump
directory approach satisfies this: we write to disk, not to `additionalContext`.

The exception: when `CLAUDE_TOOLKIT_DUMP_PROMPTS=1` is set, the dump hook writes files but
produces zero `additionalContext`. This is explicitly a non-injecting hook — it is a side-effect
observer only.

## Decision

Create `hooks/prompt-dumper.py`, a `UserPromptSubmit` hook that captures all hook injections
for the current turn and writes them to `~/.claude/debug/prompt-dumps/`. The hook is inactive
by default (zero cost, zero injection) and activated by the `CLAUDE_TOOLKIT_DUMP_PROMPTS=1`
environment variable.

### Dump Directory Structure

```
~/.claude/debug/prompt-dumps/
  2026-03-31T14-22-00-turn-001/
    00-metadata.json
    01-datetime-inject.txt
    02-afk-mode.txt
    03-instruction-reminder.txt
    04-auto-plan-detector.txt
    05-cache-break-detector.txt
    ...
    99-summary.txt
  2026-03-31T14-22-15-turn-002/
    ...
```

Each turn gets a timestamped directory. Files are numbered by hook execution order.

### Implementation Approach: Sidecar Pattern

The prompt dumper cannot directly capture other hooks' output — each hook runs independently.
Instead, use a **sidecar write** approach: each hook that produces `additionalContext` also
writes its output to a temp file when `CLAUDE_TOOLKIT_DUMP_PROMPTS=1`:

```python
# In each hook's main():
if os.environ.get("CLAUDE_TOOLKIT_DUMP_PROMPTS") == "1":
    _write_dump(hook_name, output_content)
```

The `prompt-dumper.py` hook then runs **last** (final `UserPromptSubmit` hook) and assembles
the per-hook files into a structured turn dump directory.

This requires modifying each existing hook to add the sidecar write. However, the modification
is a 3-line addition:

```python
from hook_utils import dump_if_enabled
# at the end of main():
dump_if_enabled("hook-name", context_content)
```

Add `dump_if_enabled()` to `hooks/lib/hook_utils.py` as a zero-cost no-op when the env var
is not set.

### Alternative: Capture at the Assembler Level

If Claude Code assembles `additionalContext` from all hooks before sending to the model, there
may be a point where all injections are visible in a single structure. However, the hook API
does not expose this assembly point — each hook runs independently and produces its own output.
The sidecar approach is the practical alternative.

### Dump File Contents

**`00-metadata.json`**:
```json
{
  "turn": 7,
  "session_pid": 12345,
  "timestamp": "2026-03-31T14:22:00Z",
  "afk_mode_active": true,
  "operator_profile": "personal",
  "hooks_fired": ["datetime-inject", "afk-mode", "instruction-reminder"],
  "hooks_skipped": ["auto-plan-detector", "cache-break-detector"]
}
```

**`01-datetime-inject.txt`**:
```
=== datetime-inject | 2ms ===
<current-date>2026-03-31</current-date>
```

**`99-summary.txt`**:
```
=== PROMPT DUMP SUMMARY: turn-007 ===
Total hooks fired: 3
Total injection tokens (estimated): ~380
Hooks: datetime-inject (10t), afk-mode (150t), instruction-reminder (220t)
Hooks skipped (no output): auto-plan-detector, cache-break-detector
```

Token estimates use a 0.25 tokens/character heuristic (rough but useful for comparison).

### Retention Policy

Dump directories accumulate on disk. Clean up dumps older than 24 hours automatically on each
session start. Maximum 100 directories retained (configurable). A `Stop` hook event or a
`scripts/clear-dumps.py` utility handles cleanup.

### Activation

| Mechanism | Command | Effect |
|-----------|---------|--------|
| Environment variable | `CLAUDE_TOOLKIT_DUMP_PROMPTS=1 claude` | Dumps all turns in session |
| Per-session | Export in `.env` for the project | Dumps all turns while working in that project |
| One-shot | `CLAUDE_TOOLKIT_DUMP_PROMPTS=1 claude -p "debug this"` | Dumps a single `-p` run |

The variable is not set by default. Normal sessions incur zero overhead.

### Relationship to ADR-152 (Cache Break Detection)

ADR-152 detects cache breaks by comparing injection hashes. ADR-157 dumps the actual injection
content. They are complementary: when ADR-152 logs a cache break, use ADR-157 dumps to identify
exactly what changed between turns. The combination of "break detected" (ADR-152) + "content
visible" (ADR-157) provides a complete debugging workflow.

### Relationship to Other ADRs in This Set

All hooks introduced in ADR-151 through ADR-156 should include the `dump_if_enabled()` call
when implemented. The sidecar pattern is a cross-cutting concern that ADR-157 introduces as
a `hook_utils.py` standard.

## Affected Files

| File | Action | Purpose |
|------|--------|---------|
| `hooks/prompt-dumper.py` | Create | Assembles per-turn dump directory |
| `hooks/lib/hook_utils.py` | Modify | Add `dump_if_enabled()` utility function |
| `hooks/*.py` (existing) | Modify | Add `dump_if_enabled()` call to each hook |
| `scripts/clear-dumps.py` | Create | Dump retention cleanup utility |
| `.claude/settings.json` | Modify | Register prompt-dumper last in `UserPromptSubmit` |

## Alternatives Considered

### A. Capture the full Claude Code prompt including base system prompt

Intercept the actual API call to capture the full `system` parameter sent to the Anthropic API.

**Not feasible without modifying Claude Code**: the API call is made inside Claude Code, not from
hook context. We can only observe the hook API surface, not the full API call.

### B. Write each hook's output independently without an assembler hook

Have each hook write its own dump file; no assembler hook needed.

**Simpler but less structured**: individual dump files without metadata correlation make it
harder to reconstruct the full turn context. The assembler hook provides the summary and
metadata that makes dumps useful rather than just a pile of text files.

### C. Use Claude Code's own dump-prompts feature

Enable the internal Anthropic feature for dump-prompts if it is possible to gate on in external
builds.

**Not accessible**: the feature is behind a build-time gate that is off in the external Claude
Code binary. We cannot enable it from hook context or settings.

### D. Log injections to `learning.db` rather than file dumps

Store injection content in SQLite rather than files, enabling structured queries.

**Complementary, not a replacement**: SQLite queries are better for aggregate analysis (which
hooks fire most often, average injection size over time). File dumps are better for turn-by-turn
debugging (what exactly did the model see on turn 7 of last night's session). Both have value.
Phase 1 ships file dumps; Phase 2 can add SQLite logging of injection metadata.

## Design Questions Resolved

**Should dumps capture tool schemas?**

No. Tool schemas are deterministic from `settings.json` and do not change within a session.
They are not a debugging target for hook-injection issues. Keeping dumps focused on hook
injections makes them smaller and more readable.

**Should the dump directory be in `~/.claude/debug/` or in the project directory?**

`~/.claude/debug/prompt-dumps/` — user-global location, consistent across projects, does not
pollute project directories or `.gitignore` concerns.

**Should dumps be gzipped to save space?**

Not in Phase 1. Dumps are small (< 50KB per turn for typical injection volumes) and are cleaned
up every 24 hours. Compression adds complexity for minimal space savings at typical retention
volumes.

**Does the dump hook add any latency when disabled?**

Zero. The `CLAUDE_TOOLKIT_DUMP_PROMPTS` check is an environment variable read followed
by an immediate return. Sub-microsecond. The `dump_if_enabled()` utility in `hook_utils.py`
is equally trivial when the env var is not set.

## Consequences

### Positive

- First-time visibility into what the model actually receives per turn from our hooks
- Debugging hook conflicts, unexpected behavior, and cache breaks becomes tractable
- The sidecar pattern (`dump_if_enabled()`) establishes a standard for observability across all
  hooks without requiring a centralized aggregator
- Zero cost when not enabled — normal sessions are completely unaffected
- Trivial to enable on-demand via `CLAUDE_TOOLKIT_DUMP_PROMPTS=1`

### Negative / Risks

**Dump files contain system context**: the dump files include agent directives, operator profile
context, and behavioral instructions. These should not be committed to repos or shared publicly.

Mitigation: `~/.claude/debug/` is user-global, not in any repo. Add `debug/` to any relevant
`.gitignore` templates. Document that dump files are private debugging artifacts.

**Disk space without cleanup**: if the retention policy is not enforced, dump directories
accumulate. A long debugging session with 100+ turns produces 100+ directories.

Mitigation: automatic cleanup of dumps older than 24 hours on session start. The `Stop` hook
can also trigger cleanup.

**Sidecar writes in each hook**: every hook needs a `dump_if_enabled()` call. This is a small
addition but touches every hook file. A missed hook means its injections are invisible in dumps.

Mitigation: add the call as part of the hook template so new hooks automatically include it.
The `hook_utils.py` modification makes this a one-line addition.

## Implementation Notes

**`dump_if_enabled()` signature in `hook_utils.py`**:

```python
def dump_if_enabled(hook_name: str, content: str, execution_ms: float = 0.0) -> None:
    """Write hook output to dump directory if CLAUDE_TOOLKIT_DUMP_PROMPTS=1.
    Zero-cost no-op when env var is not set."""
    if os.environ.get("CLAUDE_TOOLKIT_DUMP_PROMPTS") != "1":
        return
    # write to /tmp/claude-dump-{session_pid}/{hook_name}.txt
    # prompt-dumper.py assembles these files into the final dump directory
```

**Hook ordering**: `prompt-dumper.py` must register **last** in `UserPromptSubmit` so it runs
after all other hooks have written their sidecar files.

**Deploy order** (per established protocol):

1. Modify `hooks/lib/hook_utils.py` to add `dump_if_enabled()`.
2. Add `dump_if_enabled()` to each existing hook.
3. Create `hooks/prompt-dumper.py`.
4. Create `scripts/clear-dumps.py`.
5. Sync to `~/.claude/` via sync script.
6. Test: `CLAUDE_TOOLKIT_DUMP_PROMPTS=1 python3 ~/.claude/hooks/afk-mode.py < /dev/null`
   creates a sidecar file in `/tmp/claude-dump-{ppid}/`.
7. Test: run `prompt-dumper.py` after running other hooks; confirm turn directory is assembled.
8. Register `prompt-dumper.py` last in `UserPromptSubmit` in `.claude/settings.json`.

## Validation Requirements

Before merging:

1. `CLAUDE_TOOLKIT_DUMP_PROMPTS` not set: no files written, all hooks execute normally.
2. `CLAUDE_TOOLKIT_DUMP_PROMPTS=1`: each hook writes sidecar file; prompt-dumper assembles
   turn directory.
3. Turn directory contains `00-metadata.json`, per-hook files, `99-summary.txt`.
4. Metadata accurately reflects which hooks fired vs. produced no output.
5. Cleanup: dumps older than 24 hours are removed on `clear-dumps.py` run.
6. Dump files not created in current working directory or project directory.
7. No latency impact when env var not set: all hooks execute in same time as before.
8. `prompt-dumper.py` exits 0 on all paths including when no sidecar files exist.

## Effort Estimate

**Trivial** — the hook itself is a file-system assembler. The `dump_if_enabled()` utility is
a 10-line addition to `hook_utils.py`. The main effort is the mechanical work of adding the
sidecar call to each existing hook and creating the cleanup script. Estimated 1-2 hours for
full implementation across all hooks.

## References

- Claude Code source: internal `dump-prompts` feature (Ant-only, `~/.config/claude/dump-prompts/`)
- `hooks/lib/hook_utils.py` — modification target for `dump_if_enabled()`
- ADR-141 — prompt cache stability; dumps reveal which injections affect cache
- ADR-152 — cache break detection; dumps complement break detection with full content visibility
- ADR-142 (`instruction-reminder.py`) — largest injection hook; most informative dump target
- ADR-143 (`afk-mode.py`) — first hook to add sidecar write in implementation
- `.claude/settings.json` — registration of `prompt-dumper.py` last in `UserPromptSubmit`
