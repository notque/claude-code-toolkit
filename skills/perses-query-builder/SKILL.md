---
name: perses-query-builder
user-invocable: false
description: |
  Build PromQL, LogQL, TraceQL queries for Perses panels. Validate query syntax,
  suggest optimizations, handle variable templating with Perses interpolation formats.
  Integrates with prometheus-grafana-engineer for deep PromQL expertise. Use for
  "perses query", "promql perses", "logql perses", "perses panel query". Do NOT use
  for datasource configuration (use perses-datasource-manage).
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

# Perses Query Builder

Build and optimize queries for Perses dashboard panels.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Variable-aware**: Always use Perses variable syntax `$var` or `${var:format}` where appropriate
- **Datasource-scoped**: Queries must reference the correct datasource by name and kind

### Default Behaviors (ON unless disabled)
- **PromQL default**: Default to PrometheusTimeSeriesQuery if query type not specified
- **Optimization suggestions**: Suggest recording rules for expensive queries

## Instructions

### Phase 1: IDENTIFY
Determine query type and datasource:
- PrometheusTimeSeriesQuery (PromQL)
- TempoTraceQuery (TraceQL)
- LokiLogQuery (LogQL)

### Phase 2: BUILD
Construct the query with proper variable templating:

```yaml
queries:
  - kind: TimeSeriesQuery
    spec:
      plugin:
        kind: PrometheusTimeSeriesQuery
        spec:
          query: "rate(http_requests_total{job=\"$job\", instance=~\"${instance:regex}\"}[5m])"
          datasource:
            kind: PrometheusDatasource
            name: prometheus
```

### Phase 3: OPTIMIZE
- Avoid high-cardinality label selectors
- Use recording rules for complex aggregations
- Use appropriate `rate()` intervals
- Leverage variable interpolation formats for multi-value variables
