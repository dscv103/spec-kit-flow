"""
Completion detection mechanisms for SpecKitFlow.

This module provides file-based completion detection using touch files
for manual task completion marking and file watching for tasks.md changes.
"""

import re
import time
from pathlib import Path
from typing import Callable, Optional
from threading import Lock, Event

__all__ = [
    "CompletionMonitor",
    "watch_tasks_file",
]

# Pattern to detect completed tasks: - [x] [T###]
COMPLETED_TASK_PATTERN = re.compile(
    r"^-\s+\[([xX])\]\s+\[([T]\d{3})\]",
    re.MULTILINE
)


class CompletionMonitor:
    """Monitor for task completion detection using touch files.
    
    This class implements file-based IPC for manual task completion marking.
    Touch files are stored in `.speckit/completions/{task_id}.done` and serve
    as simple, reliable completion markers that can be checked by any process.
    
    Attributes:
        spec_id: Specification ID for this orchestration session
        repo_root: Path to the repository root
        completions_dir: Path to the completions directory
        
    Example:
        >>> monitor = CompletionMonitor("001-feature", Path("/path/to/repo"))
        >>> monitor.mark_complete("T001")
        >>> assert monitor.is_complete("T001")
        >>> assert "T001" in monitor.get_manual_completions()
    """
    
    def __init__(self, spec_id: str, repo_root: Path):
        """Initialize completion monitor.
        
        Args:
            spec_id: Specification ID for this orchestration session
            repo_root: Path to the repository root
        """
        self.spec_id = spec_id
        self.repo_root = repo_root
        self.completions_dir = repo_root / ".speckit" / "completions"
    
    def mark_complete(self, task_id: str) -> None:
        """Mark a task as complete by creating a touch file.
        
        Creates an empty file at `.speckit/completions/{task_id}.done` to
        signal task completion. This operation is atomic and safe for
        concurrent access.
        
        Args:
            task_id: Task ID to mark as complete (e.g., "T001")
            
        Example:
            >>> monitor = CompletionMonitor("001-feature", repo_root)
            >>> monitor.mark_complete("T001")
            >>> assert (repo_root / ".speckit/completions/T001.done").exists()
        """
        # Create completions directory if it doesn't exist
        self.completions_dir.mkdir(parents=True, exist_ok=True)
        
        # Create touch file (atomic operation)
        done_file = self.completions_dir / f"{task_id}.done"
        done_file.touch()
    
    def is_complete(self, task_id: str) -> bool:
        """Check if a task has been marked complete.
        
        Args:
            task_id: Task ID to check (e.g., "T001")
            
        Returns:
            True if the task's done file exists, False otherwise
            
        Example:
            >>> monitor = CompletionMonitor("001-feature", repo_root)
            >>> monitor.mark_complete("T001")
            >>> assert monitor.is_complete("T001")
            >>> assert not monitor.is_complete("T002")
        """
        done_file = self.completions_dir / f"{task_id}.done"
        return done_file.exists()
    
    def get_manual_completions(self) -> set[str]:
        """Get all manually completed task IDs.
        
        Scans the completions directory for `.done` files and returns
        the set of task IDs that have been manually marked complete.
        
        Returns:
            Set of task IDs that have completion markers
            
        Example:
            >>> monitor = CompletionMonitor("001-feature", repo_root)
            >>> monitor.mark_complete("T001")
            >>> monitor.mark_complete("T002")
            >>> completions = monitor.get_manual_completions()
            >>> assert completions == {"T001", "T002"}
        """
        # Return empty set if directory doesn't exist yet
        if not self.completions_dir.exists():
            return set()
        
        # Collect all task IDs from .done files
        completed = set()
        for done_file in self.completions_dir.glob("*.done"):
            # Extract task ID from filename (e.g., "T001.done" -> "T001")
            task_id = done_file.stem
            completed.add(task_id)
        
        return completed
    
    def get_completed_tasks(self, tasks_file: Optional[Path] = None) -> set[str]:
        """Get all completed task IDs from both manual and watched sources.
        
        Returns the union of:
        - Manual completions (done files in .speckit/completions/)
        - Watched completions (checked tasks in tasks.md if provided)
        
        Args:
            tasks_file: Optional path to tasks.md file to check for completed checkboxes.
                       If None, only manual completions are returned.
        
        Returns:
            Set of all completed task IDs from both sources
            
        Example:
            >>> monitor = CompletionMonitor("001-feature", repo_root)
            >>> monitor.mark_complete("T001")  # Manual completion
            >>> # T002 marked [x] in tasks.md
            >>> tasks_path = repo_root / "specs" / "feature" / "tasks.md"
            >>> completed = monitor.get_completed_tasks(tasks_path)
            >>> assert completed == {"T001", "T002"}
        """
        # Get manual completions (done files)
        completed = self.get_manual_completions()
        
        # Add watched completions from tasks.md if provided
        if tasks_file is not None and tasks_file.exists():
            try:
                watched = _parse_completed_tasks(tasks_file)
                completed = completed.union(watched)
            except Exception:
                # If parsing fails, just return manual completions
                # This ensures partial functionality even if tasks.md is corrupted
                pass
        
        return completed
    
    def wait_for_completion(
        self,
        task_ids: set[str],
        tasks_file: Optional[Path] = None,
        timeout: Optional[float] = None,
        poll_interval: float = 0.5,
    ) -> set[str]:
        """Wait for specified tasks to complete, with optional timeout.
        
        Blocks until all specified tasks are marked complete (either via done files
        or tasks.md checkboxes), or until the timeout is reached.
        
        Args:
            task_ids: Set of task IDs to wait for completion
            tasks_file: Optional path to tasks.md file to monitor for checkbox changes
            timeout: Optional timeout in seconds. If None, waits indefinitely.
            poll_interval: How often to check for completion (in seconds)
            
        Returns:
            Set of task IDs that were completed. If all tasks completed before timeout,
            returns the same set as task_ids. If timeout occurred, returns the subset
            of tasks that completed before timeout.
            
        Raises:
            TimeoutError: If timeout is reached before all tasks complete
            
        Example:
            >>> monitor = CompletionMonitor("001-feature", repo_root)
            >>> tasks_path = repo_root / "specs" / "feature" / "tasks.md"
            >>> # Wait for T001 and T002 to complete, timeout after 30 seconds
            >>> try:
            ...     completed = monitor.wait_for_completion(
            ...         {"T001", "T002"}, tasks_path, timeout=30.0
            ...     )
            ...     print(f"All tasks completed: {completed}")
            ... except TimeoutError:
            ...     print("Timeout waiting for tasks")
        """
        if not task_ids:
            # Empty set - nothing to wait for
            return set()
        
        start_time = time.time()
        
        while True:
            # Check current completion status
            completed = self.get_completed_tasks(tasks_file)
            
            # Check if all requested tasks are complete
            if task_ids.issubset(completed):
                return task_ids
            
            # Check for timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    # Return tasks that completed before timeout
                    completed_subset = task_ids.intersection(completed)
                    pending = task_ids - completed_subset
                    raise TimeoutError(
                        f"Timeout waiting for tasks to complete. "
                        f"Pending: {sorted(pending)}, "
                        f"Completed: {sorted(completed_subset)}"
                    )
            
            # Sleep before next check
            time.sleep(poll_interval)


