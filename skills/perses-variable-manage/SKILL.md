---
name: perses-variable-manage
user-invocable: false
description: |
  Perses variable lifecycle management: create Text and List variables at global,
  project, or dashboard scope. Handle variable chains with dependencies (A depends
  on B depends on C). Supports 14+ interpolation formats. Uses MCP tools when
  available, percli CLI as fallback. Use for "perses variable", "dashboard variable",
  "perses filter", "add variable". Do NOT use for datasource management
  (use perses-datasource-manage).
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

# Perses Variable Management

Create and manage variables with chains and interpolation.

## Operator Context

This skill operates as the lifecycle manager for Perses variables, handling creation, chaining, and interpolation configuration across scopes.

### Hardcoded Behaviors (Always Apply)
- **Chain ordering**: Variables must be ordered so dependencies come first — Perses evaluates variables in array order, so a variable referencing `$cluster` must appear after the cluster variable
- **MCP-first**: Use Perses MCP tools when available, percli as fallback
- **Interpolation format**: Document which format is used and why — wrong format causes query syntax errors (e.g., regex format for Prometheus matchers, csv for multi-select labels)

### Default Behaviors (ON unless disabled)
- **ListVariable**: Default to ListVariable with PrometheusLabelValuesVariable plugin
- **Dashboard scope**: Create variables at dashboard scope unless otherwise specified
- **Multi-select**: Enable allowMultiple and allowAllValue by default for filter variables

### Optional Behaviors (OFF unless enabled)
- **Global/project variables**: Create at global or project scope for reuse across dashboards
- **TextVariable**: Use TextVariable for free-form user input fields

## What This Skill CAN Do
- Create TextVariable and ListVariable at any scope (global, project, dashboard)
- Set up variable chains with cascading dependencies
- Configure interpolation formats (csv, regex, json, lucene, pipe, glob, etc.)
- Use all 4 variable plugin types

## What This Skill CANNOT Do
- Create custom variable plugins (use perses-plugin-create)
- Create dashboards (use perses-dashboard-create)

---

## Instructions

### Phase 1: IDENTIFY

**Goal**: Determine variable type, scope, and dependencies.

**Variable types**:
- **TextVariable**: Static text input — user types a value. Use for free-form filters like custom regex or label values not available via query.
- **ListVariable**: Dynamic dropdown populated by a plugin. Use for most filter/selector use cases.

**Variable plugins** (for ListVariable):

| Plugin Kind | Source | Use Case |
|-------------|--------|----------|
| PrometheusLabelValuesVariable | Label values query | Filter by namespace, pod, job |
| PrometheusPromQLVariable | PromQL query results | Dynamic values from expressions |
| StaticListVariable | Hardcoded list | Fixed options (env, region) |
| DatasourceVariable | Available datasources | Switch between datasource instances |

**Interpolation formats** (`${var:format}`):

| Format | Output Example | Use Case |
|--------|---------------|----------|
| csv | `a,b,c` | Multi-value in most contexts |
| json | `["a","b","c"]` | JSON-compatible contexts |
| regex | `a\|b\|c` | Prometheus label matchers with `=~` |
| pipe | `a\|b\|c` | Pipe-delimited lists |
| glob | `{a,b,c}` | Glob-style matching |
| lucene | `("a" OR "b" OR "c")` | Loki/Elasticsearch queries |
| doublequote | `"a","b","c"` | Quoted CSV |
| singlequote | `'a','b','c'` | Single-quoted CSV |
| raw | `a` (first only) | Single value extraction |

**Gate**: Variable type, plugin, and dependencies identified. Proceed to Phase 2.

### Phase 2: CREATE

**Goal**: Create the variable resource(s).

**Single variable** (global scope):
```bash
percli apply -f - <<EOF
kind: GlobalVariable
metadata:
  name: namespace
spec:
  kind: ListVariable
  spec:
    name: namespace
    display:
      name: Namespace
      hidden: false
    allowAllValue: true
    allowMultiple: true
    plugin:
      kind: PrometheusLabelValuesVariable
      spec:
        labelName: namespace
        datasource:
          kind: PrometheusDatasource
          name: prometheus
EOF
```

**Variable chain** (dashboard scope — cluster -> namespace -> pod):

Variables must be ordered with dependencies first. Each subsequent variable uses matchers that reference the previous variables:

```yaml
variables:
  - kind: ListVariable
    spec:
      name: cluster
      display:
        name: Cluster
      allowAllValue: false
      allowMultiple: false
      plugin:
        kind: PrometheusLabelValuesVariable
        spec:
          labelName: cluster
          datasource:
            kind: PrometheusDatasource
            name: prometheus
  - kind: ListVariable
    spec:
      name: namespace
      display:
        name: Namespace
      allowAllValue: true
      allowMultiple: true
      plugin:
        kind: PrometheusLabelValuesVariable
        spec:
          labelName: namespace
          datasource:
            kind: PrometheusDatasource
            name: prometheus
          matchers:
            - "cluster=\"$cluster\""
  - kind: ListVariable
    spec:
      name: pod
      display:
        name: Pod
      allowAllValue: true
      allowMultiple: true
      plugin:
        kind: PrometheusLabelValuesVariable
        spec:
          labelName: pod
          datasource:
            kind: PrometheusDatasource
            name: prometheus
          matchers:
            - "cluster=\"$cluster\""
            - "namespace=\"$namespace\""
```

**Gate**: Variables created without errors. Proceed to Phase 3.

### Phase 3: VERIFY

**Goal**: Confirm variables exist and chains resolve correctly.

```bash
# List variables in project
percli get variable --project <project>

# List global variables
percli get globalvariable

# Describe specific variable
percli describe variable <name> --project <project>
```

Or via MCP:
```
perses_list_variables(project="<project>")
perses_list_global_variables()
```

Verify chain behavior by checking that dependent variables correctly filter when parent values change (requires UI or API query testing).

**Gate**: Variables listed and chain dependencies confirmed. Task complete.
