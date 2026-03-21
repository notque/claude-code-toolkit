---
name: perses-plugin-test
user-invocable: false
description: |
  Perses plugin testing: CUE schema unit tests with percli plugin test-schemas, React
  component tests, integration testing with local Perses server, and Grafana migration
  compatibility testing. Use for "test perses plugin", "perses plugin test",
  "perses schema test". Do NOT use for dashboard validation (use perses-lint).
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
agent: perses-plugin-engineer
version: 2.0.0
---

# Perses Plugin Testing

Test Perses plugins: CUE schemas, React components, and integration.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Schema tests first**: Always run CUE schema tests before component tests
- **JSON examples required**: Every schema must have a matching JSON example for testing

## Instructions

### Phase 1: SCHEMA TESTS
```bash
percli plugin test-schemas
```

### Phase 2: COMPONENT TESTS
Run React component tests in the plugin module.

### Phase 3: INTEGRATION TESTS
Start local dev server and verify against running Perses:
```bash
percli plugin start
```

### Phase 4: MIGRATION TESTS (optional)
If migration logic exists, test with sample Grafana dashboard JSON.
