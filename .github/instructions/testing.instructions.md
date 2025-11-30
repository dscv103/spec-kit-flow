---
name: Testing Standards

description: Testing principles, AAA pattern, coverage thresholds, fixture patterns, and edge case requirements for SpecKitFlow test suites.

applyTo: "tests/**/*.py"
---

# Testing Standards Instructions

## Purpose

This document establishes testing standards for SpecKitFlow. Every feature must have corresponding tests before being considered complete.

## Testing Principles

### Principle 1: Tests Are Documentation

Tests should demonstrate how to use the code:

```python
def test_dag_engine_builds_graph_from_tasks():
    """DAGEngine creates a directed graph with tasks as nodes."""
    # Given: A list of tasks with dependencies
    tasks = [
        TaskInfo(id="T001", name="Setup", dependencies=[]),
        TaskInfo(id="T002", name="Build", dependencies=["T001"]),
        TaskInfo(id="T003", name="Test", dependencies=["T002"]),
    ]
    
    # When: Building the DAG
    engine = DAGEngine(tasks)
    
    # Then: Graph contains all tasks with correct edges
    assert len(engine.graph.nodes) == 3
    assert engine.graph.has_edge("T001", "T002")
    assert engine.graph.has_edge("T002", "T003")
    assert not engine.graph.has_edge("T001", "T003")  # No transitive edge
```

### Principle 2: Test Behavior, Not Implementation

```python
# ❌ Tests implementation details
def test_state_manager_uses_temp_file():
    manager = StateManager(repo_root)
    with patch("pathlib.Path.rename") as mock_rename:
        manager.save(state)
    mock_rename.assert_called_once()

# ✅ Tests behavior
def test_state_manager_save_is_atomic():
    """Save operation should not corrupt state on interruption."""
    manager = StateManager(repo_root)
    state = create_sample_state()
    
    # Simulate interruption during save
    with patch.object(manager, "_write_content", side_effect=IOError("Disk full")):
        with pytest.raises(IOError):
            manager.save(state)
    
    # State file should be unchanged (no partial write)
    assert not manager.exists() or manager.load() != state
```

### Principle 3: Arrange-Act-Assert Pattern

Every test follows the AAA pattern:

```python
def test_worktree_manager_creates_branch_and_directory():
    # Arrange: Set up test conditions
    repo_root = create_test_repo()
    manager = WorktreeManager(repo_root)
    
    # Act: Perform the action being tested
    worktree_path = manager.create(
        spec_id="001-feature",
        session_id=0,
        task_name="setup"
    )
    
    # Assert: Verify expected outcomes
    assert worktree_path.exists()
    assert worktree_path.is_dir()
    assert (worktree_path / ".git").exists()
    assert get_branch_name(worktree_path) == "impl-001-feature-session-0"
```

### Principle 4: One Assertion Concept Per Test

Test one logical concept, even if it requires multiple assertions:

```python
# ✅ Multiple assertions for one concept (task parsing)
def test_parse_task_line_extracts_all_markers():
    """Parser extracts all optional markers from task line."""
    line = "- [ ] [T001] [P] [US1] [deps:T000] Implement feature"
    
    task = parse_task_line(line)
    
    assert task is not None
    assert task.id == "T001"
    assert task.parallelizable is True
    assert task.story == "US1"
    assert task.dependencies == ["T000"]
    assert task.name == "Implement feature"
```

## Test Categories

### Unit Tests

Test individual functions/classes in isolation:

```python
# tests/unit/speckit_core/test_tasks.py
class TestParseTaskLine:
    """Unit tests for parse_task_line function."""
    
    def test_parses_minimal_task(self):
        """Parses task with only required elements."""
        line = "- [ ] [T001] Simple task"
        task = parse_task_line(line)
        assert task.id == "T001"
        assert task.name == "Simple task"
    
    def test_returns_none_for_non_task_line(self):
        """Returns None for lines that aren't tasks."""
        assert parse_task_line("## Section Header") is None
        assert parse_task_line("Regular paragraph text") is None
        assert parse_task_line("- Regular bullet point") is None
    
    def test_handles_completed_task(self):
        """Correctly identifies completed tasks."""
        line = "- [x] [T001] Completed task"
        task = parse_task_line(line)
        assert task.completed is True
```

### Integration Tests

Test component interactions:

```python
# tests/integration/test_dag_workflow.py
class TestDAGWorkflow:
    """Integration tests for DAG generation workflow."""
    
    def test_dag_command_generates_yaml_from_tasks_file(self, temp_repo):
        """skf dag reads tasks.md and writes dag.yaml."""
        # Setup: Create tasks.md in feature directory
        tasks_content = dedent("""
            ## Phase 1
            - [ ] [T001] [deps:] Setup project
            - [ ] [T002] [deps:T001] Implement feature
        """)
        (temp_repo / "specs" / "test-feature" / "tasks.md").write_text(tasks_content)
        
        # Execute: Run dag command
        result = runner.invoke(app, ["dag"])
        
        # Verify: dag.yaml created with correct structure
        assert result.exit_code == 0
        dag_path = temp_repo / "specs" / "test-feature" / "dag.yaml"
        assert dag_path.exists()
        
        dag_content = yaml.safe_load(dag_path.read_text())
        assert len(dag_content["phases"]) == 2
        assert dag_content["phases"][0]["tasks"][0]["id"] == "T001"
```

