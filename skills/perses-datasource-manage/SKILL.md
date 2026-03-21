---
name: perses-datasource-manage
user-invocable: false
description: |
  Perses datasource lifecycle management: create, update, delete datasources at
  global, project, or dashboard scope. Supports Prometheus, Tempo, Loki, Pyroscope,
  ClickHouse, and VictoriaLogs. Uses MCP tools when available, percli CLI as fallback.
  Use for "perses datasource", "add datasource", "configure prometheus perses",
  "perses data source". Do NOT use for dashboard creation (use perses-dashboard-create).
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

# Perses Datasource Management

Create, update, and manage datasources across scopes.

## Operator Context

This skill operates as the lifecycle manager for Perses datasources, handling creation, updates, and deletion across global, project, and dashboard scopes.

### Hardcoded Behaviors (Always Apply)
- **Scope-aware**: Always clarify scope — global (all projects), project, or dashboard — because scope determines resource kind and override priority
- **MCP-first**: Use Perses MCP tools when available, percli as fallback
- **Proxy configuration**: Always configure allowedEndpoints for HTTP proxy datasources — without them, queries will be blocked by the proxy

### Default Behaviors (ON unless disabled)
- **Global scope**: Default to global datasource unless project is specified
- **Default flag**: Set first datasource of each type as default

### Optional Behaviors (OFF unless enabled)
- **Multi-backend**: Configure multiple datasources of the same type with different names
- **Dashboard-scoped**: Embed datasource config directly in dashboard spec

## What This Skill CAN Do
- Create/update/delete datasources at any scope
- Configure HTTP proxy with allowed endpoints
- Manage datasource priority (global vs project vs dashboard)
- Support all 6 datasource types: Prometheus, Tempo, Loki, Pyroscope, ClickHouse, VictoriaLogs

## What This Skill CANNOT Do
- Create the datasource backends themselves (Prometheus, Loki, etc.)
- Manage Perses server configuration (use perses-deploy)
- Create dashboards (use perses-dashboard-create)

---

## Instructions

### Phase 1: IDENTIFY

**Goal**: Determine datasource type, scope, and connection details.

**Supported types**:

| Plugin Kind | Backend | Common Endpoints |
|-------------|---------|-----------------|
| PrometheusDatasource | Prometheus | `/api/v1/.*` |
| TempoDatasource | Tempo | `/api/traces/.*`, `/api/search` |
| LokiDatasource | Loki | `/loki/api/v1/.*` |
| PyroscopeDatasource | Pyroscope | `/pyroscope/.*` |
| ClickHouseDatasource | ClickHouse | N/A (direct connection) |
| VictoriaLogsDatasource | VictoriaLogs | `/select/.*` |

**Scopes** (priority order, highest first): Dashboard > Project > Global

A dashboard-scoped datasource overrides a project-scoped one of the same name, which overrides a global one. Use global for organization-wide defaults, project for team-specific overrides, dashboard for one-off configurations.

**Gate**: Type, scope, and connection URL identified. Proceed to Phase 2.

### Phase 2: CREATE

**Goal**: Create the datasource resource.

**Via MCP** (preferred):
```
perses_create_global_datasource(name="prometheus", type="PrometheusDatasource", url="http://prometheus:9090")
```

**Via percli** (GlobalDatasource):
```bash
percli apply -f - <<EOF
kind: GlobalDatasource
metadata:
  name: prometheus
spec:
  default: true
  plugin:
    kind: PrometheusDatasource
    spec:
      proxy:
        kind: HTTPProxy
        spec:
          url: http://prometheus:9090
          allowedEndpoints:
            - endpointPattern: /api/v1/.*
              method: POST
            - endpointPattern: /api/v1/.*
              method: GET
EOF
```

**Via percli** (Project-scoped Datasource):
```bash
percli apply -f - <<EOF
kind: Datasource
metadata:
  name: prometheus
  project: <project-name>
spec:
  default: true
  plugin:
    kind: PrometheusDatasource
    spec:
      proxy:
        kind: HTTPProxy
        spec:
          url: http://prometheus:9090
          allowedEndpoints:
            - endpointPattern: /api/v1/.*
              method: POST
            - endpointPattern: /api/v1/.*
              method: GET
EOF
```

**Gate**: Datasource created without errors. Proceed to Phase 3.

### Phase 3: VERIFY

**Goal**: Confirm the datasource exists and is accessible.

```bash
# Global datasources
percli get globaldatasource

# Project datasources
percli get datasource --project <project>

# Describe specific datasource
percli describe globaldatasource <name>
```

Or via MCP:
```
perses_list_global_datasources()
perses_list_datasources(project="<project>")
```

**Gate**: Datasource listed and configuration confirmed. Task complete.
