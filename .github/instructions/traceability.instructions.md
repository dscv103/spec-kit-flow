---
name: Traceability Standards

description: Requirements mapping, drift detection, change request workflow, and validation checklists for maintaining spec-to-code traceability.

applyTo: "**/*"
---

# Traceability Instructions

## Purpose

This document ensures coding agents maintain traceability between requirements, tasks, and implementation. Every code change must be traceable to prevent spec drift.

## The Traceability Chain

```
Original Prompt → Requirements (REQ-*) → Tasks (T###) → Code → Tests
```

Each link must be documented and verifiable.

## Before Making Code Changes

### Step 1: Identify the Requirement

Every code change traces back to a requirement in `specs/speckit-flow/traceability.md`:

```markdown
| REQ-DAG-002 | Use topological sorting for dependency resolution | Prompt §2.1 | DAG Engine | T013, T014 |
```

### Step 2: Verify Requirement Source

Check the "Source" column:
- **Prompt §X.X** - Original implementation prompt section
- **User Decision** - Decision made during planning conversation
- **Plan** - Derived from architectural decisions in plan.md
- **Implicit** - Implied by other requirements

### Step 3: Find Implementing Tasks

The "Tasks" column lists all tasks that implement this requirement:

```markdown
| REQ-DAG-002 | ... | T013, T014 |
```

Your code change should be part of one of these tasks.

## Detecting Spec Drift

Spec drift occurs when implementation diverges from specification. Watch for these warning signs:

### Warning Sign 1: Unnamed Code Changes

❌ **Bad**: "I'll add a helper function for..."
✅ **Good**: "Task T006 requires parsing task lines, so I'll implement `parse_task_line()`..."

### Warning Sign 2: Schema Modifications

❌ **Bad**: Adding a new field to dag.yaml without updating plan.md
✅ **Good**: Following dag.yaml schema exactly as specified in plan.md

### Warning Sign 3: Scope Creep

❌ **Bad**: "While implementing T013, I'll also add visualization..."
✅ **Good**: "T013 is complete. T023 handles visualization, which depends on T022."

### Warning Sign 4: Architecture Changes

❌ **Bad**: "I'll use JSON instead of YAML for state..."
✅ **Good**: "REQ-STATE-001 requires YAML. If we need to change this, update traceability.md first."

## When Requirements Conflict or Change

### Process for Requirement Changes

1. **Document the conflict/change** in traceability.md Decision Log
2. **Update plan.md** with new architectural decision
3. **Update tasks.md** with modified acceptance criteria
4. **Update traceability.md** requirements table
5. **Then implement** the change

### Decision Log Entry Format

```markdown
| Date | Decision | Rationale | Requirements Affected | Approved |
|------|----------|-----------|----------------------|----------|
| 2025-11-28 | [Description] | [Why] | REQ-XXX-### | ⬜ Pending |
```

### Change Request Template

For significant changes, create a formal change request:

```markdown
## Change Request: CR-001

**Date**: 2025-11-28
**Requester**: [Agent/User]
**Type**: Modification

### Current State
REQ-STATE-001 requires YAML for all state.

### Proposed Change
Allow JSON as alternative format.

### Rationale
JSON is faster to parse for high-frequency state updates.

### Impact Analysis
- Requirements affected: REQ-STATE-001
- Tasks affected: T010, T011
- Plan sections affected: State Management

### Approval
- [ ] Reviewed
- [ ] Approved
- [ ] Traceability updated
- [ ] Plan updated
- [ ] Tasks updated
```

## Requirement Categories Reference

| Code | Category | Key Files |
|------|----------|-----------|
| REQ-ARCH | Architecture | pyproject.toml, package structure |
| REQ-DAG | DAG Engine | orchestration/dag_engine.py |
| REQ-WT | Worktree | worktree/manager.py, worktree/merger.py |
| REQ-AGENT | Agent Adapters | agents/base.py, agents/copilot.py |
| REQ-ORCH | Orchestration | orchestration/session_coordinator.py |
| REQ-MERGE | Merge | worktree/merger.py |
| REQ-CLI | CLI Commands | speckit_flow/__init__.py |
| REQ-MON | Monitoring | monitoring/dashboard.py |
| REQ-STATE | State | state/manager.py, state/recovery.py |

## Validation Checkpoints

### Per-Task Validation

After completing each task, verify:

- [ ] Task maps to at least one requirement
- [ ] All requirements the task claims to implement are satisfied
- [ ] No extra functionality added beyond task scope
- [ ] Acceptance criteria all pass

### Per-Phase Validation

