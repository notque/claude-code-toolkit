---
name: perses-plugin-create
user-invocable: false
description: |
  Perses plugin scaffolding and creation: select plugin type (Panel, Datasource, Query,
  Variable, Explore), generate with percli plugin generate, implement CUE schema and React
  component, test with percli plugin start, build archive with percli plugin build. Use for
  "create perses plugin", "new panel plugin", "new datasource plugin", "perses plugin scaffold".
  Do NOT use for dashboard creation (use perses-dashboard-create).
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

# Perses Plugin Create

Scaffold and implement Perses plugins with CUE schemas and React components.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Schema + example**: Always create both CUE schema and JSON example
- **Test before build**: Always run `percli plugin test-schemas` before `percli plugin build`
- **Model package**: CUE schemas must use `package model`

### Default Behaviors (ON unless disabled)
- **Panel type**: Default to Panel plugin type if not specified
- **Include migration**: Generate Grafana migration scaffold if Grafana equivalent exists

## Instructions

### Phase 1: SCAFFOLD
```bash
percli plugin generate \
  --module.org=<org> \
  --module.name=<name> \
  --plugin.type=<Panel|Datasource|TimeSeriesQuery|TraceQuery|ProfileQuery|LogQuery|Variable|Explore> \
  --plugin.name=<PluginName> \
  <directory>
```

### Phase 2: SCHEMA
Edit CUE schema at `schemas/<type>/<name>/<name>.cue`:
```cue
package model

kind: "<PluginName>"
spec: close({
    // Define your plugin's data model here
    field1: string
    field2?: int
})
```

Create JSON example at `schemas/<type>/<name>/<name>.json`.

### Phase 3: IMPLEMENT
Implement React component at `src/<type>/<name>/`.

### Phase 4: TEST
```bash
percli plugin test-schemas
percli plugin start  # Hot-reload dev server
```

### Phase 5: BUILD
```bash
percli plugin build  # Creates archive
```

### Phase 6: DEPLOY
Install archive in Perses server's `plugins-archive/` directory or embed via npm.
