---
name: Performance Standards

description: Performance targets, lazy loading patterns, file I/O optimization, DAG computation efficiency, and benchmarking guidelines for SpecKitFlow.

applyTo: "src/**/*.py"
---

# Performance Instructions

## Purpose

This document establishes performance requirements and optimization guidelines for SpecKitFlow. Fast, responsive operations are essential for developer productivity.

## Performance Targets

### Response Time Targets

| Operation Category | Target | Hard Limit |
|-------------------|--------|------------|
| CLI startup | < 200ms | 500ms |
| DAG generation (50 tasks) | < 500ms | 1s |
| State file read | < 50ms | 100ms |
| State file write | < 100ms | 200ms |
| Worktree creation (each) | < 2s | 5s |
| Completion detection | < 100ms | 250ms |

### Memory Targets

| Scenario | Target | Hard Limit |
|----------|--------|------------|
| CLI idle | < 50MB | 100MB |
| DAG in memory (100 tasks) | < 10MB | 50MB |
| State monitoring | < 75MB | 150MB |
| Peak during orchestration | < 200MB | 500MB |

### Throughput Targets

| Operation | Target |
|-----------|--------|
| Parse tasks.md (100 tasks) | < 100ms |
| Generate DAG (100 tasks) | < 200ms |
| Topological sort (100 nodes) | < 10ms |
| YAML serialize (1000 lines) | < 50ms |

## Lazy Loading

### Import Optimization

Only import heavy modules when needed:

```python
# ❌ Top-level imports of heavy modules
import networkx as nx
from watchfiles import watch
import yaml

# ✅ Lazy imports
def build_dag(tasks: list[TaskInfo]) -> DAGEngine:
    import networkx as nx  # Only imported when building DAG
    
    graph = nx.DiGraph()
    for task in tasks:
        graph.add_node(task.id)
        for dep in task.dependencies:
            graph.add_edge(dep, task.id)
    
    return DAGEngine(graph)

def watch_for_completion():
    from watchfiles import watch  # Only imported when watching
    
    for changes in watch(tasks_path):
        process_changes(changes)
```

### Deferred Initialization

Don't initialize expensive resources until needed:

```python
class DAGEngine:
    def __init__(self, tasks: list[TaskInfo]):
        self._tasks = tasks
        self._graph = None  # Lazy
        self._phases = None  # Lazy
    
    @property
    def graph(self) -> "nx.DiGraph":
        if self._graph is None:
            import networkx as nx
            self._graph = self._build_graph()
        return self._graph
    
    @property
    def phases(self) -> list[Phase]:
        if self._phases is None:
            self._phases = self._compute_phases()
        return self._phases
```

## File I/O Optimization

### Buffered Reading

Read files efficiently:

```python
# ❌ Multiple small reads
def parse_tasks(path: Path) -> list[TaskInfo]:
    with open(path) as f:
        lines = []
        for line in f:  # Line-by-line read
            lines.append(line)
    return parse_lines(lines)

# ✅ Single buffered read
def parse_tasks(path: Path) -> list[TaskInfo]:
    content = path.read_text()  # Single read operation
    return parse_content(content)
```

### Atomic Writes

Use atomic writes with temp files:

```python
import tempfile

def write_state(state: OrchestrationState, path: Path) -> None:
    """Atomic write with temp file and rename."""
    content = yaml.dump(state.model_dump())
    
    # Write to temp file in same directory (for same filesystem)
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".state_",
        suffix=".yaml.tmp",
    )
    try:
        os.write(fd, content.encode())
        os.fsync(fd)  # Ensure data is on disk
        os.close(fd)
        
        # Atomic rename
        os.replace(temp_path, path)
    except:
        os.unlink(temp_path)  # Clean up on failure
        raise
```

### Minimal State Updates

Don't rewrite entire state for small changes:

```python
# ❌ Full state rewrite for each task completion
def mark_task_complete(task_id: str):
    state = load_state()  # Full read
    state.tasks[task_id].status = "completed"
    save_state(state)  # Full write

# ✅ Incremental update approach (for high-frequency updates)
class StateManager:
    def __init__(self, path: Path):
        self._path = path
        self._state = None
        self._dirty = False
    
    def mark_complete(self, task_id: str) -> None:
        self._ensure_loaded()
        self._state.tasks[task_id].status = "completed"
        self._dirty = True
    
    def flush(self) -> None:
        """Batch write dirty state."""
        if self._dirty:
            self._save()
            self._dirty = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.flush()
```

## DAG Computation Efficiency

### Topological Sort Once

Compute topological order once, reuse:

