---
name: Task Workflow

description: Task identification, dependency verification, acceptance criteria validation, and completion workflow for implementing SpecKitFlow tasks.

applyTo: "**/*"
---

# Task Workflow Instructions

## Purpose

This document ensures coding agents follow the correct workflow when implementing tasks from `specs/speckit-flow/tasks.md`. Every code change MUST be traceable to a specific task.

## Task Identification

Tasks are identified by their ID pattern: `[T###]` where ### is a 3-digit number (T001-T043).

### Task Format in tasks.md

```markdown
- [ ] [T001] [deps:] **Task Title**
  - Description line 1
  - Description line 2
  - **AC**:
    - [ ] Acceptance criterion 1
    - [ ] Acceptance criterion 2
```

### Task Markers

| Marker | Meaning |
|--------|---------|
| `[T###]` | Task ID (required) |
| `[P]` | Parallelizable (can run alongside other [P] tasks in same phase) |
| `[deps:T001,T002]` | Dependencies (must complete first) |
| `[deps:]` | No dependencies |
| `**AC**:` | Acceptance Criteria section |

## Workflow: Before Starting a Task

### Step 1: Identify the Task

When asked to implement something, first map it to a task ID:

```
User: "Implement the DAG engine"
→ This maps to T013, T014, T015, T016 (Step 5 in tasks.md)
```

### Step 2: Check Dependencies

Look at the `[deps:]` marker. ALL dependencies must be complete:

```markdown
- [ ] [T013] [deps:T006,T010] **Implement orchestration/dag_engine.py core**
```

This task requires T006 (tasks.py) and T010 (state/models.py) to be complete first.

**If dependencies are incomplete**: Stop and complete them first, or inform the user.

### Step 3: Read Full Task Details

Read the entire task block including ALL acceptance criteria:

```markdown
- [ ] [T013] [deps:T006,T010] **Implement orchestration/dag_engine.py core**
  - Create `DAGEngine(tasks: list[TaskInfo])` class
  - Implement `build_graph() -> nx.DiGraph` creating nodes with task data, edges from dependencies
  - Implement `validate() -> bool` checking `nx.is_directed_acyclic_graph()`
  - Raise `CyclicDependencyError` with cycle path if validation fails
  - **AC**:
    - [ ] Creates valid networkx DiGraph from task list
    - [ ] Node attributes contain full TaskInfo data
    - [ ] Detects and reports circular dependencies
    - [ ] Handles empty task list gracefully
```

### Step 4: Cross-Reference Requirements

Check traceability.md for the requirement(s) this task implements:

```markdown
| REQ-DAG-001 | Parse implementation plans to construct DAG | ... | T006, T013 | ⬜ Pending |
| REQ-DAG-008 | Detect and report circular dependencies | ... | T013 | ⬜ Pending |
```

Ensure your implementation satisfies the original requirement intent.

## Workflow: During Implementation

### Rule 1: One Task at a Time

Focus on completing ONE task fully before moving to the next. Do not partially implement multiple tasks.

### Rule 2: Follow Acceptance Criteria Literally

Each acceptance criterion is a testable condition. Your code must satisfy it exactly:

```markdown
- [ ] Creates valid networkx DiGraph from task list
```

This means: The method returns a `networkx.DiGraph` object that passes `nx.is_directed_acyclic_graph()`.

### Rule 3: Match Schemas Exactly

If plan.md defines a schema, match it exactly:

```yaml
# From plan.md - DAG YAML Schema
version: "1.0"
spec_id: "001-feature-name"
generated_at: "2025-11-28T10:30:00Z"
num_sessions: 3
phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        # ... exact fields as specified
```

Do not add extra fields. Do not omit required fields. Do not change field names.

### Rule 4: Use Specified Patterns

When tasks specify implementation patterns, use them:

```markdown
- Implement `save(state: OrchestrationState)` with atomic write (temp file + rename)
```

