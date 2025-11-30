# SpecKitFlow Traceability Matrix

## Purpose

This document tracks the relationship between original requirements (from the implementation prompt), plan decisions, and implementation tasks. Use this matrix to:

1. Verify all requirements are addressed
2. Trace changes back to original intent
3. Detect and prevent spec drift during implementation
4. Validate completeness before delivery

---

## Requirement Categories

| Code | Category | Description |
|------|----------|-------------|
| REQ-ARCH | Architecture | Core system design requirements |
| REQ-DAG | DAG Engine | Task graph and dependency management |
| REQ-WT | Worktree | Git worktree isolation and management |
| REQ-AGENT | Agent Adapters | AI agent integration |
| REQ-ORCH | Orchestration | Parallel execution coordination |
| REQ-MERGE | Merge | Branch integration and conflict handling |
| REQ-CLI | CLI Commands | User-facing command interface |
| REQ-MON | Monitoring | Progress tracking and visualization |
| REQ-STATE | State | Persistence and recovery |

---

## Requirements Traceability

### REQ-ARCH: Architecture Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-ARCH-001 | Monorepo with 3 packages: specify-cli, speckit-core, speckit-flow | User Decision | Package Structure | T001, T002, T003, T008 | ✅ Complete |
| REQ-ARCH-002 | Hatch workspaces for package management | User Decision | Package Structure | T001 | ✅ Complete |
| REQ-ARCH-003 | speckit-core as shared library (no CLI entry point) | User Decision | Package Structure | T003-T007 | ✅ Complete |
| REQ-ARCH-004 | Entry points: `skf` and `speckit-flow` for speckit-flow package | Plan | Package Structure | T008 | ✅ Complete |
| REQ-ARCH-005 | Preserve existing `specify` CLI functionality | Implicit | Package Structure | T002, T043 | ✅ Complete |

### REQ-DAG: DAG Engine Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-DAG-001 | Parse implementation plans to construct DAG | Prompt §2.1 | DAG Engine | T006, T013 | ✅ Complete |
| REQ-DAG-002 | Use topological sorting for dependency resolution | Prompt §2.1 | DAG Engine | T013, T014 | ✅ Complete |
| REQ-DAG-003 | Identify parallel execution blocks (no inter-dependencies) | Prompt §2.1 | DAG Engine | T014 | ✅ Complete |
| REQ-DAG-004 | Assign tasks to sessions based on availability | Prompt §2.1 | DAG Engine | T015 | ✅ Complete |
| REQ-DAG-005 | Generate dag.yaml in specs/{branch}/ | User Decision | DAG YAML Schema | T016, T022 | ✅ Complete |
| REQ-DAG-006 | Extend task format with [deps:T001,T002] markers | Plan | Task Format Extension | T006 | ✅ Complete |
| REQ-DAG-007 | Backward compatible with existing [P] marker format | Plan | Task Format Extension | T006 | ✅ Complete |
| REQ-DAG-008 | Detect and report circular dependencies | Prompt §2.1 | DAG Engine | T013 | ✅ Complete |
| REQ-DAG-009 | Critical path analysis for optimal distribution | Prompt §2.1 | DAG Engine | T014 | ✅ Complete |

### REQ-WT: Worktree Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-WT-001 | Create isolated git worktrees for each session | Prompt §2.2 | Worktree Manager | T017 | ✅ Complete |
| REQ-WT-002 | Directory structure: .worktrees-{spec-id}/session-{N}-{task-name}/ | Prompt §2.2 | Runtime Artifacts | T017 | ✅ Complete |
| REQ-WT-003 | Branch naming: impl-{spec-id}-session-{N} | Prompt §2.2 | Worktree Manager | T017 | ✅ Complete |
| REQ-WT-004 | Worktree lifecycle: create, track, cleanup | Prompt §2.2 | Worktree Manager | T017, T018, T019 | ✅ Complete |
| REQ-WT-005 | Ensure complete isolation between sessions | Prompt §2.2 | Worktree Manager | T017 | ✅ Complete |
| REQ-WT-006 | Automatic cleanup on completion (configurable) | Prompt §2.2 | Merge Orchestrator | T033, T039 | ✅ Complete |