```python
class DAGEngine:
    def __init__(self, graph: "nx.DiGraph"):
        self._graph = graph
        # Compute once during initialization
        self._topo_order = list(nx.topological_sort(graph))
        self._phases = self._compute_phases_from_order(self._topo_order)
    
    def get_available_tasks(self, completed: set[str]) -> list[str]:
        """O(n) lookup using pre-computed order."""
        available = []
        for task_id in self._topo_order:
            if task_id in completed:
                continue
            deps = set(self._graph.predecessors(task_id))
            if deps <= completed:  # All deps complete
                available.append(task_id)
        return available
```

### Cycle Detection During Build

Detect cycles during DAG construction, not after:

```python
def build_dag(tasks: list[TaskInfo]) -> DAGEngine:
    import networkx as nx
    
    graph = nx.DiGraph()
    
    for task in tasks:
        graph.add_node(task.id)
        for dep in task.dependencies:
            graph.add_edge(dep, task.id)
            
            # Check for cycle immediately after adding edge
            if not nx.is_directed_acyclic_graph(graph):
                # Find and report the cycle
                try:
                    cycle = nx.find_cycle(graph)
                    cycle_nodes = [edge[0] for edge in cycle]
                    raise CyclicDependencyError(cycle=cycle_nodes)
                except nx.NetworkXNoCycle:
                    pass
    
    return DAGEngine(graph)
```

### Index by Task ID

Use dictionaries for O(1) task lookup:

```python
# ❌ Linear search
def get_task(tasks: list[TaskInfo], task_id: str) -> TaskInfo:
    for task in tasks:
        if task.id == task_id:
            return task
    raise TaskNotFoundError(task_id)

# ✅ O(1) lookup
class TaskRegistry:
    def __init__(self, tasks: list[TaskInfo]):
        self._by_id: dict[str, TaskInfo] = {t.id: t for t in tasks}
        self._by_phase: dict[str, list[TaskInfo]] = {}
        for task in tasks:
            self._by_phase.setdefault(task.phase, []).append(task)
    
    def get(self, task_id: str) -> TaskInfo:
        return self._by_id[task_id]
    
    def by_phase(self, phase: str) -> list[TaskInfo]:
        return self._by_phase.get(phase, [])
```

## Worktree Operations

### Parallel Worktree Creation

Create multiple worktrees concurrently:

```python
import concurrent.futures
import subprocess

def create_worktrees(sessions: int, base_path: Path) -> list[Path]:
    """Create worktrees in parallel."""
    
    def create_one(session_id: int) -> Path:
        path = base_path / f"session-{session_id}"
        branch = f"impl-session-{session_id}"
        
        subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(path)],
            capture_output=True,
            check=True,
        )
        return path
    
    # Use ThreadPoolExecutor for I/O-bound git operations
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(create_one, i) for i in range(sessions)]
        paths = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    return sorted(paths)
```

### Incremental Worktree Cleanup

Clean up worktrees as sessions complete:

```python
def cleanup_completed_session(session: SessionState) -> None:
    """Clean up a single completed session's worktree."""
    if session.status != "completed":
        return
    
    worktree_path = session.worktree_path
    
    # Merge branch if configured
    if session.merge_on_complete:
        merge_branch(session.branch_name)
    
    # Remove worktree
    subprocess.run(
        ["git", "worktree", "remove", str(worktree_path)],
        capture_output=True,
        check=True,
    )
    
    # Optionally delete branch
    if session.delete_branch_after:
        subprocess.run(
            ["git", "branch", "-d", session.branch_name],
            capture_output=True,
            check=False,  # May fail if not fully merged
        )
```

## Completion Detection Efficiency

### Efficient File Watching

Use watchfiles efficiently:

```python
from watchfiles import watch, Change

def watch_tasks_file(tasks_path: Path, callback: Callable[[str], None]) -> None:
    """Watch tasks.md for checkbox changes."""
    
    # Watch only the specific file, not directory
    for changes in watch(
        tasks_path,
        watch_filter=lambda change, path: change == Change.modified,
        debounce=100,  # Debounce rapid changes (ms)
        step=50,  # Check interval (ms)
    ):
        for change_type, path in changes:
            callback(path)
```

### Efficient Task Status Parsing

Parse only task checkboxes, not full content:

