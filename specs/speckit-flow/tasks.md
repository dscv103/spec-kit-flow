# SpecKitFlow Implementation Tasks

## Task Format

Each task follows this structure:
- `[T###]` - Unique task ID
- `[P]` - Parallelizable within phase
- `[deps:...]` - Dependencies on other tasks
- **AC**: Acceptance Criteria (must all pass for task completion)

---

## Phase 1: Core Infrastructure

### Step 1: Restructure to Hatch Workspaces Monorepo

- [x] [T001] [deps:] **Update pyproject.toml for Hatch workspaces**
  - Configure `[tool.hatch.build]` for multi-package builds
  - Define three packages: `specify-cli`, `speckit-core`, `speckit-flow`
  - Add `[tool.hatch.envs.default]` with inter-package dependencies
  - **AC**:
    - [x] `hatch env create` succeeds without errors
    - [x] `hatch build` produces three separate wheel files
    - [x] All three packages can be imported in Python REPL

- [x] [T002] [deps:T001] **Verify existing specify-cli still works**
  - Ensure `specify` entry point remains functional
  - Run existing tests if any
  - **AC**:
    - [x] `specify --help` displays help text
    - [x] `specify check` runs without import errors
    - [x] Existing functionality unchanged

---

### Step 2: Create speckit-core Shared Library

- [x] [T003] [P] [deps:T001] **Create speckit_core package skeleton**
  - Create `src/speckit_core/__init__.py` with version and exports
  - Create empty module files: `paths.py`, `tasks.py`, `models.py`, `config.py`
  - **AC**:
    - [x] `from speckit_core import __version__` works
    - [x] Package structure matches plan.md specification

- [x] [T004] [P] [deps:T003] **Implement paths.py**
  - Port `get_repo_root()` from bash using `subprocess.run(["git", "rev-parse", "--show-toplevel"])`
  - Port `get_current_branch()` with fallback to `SPECIFY_FEATURE` env var
  - Port `get_feature_paths()` returning `FeatureContext` dataclass
  - Implement `find_feature_dir_by_prefix()` for numeric prefix matching
  - **AC**:
    - [x] `get_repo_root()` returns correct path in git repo
    - [x] `get_repo_root()` raises `NotInGitRepoError` outside git repo
    - [x] `get_current_branch()` returns branch name or raises
    - [x] `get_feature_paths()` returns all standard paths (spec.md, plan.md, tasks.md, etc.)
    - [x] Works on Linux, macOS, and Windows (Path handling)

- [x] [T005] [P] [deps:T003] **Implement models.py with Pydantic**
  - Define `TaskInfo` model: id, name, description, dependencies, session, parallelizable, story, files, status
  - Define `FeatureContext` model: repo_root, branch, feature_dir, spec_path, plan_path, tasks_path, etc.
  - Define `DAGNode` model for graph serialization
  - Define `SessionState` model for orchestration tracking
  - **AC**:
    - [x] All models validate correctly with sample data
    - [x] Models serialize to/from dict and YAML
    - [x] Type hints complete for IDE support
    - [x] Pydantic v2 validation works (not v1 syntax)

- [x] [T006] [P] [deps:T003,T005] **Implement tasks.py**
  - Create regex pattern for task line parsing: `[T###] [P] [US#] [deps:...]`
  - Implement `parse_task_line(line: str) -> TaskInfo | None`
  - Implement `parse_tasks_file(path: Path) -> list[TaskInfo]`
  - Handle backward compatibility (tasks without `[deps:]` marker)
  - **AC**:
    - [x] Parses standard format: `- [ ] [T001] [P] [US1] Description`
    - [x] Parses extended format: `- [ ] [T001] [P] [US1] [deps:T000] Description`
    - [x] Handles completed tasks: `- [x] [T001] ...`
    - [x] Handles tasks without optional markers
    - [x] Returns empty list for invalid/empty files
    - [x] Extracts file paths from description if present