### REQ-AGENT: Agent Adapter Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-AGENT-001 | Abstract AgentSessionAdapter interface | Prompt §2.3 | Agents | T020 | ✅ Complete |
| REQ-AGENT-002 | GitHub Copilot as primary adapter | User Decision | Agents | T021 | ✅ Complete |
| REQ-AGENT-003 | IDE notification mode (not CLI spawning) | User Decision | Agents | T021 | ✅ Complete |
| REQ-AGENT-004 | Inject context into .github/copilot-instructions.md | Prompt §2.3 | Agents | T021 | ✅ Complete |
| REQ-AGENT-005 | Rich-formatted user prompts with worktree paths | Plan | Agents | T021 | ✅ Complete |
| REQ-AGENT-006 | Support for future adapters (Goose, OpenCode) | Prompt §2.3 | Agents | T020 | ✅ Complete |

### REQ-ORCH: Orchestration Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-ORCH-001 | Coordinate parallel execution with synchronization points | Prompt §2.1 | Session Coordinator | T029 | ✅ Complete |
| REQ-ORCH-002 | Phase-based execution (sequential phases, parallel tasks within) | Prompt §3.3 | Session Coordinator | T029, T030 | ✅ Complete |
| REQ-ORCH-003 | Dual completion detection: file watching + manual command | User Decision | Completion Detection | T025, T026, T027 | ✅ Complete |
| REQ-ORCH-004 | File-based IPC for manual completion (touch files) | User Decision | Completion Detection | T025 | ✅ Complete |
| REQ-ORCH-005 | Watch tasks.md for checkbox changes | Plan | Completion Detection | T026 | ✅ Complete |
| REQ-ORCH-006 | Checkpoint system for recovery | Prompt §2.1 | State Management | T012, T029 | ✅ Complete |
| REQ-ORCH-007 | Resume from interrupted state | Prompt §2.1 | Session Coordinator | T030 | ✅ Complete |
| REQ-ORCH-008 | Graceful shutdown on SIGINT/SIGTERM | Plan | Session Coordinator | T030 | ✅ Complete |

### REQ-MERGE: Merge Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-MERGE-001 | Analyze file changes across session branches | Prompt §3.4 | Merge Orchestrator | T031 | ✅ Complete |
| REQ-MERGE-002 | Detect potential conflicts before integration | Prompt §3.4 | Merge Orchestrator | T031 | ✅ Complete |
| REQ-MERGE-003 | Create integration branch impl-{spec-id}-integrated | Prompt §3.4 | Merge Orchestrator | T032 | ✅ Complete |
| REQ-MERGE-004 | Sequential merge strategy | Prompt §3.4 | Merge Orchestrator | T032 | ✅ Complete |
| REQ-MERGE-005 | Run validation (tests) after merge | Prompt §3.4 | Merge Orchestrator | T033 | ✅ Complete |
| REQ-MERGE-006 | Optional worktree preservation (--keep-worktrees) | Plan | Merge Orchestrator | T033, T038 | ✅ Complete |

### REQ-CLI: CLI Command Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-CLI-001 | skf init --sessions N | Plan | CLI Commands | T034 | ✅ Complete |
| REQ-CLI-002 | skf dag (generate DAG) | Plan | CLI Commands | T022 | ✅ Complete |
| REQ-CLI-003 | skf dag --visualize (ASCII tree) | Plan | CLI Commands | T023 | ✅ Complete |
| REQ-CLI-004 | skf run (full orchestration) | Plan | CLI Commands | T035 | ✅ Complete |
| REQ-CLI-005 | skf status (progress display) | Plan | CLI Commands | T036 | ✅ Complete |
| REQ-CLI-006 | skf complete TASK_ID (manual completion) | Plan | CLI Commands | T037 | ✅ Complete |
| REQ-CLI-007 | skf merge [--keep-worktrees] | Plan | CLI Commands | T038 | ✅ Complete |
| REQ-CLI-008 | skf abort (cleanup) | Plan | CLI Commands | T039 | ✅ Complete |