### End-to-End Tests

Test complete user workflows:

```python
# tests/e2e/test_full_orchestration.py
class TestFullOrchestration:
    """End-to-end tests for complete orchestration workflow."""
    
    @pytest.mark.slow
    def test_complete_workflow_init_to_merge(self, temp_repo_with_spec):
        """Full workflow from init through merge."""
        # 1. Initialize
        result = runner.invoke(app, ["init", "--sessions", "2"])
        assert result.exit_code == 0
        
        # 2. Generate DAG
        result = runner.invoke(app, ["dag"])
        assert result.exit_code == 0
        
        # 3. Check status (no active orchestration yet)
        result = runner.invoke(app, ["status"])
        assert "No active orchestration" in result.output
        
        # 4. Simulate task completion and merge
        # ... (uses mocked completion detection)
```

## Test File Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── speckit_core/
│   │   ├── test_paths.py
│   │   ├── test_tasks.py
│   │   ├── test_models.py
│   │   └── test_config.py
│   └── speckit_flow/
│       ├── orchestration/
│       │   ├── test_dag_engine.py
│       │   └── test_completion.py
│       ├── state/
│       │   ├── test_manager.py
│       │   └── test_recovery.py
│       └── worktree/
│           ├── test_manager.py
│           └── test_merger.py
├── integration/
│   ├── test_dag_workflow.py
│   ├── test_state_persistence.py
│   └── test_worktree_operations.py
└── e2e/
    ├── test_cli_commands.py
    └── test_full_orchestration.py
```

## Fixtures

### Shared Test Fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path
import tempfile
import subprocess

@pytest.fixture
def temp_dir():
    """Temporary directory that's cleaned up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def temp_repo(temp_dir):
    """Temporary git repository."""
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir, check=True, capture_output=True
    )
    # Initial commit required for worktrees
    (temp_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir, check=True, capture_output=True
    )
    yield temp_dir

@pytest.fixture
def temp_repo_with_spec(temp_repo):
    """Temporary repo with spec-kit structure."""
    spec_dir = temp_repo / "specs" / "001-test-feature"
    spec_dir.mkdir(parents=True)
    
    (spec_dir / "spec.md").write_text("# Test Feature Spec")
    (spec_dir / "plan.md").write_text("# Implementation Plan")
    (spec_dir / "tasks.md").write_text(dedent("""
        # Tasks
        - [ ] [T001] [deps:] Setup
        - [ ] [T002] [P] [deps:T001] Feature A
        - [ ] [T003] [P] [deps:T001] Feature B
        - [ ] [T004] [deps:T002,T003] Integration
    """))
    
    subprocess.run(["git", "add", "."], cwd=temp_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add spec"], 
        cwd=temp_repo, check=True, capture_output=True
    )
    
    yield temp_repo

@pytest.fixture
def sample_tasks():
    """Sample TaskInfo list for testing."""
    return [
        TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
        TaskInfo(id="T002", name="Feature A", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T003", name="Feature B", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T004", name="Integration", dependencies=["T002", "T003"], parallelizable=False),
    ]

@pytest.fixture
def sample_state():
    """Sample OrchestrationState for testing."""
    return OrchestrationState(
        version="1.0",
        spec_id="001-test",
        agent_type="copilot",
        num_sessions=2,
        current_phase="phase-1",
        phases_completed=["phase-0"],
        sessions=[
            SessionState(session_id=0, status="executing", current_task="T002"),
            SessionState(session_id=1, status="executing", current_task="T003"),
        ],
        tasks={
            "T001": TaskStatus(status="completed"),
            "T002": TaskStatus(status="in_progress"),
            "T003": TaskStatus(status="in_progress"),
            "T004": TaskStatus(status="pending"),
        },
    )
```

## Test Coverage Requirements

### Coverage Thresholds