- [x] [T007] [P] [deps:T003,T005] **Implement config.py**
  - Define `SpecKitFlowConfig` Pydantic model for `.speckit/speckit-flow.yaml`
  - Implement `load_config(repo_root: Path) -> SpecKitFlowConfig`
  - Implement `save_config(config: SpecKitFlowConfig, repo_root: Path)`
  - Provide sensible defaults (agent=copilot, sessions=3)
  - **AC**:
    - [x] Loads valid YAML config files
    - [x] Raises clear error for invalid/missing config
    - [x] Saves config with proper YAML formatting
    - [x] Default values applied when fields missing

---

### Step 3: Create speckit-flow Package Skeleton

- [x] [T008] [deps:T002,T003] **Create speckit_flow package structure**
  - Create `src/speckit_flow/__init__.py` with Typer app stub
  - Create subpackage directories with `__init__.py`:
    - `orchestration/` (dag_engine, scheduler, session_coordinator, completion)
    - `agents/` (base, copilot)
    - `worktree/` (manager, merger)
    - `monitoring/` (dashboard)
    - `state/` (manager, recovery)
  - **AC**:
    - [x] `from speckit_flow import app` works (Typer app)
    - [x] All subpackages importable without errors
    - [x] `skf --help` displays CLI help
    - [x] `speckit-flow --help` works as alias

- [x] [T009] [deps:T008] **Add speckit-flow dependencies**
  - Update pyproject.toml with speckit-flow dependencies
  - Include: speckit-core, typer, rich, networkx, pyyaml, pydantic>=2.0, filelock, watchfiles
  - **AC**:
    - [x] `hatch env create` installs all dependencies
    - [x] All imports work: `import networkx`, `import watchfiles`, etc.

---

### Step 4: Implement YAML State Management

- [x] [T010] [P] [deps:T005,T008] **Implement state/models.py**
  - Define `OrchestrationState` Pydantic model matching flow-state.yaml schema
  - Define `TaskState` enum: pending, in_progress, completed, failed
  - Define `SessionStatus` enum: idle, executing, waiting, completed, failed
  - **AC**:
    - [x] Models match schema in plan.md exactly
    - [x] Round-trip YAML serialization preserves all fields
    - [x] Timestamps use ISO 8601 format

- [x] [T011] [P] [deps:T010] **Implement state/manager.py**
  - Create `StateManager(repo_root: Path)` class
  - Implement `load() -> OrchestrationState` reading `.speckit/flow-state.yaml`
  - Implement `save(state: OrchestrationState)` with atomic write (temp file + rename)
  - Implement `exists() -> bool` checking for state file
  - Implement `delete()` removing state file
  - Use `filelock.FileLock` on `.speckit/flow-state.yaml.lock`
  - **AC**:
    - [x] Creates `.speckit/` directory if missing
    - [x] Atomic write prevents corruption on crash
    - [x] File lock prevents concurrent write corruption
    - [x] Raises `StateNotFoundError` when loading missing state

- [x] [T012] [P] [deps:T011] **Implement state/recovery.py**
  - Implement `checkpoint(state: OrchestrationState)` saving to `.speckit/checkpoints/{timestamp}.yaml`
  - Implement `list_checkpoints() -> list[Path]` returning sorted checkpoint files
  - Implement `get_latest_checkpoint() -> Path | None`
  - Implement `restore_from_checkpoint(path: Path) -> OrchestrationState`
  - Implement `cleanup_old_checkpoints(keep: int = 10)` removing old snapshots
  - **AC**:
    - [x] Checkpoints created with ISO 8601 timestamp filenames
    - [x] Restore returns valid OrchestrationState
    - [x] Cleanup preserves N most recent checkpoints
    - [x] Handles empty checkpoints directory gracefully

---

### Step 5: Build DAG Engine

- [x] [T013] [deps:T006,T010] **Implement orchestration/dag_engine.py core**
  - Create `DAGEngine(tasks: list[TaskInfo])` class
  - Implement `build_graph() -> nx.DiGraph` creating nodes with task data, edges from dependencies
  - Implement `validate() -> bool` checking `nx.is_directed_acyclic_graph()`
  - Raise `CyclicDependencyError` with cycle path if validation fails
  - **AC**:
    - [x] Creates valid networkx DiGraph from task list
    - [x] Node attributes contain full TaskInfo data
    - [x] Detects and reports circular dependencies
    - [x] Handles empty task list gracefully

