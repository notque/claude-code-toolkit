---
name: perses-dac-pipeline
user-invocable: false
description: |
  Dashboard-as-Code pipeline: initialize CUE or Go module with percli dac setup,
  write dashboard definitions, build with percli dac build, validate, apply, and
  integrate with CI/CD via GitHub Actions (perses/cli-actions). Use for "dashboard
  as code", "perses dac", "perses cue", "perses gitops", "perses ci/cd". Do NOT
  use for one-off dashboard creation (use perses-dashboard-create) or Grafana
  migration (use perses-grafana-migrate).
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

# Perses Dashboard-as-Code Pipeline

Set up and manage Dashboard-as-Code workflows with CUE or Go SDK.

## Operator Context

This skill operates as a pipeline for Dashboard-as-Code workflows, from module initialization through CI/CD integration.

### Hardcoded Behaviors (Always Apply)
- **One dashboard per file**: Follow Perses convention of one dashboard definition per file — keeps diffs clean and enables per-dashboard CI validation
- **Build before apply**: Always run `percli dac build` before `percli apply` — raw CUE/Go files cannot be applied directly
- **Validate built output**: Always run `percli lint` on built JSON/YAML before deploying — build success does not guarantee valid dashboard spec
- **Go SDK stdout warning**: Never log/print to stdout in Go DaC programs — `dac build` captures stdout as the dashboard definition, so any stray output corrupts it

### Default Behaviors (ON unless disabled)
- **CUE SDK**: Default to CUE SDK unless user requests Go
- **JSON output**: Build to JSON format by default
- **Git-friendly**: Organize files for version control (one dashboard per file, clear naming)

### Optional Behaviors (OFF unless enabled)
- **Go SDK**: Use Go SDK instead of CUE for teams more comfortable with Go
- **YAML output**: Build to YAML format instead of JSON

## What This Skill CAN Do
- Initialize CUE or Go DaC modules
- Write dashboard definitions using SDK builders
- Build definitions to JSON/YAML
- Set up CI/CD with GitHub Actions
- Manage multi-dashboard repositories

## What This Skill CANNOT Do
- Create custom plugins (use perses-plugin-create)
- Deploy Perses server (use perses-deploy)
- Migrate Grafana dashboards (use perses-grafana-migrate)

---

## Instructions

### Phase 1: INITIALIZE

**Goal**: Set up the DaC module.

**CUE SDK** (default):
```bash
mkdir -p dac && cd dac
cue mod init my-dashboards
percli dac setup
cue mod tidy
```
Requirements: `percli` >= v0.51.0, `cue` >= v0.12.0

**Go SDK**:
```bash
mkdir -p dac && cd dac
go mod init my-dashboards
percli dac setup --language go
go mod tidy
```
Requirements: `percli` >= v0.44.0, Go installed

**Gate**: Module initialized, dependencies resolved. `cue mod tidy` or `go mod tidy` succeeds without errors. Proceed to Phase 2.

### Phase 2: DEFINE

**Goal**: Write dashboard definitions using SDK builders.

CUE example structure:
```
dac/
├── cue.mod/
├── dashboards/
│   ├── cpu-monitoring.cue
│   └── network-overview.cue
└── shared/
    ├── datasources.cue
    └── variables.cue
```

**Gate**: Dashboard definitions written. Files parse without syntax errors. Proceed to Phase 3.

### Phase 3: BUILD

**Goal**: Build definitions to deployable format.

```bash
# Single file
percli dac build -f dashboards/cpu-monitoring.cue -ojson

# Directory (all dashboards)
percli dac build -d dashboards/ -ojson

# Go SDK
percli dac build -f main.go -ojson
```

Output appears in `built/` directory.

**Gate**: Build succeeds, JSON/YAML output in `built/`. Proceed to Phase 4.

### Phase 4: VALIDATE

**Goal**: Ensure built dashboards are valid.

```bash
percli lint -f built/cpu-monitoring.json
# Or with server validation
percli lint -f built/cpu-monitoring.json --online
```

**Gate**: Validation passes. Proceed to Phase 5.

### Phase 5: DEPLOY

**Goal**: Apply dashboards to Perses.

```bash
percli apply -f built/cpu-monitoring.json --project <project>
```

Verify deployment:
```bash
percli get dashboard --project <project>
```

**Gate**: Dashboards deployed and accessible. Proceed to Phase 6 if CI/CD is requested.

### Phase 6: CI/CD INTEGRATION (optional)

**Goal**: Set up GitHub Actions for automated DaC pipeline.

```yaml
name: Dashboard-as-Code
on:
  push:
    paths: ['dac/**']
jobs:
  dac:
    uses: perses/cli-actions/.github/workflows/dac.yaml@v0.1.0
    with:
      url: ${{ vars.PERSES_URL }}
      directory: ./dac
      server-validation: true
    secrets:
      username: ${{ secrets.PERSES_USERNAME }}
      password: ${{ secrets.PERSES_PASSWORD }}
```

**Gate**: CI/CD pipeline configured and tested. Pipeline complete.