This means:
```python
def save(self, state: OrchestrationState) -> None:
    temp_path = self.state_path.with_suffix('.tmp')
    temp_path.write_text(yaml.dump(state.model_dump()))
    temp_path.rename(self.state_path)  # Atomic on POSIX
```

### Rule 5: Handle Edge Cases from AC

If an acceptance criterion mentions an edge case, implement it:

```markdown
- [ ] Handles empty task list gracefully
```

This requires explicit code to handle `tasks = []`.

## Workflow: After Completing a Task

### Step 1: Verify All Acceptance Criteria

Go through each AC checkbox and verify your code satisfies it:

```markdown
- [x] Creates valid networkx DiGraph from task list  ← Verified
- [x] Node attributes contain full TaskInfo data     ← Verified
- [x] Detects and reports circular dependencies      ← Verified
- [x] Handles empty task list gracefully             ← Verified
```

### Step 2: Update tasks.md

Change the task checkbox from `[ ]` to `[x]`:

```markdown
- [x] [T013] [deps:T006,T010] **Implement orchestration/dag_engine.py core**
```

### Step 3: Verify No Regressions

If the task touches existing code:
- Run `specify --help` to verify CLI still works
- Run any existing tests

### Step 4: Commit with Task Reference

Include the task ID in your commit message:

```
[T013] Implement DAGEngine core with graph building and validation
```

## Task Dependencies Graph

### Phase 1 Critical Path

```
T001 → T002 → T008 → T009
  ↓      ↓
T003 ──→ T004, T005, T006, T007
           ↓      ↓      ↓
         T017  T010   T013
                 ↓      ↓
               T011   T014 → T015 → T016
                 ↓
               T012
                        ↓
T020 → T021          T022 → T023 → T024
```

### Parallelizable Tasks (Same Phase)

Within each step, tasks marked `[P]` can be implemented in parallel:
- Step 2: T003, T004, T005, T006, T007 (after T001 complete)
- Step 4: T010, T011, T012 (after their deps)
- Step 5: T014, T015, T016 (after T013)
- Step 6: T018, T019 (after T017)

## Error Recovery

### If You Implemented Wrong Task

1. Revert changes
2. Identify correct task
3. Start over with correct task

### If Dependencies Are Missing

1. Stop current task
2. List missing dependencies
3. Complete dependencies first
4. Resume original task

### If Acceptance Criteria Is Unclear

1. Check plan.md for schema/specification details
2. Check traceability.md for requirement source
3. Ask for clarification with specific question

## Quick Reference: Phase 1 Task Sequence

| Order | Task | Dependencies | Description |
|-------|------|--------------|-------------|
| 1 | T001 | - | pyproject.toml Hatch workspaces |
| 2 | T002 | T001 | Verify specify-cli works |
| 3 | T003 | T001 | speckit_core skeleton |
| 4 | T004 | T003 | paths.py |
| 4 | T005 | T003 | models.py |
| 4 | T006 | T003,T005 | tasks.py |
| 4 | T007 | T003,T005 | config.py |
| 5 | T008 | T002,T003 | speckit_flow skeleton |
| 6 | T009 | T008 | speckit_flow dependencies |
| 7 | T010 | T005,T008 | state/models.py |
| 7 | T011 | T010 | state/manager.py |
| 7 | T012 | T011 | state/recovery.py |
| 8 | T013 | T006,T010 | dag_engine core |
| 9 | T014 | T013 | phase generation |
| 9 | T015 | T014 | session assignment |
| 9 | T016 | T015 | DAG serialization |
| 10 | T017 | T004,T008 | worktree/manager core |
| 10 | T018 | T017 | worktree list/remove |
| 10 | T019 | T018 | spec cleanup |
| 11 | T020 | T008 | agents/base.py |
| 12 | T021 | T020 | agents/copilot.py |
| 13 | T022 | T004,T006,T016 | skf dag command |
| 14 | T023 | T022 | skf dag --visualize |
| 15 | T024 | T023 | skf dag --sessions |
