---
name: perses-lint
user-invocable: false
description: |
  Validate Perses resources: run percli lint locally or with --online against a server.
  Check dashboard definitions, datasource configs, variable schemas. Report errors with
  actionable fixes. Use for "perses lint", "validate perses", "check dashboard",
  "perses validate". Do NOT use for plugin schema testing (use perses-plugin-test).
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
agent: perses-dashboard-engineer
version: 2.0.0
---

# Perses Lint

Validate Perses resource definitions.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Show full output**: Always display complete lint output, never summarize
- **Online when possible**: Prefer `--online` mode when connected to a Perses server

## Instructions

### Phase 1: VALIDATE
```bash
# Local validation
percli lint -f <file>

# Online validation (includes plugin schema checks)
percli lint -f <file> --online

# Batch validation
for f in *.json; do percli lint -f "$f"; done
```

### Phase 2: FIX
For each error, provide the fix. Common issues:
- Invalid panel plugin kind → check against official 27 plugins
- Missing datasource reference → add datasource to dashboard spec
- Invalid variable reference → check variable name matches `${var}` usage
- Layout $ref mismatch → verify panel ID exists in panels map

### Phase 3: RE-VALIDATE
Run lint again after fixes to confirm all issues resolved.
