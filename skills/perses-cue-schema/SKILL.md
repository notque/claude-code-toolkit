---
name: perses-cue-schema
user-invocable: false
description: |
  CUE schema authoring for Perses plugins: define data models, write validation
  constraints, create JSON examples, implement Grafana migration schemas in
  migrate/migrate.cue. Educational skill that explains CUE patterns specific to
  Perses plugin development. Use for "perses cue schema", "perses model",
  "plugin schema", "cue validation perses". Do NOT use for dashboard CUE
  definitions (use perses-dac-pipeline).
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

# Perses CUE Schema Authoring

Write CUE schemas for Perses plugin data models and migration logic.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Package model**: All plugin CUE schemas must use `package model`
- **Closed specs**: Use `close({...})` for spec definitions to prevent unknown fields
- **JSON example**: Always create a matching JSON example file
- **Test after write**: Run `percli plugin test-schemas` after creating/modifying schemas

### Default Behaviors (ON unless disabled)
- **Educational mode**: Explain CUE syntax and patterns as schemas are created
- **Import common**: Import `github.com/perses/shared/cue/common` for shared types

## Instructions

### Phase 1: DEFINE DATA MODEL
Location: `schemas/<plugin-type>/<plugin-name>/<plugin-name>.cue`

```cue
package model

import "github.com/perses/shared/cue/common"

kind: "<PluginKind>"
spec: close({
    // Required fields
    requiredField: string

    // Optional fields (note the ?)
    optionalField?: int

    // Constrained fields
    format?: common.#format
    thresholds?: common.#thresholds

    // Arrays
    items: [...#item]

    // Nested types
    #item: {
        name: string
        value: number
    }
})
```

### Phase 2: CREATE JSON EXAMPLE
Location: `schemas/<plugin-type>/<plugin-name>/<plugin-name>.json`

### Phase 3: WRITE MIGRATION (optional)
Location: `schemas/<plugin-type>/<plugin-name>/migrate/migrate.cue`

```cue
package migrate

import "github.com/perses/shared/cue/migrate"

#grafanaType: "<GrafanaPluginType>"
#mapping: {
    // Map Grafana fields to Perses fields
    perses_field: #panel.grafana_field
}
```

### Phase 4: VALIDATE
```bash
percli plugin test-schemas
```