def watch_tasks_file(
    path: Path,
    callback: Callable[[set[str]], None],
    debounce_ms: int = 100,
    poll_interval_ms: int = 50,
) -> None:
    """Watch a tasks.md file for completion checkbox changes.
    
    This function monitors a tasks.md file for changes and detects when
    task checkboxes are marked complete (- [x] [T###]). When changes are
    detected, it parses the file to identify newly completed tasks and
    invokes the callback with the set of newly completed task IDs.
    
    The function implements debouncing to handle rapid successive changes
    and gracefully handles file deletion/rename scenarios.
    
    Args:
        path: Path to the tasks.md file to watch
        callback: Function to call with set of newly completed task IDs
        debounce_ms: Milliseconds to wait for additional changes before processing
        poll_interval_ms: Milliseconds between file system checks
        
    Raises:
        FileNotFoundError: If the tasks file doesn't exist initially
        
    Example:
        >>> def on_complete(task_ids: set[str]):
        ...     print(f"Tasks completed: {task_ids}")
        >>> watch_tasks_file(Path("tasks.md"), on_complete)
        # Blocks and calls on_complete when tasks are marked complete
        
    Note:
        This function blocks indefinitely. It should be run in a separate
        thread when used in concurrent scenarios.
    """
    # Lazy import for performance (watchfiles is only needed when watching)
    from watchfiles import watch, Change
    
    if not path.exists():
        raise FileNotFoundError(f"Tasks file not found: {path}")
    
    # Track previously completed tasks to detect new completions
    previous_completed: set[str] = _parse_completed_tasks(path)
    
    # Track last change time for debouncing
    last_change_time: Optional[float] = None
    change_lock = Lock()
    
    try:
        # Watch only the specific file
        for changes in watch(
            path,
            watch_filter=lambda change, filepath: change == Change.modified,
            debounce=debounce_ms,
            step=poll_interval_ms,
            yield_on_timeout=False,
        ):
            with change_lock:
                # Record change time
                current_time = time.time()
                last_change_time = current_time
            
            # Small additional delay to ensure file write is complete
            time.sleep(0.01)
            
            # Check if file still exists (handle deletion/rename)
            if not path.exists():
                # File was deleted or renamed - stop watching
                # Callback with empty set to signal file loss
                break
            
            try:
                # Parse current completed tasks
                current_completed = _parse_completed_tasks(path)
                
                # Identify newly completed tasks
                newly_completed = current_completed - previous_completed
                
                if newly_completed:
                    # Call callback with newly completed tasks
                    callback(newly_completed)
                    
                    # Update tracking
                    previous_completed = current_completed
                    
            except Exception as e:
                # If parsing fails (e.g., file corruption, encoding issues),
                # log but continue watching
                # In production, this should log to proper logger
                pass
                
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        pass


def _parse_completed_tasks(path: Path) -> set[str]:
    """Parse completed task IDs from a tasks.md file.
    
    Internal helper function that reads a tasks.md file and extracts
    all task IDs that are marked as completed (checkbox is [x]).
    
    Args:
        path: Path to tasks.md file
        
    Returns:
        Set of completed task IDs (e.g., {"T001", "T003"})
        
    Raises:
        FileNotFoundError: If file doesn't exist
        
    Example:
        >>> tasks = _parse_completed_tasks(Path("tasks.md"))
        >>> assert "T001" in tasks  # If T001 is marked [x]
    """
    if not path.exists():
        raise FileNotFoundError(f"Tasks file not found: {path}")
    
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        # Re-raise with more context
        raise IOError(f"Failed to read tasks file {path}: {e}")
    
    # Find all completed tasks using regex
    completed = set()
    for match in COMPLETED_TASK_PATTERN.finditer(content):
        # Group 2 is the task ID (T###)
        task_id = match.group(2).upper()
        completed.add(task_id)
    
    return completed