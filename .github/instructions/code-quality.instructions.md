---
name: Code Quality Standards

description: Code quality principles, type safety requirements, error handling patterns, and documentation standards for SpecKitFlow implementation.

applyTo: "src/**/*.py"
---

# Code Quality Instructions

## Purpose

This document establishes code quality standards for SpecKitFlow. All code must meet these standards before being considered complete.

## Core Principles

### Principle 1: Correctness Over Cleverness

Write code that is obviously correct, not code that requires explanation.

```python
# ❌ Clever but unclear
phases = [list(g) for _, g in groupby(sorted(tasks, key=lambda t: len(t.deps)), key=lambda t: len(t.deps))]

# ✅ Obvious and correct
def group_tasks_by_dependency_depth(tasks: list[TaskInfo]) -> list[list[TaskInfo]]:
    """Group tasks by their dependency depth for parallel execution."""
    depth_map: dict[int, list[TaskInfo]] = {}
    for task in tasks:
        depth = len(task.dependencies)
        depth_map.setdefault(depth, []).append(task)
    return [depth_map[d] for d in sorted(depth_map.keys())]
```

### Principle 2: Explicit Over Implicit

Make behavior visible and predictable.

```python
# ❌ Implicit behavior
def save(self, state):
    self._backup()  # Hidden side effect
    self._write(state)

# ✅ Explicit behavior  
def save(self, state: OrchestrationState, *, create_backup: bool = True) -> None:
    """Save state to disk with optional backup."""
    if create_backup:
        self.create_backup()
    self._write_atomic(state)
```

### Principle 3: Fail Fast and Loud

Detect errors early and report them clearly.

```python
# ❌ Silent failure
def get_task(self, task_id: str) -> TaskInfo | None:
    return self.tasks.get(task_id)

# ✅ Explicit failure with context
def get_task(self, task_id: str) -> TaskInfo:
    """Get task by ID. Raises TaskNotFoundError if not found."""
    if task_id not in self.tasks:
        available = ", ".join(sorted(self.tasks.keys())[:5])
        raise TaskNotFoundError(
            f"Task '{task_id}' not found. Available: {available}..."
        )
    return self.tasks[task_id]
```

### Principle 4: Defensive Programming

Validate inputs at boundaries, trust internal data.

```python
# ✅ Validate at public API boundary
def parse_tasks_file(path: Path) -> list[TaskInfo]:
    """Parse tasks from file. Raises FileNotFoundError, TaskParseError."""
    if not path.exists():
        raise FileNotFoundError(f"Tasks file not found: {path}")
    if not path.suffix == ".md":
        raise ValueError(f"Expected .md file, got: {path.suffix}")
    
    content = path.read_text(encoding="utf-8")
    return _parse_tasks_content(content)  # Internal function trusts input

# Internal function - no validation needed
def _parse_tasks_content(content: str) -> list[TaskInfo]:
    """Parse tasks from validated content."""
    # ... implementation
```

## Type Safety

### Required Type Annotations

All public functions MUST have complete type annotations:

```python
# ✅ Complete type annotations
def assign_sessions(
    tasks: list[TaskInfo],
    num_sessions: int,
    *,
    strategy: Literal["round-robin", "load-balanced"] = "round-robin",
) -> dict[int, list[TaskInfo]]:
    """Assign tasks to sessions.
    
    Args:
        tasks: List of tasks to assign
        num_sessions: Number of available sessions
        strategy: Assignment strategy to use
        
    Returns:
        Mapping of session ID to assigned tasks
        
    Raises:
        ValueError: If num_sessions < 1
    """
```

### Use Strict Types

Prefer specific types over generic ones:

```python
# ❌ Too generic
def process(data: dict) -> list:
    ...

# ✅ Specific types
def process(data: dict[str, TaskInfo]) -> list[DAGPhase]:
    ...
```

### Leverage Type Aliases

Define type aliases for complex types:

```python
# In speckit_core/types.py
from typing import TypeAlias

TaskId: TypeAlias = str  # Format: T###
SessionId: TypeAlias = int  # 0-based session index
PhaseIndex: TypeAlias = int  # 0-based phase index
TaskGraph: TypeAlias = "nx.DiGraph[TaskId]"
```

## Error Handling

### Custom Exception Hierarchy

```python
# speckit_core/exceptions.py
class SpecKitError(Exception):
    """Base exception for all SpecKit errors."""
    pass

class ConfigurationError(SpecKitError):
    """Invalid or missing configuration."""
    pass

class NotInGitRepoError(SpecKitError):
    """Operation requires git repository."""
    pass

class FeatureNotFoundError(SpecKitError):
    """Feature branch or spec directory not found."""
    pass

# speckit_flow/exceptions.py
class SpecKitFlowError(Exception):
    """Base exception for SpecKitFlow errors."""
    pass

class CyclicDependencyError(SpecKitFlowError):
    """Task dependency graph contains cycles."""
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' → '.join(cycle)}")

class StateNotFoundError(SpecKitFlowError):
    """Orchestration state file not found."""
    pass

class WorktreeExistsError(SpecKitFlowError):
    """Git worktree already exists."""
    pass
```

### Error Message Quality

Error messages must be:
1. **Specific**: What exactly failed
2. **Actionable**: What can the user do
3. **Contextual**: Relevant details included

```python
# ❌ Unhelpful error
raise ValueError("Invalid task")

# ✅ Helpful error
raise TaskParseError(
    f"Failed to parse task on line {line_num}: {line!r}\n"
    f"Expected format: '- [ ] [T###] [optional markers] Description'\n"
    f"Example: '- [ ] [T001] [P] [deps:] Implement feature'"
)
```

## Documentation Standards