- [x] [T014] [P] [deps:T013] **Implement phase generation**
  - Implement `get_phases() -> list[list[str]]` using `nx.topological_generations()`
  - Each phase contains task IDs that can execute in parallel
  - Implement `get_critical_path() -> list[str]` returning longest dependency chain
  - **AC**:
    - [x] Tasks with no deps in phase 0
    - [x] Tasks only appear after all deps completed
    - [x] Critical path identifies bottleneck tasks

- [x] [T015] [P] [deps:T014] **Implement session assignment**
  - Implement `assign_sessions(num_sessions: int)` distributing tasks round-robin within phases
  - Update task objects with assigned session ID
  - Implement `get_session_tasks(session_id: int) -> list[TaskInfo]`
  - **AC**:
    - [x] Tasks distributed evenly across sessions
    - [x] Same task never assigned to multiple sessions
    - [x] Sequential (non-parallel) tasks assigned to session 0

- [x] [T016] [P] [deps:T015] **Implement DAG serialization**
  - Implement `to_yaml() -> str` serializing DAG to dag.yaml format
  - Implement `save(path: Path)` writing dag.yaml file
  - Implement `load(path: Path) -> DAGEngine` class method loading from dag.yaml
  - **AC**:
    - [x] Output matches dag.yaml schema in plan.md
    - [x] Round-trip (save + load) preserves all data
    - [x] Includes metadata: version, spec_id, generated_at, num_sessions

---

### Step 6: Implement Worktree Manager

- [x] [T017] [deps:T004,T008] **Implement worktree/manager.py core**
  - Create `WorktreeManager(repo_root: Path)` class
  - Implement `create(spec_id: str, session_id: int, task_name: str) -> Path`
    - Creates branch `impl-{spec_id}-session-{session_id}`
    - Creates worktree at `.worktrees-{spec_id}/session-{session_id}-{task_name}/`
  - Handle sanitizing task_name for filesystem (remove special chars)
  - **AC**:
    - [x] Creates worktree directory and git branch
    - [x] Returns Path to created worktree
    - [x] Raises `WorktreeExistsError` if already exists
    - [x] Works with long spec_id and task names (truncation)

- [x] [T018] [P] [deps:T017] **Implement worktree listing and removal**
  - Implement `list() -> list[WorktreeInfo]` parsing `git worktree list --porcelain`
  - Define `WorktreeInfo` dataclass: path, branch, commit, locked
  - Implement `remove(path: Path)` running `git worktree remove`
  - Implement `remove_force(path: Path)` with `--force` flag
  - **AC**:
    - [x] Lists all worktrees including main
    - [x] Correctly parses porcelain output
    - [x] Remove works for clean worktrees
    - [x] Force remove works for dirty worktrees

- [x] [T019] [P] [deps:T018] **Implement spec cleanup**
  - Implement `cleanup_spec(spec_id: str)` removing all worktrees for spec
  - Implement `get_spec_worktrees(spec_id: str) -> list[WorktreeInfo]` filtering by spec
  - Delete `.worktrees-{spec_id}/` directory after all worktrees removed
  - **AC**:
    - [x] Removes all session worktrees for spec
    - [x] Removes parent directory
    - [x] Handles missing worktrees gracefully
    - [x] Reports which worktrees were removed

---

### Step 7: Create Copilot IDE Adapter Stub

- [x] [T020] [deps:T008] **Implement agents/base.py**
  - Create abstract `AgentAdapter` class with methods:
    - `setup_session(worktree: Path, task: TaskInfo) -> None`
    - `notify_user(session_id: int, worktree: Path, task: TaskInfo) -> None`
    - `get_files_to_watch(worktree: Path) -> list[Path]`
    - `get_context_file_path(worktree: Path) -> Path`
  - **AC**:
    - [x] Abstract methods raise NotImplementedError
    - [x] Type hints complete
    - [x] Docstrings explain expected behavior