### REQ-MON: Monitoring Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-MON-001 | Real-time terminal dashboard | Prompt §3.3 | Monitoring | T040 | ✅ Complete |
| REQ-MON-002 | Session status table (ID, worktree, task, status) | Prompt §3.3 | Monitoring | T040 | ✅ Complete |
| REQ-MON-003 | DAG phase tree with completion indicators | Plan | Monitoring | T040 | ✅ Complete |
| REQ-MON-004 | Overall progress bar | Prompt §3.3 | Monitoring | T040 | ✅ Complete |
| REQ-MON-005 | Next-action prompts for user | Plan | Monitoring | T041 | ✅ Complete |
| REQ-MON-006 | Integrate dashboard into skf run | Plan | Monitoring | T042 | ✅ Complete |

### REQ-STATE: State Management Requirements

| ID | Requirement | Source | Plan Section | Tasks | Status |
|----|-------------|--------|--------------|-------|--------|
| REQ-STATE-001 | YAML for all state persistence | User Decision | State Management | T010, T011 | ✅ Complete |
| REQ-STATE-002 | Centralized immutable state in .speckit/flow-state.yaml | Prompt §2.1 | State Management | T011 | ✅ Complete |
| REQ-STATE-003 | Atomic writes to prevent corruption | Plan | State Management | T011 | ✅ Complete |
| REQ-STATE-004 | File locking for concurrent access | Plan | State Management | T011 | ✅ Complete |
| REQ-STATE-005 | Checkpoint snapshots for recovery | Prompt §2.1 | State Management | T012 | ✅ Complete |
| REQ-STATE-006 | State schema matching plan.md specification | Plan | State Management | T010 | ✅ Complete |

---

## Decision Log

Track decisions made during implementation that may cause drift from original requirements.

| Date | Decision | Rationale | Requirements Affected | Approved |
|------|----------|-----------|----------------------|----------|
| 2025-11-28 | Separate package (not extending specify-cli) | Avoid breaking existing users | REQ-ARCH-001 | ✅ User |
| 2025-11-28 | Copilot as first agent (IDE notification mode) | Most common, well-documented | REQ-AGENT-002, REQ-AGENT-003 | ✅ User |
| 2025-11-28 | YAML for all state | Human-readable, matches existing patterns | REQ-STATE-001 | ✅ User |
| 2025-11-28 | Dual completion detection | Redundancy for reliability | REQ-ORCH-003 | ✅ User |
| 2025-11-28 | File-based IPC (touch files) | Simple, no daemon required | REQ-ORCH-004 | ✅ User |
| 2025-11-28 | Monorepo with Hatch workspaces | Easier development, separate packages | REQ-ARCH-001, REQ-ARCH-002 | ✅ User |
| 2025-11-28 | DAG in specs/{branch}/dag.yaml | Transparent, version-controlled | REQ-DAG-005 | ✅ User |
| 2025-11-28 | Create speckit-core shared package | Avoid duplication | REQ-ARCH-003 | ✅ User |
| 2025-11-28 | Phase 1 ends at working skf dag command | Incremental delivery | N/A | ✅ User |
| 2025-11-28 | Phase 1 Complete | All 24 tasks implemented and verified | All Phase 1 REQ-* | ✅ Agent |
| 2025-11-29 | Phase 2 Complete | All 19 tasks implemented and verified | All Phase 2 REQ-* | ✅ Agent |
| 2025-11-29 | All Requirements Complete | 58/58 requirements satisfied, 43/43 tasks complete | All REQ-* | ✅ Agent |

---

## Spec Drift Checklist

Run this checklist before completing each phase to detect drift.

