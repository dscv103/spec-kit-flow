# SpecKitFlow Implementation Plan

## Project Overview

**SpecKitFlow** is a fork of GitHub's spec-kit that enables parallel implementation through DAG-based orchestration and git worktrees. It allows developers to run multiple concurrent sessions of the same AI agent (starting with GitHub Copilot) working on independent tasks simultaneously, targeting 60-70% reduction in implementation time.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Package structure | Monorepo with Hatch workspaces | Easier development, separate PyPI packages for users |
| Primary agent | GitHub Copilot (IDE notification mode) | Most common, prompts user to open worktrees in VS Code |
| State persistence | YAML | Human-readable, matches existing spec-kit patterns |
| Completion detection | Dual: file watching + manual command | Redundancy for reliability |
| IPC mechanism | File-based (touch files) | Simple, no daemon required |
| DAG location | `specs/{branch}/dag.yaml` | Transparent, version-controlled |
| Shared utilities | `speckit-core` package | Avoid duplication between specify-cli and speckit-flow |

## Package Structure

```
spec-kit-flow/                          # Monorepo root
├── pyproject.toml                      # Hatch workspaces configuration
├── src/
│   ├── specify_cli/                    # Existing CLI (entry point: specify)
│   │   └── __init__.py
│   ├── speckit_core/                   # NEW: Shared library (no entry point)
│   │   ├── __init__.py
│   │   ├── paths.py                    # Repository/feature path utilities
│   │   ├── tasks.py                    # Task parsing with DAG markers
│   │   ├── models.py                   # Pydantic data models
│   │   └── config.py                   # YAML configuration loading
│   └── speckit_flow/                   # NEW: Orchestrator (entry points: skf, speckit-flow)
│       ├── __init__.py                 # Typer CLI
│       ├── orchestration/
│       │   ├── dag_engine.py           # DAG construction and analysis
│       │   ├── scheduler.py            # Task-to-session assignment
│       │   ├── session_coordinator.py  # Multi-session lifecycle
│       │   └── completion.py           # Completion detection
│       ├── agents/
│       │   ├── base.py                 # Abstract AgentAdapter
│       │   └── copilot.py              # Copilot IDE notification adapter
│       ├── worktree/
│       │   ├── manager.py              # Git worktree CRUD
│       │   └── merger.py               # Branch integration
│       ├── monitoring/
│       │   └── dashboard.py            # Rich terminal UI
│       └── state/
│           ├── manager.py              # YAML state persistence
│           └── recovery.py             # Checkpoint/restore
```

## Runtime Artifacts

```
project-root/
├── .speckit/
│   ├── speckit-flow.yaml              # Project configuration
│   ├── flow-state.yaml                # Current orchestration state
│   ├── flow-state.yaml.lock           # File lock for concurrent access
│   ├── checkpoints/
│   │   └── {timestamp}.yaml           # State snapshots
│   └── completions/
│       └── {task_id}.done             # Manual completion markers
├── .worktrees-{spec-id}/
│   ├── session-0-{task-name}/         # Session 0 worktree
│   ├── session-1-{task-name}/         # Session 1 worktree
│   └── session-N-{task-name}/         # Session N worktree
└── specs/{branch}/
    ├── spec.md                         # Feature specification
    ├── plan.md                         # Implementation plan
    ├── tasks.md                        # Task breakdown (with DAG markers)
    └── dag.yaml                        # Generated DAG definition
```

## Task Format Extension

Extend existing tasks.md format to support DAG dependencies:

```markdown
## Current Format
- [ ] [T001] [P] [US1] Implement User model in src/models/User.ts

## Extended Format (backward compatible)
- [ ] [T001] [P] [US1] [deps:] Implement User model in src/models/User.ts
- [ ] [T002] [P] [US1] [deps:T001] Add User validation in src/models/User.ts
- [ ] [T003] [P] [US2] [deps:T001,T002] Create UserService in src/services/UserService.ts
```

Markers:
- `[T###]` - Task ID (required)
- `[P]` - Parallelizable (optional, indicates no shared file dependencies)
- `[US#]` - User story mapping (optional)
- `[deps:T###,T###]` - Explicit dependencies (optional, empty `[deps:]` = no dependencies)

## DAG YAML Schema

