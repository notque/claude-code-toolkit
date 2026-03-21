---
name: perses-code-review
user-invocable: false
description: |
  Perses-aware code review: check Go backend against Perses patterns, React components
  against Perses UI conventions, CUE schemas against plugin spec, and dashboard
  definitions against best practices. Dispatches appropriate sub-reviewers. Use for
  "review perses", "perses pr", "perses code review". Do NOT use for general Go/React
  review without Perses context.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
  - Agent
agent: perses-core-engineer
version: 2.0.0
---

# Perses Code Review

Review code for Perses-specific patterns and best practices.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Perses-specific**: Focus on Perses patterns, not general Go/React review
- **CUE validation**: Check CUE schemas are in model package with closed specs
- **Dashboard validation**: Validate panel references, variable chains, datasource scopes

### Default Behaviors (ON unless disabled)
- **Multi-domain dispatch**: Dispatch Go reviewer for .go files, React reviewer for .tsx, CUE reviewer for .cue
- **Dashboard lint**: Run `percli lint` on any dashboard definitions in the PR

## Instructions

### Phase 1: CLASSIFY
Determine what types of files are changed: Go backend, React frontend, CUE schemas, dashboard definitions.

### Phase 2: REVIEW
For each file type, check Perses-specific patterns:

**Go backend**: API handler patterns, storage interface compliance, auth middleware usage
**React frontend**: Plugin-system hook usage, component patterns, @perses-dev/* package usage
**CUE schemas**: Package model, closed specs, JSON examples, migration logic
**Dashboard definitions**: Valid panel references, variable chains, datasource scopes, layout grid

### Phase 3: REPORT
Report findings with severity levels and Perses-specific fix suggestions.
