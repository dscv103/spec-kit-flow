# Session Distribution Fix

## Issue

When running `skf dag --visualize` with 4 configured agents, all tasks were being assigned to Session 0, despite having multiple sessions available.

## Root Cause

The `assign_sessions()` method in [dag_engine.py](../src/speckit_flow/orchestration/dag_engine.py) was too conservative in its session assignment logic:

**Previous behavior:**
```python
# Check if all tasks in phase are parallelizable
all_parallel = all(t.parallelizable for t in phase_tasks)

if not all_parallel or len(phase) == 1:
    # Assign all to session 0
    for task in phase_tasks:
        task.session = 0
else:
    # Round-robin assignment
    for idx, task in enumerate(phase_tasks):
        task.session = idx % num_sessions
```

This meant that if **any** task in a phase lacked the explicit `[P]` (parallelizable) marker, **all** tasks in that phase would be assigned to Session 0.

## The Fix

The `parallelizable` flag is **informational only** and should not control session distribution. Tasks in the same phase can execute in parallel **by definition** (they have no dependencies on each other).

**New behavior:**
```python
for phase in phases:
    phase_tasks = [self.get_task(tid) for tid in phase]
    
    if len(phase) == 1:
        # Single task: assign to session 0
        phase_tasks[0].session = 0
    else:
        # Multiple tasks in same phase: distribute round-robin
        # (tasks in same phase have no dependencies on each other)
        for idx, task in enumerate(phase_tasks):
            task.session = idx % num_sessions
```

## What Changed

1. **Removed** the `all_parallel` check
2. **Simplified** logic to: single-task phases go to session 0, multi-task phases distribute round-robin
3. **Updated** docstring to reflect that tasks in same phase are parallel by definition

## Why This is Correct

The DAG phase structure guarantees safe parallelization:

- **Phase N** contains tasks that depend only on tasks from phases 0..N-1
- Tasks **within the same phase** have no inter-dependencies
- Therefore, tasks in the same phase **can always run concurrently**

The `[P]` marker is a hint for human readers and planning purposes, but the DAG structure itself determines what's actually parallelizable.

## Impact

- Tasks without explicit `[P]` markers now distribute correctly across sessions
- Multi-agent workflows work as expected without requiring manual markers
- The `[P]` flag remains useful for documentation and planning, but doesn't control runtime behavior

## Test Updates

Updated [test_dag_sessions.py](../tests/unit/speckit_flow/orchestration/test_dag_sessions.py) to reflect the new behavior:

- Removed reliance on `parallelizable=True` in test setup
- Updated docstrings to clarify phase-based distribution
- Added test case for mixed `parallelizable` flags in same phase

## Example

**Before the fix:**
```
Phase 1 (4 tasks)
├── T029 Create formatter [Session 0]
├── T030 Create exporter [Session 0]
├── T031 Add options [Session 0]
└── T032 Add error handling [Session 0]
```

**After the fix (with 4 sessions):**
```
Phase 1 (4 tasks)
├── T029 Create formatter [Session 0]
├── T030 Create exporter [Session 1]
├── T031 Add options [Session 2]
└── T032 Add error handling [Session 3]
```

## Try It

Run `skf dag --visualize` again to see tasks properly distributed across your 4 configured sessions!

```bash
# In your project
skf dag --sessions 4 --visualize
```

You should now see different session numbers assigned to tasks in the same phase.