- [x] [T021] [deps:T020] **Implement agents/copilot.py**
  - Create `CopilotIDEAdapter(AgentAdapter)` class
  - Implement `setup_session()`:
    - Create `.github/` directory in worktree
    - Write `copilot-instructions.md` with task context template in `.github/`
    - Note: `.github/agents/` is reserved for `*.agent.md` files only
  - Implement `notify_user()`:
    - Print Rich Panel with session info, worktree path, task description
    - Include instruction: "Open this path in VS Code and run /speckit.implement"
  - Implement `get_files_to_watch()` returning `[worktree / "specs" / branch / "tasks.md"]`
  - **AC**:
    - [x] Creates context file in correct location (.github/copilot-instructions.md)
    - [x] Context file includes task ID, description, files to modify
    - [x] Rich output is visually clear with colors
    - [x] Worktree path is absolute and copy-pasteable

---

### Step 8: Implement skf dag Command

- [x] [T022] [deps:T004,T006,T016] **Implement skf dag command**
  - Add `dag` command to Typer app in `__init__.py`
  - Load feature context using `speckit_core.paths`
  - Parse tasks.md using `speckit_core.tasks`
  - Build DAG using `DAGEngine`
  - Save to `specs/{branch}/dag.yaml`
  - Print summary: task count, phase count, parallelizable tasks per phase
  - **AC**:
    - [x] `skf dag` generates dag.yaml in correct location
    - [x] Prints human-readable summary to stdout
    - [x] Exits with error code 1 if no tasks.md found
    - [x] Exits with error code 1 if cyclic dependencies detected

- [x] [T023] [deps:T022] **Implement skf dag --visualize**
  - Add `--visualize` flag to dag command
  - Generate ASCII tree using Rich Tree showing phases and tasks
  - Show task dependencies inline: `T003 (deps: T001, T002)`
  - Indicate parallelizable tasks with `[P]` marker
  - **AC**:
    - [x] Tree clearly shows phase hierarchy
    - [x] Dependencies visible for each task
    - [x] Colors distinguish phases from tasks
    - [x] Works in terminals without Unicode support (ASCII fallback)

- [x] [T024] [deps:T023] **Add skf dag --sessions N option**
  - Add `--sessions` option to override default session count
  - Re-run session assignment with new count
  - Show session assignment in visualization
  - **AC**:
    - [x] `skf dag --sessions 5` assigns to 5 sessions
    - [x] Session shown for each task in output
    - [x] dag.yaml includes num_sessions field

---

## Phase 2: Orchestration & Integration

### Step 9: Build File-Based Completion Detection

- [x] [T025] [deps:T006,T012] **Implement orchestration/completion.py core**
  - Create `CompletionMonitor(spec_id: str, repo_root: Path)` class
  - Implement `mark_complete(task_id: str)` touching `.speckit/completions/{task_id}.done`
  - Implement `is_complete(task_id: str) -> bool` checking for done file
  - Implement `get_manual_completions() -> set[str]` listing all done files
  - **AC**:
    - [x] Creates completions directory if missing
    - [x] Done files are empty (touch only)
    - [x] Handles concurrent marking safely

- [x] [T026] [P] [deps:T025] **Implement tasks.md file watching**
  - Implement `watch_tasks_file(path: Path, callback: Callable)` using watchfiles
  - Parse file on change, detect newly checked tasks `- [x] [T###]`
  - Call callback with set of completed task IDs
  - **AC**:
    - [x] Detects checkbox state changes
    - [x] Handles rapid successive changes (debounce)
    - [x] Works across multiple worktree watches simultaneously
    - [x] Graceful handling of file deletion/rename

- [x] [T027] [P] [deps:T025,T026] **Implement unified completion checking**
  - Implement `get_completed_tasks() -> set[str]` returning union of:
    - Manual completions (done files)
    - Watched completions (tasks.md checkboxes)
  - Implement `wait_for_completion(task_ids: set[str], timeout: float | None) -> set[str]`
  - Return completed tasks, raise TimeoutError if timeout exceeded
  - **AC**:
    - [x] Union correctly combines both sources
    - [x] wait_for_completion blocks until all tasks done or timeout
    - [x] Handles partial completion (some tasks done, some pending)

---

### Step 10: Implement Session Coordinator