### Docstring Requirements

All public classes and functions require docstrings:

```python
class DAGEngine:
    """Directed Acyclic Graph engine for task dependency resolution.
    
    This engine builds a dependency graph from tasks, validates it for
    cycles, and provides methods to extract parallel execution phases.
    
    Attributes:
        graph: The underlying networkx DiGraph
        tasks: Mapping of task ID to TaskInfo
        
    Example:
        >>> tasks = parse_tasks_file(Path("tasks.md"))
        >>> engine = DAGEngine(tasks)
        >>> engine.validate()  # Raises CyclicDependencyError if cycles exist
        >>> phases = engine.get_phases()
        >>> print(f"Found {len(phases)} execution phases")
    """
```

### Inline Comments

Use comments to explain **why**, not **what**:

```python
# ❌ Comments that describe what code does
# Loop through tasks
for task in tasks:
    # Check if task is parallelizable
    if task.parallelizable:
        # Add to parallel list
        parallel.append(task)

# ✅ Comments that explain why
# Tasks marked [P] can run concurrently because they modify
# different files and have no shared dependencies
for task in tasks:
    if task.parallelizable:
        parallel.append(task)
```

## Code Organization

### Module Structure

Each module should have a clear, single responsibility:

```python
# speckit_core/tasks.py - ONLY task parsing
"""Task parsing utilities for tasks.md files."""

from .models import TaskInfo  # Import models, don't define here
from .exceptions import TaskParseError  # Import exceptions

# All functions relate to parsing
def parse_task_line(line: str) -> TaskInfo | None: ...
def parse_tasks_file(path: Path) -> list[TaskInfo]: ...
def _extract_markers(text: str) -> dict[str, str]: ...  # Private helper
```

### Import Order

Follow PEP 8 import ordering with blank lines:

```python
# Standard library
import re
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party
import networkx as nx
from pydantic import BaseModel
from rich.console import Console

# Local - absolute imports preferred
from speckit_core.models import TaskInfo
from speckit_core.exceptions import TaskParseError

if TYPE_CHECKING:
    from speckit_flow.state.manager import StateManager
```

### Function Length

Functions should be < 50 lines. If longer, extract helpers:

```python
# ❌ Too long - hard to understand and test
def process_orchestration(config, tasks, state):
    # ... 100 lines of mixed concerns ...

# ✅ Decomposed into focused functions
def process_orchestration(config: Config, tasks: list[TaskInfo], state: State) -> Result:
    """Orchestrate task execution across sessions."""
    dag = _build_dag(tasks)
    phases = _extract_phases(dag)
    sessions = _create_sessions(config.num_sessions, phases)
    return _execute_phases(sessions, state)

def _build_dag(tasks: list[TaskInfo]) -> nx.DiGraph: ...
def _extract_phases(dag: nx.DiGraph) -> list[Phase]: ...
def _create_sessions(num: int, phases: list[Phase]) -> list[Session]: ...
def _execute_phases(sessions: list[Session], state: State) -> Result: ...
```

## Naming Conventions

### Variables and Functions

```python
# Use descriptive names
task_count = len(tasks)  # Not: n, cnt, tc
is_parallelizable = task.parallelizable  # Not: p, para
completed_task_ids = {t.id for t in tasks if t.completed}  # Not: done

# Boolean variables/functions start with is_, has_, can_, should_
is_valid = dag.validate()
has_cycles = not nx.is_directed_acyclic_graph(graph)
can_execute = all(dep in completed for dep in task.dependencies)
should_checkpoint = phase_idx % checkpoint_interval == 0
```

### Classes

```python
# Classes are nouns, methods are verbs
class WorktreeManager:
    def create(self, spec_id: str, session_id: int) -> Path: ...
    def remove(self, path: Path) -> None: ...
    def list_all(self) -> list[WorktreeInfo]: ...
    def cleanup_spec(self, spec_id: str) -> int: ...  # Returns count removed
```

### Constants

```python
# Module-level constants in UPPER_SNAKE_CASE
DEFAULT_NUM_SESSIONS = 3
MAX_CHECKPOINT_AGE_DAYS = 7
TASK_ID_PATTERN = re.compile(r"\[T(\d{3})\]")

# In a dedicated constants module for shared values
# speckit_core/constants.py
STATE_FILE_NAME = "flow-state.yaml"
CONFIG_FILE_NAME = "speckit-flow.yaml"
SPECKIT_DIR = ".speckit"
```

## Code Review Checklist

Before submitting code, verify:

### Correctness
- [ ] All acceptance criteria from task met
- [ ] Edge cases handled (empty inputs, missing files, etc.)
- [ ] Error messages are helpful and actionable

### Type Safety
- [ ] All public functions have complete type annotations
- [ ] No `Any` types without justification
- [ ] Pydantic models use v2 syntax (`model_dump()`, not `dict()`)

### Documentation
- [ ] All public classes/functions have docstrings
- [ ] Complex logic has explanatory comments
- [ ] No commented-out code

### Style
- [ ] Functions < 50 lines
- [ ] Descriptive variable names
- [ ] Imports properly ordered
- [ ] No magic numbers (use named constants)

### Safety
- [ ] File operations use `pathlib.Path`
- [ ] Subprocess calls use `check=True` or explicit error handling
- [ ] State writes are atomic (temp + rename)
- [ ] File locks used for concurrent access

## Automated Quality Checks

The following tools should pass before code is considered complete:

```bash
# Type checking
mypy src/speckit_core src/speckit_flow --strict

# Linting
ruff check src/

# Formatting
ruff format --check src/

# Import sorting
ruff check --select I src/
```

### Recommended pyproject.toml Configuration

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
]
```
