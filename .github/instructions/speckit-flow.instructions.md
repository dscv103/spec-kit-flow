---
name: SpecKitFlow Development

description: Core development instructions for SpecKitFlow parallel DAG-based orchestration. Architecture constraints, package structure, and implementation governance.

applyTo: "**/*"
---

# SpecKitFlow Development Instructions

## Overview

You are implementing **SpecKitFlow**, a parallel DAG-based orchestration system for AI coding agents. This project is a fork of GitHub's spec-kit that enables multiple concurrent agent sessions working on independent tasks via git worktrees.

## Critical Documents

Before making ANY code changes, you MUST read and understand:

1. **[specs/speckit-flow/plan.md](../../specs/speckit-flow/plan.md)** - Architecture decisions, package structure, schemas
2. **[specs/speckit-flow/tasks.md](../../specs/speckit-flow/tasks.md)** - Atomic tasks with acceptance criteria
3. **[specs/speckit-flow/traceability.md](../../specs/speckit-flow/traceability.md)** - Requirements matrix and drift detection

## Instruction Files

The following instruction files establish quality standards for implementation:

| File | Purpose | When to Reference |
|------|---------|-------------------|
| [code-quality.instructions.md](code-quality.instructions.md) | Code principles, type safety, error handling | Every code change |
| [testing.instructions.md](testing.instructions.md) | Testing standards, AAA pattern, coverage | Writing tests |
| [user-experience.instructions.md](user-experience.instructions.md) | CLI UX, Rich formatting, error messages | User-facing features |
| [performance.instructions.md](performance.instructions.md) | Performance targets, optimization patterns | Performance-critical code |
| [task-workflow.instructions.md](task-workflow.instructions.md) | Task identification, completion workflow | Starting/finishing tasks |
| [traceability.instructions.md](traceability.instructions.md) | Requirements mapping, drift detection | Architecture changes |

## Governance: Guiding Principles

These principles guide all technical decisions and implementation choices:

### Principle Hierarchy

When principles conflict, resolve in this order:

1. **Correctness** - Code must work correctly before anything else
2. **Maintainability** - Code must be readable and modifiable
3. **Usability** - User experience must be intuitive and helpful
4. **Performance** - Code must meet performance targets

### Decision Framework

When making technical decisions:

1. **Check the plan first** - plan.md contains binding architecture decisions
2. **Map to requirements** - Every feature must trace to a requirement in traceability.md
3. **Follow established patterns** - Use patterns from instruction files consistently
4. **Document deviations** - If you must deviate, update relevant docs and traceability.md

### Change Governance

| Change Type | Required Actions |
|-------------|------------------|
| Bug fix | Follow code-quality.instructions.md, add regression test |
| New feature | Verify requirement mapping, follow all instruction files |
| Architecture change | Update plan.md, traceability.md, get approval |
| Schema change | Update plan.md schema, update affected tests |
| Performance fix | Document baseline, verify improvement, add benchmark test |
| UX change | Follow user-experience.instructions.md, verify consistency |

### Non-Negotiable Standards

These standards apply to ALL code changes without exception:

- **Type hints** on all public functions (code-quality)
- **Docstrings** on all public classes and functions (code-quality)
- **Unit tests** for all business logic (testing)
- **Atomic writes** for all state files (performance/correctness)
- **File locking** for concurrent access (correctness)
- **Error messages** must be helpful with next steps (user-experience)

## Architecture Constraints

### Package Structure (Monorepo with Hatch Workspaces)

```
src/
├── specify_cli/      # Existing CLI - DO NOT BREAK
├── speckit_core/     # Shared library (NO entry point)
└── speckit_flow/     # New orchestrator (entry points: skf, speckit-flow)
```

### Key Decisions (DO NOT CHANGE without updating traceability.md)

| Decision | Choice | Document Reference |
|----------|--------|-------------------|
| Package manager | Hatch workspaces | plan.md §Package Structure |
| State format | YAML only | plan.md §Architecture Decisions |
| Primary agent | Copilot (IDE notification mode) | plan.md §Architecture Decisions |
| Completion detection | Dual (file watch + touch files) | plan.md §Architecture Decisions |
| DAG location | `specs/{branch}/dag.yaml` | plan.md §Runtime Artifacts |

