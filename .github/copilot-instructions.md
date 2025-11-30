## Copilot Quickstart: SpecKitFlow

This document helps Copilot-style IDE assistants be productive in this repo.

### Big picture
- Monorepo with three packages (Hatch workspaces): `specify-cli`, `speckit_core`, `speckit_flow` (see [pyproject.toml](pyproject.toml)).
- `speckit_core` contains shared utilities: `paths.py`, `tasks.py`, `models.py`, `config.py`.
- `speckit_flow` contains orchestrator components: `orchestration/`, `agents/`, `worktree/`, `state/`, `monitoring/`.

### Files to read first
- `specs/speckit-flow/plan.md` — architecture and schema decisions.
- `specs/speckit-flow/tasks.md` — tasks and ACs; follow tasks IDs (T001–T043).
- `specs/speckit-flow/traceability.md` — requirement -> task mapping.
- `AGENTS.md` — agent support and Copilot mode expectations.
- `.github/agents/speckit-flow.agent.md` — agent runtime behavior and guardrails.

### Developer workflow (run locally)
- Create Hatch env and install deps: `hatch env create`.
- Build: `hatch build` (produces wheels per package in Phase 1 once configured).
- Run tests: `hatch run -e default pytest` or `pytest` inside the created env.
- Existing CLI: `specify --help`. The `skf` CLI is provided by `speckit_flow` (entry points planned as `skf`, but use local invocation if not installed).

### Project conventions (do not deviate)
- Use `pathlib.Path` for file paths. No hard-coded OS paths.
- Pydantic v2: use `model_dump()`, `model_validate()`. Avoid v1 APIs.
- State writes must be atomic: write to a temp file within the same directory and rename.
- Use `filelock.FileLock` for state concurrency management (see `state/manager.py` ACs).
- Use `subprocess.run([...], check=True)` for git commands; capture output only when needed.
- Follow Task format in `tasks.md`: lines include `- [ ] [T001] [P] [deps:T000] Description` (ACs assume this format).

### Key integration points
- DAG engine: `src/speckit_flow/orchestration/dag_engine.py` — networkx graphs, topological phases.
- State manager: `src/speckit_flow/state/manager.py` — `.speckit/flow-state.yaml` and `.speckit/flow-state.yaml.lock`.
- Worktree manager: `src/speckit_flow/worktree/manager.py` — create/remove `git worktree` branches: `.worktrees-{spec-id}/`.
- Copilot adapter: `src/speckit_flow/agents/copilot.py` — creates `.github/copilot-instructions.md` inside worktrees and prints user prompts in IDE mode. (Note: .github/agents/ is for *.agent.md files only)
- DAG output (generated): `specs/{branch}/dag.yaml` per `plan.md` schema.

### Coding patterns & tests
- Follow docstring and type-hint rules in `code-quality.instructions.md` and testing patterns in `testing.instructions.md`.
- Tests: unit tests under `tests/` and use the AAA pattern. Use fixtures (e.g., `temp_repo`, `sample_tasks`).
- For heavy imports (networkx, watchfiles), prefer lazy imports where performance matters (see `performance.instructions.md`).

### Common tasks for Copilot suggestions
- Implement tasks from `specs/speckit-flow/tasks.md` and reference the task ID (Txxx) in code suggestions.
- When suggesting new modules or public APIs, also suggest tests for edge cases and validation of ACs.
- When updating `pyproject.toml`, ensure `specify` script remains unchanged (T002) and new packages are added as Hatch build targets (T001).

### Examples (short & concrete)
- Task line example (parsing): `- [ ] [T004] [P] [deps:T003] Implement paths.get_current_branch()`
- Atomic write example for YAML: use `tempfile.mkstemp(dir=path.parent)` -> write -> fsync -> `os.replace(temp_path, path)`.
- Lock usage: `with FileLock(str(state_path) + ".lock"):` before reading/writing state.

### When in doubt
- Read `plan.md` first for architecture decisions and `traceability.md` to map requirements to tasks.
- Confirm any schema change (DAG YAML, state YAML) against `plan.md` and update `traceability.md` before making code changes.
- If a task depends on other tasks, do not proceed until dependencies are complete.

### Questions for reviewers
1. Is there a preferred `hatch` env name to use for running tests? If not, `default` is fine.
2. Confirm if `skf` entry points should be verified by local `pip install -e` (dev workflow) or via `hatch run`.


