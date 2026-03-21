---
name: perses-dashboard-review
user-invocable: false
description: |
  Review existing Perses dashboards for quality: fetch via MCP or API, analyze panel
  layout, query efficiency, variable usage, datasource configuration. Generate
  improvement report. Optional --fix mode. 4-phase pipeline: FETCH, ANALYZE, REPORT, FIX.
  Use for "review perses dashboard", "audit dashboard", "perses dashboard quality".
  Do NOT use for creating new dashboards (use perses-dashboard-create).
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
  - Agent
agent: perses-dashboard-engineer
version: 2.0.0
---

# Perses Dashboard Review

Analyze and improve existing Perses dashboards.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Non-destructive**: Never modify dashboards without explicit --fix mode
- **MCP-first**: Fetch dashboards via MCP tools when available

## Instructions

### Phase 1: FETCH
Retrieve dashboard definition via MCP or percli:
```
perses_get_dashboard_by_name(project=<project>, dashboard=<name>)
# OR
percli describe dashboard <name> --project <project> -ojson
```

### Phase 2: ANALYZE
Check for:
- Panel layout efficiency (are panels well-organized in grid?)
- Query quality (efficient PromQL, proper rate intervals, recording rule candidates)
- Variable chain correctness (proper dependency ordering, matchers include parent vars)
- Datasource scoping (appropriate scope for each datasource)
- Missing descriptions, unclear panel titles
- Unused panels (defined but not referenced in layouts)

### Phase 3: REPORT
Generate a structured report with findings by severity.

### Phase 4: FIX (optional, requires --fix)
Apply improvements to the dashboard and redeploy.