## Implementation Rules

### Before Starting Any Task

1. Identify the task ID (T001-T043) from tasks.md
2. Read ALL acceptance criteria for that task
3. Check dependencies - ensure prerequisite tasks are complete
4. Verify the task maps to requirements in traceability.md

### During Implementation

1. **Follow the schemas exactly** - DAG YAML, state YAML, and config formats are defined in plan.md
2. **Use Pydantic v2 syntax** - Not v1 (see T005 acceptance criteria)
3. **Preserve backward compatibility** - Existing `[P]` marker format must still work (REQ-DAG-007)
4. **Atomic state writes** - Use temp file + rename pattern (REQ-STATE-003)
5. **File locking** - Use `filelock` for concurrent access (REQ-STATE-004)

### After Completing a Task

1. Verify ALL acceptance criteria checkboxes can be checked
2. Update tasks.md to mark task complete: `- [x] [T###]`
3. Run relevant tests if they exist
4. Do NOT proceed to dependent tasks until current task is fully validated

## Code Style Requirements

### Python Standards

- Python 3.11+ required
- Type hints on all public functions
- Docstrings for all public classes and functions
- Use `pathlib.Path` for all file operations
- Use `subprocess.run()` with `check=True` for git commands

### Import Patterns

```python
# speckit_core imports (shared library)
from speckit_core.paths import get_repo_root, get_feature_paths
from speckit_core.tasks import parse_tasks_file
from speckit_core.models import TaskInfo, FeatureContext
from speckit_core.config import load_config

# speckit_flow internal imports
from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.state.manager import StateManager
from speckit_flow.worktree.manager import WorktreeManager
```

### Error Handling

Define custom exceptions in appropriate modules:
- `speckit_core.exceptions`: `NotInGitRepoError`, `FeatureNotFoundError`
- `speckit_flow.exceptions`: `CyclicDependencyError`, `StateNotFoundError`, `WorktreeExistsError`

## Phase Boundaries

### Phase 1 Scope (T001-T024)

**Goal**: Working `skf dag` command

**Deliverables**:
- Three-package Hatch monorepo structure
- speckit_core with paths, tasks, models, config modules
- speckit_flow skeleton with all subpackages
- DAG engine with networkx
- `skf dag` and `skf dag --visualize` commands

**DO NOT** implement Phase 2 features (orchestration, merge, dashboard) during Phase 1.

### Phase 2 Scope (T025-T043)

**Goal**: Full parallel orchestration

**Prerequisites**: ALL Phase 1 tasks must be complete and validated.

## Validation Checkpoints

### Before Committing Code

- [ ] Task acceptance criteria met
- [ ] No regressions to `specify` CLI functionality
- [ ] Imports resolve correctly
- [ ] Type hints present on public API
- [ ] Docstrings present on public API

### Before Completing a Phase

Run the Spec Drift Checklist from traceability.md:
- [ ] All requirements for this phase have implementing tasks
- [ ] Schemas match plan.md specification
- [ ] No undocumented dependencies added

## Common Pitfalls to Avoid

1. **Don't modify specify_cli directly** - Extract to speckit_core first (T043)
2. **Don't use Pydantic v1 syntax** - Use `model_dump()` not `dict()`, `model_validate()` not `parse_obj()`
3. **Don't hardcode paths** - Use `speckit_core.paths` utilities
4. **Don't skip atomic writes** - State corruption is unrecoverable
5. **Don't forget file locking** - Multiple agents may access state concurrently

## Quick Reference: Key Files

| Purpose | Location |
|---------|----------|
| Hatch config | `pyproject.toml` |
| CLI entry point | `src/speckit_flow/__init__.py` |
| DAG engine | `src/speckit_flow/orchestration/dag_engine.py` |
| State management | `src/speckit_flow/state/manager.py` |
| Worktree ops | `src/speckit_flow/worktree/manager.py` |
| Copilot adapter | `src/speckit_flow/agents/copilot.py` |
| Shared models | `src/speckit_core/models.py` |
| Task parsing | `src/speckit_core/tasks.py` |

## When in Doubt

1. Re-read plan.md for architectural guidance
2. Check traceability.md for requirement sources
3. Verify task dependencies in tasks.md
4. Ask for clarification rather than assuming
