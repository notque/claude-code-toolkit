# ADR-040: Do-Router Landscape Research

## Status

Accepted

## Date

2026-03-22

## Context

The `/do` router is the primary entry point for this toolkit's agent orchestration system. As the Claude Code ecosystem has matured, multiple independent projects have built similar routing, dispatch, and orchestration systems. Understanding the landscape helps identify convergent patterns, novel approaches worth studying, and our toolkit's distinctive contributions.

This ADR authorizes a systematic survey of routing/dispatch systems in the Claude Code ecosystem, documenting findings in `research/do-router-landscape.md` and updating `docs/CITATIONS.md` with discovered repos.

## Decision

Conduct a landscape research survey covering:
- GitHub repos implementing routing, dispatch, or agent orchestration for Claude Code
- Blog posts and community discussions about routing patterns
- Comparison against our toolkit's approach

Produce two artifacts:
1. `research/do-router-landscape.md` -- comprehensive landscape report
2. Updated `docs/CITATIONS.md` -- citations for discovered repos

## Consequences

- Establishes prior art documentation for future architectural decisions
- Identifies patterns worth adopting (tier-based escalation, progressive disclosure, self-improving skills)
- Confirms our toolkit's distinctive contributions (anti-rationalization, deterministic validation, learning graduation)
- Creates a reference point for future landscape surveys as the ecosystem evolves