```yaml
# specs/{branch}/dag.yaml
version: "1.0"
spec_id: "001-feature-name"
generated_at: "2025-11-28T10:30:00Z"
num_sessions: 3

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Initialize project structure"
        description: "Set up base configuration and dependencies"
        files: ["package.json", "tsconfig.json"]
        dependencies: []
        session: 0
        parallelizable: false
        story: null
        
  - name: "phase-1"
    tasks:
      - id: "T002"
        name: "Implement User model"
        description: "Create User entity with validation"
        files: ["src/models/User.ts", "src/models/__tests__/User.test.ts"]
        dependencies: ["T001"]
        session: 0
        parallelizable: true
        story: "US1"
        
      - id: "T003"
        name: "Implement Task model"
        description: "Create Task entity with status tracking"
        files: ["src/models/Task.ts", "src/models/__tests__/Task.test.ts"]
        dependencies: ["T001"]
        session: 1
        parallelizable: true
        story: "US2"
```

## Orchestration State Schema

```yaml
# .speckit/flow-state.yaml
version: "1.0"
spec_id: "001-feature-name"
agent_type: "copilot"
num_sessions: 3
base_branch: "main"
started_at: "2025-11-28T10:30:00Z"
updated_at: "2025-11-28T11:45:00Z"

current_phase: "phase-1"
phases_completed: ["phase-0"]

sessions:
  - session_id: 0
    worktree_path: ".worktrees-001/session-0-user-model"
    branch_name: "impl-001-session-0"
    current_task: "T002"
    completed_tasks: ["T001"]
    status: "executing"  # idle, executing, waiting, completed, failed
    
  - session_id: 1
    worktree_path: ".worktrees-001/session-1-task-model"
    branch_name: "impl-001-session-1"
    current_task: "T003"
    completed_tasks: []
    status: "executing"

tasks:
  T001: {status: "completed", session: 0, completed_at: "2025-11-28T10:45:00Z"}
  T002: {status: "in_progress", session: 0, started_at: "2025-11-28T10:46:00Z"}
  T003: {status: "in_progress", session: 1, started_at: "2025-11-28T10:46:00Z"}
  T004: {status: "pending", session: null}

merge_status: null  # null, in_progress, completed, failed
```

## CLI Commands

### Phase 1 Commands

| Command | Description |
|---------|-------------|
| `skf dag` | Parse tasks.md, build DAG, write specs/{branch}/dag.yaml |
| `skf dag --visualize` | Display ASCII tree of phases and tasks |

### Phase 2 Commands

| Command | Description |
|---------|-------------|
| `skf init --sessions N` | Create .speckit/speckit-flow.yaml configuration |
| `skf run` | Execute full orchestration with IDE prompts |
| `skf status` | Display current progress and session states |
| `skf complete TASK_ID` | Manually mark task as completed |
| `skf merge [--keep-worktrees]` | Integrate all session branches |
| `skf abort` | Terminate orchestration, cleanup worktrees |

## Implementation Phases

### Phase 1: Core Infrastructure

**Goal**: Working `skf dag` command that generates DAG from tasks.md

**Duration**: Steps 1-8

**Deliverables**:
1. Hatch monorepo structure with 3 packages
2. `speckit-core` library with path utilities, task parsing, Pydantic models
3. `speckit-flow` package skeleton with all submodules
4. YAML state management with checkpoints
5. DAG engine using networkx
6. Worktree manager wrapping git commands
7. Copilot adapter stub (IDE notification)
8. Working `skf dag` and `skf dag --visualize` commands

### Phase 2: Orchestration & Integration

**Goal**: Full parallel orchestration system

**Duration**: Steps 9-13

**Deliverables**:
1. File-based completion detection (watchfiles + touch files)
2. Session coordinator managing parallel phases
3. Merge orchestrator with conflict detection
4. All remaining CLI commands
5. Rich monitoring dashboard
6. specify-cli refactored to use speckit-core

## Dependencies

### speckit-core

```toml
dependencies = [
    "pydantic>=2.0",
    "pyyaml",
]
```

### speckit-flow

```toml
dependencies = [
    "speckit-core",
    "typer",
    "rich",
    "networkx",
    "pyyaml",
    "pydantic>=2.0",
    "filelock",
    "watchfiles",
]
```

## Success Criteria

### Performance
- 60-70% reduction in implementation time with 3+ concurrent sessions
- Sub-second DAG generation for typical specs (10-20 tasks)
- Zero merge conflicts during isolated worktree development

### Reliability
- Checkpoint recovery after session/system failure
- Graceful degradation to sequential execution if needed
- Atomic state updates preventing corruption

### Developer Experience
- Intuitive slash command extension of spec-kit
- Clear IDE prompts for each session action
- Real-time progress visibility
- One-command merge with conflict detection

## References

- [Original spec-kit](https://github.com/github/spec-kit)
- [Spec-Driven Development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [Git Worktrees for AI Agents](https://nx.dev/blog/git-worktrees-ai-agents)
- [Parallel Copilot Workflow](https://harrybin.de/posts/parallel-github-copilot-workflow/)