| Package | Minimum Coverage |
|---------|-----------------|
| speckit_core | 90% |
| speckit_flow.orchestration | 85% |
| speckit_flow.state | 90% |
| speckit_flow.worktree | 80% |
| speckit_flow.agents | 75% |
| speckit_flow.monitoring | 70% |

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src/speckit_core", "src/speckit_flow"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@abstractmethod",
]
fail_under = 80
```

## Testing Edge Cases

### Required Edge Case Tests

Every function should test these scenarios where applicable:

```python
class TestParseTasksFile:
    """Edge case tests for parse_tasks_file."""
    
    def test_empty_file(self, temp_dir):
        """Handles empty file gracefully."""
        path = temp_dir / "empty.md"
        path.write_text("")
        assert parse_tasks_file(path) == []
    
    def test_file_with_only_headers(self, temp_dir):
        """Handles file with no tasks."""
        path = temp_dir / "headers.md"
        path.write_text("# Header\n## Subheader\n")
        assert parse_tasks_file(path) == []
    
    def test_file_not_found(self, temp_dir):
        """Raises FileNotFoundError for missing file."""
        path = temp_dir / "nonexistent.md"
        with pytest.raises(FileNotFoundError):
            parse_tasks_file(path)
    
    def test_unicode_content(self, temp_dir):
        """Handles Unicode in task descriptions."""
        path = temp_dir / "unicode.md"
        path.write_text("- [ ] [T001] Implement émojis 🚀")
        tasks = parse_tasks_file(path)
        assert tasks[0].name == "Implement émojis 🚀"
    
    def test_very_long_line(self, temp_dir):
        """Handles very long task descriptions."""
        path = temp_dir / "long.md"
        long_desc = "A" * 10000
        path.write_text(f"- [ ] [T001] {long_desc}")
        tasks = parse_tasks_file(path)
        assert len(tasks[0].name) == 10000
```

### Concurrency Tests

For state management and file operations:

```python
class TestStateConcurrency:
    """Concurrency tests for StateManager."""
    
    def test_concurrent_reads_safe(self, temp_repo, sample_state):
        """Multiple readers don't block each other."""
        manager = StateManager(temp_repo)
        manager.save(sample_state)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(manager.load) for _ in range(10)]
            results = [f.result() for f in futures]
        
        assert all(r == sample_state for r in results)
    
    def test_concurrent_writes_serialized(self, temp_repo, sample_state):
        """Concurrent writes don't corrupt state."""
        manager = StateManager(temp_repo)
        
        def write_state(n: int):
            state = sample_state.model_copy()
            state.current_phase = f"phase-{n}"
            manager.save(state)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_state, i) for i in range(5)]
            [f.result() for f in futures]
        
        # State should be valid (one of the writes)
        final_state = manager.load()
        assert final_state.current_phase.startswith("phase-")
```

## Mocking Guidelines

### When to Mock

✅ **Do mock**:
- External services (GitHub API, file system in unit tests)
- Time-dependent operations (`datetime.now()`)
- Subprocess calls (git commands)
- Network operations

❌ **Don't mock**:
- The code under test
- Simple data structures
- Pure functions

### Mock Examples

```python
# ✅ Mock external git command
def test_worktree_create_calls_git_correctly(temp_repo, mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess([], 0)
    
    manager = WorktreeManager(temp_repo)
    manager.create("001-test", 0, "setup")
    
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "git" in call_args
    assert "worktree" in call_args
    assert "add" in call_args

# ✅ Mock time for deterministic tests
def test_checkpoint_uses_current_timestamp(temp_repo, sample_state, mocker):
    fixed_time = datetime(2025, 11, 28, 10, 30, 0)
    mocker.patch("speckit_flow.state.recovery.datetime", now=lambda: fixed_time)
    
    recovery = RecoveryManager(temp_repo)
    checkpoint_path = recovery.checkpoint(sample_state)
    
    assert "2025-11-28T10-30-00" in checkpoint_path.name
```

## Test Naming Conventions

### Function Names

```python
# Pattern: test_<unit>_<scenario>_<expected_result>
def test_dag_engine_with_empty_tasks_returns_empty_phases():
def test_parse_task_line_with_all_markers_extracts_correctly():
def test_worktree_create_with_existing_path_raises_error():
def test_state_save_on_disk_full_preserves_original():
```

### Test Class Names

```python
# Group by unit under test
class TestDAGEngine:
class TestParseTaskLine:
class TestStateManager:
class TestWorktreeManager:
```

## Running Tests

### Command Reference

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/speckit_core/test_tasks.py

# Run specific test
pytest tests/unit/speckit_core/test_tasks.py::TestParseTaskLine::test_parses_minimal_task

# Run only fast tests (skip slow markers)
pytest -m "not slow"

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### pytest.ini Configuration

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
addopts = -ra -q
filterwarnings =
    error
    ignore::DeprecationWarning
```

## Task Testing Requirements

Each task in tasks.md must have tests that verify its acceptance criteria:

| Task | Required Tests |
|------|---------------|
| T006 (tasks.py) | `test_parse_task_line_*`, `test_parse_tasks_file_*` |
| T011 (state/manager.py) | `test_state_manager_*`, `TestStateConcurrency` |
| T013 (dag_engine core) | `test_dag_engine_*`, cycle detection tests |
| T017 (worktree/manager.py) | `test_worktree_*`, integration tests |
| T022 (skf dag command) | CLI tests, e2e workflow tests |

Before marking a task complete:
- [ ] Unit tests written and passing
- [ ] Edge cases covered
- [ ] Coverage threshold met for affected code
- [ ] Integration tests if component interacts with others
