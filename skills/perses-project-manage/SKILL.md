---
name: perses-project-manage
user-invocable: false
description: |
  Perses project lifecycle management: create, list, switch, and configure projects.
  Manage RBAC with roles and role bindings per project. Uses MCP tools when available,
  percli CLI as fallback. Use for "perses project", "create project", "perses rbac",
  "perses roles", "perses permissions". Do NOT use for dashboard creation
  (use perses-dashboard-create).
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

# Perses Project Management

Create and manage projects with RBAC configuration.

## Operator Context

This skill operates as the lifecycle manager for Perses projects and their RBAC configuration, handling project creation, role definitions, and role bindings.

### Hardcoded Behaviors (Always Apply)
- **MCP-first**: Use Perses MCP tools when available, percli as fallback
- **RBAC awareness**: When creating projects in production, always set up roles and bindings — an unprotected project allows any authenticated user full access
- **Project context**: Always verify/set active project with `percli project` before operating on project-scoped resources — wrong project context silently applies resources to the wrong project

### Default Behaviors (ON unless disabled)
- **Simple create**: Create project with default settings unless RBAC is requested
- **Set active**: After creating a project, set it as the active project context

### Optional Behaviors (OFF unless enabled)
- **RBAC setup**: Create roles and role bindings alongside project creation
- **Multi-project**: Create multiple projects in batch for team onboarding

## What This Skill CAN Do
- Create, list, describe, and delete projects
- Set up roles with granular permissions (read/create/update/delete on specific resource types)
- Create role bindings to assign users to roles
- Switch active project context
- Manage global roles and global role bindings

## What This Skill CANNOT Do
- Manage user accounts (that's Perses server admin configuration)
- Configure authentication providers (use perses-deploy)
- Create dashboards or datasources (use perses-dashboard-create, perses-datasource-manage)

---

## Instructions

### Phase 1: CREATE PROJECT

**Goal**: Create a new Perses project.

**Via percli**:
```bash
percli apply -f - <<EOF
kind: Project
metadata:
  name: <project-name>
spec: {}
EOF

# Set as active project
percli project <project-name>
```

**Via MCP** (preferred):
```
perses_create_project(project="<project-name>")
```

**Gate**: Project created and set as active context. Proceed to Phase 2 if RBAC is needed, otherwise task complete.

### Phase 2: CONFIGURE RBAC (optional)

**Goal**: Set up roles and role bindings for access control.

**Step 1: Create a role**

Roles define what actions are allowed on which resource types within a project:

```bash
percli apply -f - <<EOF
kind: Role
metadata:
  name: dashboard-editor
  project: <project-name>
spec:
  permissions:
    - actions: [read, create, update]
      scopes: [Dashboard, Datasource, Variable]
EOF
```

**Available actions**: read, create, update, delete

**Available scopes** (resource types): Dashboard, Datasource, EphemeralDashboard, Folder, Role, RoleBinding, Secret, Variable

For organization-wide roles, use GlobalRole:
```bash
percli apply -f - <<EOF
kind: GlobalRole
metadata:
  name: org-viewer
spec:
  permissions:
    - actions: [read]
      scopes: ["*"]
EOF
```

**Step 2: Create a role binding**

Role bindings assign users or groups to roles:

```bash
percli apply -f - <<EOF
kind: RoleBinding
metadata:
  name: team-editors
  project: <project-name>
spec:
  role: dashboard-editor
  subjects:
    - kind: User
      name: user@example.com
EOF
```

For global role bindings:
```bash
percli apply -f - <<EOF
kind: GlobalRoleBinding
metadata:
  name: org-viewers
spec:
  role: org-viewer
  subjects:
    - kind: User
      name: viewer@example.com
EOF
```

**Gate**: Roles and bindings created. Proceed to Phase 3.

### Phase 3: VERIFY

**Goal**: Confirm project, roles, and bindings are correctly configured.

```bash
# List projects
percli get project

# Describe project
percli describe project <project-name>

# List roles in project
percli get role --project <project-name>

# List role bindings in project
percli get rolebinding --project <project-name>

# List global roles
percli get globalrole

# List global role bindings
percli get globalrolebinding
```

Or via MCP:
```
perses_list_projects()
```

**Gate**: Project listed, roles and bindings confirmed. Task complete.