### Before Completing Phase 1

- [x] All REQ-ARCH requirements have implementing tasks
- [x] All REQ-DAG requirements have implementing tasks
- [x] All REQ-WT requirements have implementing tasks (at least stubs)
- [x] All REQ-AGENT requirements have implementing tasks (at least stubs)
- [x] All REQ-STATE requirements have implementing tasks
- [x] `skf dag` output matches dag.yaml schema in plan.md
- [x] Task format extension is backward compatible
- [x] No new dependencies added without updating plan.md

### Before Completing Phase 2

- [x] All REQ-ORCH requirements have implementing tasks
- [x] All REQ-MERGE requirements have implementing tasks
- [x] All REQ-CLI requirements have implementing tasks
- [x] All REQ-MON requirements have implementing tasks
- [x] State file schema matches plan.md specification
- [x] All CLI commands match documented behavior
- [x] Dashboard displays all required information
- [x] specify-cli still works after refactoring

---

## Change Control

When making changes that affect requirements:

1. **Update this matrix first** - Add new requirements or modify existing
2. **Update plan.md** - Reflect architectural changes
3. **Update tasks.md** - Add/modify tasks and acceptance criteria
4. **Log the decision** - Add entry to Decision Log with rationale

### Change Request Template

```markdown
## Change Request: [CR-###]

**Date**: YYYY-MM-DD
**Requester**: [Name/Role]
**Type**: [Addition | Modification | Removal]

### Current State
[Description of current requirement/behavior]

### Proposed Change
[Description of proposed change]

### Rationale
[Why is this change needed?]

### Impact Analysis
- Requirements affected: [REQ-XXX-###, ...]
- Tasks affected: [T###, ...]
- Plan sections affected: [Section names]

### Approval
- [ ] Reviewed by: ___________
- [ ] Approved by: ___________
- [ ] Traceability updated
- [ ] Plan updated
- [ ] Tasks updated
```

---

## Validation Matrix

Map requirements to validation methods.

| Requirement | Validation Type | Test/Check | Location |
|-------------|-----------------|------------|----------|
| REQ-ARCH-001 | Build | `hatch build` produces 3 wheels | CI/CD |
| REQ-DAG-002 | Unit Test | Topological sort correctness | tests/test_dag_engine.py |
| REQ-DAG-008 | Unit Test | Cycle detection test | tests/test_dag_engine.py |
| REQ-WT-001 | Integration | Worktree isolation test | tests/test_worktree.py |
| REQ-ORCH-003 | Integration | Both completion methods work | tests/test_completion.py |
| REQ-CLI-002 | E2E | `skf dag` generates valid YAML | tests/e2e/test_dag_command.py |
| REQ-MON-001 | Manual | Dashboard visual inspection | Manual QA |
| REQ-STATE-003 | Unit Test | Atomic write crash recovery | tests/test_state.py |

---

## Appendix: Source References

| Reference | Section | Key Points |
|-----------|---------|------------|
| Implementation Prompt | §1 Core Mission | 60-70% reduction, X concurrent sessions |
| Implementation Prompt | §2.1 DAG Engine | Topological sort, parallel blocks, checkpoint |
| Implementation Prompt | §2.2 Worktree Manager | Create/track/cleanup, isolation, merge orchestration |
| Implementation Prompt | §2.3 Agent Adapters | Abstract interface, Copilot/Goose/OpenCode |
| Implementation Prompt | §3.2 DAG Generation | tasks-dag.yaml format, phase structure |
| Implementation Prompt | §3.3 Parallel Execution | Initialize, execute DAG, synchronization points |
| Implementation Prompt | §3.4 Merge & Integration | Pre-merge analysis, automated merge, validation |
| Implementation Prompt | §4 CLI Commands | New and modified slash commands |
| Implementation Prompt | §5 Technical Details | Python package structure, state schema |
| Implementation Prompt | §6 Success Criteria | Performance, reliability, DX, quality |
