---
name: perses-plugin-pipeline
user-invocable: false
description: |
  End-to-end Perses plugin development pipeline: SCAFFOLD, SCHEMA, IMPLEMENT, TEST,
  BUILD, DEPLOY. From percli plugin generate through CUE schema authoring, React
  component implementation, testing, and archive deployment. Use for comprehensive
  plugin development workflows. Use for "perses plugin pipeline", "full plugin
  development". Do NOT use for quick scaffolding only (use perses-plugin-create).
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
  - Agent
agent: perses-plugin-engineer
version: 2.0.0
---

# Perses Plugin Development Pipeline

6-phase pipeline for complete plugin development.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Phase gates**: Do not proceed to next phase until current phase passes
- **Test before build**: Schema tests must pass before building archive
- **Schema + component**: Both CUE schema and React component must be implemented

## Instructions

### Phase 1: SCAFFOLD
Generate plugin scaffold with `percli plugin generate`.
Determine plugin type, organization, and module name.

### Phase 2: SCHEMA
Author CUE schema defining the plugin's data model.
Create JSON example for validation.
Optional: Write Grafana migration schema in `migrate/migrate.cue`.

### Phase 3: IMPLEMENT
Build React component in `src/<type>/<name>/`.
Follow Perses component patterns using `@perses-dev/plugin-system` hooks.

### Phase 4: TEST
- Run `percli plugin test-schemas` for CUE validation
- Run component tests for React UI
- Test with `percli plugin start` against running Perses server

### Phase 5: BUILD
Run `percli plugin build` to create distribution archive.
Verify archive contents: package.json, mf-manifest.json, schemas/, __mf/.

### Phase 6: DEPLOY
Install in Perses server:
- Copy archive to `plugins-archive/` directory
- Restart Perses (or use hot-reload if enabled)
- Verify with `percli get plugin` or `perses_list_plugins` MCP tool