- [x] [T028] [deps:T011,T015,T017,T021,T027] **Implement orchestration/session_coordinator.py**
  - Create `SessionCoordinator(dag: DAGEngine, config: SpecKitFlowConfig, adapter: AgentAdapter)`
  - Implement `initialize()`:
    - Create worktrees for all sessions
    - Setup adapter context in each worktree
    - Initialize state file
  - **AC**:
    - [x] Creates N worktrees matching session count
    - [x] Each worktree has agent context file
    - [x] State file reflects initialized sessions

- [x] [T029] [P] [deps:T028] **Implement phase execution**
  - Implement `run_phase(phase_idx: int)`:
    - Get tasks for current phase
    - Notify user for each session with task assignments
    - Start completion monitors
    - Wait for all phase tasks to complete
  - Implement `checkpoint_phase()` saving state after phase completion
  - **AC**:
    - [x] User prompted for each active session
    - [x] Waits until all parallel tasks complete
    - [x] State checkpointed after each phase
    - [x] Handles keyboard interrupt gracefully

- [x] [T030] [P] [deps:T029] **Implement full orchestration run**
  - Implement `run()`:
    - Initialize if not already running
    - Resume from current phase if restarting
    - Iterate through all phases
    - Mark orchestration complete when done
  - Handle SIGINT/SIGTERM for graceful shutdown
  - **AC**:
    - [x] Executes all phases in order
    - [x] Resumes from checkpoint after crash
    - [x] Ctrl+C saves state before exit
    - [x] Final state shows all tasks completed

---

### Step 11: Implement Merge Orchestrator

- [x] [T031] [deps:T017,T018] **Implement worktree/merger.py analysis**
  - Create `MergeOrchestrator(spec_id: str, repo_root: Path)`
  - Implement `analyze() -> MergeAnalysis`:
    - Get changed files per session branch vs base
    - Detect overlapping files (same file in multiple sessions)
    - Categorize: safe to merge, potential conflict
  - Define `MergeAnalysis` dataclass with per-session file changes
  - **AC**:
    - [x] Correctly identifies all changed files per branch
    - [x] Detects overlapping file modifications
    - [x] Reports which sessions conflict on which files

- [x] [T032] [P] [deps:T031] **Implement sequential merge strategy**
  - Implement `merge_sequential() -> MergeResult`:
    - Create integration branch `impl-{spec_id}-integrated` from base
    - Merge session branches in order (0, 1, 2, ...)
    - Use `--no-ff` to preserve branch history
    - Stop on conflict, report conflicting files
  - **AC**:
    - [x] Creates integration branch
    - [x] Merges cleanly for non-overlapping changes
    - [x] Reports conflict details when merge fails
    - [x] Leaves repo in clean state on failure

- [x] [T033] [P] [deps:T032] **Implement merge validation and cleanup**
  - Implement `validate(test_cmd: str | None)`:
    - Run test command in integration branch if provided
    - Return success/failure with output
  - Implement `finalize(keep_worktrees: bool = False)`:
    - Delete session worktrees unless keep_worktrees
    - Remove `.worktrees-{spec_id}/` directory
    - Output summary of merged changes
  - **AC**:
    - [x] Test command runs in correct directory
    - [x] Cleanup removes all worktrees
    - [x] Summary shows files changed, lines added/removed

---

### Step 12: Add Remaining CLI Commands

- [x] [T034] [deps:T007,T008] **Implement skf init command**
  - Add `init` command with options: `--sessions N`, `--agent TYPE`
  - Create `.speckit/speckit-flow.yaml` with configuration
  - Validate current directory is in git repo with spec-kit structure
  - **AC**:
    - [x] Creates config file with specified options
    - [x] Defaults: sessions=3, agent=copilot
    - [x] Errors if not in git repo
    - [x] Errors if no specs/ directory exists

- [x] [T035] [P] [deps:T030] **Implement skf run command**
  - Add `run` command invoking SessionCoordinator
  - Show progress during execution
  - Print summary on completion
  - **AC**:
    - [x] Loads config and DAG
    - [x] Runs full orchestration
    - [x] Handles resume from interrupted state
    - [x] Final output shows completion status

- [x] [T036] [P] [deps:T011] **Implement skf status command**
  - Add `status` command reading current state
  - Display: current phase, completed tasks, pending tasks, session states
  - Use Rich table for clear formatting
  - **AC**:
    - [x] Shows accurate current state
    - [x] Handles no-state-yet case with helpful message
    - [x] Colors indicate status (green=done, yellow=in-progress, red=failed)

