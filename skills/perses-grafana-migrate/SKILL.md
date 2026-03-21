---
name: perses-grafana-migrate
user-invocable: false
description: |
  Grafana-to-Perses dashboard migration: export Grafana dashboards, convert with
  percli migrate, validate converted output, fix incompatibilities, deploy to Perses.
  Handles bulk migration with parallel processing. Use for "migrate grafana",
  "grafana to perses", "perses migrate", "convert grafana". Do NOT use for creating
  new dashboards from scratch (use perses-dashboard-create).
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

# Perses Grafana Migration

Convert Grafana dashboards to Perses format with validation and deployment.

## Operator Context

This skill operates as a migration pipeline for converting Grafana dashboards to Perses format, handling export, conversion, validation, and deployment.

### Hardcoded Behaviors (Always Apply)
- **Validate after conversion**: Always run `percli lint` on migrated dashboards — conversion may produce structurally valid but semantically broken output
- **Preserve originals**: Never modify Grafana source files — migration is a one-way copy operation
- **Report incompatibilities**: List all plugins/panels that couldn't be migrated — unsupported Grafana plugins become StaticListVariable placeholders that need manual attention

### Default Behaviors (ON unless disabled)
- **Online mode**: Use `percli migrate --online` when connected to a Perses server (recommended — uses latest plugin migration logic)
- **JSON output**: Default to JSON format for migrated dashboards
- **Batch processing**: Process multiple dashboards in parallel when given a directory

### Optional Behaviors (OFF unless enabled)
- **K8s CR output**: Generate Kubernetes CustomResource format with `--format cr`
- **Auto-deploy**: Apply migrated dashboards immediately after validation

## What This Skill CAN Do
- Convert Grafana dashboard JSON to Perses format
- Handle bulk migration of multiple dashboards
- Validate migrated output and report incompatibilities
- Deploy migrated dashboards to Perses

## What This Skill CANNOT Do
- Migrate Grafana alerts, users, or datasource configurations
- Convert unsupported Grafana plugins (they become StaticListVariable placeholders)
- Create dashboards from scratch (use perses-dashboard-create)

---

## Instructions

### Phase 1: EXPORT

**Goal**: Export Grafana dashboards as JSON files. If user has JSON files already, skip to Phase 2.

```bash
# Export from Grafana API
curl -H "Authorization: Bearer <token>" \
  https://grafana.example.com/api/dashboards/uid/<uid> \
  | jq '.dashboard' > grafana-dashboard.json
```

For bulk export, iterate over all dashboards:
```bash
curl -H "Authorization: Bearer <token>" \
  https://grafana.example.com/api/search?type=dash-db \
  | jq -r '.[].uid' | while read uid; do
    curl -s -H "Authorization: Bearer <token>" \
      "https://grafana.example.com/api/dashboards/uid/$uid" \
      | jq '.dashboard' > "grafana-$uid.json"
done
```

**Gate**: Grafana dashboard JSON files available. Proceed to Phase 2.

### Phase 2: CONVERT

**Goal**: Convert Grafana JSON to Perses format.

```bash
# Single dashboard (online mode - recommended)
percli migrate -f grafana-dashboard.json --online -o json > perses-dashboard.json

# Bulk migration
for f in grafana-*.json; do
  percli migrate -f "$f" --online -o json > "perses-${f#grafana-}"
done

# K8s CR format
percli migrate -f grafana-dashboard.json --online --format cr -o json > perses-cr.json
```

**Migration notes**:
- Requires Perses server connection for online mode (uses latest plugin migration logic)
- Compatible with Grafana 9.0.0+, latest version recommended
- Unsupported variables become `StaticListVariable` with values `["grafana", "migration", "not", "supported"]`

**Gate**: Conversion complete. All files produced without errors. Proceed to Phase 3.

### Phase 3: VALIDATE

**Goal**: Validate converted dashboards and report incompatibilities.

```bash
percli lint -f perses-dashboard.json
```

Check for:
- Panel types that weren't converted (search for StaticListVariable placeholders)
- Missing datasource references
- Variable references that didn't translate

**Gate**: Validation passes (or issues documented with remediation plan). Proceed to Phase 4.

### Phase 4: DEPLOY

**Goal**: Deploy migrated dashboards to Perses.

```bash
# Ensure project exists
percli apply -f - <<EOF
kind: Project
metadata:
  name: <project>
spec: {}
EOF

# Deploy dashboards
percli apply -f perses-dashboard.json --project <project>
```

Verify migration:
```bash
percli get dashboard --project <project>
```

**Gate**: Dashboards deployed and accessible. Migration complete.