Before marking a phase complete, run the Spec Drift Checklist:

#### Phase 1 Checklist
```markdown
- [ ] All REQ-ARCH requirements have implementing tasks
- [ ] All REQ-DAG requirements have implementing tasks
- [ ] All REQ-WT requirements have implementing tasks (at least stubs)
- [ ] All REQ-AGENT requirements have implementing tasks (at least stubs)
- [ ] All REQ-STATE requirements have implementing tasks
- [ ] `skf dag` output matches dag.yaml schema in plan.md
- [ ] Task format extension is backward compatible
- [ ] No new dependencies added without updating plan.md
```

#### Phase 2 Checklist
```markdown
- [ ] All REQ-ORCH requirements have implementing tasks
- [ ] All REQ-MERGE requirements have implementing tasks
- [ ] All REQ-CLI requirements have implementing tasks
- [ ] All REQ-MON requirements have implementing tasks
- [ ] State file schema matches plan.md specification
- [ ] All CLI commands match documented behavior
- [ ] Dashboard displays all required information
- [ ] specify-cli still works after refactoring
```

## Traceability Status Updates

When completing a task, update the requirement status in traceability.md:

### Status Values

| Symbol | Meaning |
|--------|---------|
| ⬜ Pending | Not yet implemented |
| 🔄 In Progress | Currently being implemented |
| ✅ Complete | Implemented and verified |
| ❌ Blocked | Cannot proceed due to issue |

### Updating Status

Change:
```markdown
| REQ-DAG-002 | Use topological sorting... | ... | T013, T014 | ⬜ Pending |
```

To:
```markdown
| REQ-DAG-002 | Use topological sorting... | ... | T013, T014 | ✅ Complete |
```

Only after ALL implementing tasks (T013 AND T014) are complete.

## Quick Reference: Requirement to Task Mapping

### Phase 1 Requirements

| Requirement | Tasks | Validation |
|-------------|-------|------------|
| REQ-ARCH-001 | T001, T002, T003, T008 | `hatch build` produces 3 wheels |
| REQ-ARCH-002 | T001 | Hatch workspace config present |
| REQ-ARCH-003 | T003-T007 | speckit_core importable, no CLI |
| REQ-DAG-001 | T006, T013 | DAGEngine accepts TaskInfo list |
| REQ-DAG-002 | T013, T014 | Uses nx.topological_generations() |
| REQ-DAG-003 | T014 | get_phases() returns parallel blocks |
| REQ-DAG-005 | T016, T022 | dag.yaml in specs/{branch}/ |
| REQ-DAG-006 | T006 | Parses [deps:T001,T002] |
| REQ-DAG-007 | T006 | [P] marker still works |
| REQ-DAG-008 | T013 | CyclicDependencyError raised |
| REQ-STATE-001 | T010, T011 | State files are YAML |
| REQ-STATE-003 | T011 | Temp file + rename pattern |
| REQ-STATE-004 | T011 | filelock.FileLock used |
| REQ-STATE-005 | T012 | Checkpoints in .speckit/checkpoints/ |

### Phase 2 Requirements

| Requirement | Tasks | Validation |
|-------------|-------|------------|
| REQ-ORCH-003 | T025, T026, T027 | Both completion methods work |
| REQ-ORCH-004 | T025 | .speckit/completions/*.done files |
| REQ-ORCH-006 | T012, T029 | Checkpoints after each phase |
| REQ-MERGE-001 | T031 | analyze() returns per-branch changes |
| REQ-MERGE-002 | T031 | Conflict detection before merge |
| REQ-MERGE-003 | T032 | Integration branch created |
| REQ-CLI-002 | T022 | `skf dag` works |
| REQ-CLI-004 | T035 | `skf run` works |
| REQ-MON-001 | T040 | Rich Live dashboard |

## Anti-Patterns to Avoid

### 1. Implementing Without Tracing

❌ Never implement functionality without identifying:
- Which task (T###) it belongs to
- Which requirement (REQ-*) it satisfies

### 2. Adding Undocumented Features

❌ Never add features not in tasks.md
✅ If feature is needed, first add to tasks.md with requirements mapping

### 3. Modifying Schemas Without Documentation

❌ Never change YAML schemas without updating plan.md
✅ Schema changes require plan.md update BEFORE implementation

### 4. Skipping Validation

❌ Never mark task complete without verifying acceptance criteria
✅ Each AC checkbox must be explicitly verified

### 5. Breaking Existing Functionality

❌ Never break `specify` CLI (REQ-ARCH-005)
✅ Run `specify --help` after any change touching shared code