- [x] [T037] [P] [deps:T025] **Implement skf complete command**
  - Add `complete TASK_ID` command
  - Mark task as complete via touch file
  - Validate task ID exists in DAG
  - **AC**:
    - [x] Creates done file for valid task
    - [x] Errors for invalid task ID
    - [x] Warns if task already complete

- [x] [T038] [P] [deps:T033] **Implement skf merge command**
  - Add `merge` command with `--keep-worktrees` flag
  - Run analysis, prompt for confirmation if conflicts detected
  - Execute merge and validation
  - **AC**:
    - [x] Shows analysis before merging
    - [x] Prompts on conflict detection
    - [x] `--keep-worktrees` preserves worktrees
    - [x] Reports merge success/failure

- [x] [T039] [P] [deps:T019] **Implement skf abort command**
  - Add `abort` command
  - Prompt for confirmation
  - Clean up all worktrees
  - Delete state file
  - **AC**:
    - [x] Requires confirmation (--force to skip)
    - [x] Removes all worktrees
    - [x] Clears state
    - [x] Reports cleanup actions

---

### Step 13: Create Rich Monitoring Dashboard

- [x] [T040] [deps:T011,T016] **Implement monitoring/dashboard.py**
  - Create `Dashboard(state_manager: StateManager)` class
  - Implement Rich Live display with:
    - Session table (ID, worktree, current task, status)
    - DAG phase tree with completion indicators (✓, ⋯, ○)
    - Overall progress bar
  - Auto-refresh by polling state file
  - **AC**:
    - [x] Updates in real-time as state changes
    - [x] Clear visual hierarchy
    - [x] Graceful degradation for narrow terminals

- [x] [T041] [P] [deps:T040] **Add next-action prompts to dashboard**
  - Show panel with actionable next steps:
    - "Open session-1 worktree in VS Code..."
    - "Waiting for tasks T003, T004 to complete..."
    - "All tasks complete. Run 'skf merge' to integrate."
  - Update prompts based on current state
  - **AC**:
    - [x] Prompts are actionable and clear
    - [x] Copy-pasteable paths and commands
    - [x] Updates as phases progress

- [x] [T042] [deps:T035,T040] **Integrate dashboard into skf run**
  - Add `--dashboard` flag to run command (default: true)
  - Launch dashboard in background thread
  - Graceful shutdown on completion or interrupt
  - **AC**:
    - [x] Dashboard runs alongside orchestration
    - [x] `--no-dashboard` disables for CI/scripting
    - [x] Clean exit without orphan processes

---

### Step 13b: Refactor specify-cli

- [x] [T043] [deps:T004,T006] **Refactor specify-cli to use speckit-core**
  - Update imports to use `speckit_core.paths` for path utilities
  - Update imports to use `speckit_core.tasks` for task parsing
  - Remove duplicated utility code
  - **AC**:
    - [x] All `specify` commands still work
    - [x] No duplicate path/task code in specify_cli
    - [x] Import from speckit_core explicit in code

---

## Summary

| Phase | Tasks | Parallelizable | Dependencies |
|-------|-------|----------------|--------------|
| Phase 1 | T001-T024 | 14/24 | Linear core, parallel features |
| Phase 2 | T025-T043 | 15/19 | Depends on Phase 1 completion |
| **Total** | **43 tasks** | **29 parallelizable** | |

## Completion Checklist

### Phase 1 Complete When:
- [x] `hatch build` produces three wheel files
- [x] `skf dag` generates valid dag.yaml
- [x] `skf dag --visualize` shows phase tree
- [x] All unit tests pass for speckit-core and speckit-flow

**Phase 1 Status**: ✅ **COMPLETE** (2025-11-28)

### Phase 2 Complete When:
- [x] `skf init && skf run` executes full workflow
- [x] Completion detection works (both methods)
- [x] `skf merge` integrates branches
- [x] Dashboard shows real-time progress
- [x] `specify` command unchanged in behavior

**Phase 2 Status**: ✅ **COMPLETE** (2025-11-29)
