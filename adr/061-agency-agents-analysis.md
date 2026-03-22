# ADR-061: Agency-Agents Repository Analysis

## Status
Accepted

## Context

The [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) repository contains a collection of agents for Claude Code. We want to do a full line-by-line read to identify patterns worth adopting or studying.

Key hypothesis: their agents are likely low-context (compact, minimal prompts) compared to our high-context agents (detailed operator context, phase gates, anti-patterns, error handling). If we want to adopt any, we need to adapt them for our high-context architecture.

## Decision

Conduct a systematic analysis of the agency-agents repo:

### Analysis Pipeline: FETCH → READ → CLASSIFY → DIFF → REPORT

**Phase 1 - FETCH**: Clone or fetch repo contents via GitHub API.

**Phase 2 - READ**: Line-by-line read of every agent file. For each agent, extract:
- Domain/purpose
- Size (lines, tokens estimate)
- Structure (frontmatter fields, sections)
- Skill pairing (if any)
- Routing mechanism (if any)
- Unique capabilities not in our toolkit

**Phase 3 - CLASSIFY**: Categorize each agent:
- **Already covered** — we have an equivalent or better agent
- **Gap filler** — covers a domain we don't have
- **Novel pattern** — uses a technique worth studying
- **Low value** — too generic or thin to be useful

**Phase 4 - DIFF**: For gap fillers and novel patterns, produce:
- What they have that we don't
- What adaptation would be needed (low-context → high-context)
- Estimated effort to adopt
- Whether to adopt, study, or skip

**Phase 5 - REPORT**: Produce `research/agency-agents-analysis.md` with:
- Repo overview and architecture summary
- Agent-by-agent analysis table
- Recommended adoptions with adaptation notes
- Update `docs/CITATIONS.md` with the repo entry

## Consequences

### Positive
- Identifies gaps in our agent coverage
- May discover novel patterns worth adopting
- Validates our architectural choices by comparison

### Negative
- Point-in-time snapshot (their repo will evolve)
- Adaptation effort may outweigh value for thin agents

### Neutral
- Research only; actual adoption would be separate ADRs per agent