```python
import re

TASK_PATTERN = re.compile(r"^- \[([ xX])\] \*\*(T\d+)\*\*:", re.MULTILINE)

def parse_task_statuses(content: str) -> dict[str, bool]:
    """Parse task completion status - O(n) single pass."""
    statuses = {}
    
    for match in TASK_PATTERN.finditer(content):
        checkbox = match.group(1)
        task_id = match.group(2)
        statuses[task_id] = checkbox.lower() == "x"
    
    return statuses

def detect_completions(
    prev_statuses: dict[str, bool],
    curr_statuses: dict[str, bool],
) -> list[str]:
    """Find newly completed tasks - O(n)."""
    return [
        task_id
        for task_id, completed in curr_statuses.items()
        if completed and not prev_statuses.get(task_id, False)
    ]
```

### Touch File Polling

Efficient touch file checking:

```python
from pathlib import Path
import os

class CompletionDetector:
    def __init__(self, touch_dir: Path):
        self._touch_dir = touch_dir
        self._known_files: dict[str, float] = {}  # task_id -> mtime
    
    def check_completions(self) -> list[str]:
        """Check for new completion touch files - O(n) where n is sessions."""
        completed = []
        
        for touch_file in self._touch_dir.glob("*.complete"):
            task_id = touch_file.stem
            mtime = touch_file.stat().st_mtime
            
            if task_id not in self._known_files:
                self._known_files[task_id] = mtime
                completed.append(task_id)
            elif mtime > self._known_files[task_id]:
                self._known_files[task_id] = mtime
                completed.append(task_id)
        
        return completed
```

## Profiling and Benchmarking

### Built-in Timing

Add timing for performance-critical operations:

```python
import time
from contextlib import contextmanager
from typing import Generator

@contextmanager
def timer(name: str, threshold_ms: float = 0) -> Generator[None, None, None]:
    """Time a block and log if over threshold."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > threshold_ms:
            logger.debug(f"{name}: {elapsed_ms:.1f}ms")

# Usage
def dag_command():
    with timer("parse_tasks", threshold_ms=100):
        tasks = parse_tasks(tasks_path)
    
    with timer("build_dag", threshold_ms=200):
        dag = build_dag(tasks)
    
    with timer("compute_phases", threshold_ms=50):
        phases = dag.compute_phases()
```

### Performance Tests

Include performance benchmarks in tests:

```python
import pytest
import time

@pytest.mark.benchmark
def test_dag_generation_performance():
    """DAG generation should complete within target time."""
    # Generate 100 tasks with complex dependencies
    tasks = generate_test_tasks(count=100, max_deps=5)
    
    start = time.perf_counter()
    dag = build_dag(tasks)
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    # Must complete within 200ms target
    assert elapsed_ms < 200, f"DAG generation took {elapsed_ms:.1f}ms, target is 200ms"
    
    # Verify correctness
    assert dag.is_valid()
    assert len(dag.phases) > 0

@pytest.mark.benchmark
def test_state_write_performance(tmp_path):
    """State writes should be fast."""
    state = generate_test_state(task_count=50, session_count=4)
    state_path = tmp_path / "state.yaml"
    
    # Warm up
    write_state(state, state_path)
    
    # Measure
    times = []
    for _ in range(10):
        start = time.perf_counter()
        write_state(state, state_path)
        times.append((time.perf_counter() - start) * 1000)
    
    avg_ms = sum(times) / len(times)
    assert avg_ms < 100, f"State write averaged {avg_ms:.1f}ms, target is 100ms"
```

## Performance Monitoring

### Debug Timing Mode

Add --debug-timing flag for performance investigation:

```python
@app.command()
def dag(
    debug_timing: bool = typer.Option(
        False, "--debug-timing", hidden=True,
        help="Show timing for each operation",
    ),
):
    """Generate DAG from tasks."""
    if debug_timing:
        import cProfile
        import pstats
        
        profiler = cProfile.Profile()
        profiler.enable()
    
    try:
        with timer("total", threshold_ms=0 if debug_timing else 500):
            with timer("parse", threshold_ms=0 if debug_timing else 100):
                tasks = parse_tasks(tasks_path)
            
            with timer("build", threshold_ms=0 if debug_timing else 200):
                dag = build_dag(tasks)
            
            with timer("output", threshold_ms=0 if debug_timing else 50):
                print_dag(dag)
    finally:
        if debug_timing:
            profiler.disable()
            stats = pstats.Stats(profiler)
            stats.sort_stats("cumulative")
            stats.print_stats(20)
```

## Performance Checklist

Before completing any performance-sensitive feature:

- [ ] Measured baseline performance
- [ ] Heavy imports are lazy-loaded
- [ ] File I/O is batched and buffered
- [ ] Data structures use appropriate indices
- [ ] Expensive computations are cached
- [ ] State updates are incremental where possible
- [ ] Long operations show progress
- [ ] Performance tests verify targets
- [ ] No N+1 query patterns (loop with I/O inside)
- [ ] Memory usage tested for large inputs
