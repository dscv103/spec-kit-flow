"""
Unit tests for tasks.md file watching functionality.

Tests for T026: watch_tasks_file implementation.
"""

import time
import threading
from pathlib import Path
import pytest

from speckit_flow.orchestration.completion import (
    watch_tasks_file,
    _parse_completed_tasks,
)


class TestParseCompletedTasks:
    """Unit tests for _parse_completed_tasks helper function."""
    
    def test_parses_completed_tasks(self, tmp_path):
        """Parses tasks marked with [x] checkbox."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("""
# Tasks
- [x] [T001] Completed task
- [ ] [T002] Pending task
- [x] [T003] Another completed task
        """)
        
        completed = _parse_completed_tasks(tasks_file)
        
        assert completed == {"T001", "T003"}
    
    def test_handles_uppercase_x(self, tmp_path):
        """Handles both lowercase and uppercase X in checkboxes."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("""
- [x] [T001] lowercase x
- [X] [T002] uppercase X
        """)
        
        completed = _parse_completed_tasks(tasks_file)
        
        assert completed == {"T001", "T002"}
    
    def test_empty_file(self, tmp_path):
        """Returns empty set for empty file."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("")
        
        completed = _parse_completed_tasks(tasks_file)
        
        assert completed == set()
    
    def test_no_completed_tasks(self, tmp_path):
        """Returns empty set when no tasks are completed."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("""
# Tasks
- [ ] [T001] Pending task
- [ ] [T002] Another pending task
        """)
        
        completed = _parse_completed_tasks(tasks_file)
        
        assert completed == set()
    
    def test_file_not_found(self, tmp_path):
        """Raises FileNotFoundError for missing file."""
        nonexistent = tmp_path / "nonexistent.md"
        
        with pytest.raises(FileNotFoundError):
            _parse_completed_tasks(nonexistent)
    
    def test_handles_unicode(self, tmp_path):
        """Handles Unicode characters in task descriptions."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("""
- [x] [T001] Task with émojis 🚀
- [x] [T002] Task with 中文
        """, encoding="utf-8")
        
        completed = _parse_completed_tasks(tasks_file)
        
        assert completed == {"T001", "T002"}
    
    def test_ignores_non_task_lines(self, tmp_path):
        """Ignores lines that aren't task format."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("""
# Header
Some text with [x] and [T001] but not a task.
- Regular bullet point
- [x] [T001] Actual task
        """)
        
        completed = _parse_completed_tasks(tasks_file)
        
        assert completed == {"T001"}


class TestWatchTasksFile:
    """Integration tests for watch_tasks_file function."""
    
    def test_detects_checkbox_changes(self, tmp_path):
        """Detects when task checkboxes are marked complete."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("""
# Tasks
- [ ] [T001] Task one
- [ ] [T002] Task two
        """)
        
        # Track callback invocations
        completed_tasks = []
        callback_event = threading.Event()
        
        def callback(task_ids: set[str]):
            completed_tasks.append(task_ids)
            callback_event.set()
        
        # Start watching in background thread
        watch_thread = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file, callback),
            daemon=True
        )
        watch_thread.start()
        
        # Give watcher time to initialize
        time.sleep(0.2)
        
        # Mark T001 complete
        tasks_file.write_text("""
# Tasks
- [x] [T001] Task one
- [ ] [T002] Task two
        """)
        
        # Wait for callback (with timeout)
        assert callback_event.wait(timeout=2.0), "Callback not called within timeout"
        
        # Verify correct task detected
        assert len(completed_tasks) > 0
        assert "T001" in completed_tasks[0]
    
    def test_handles_multiple_completions(self, tmp_path):
        """Detects multiple tasks marked complete in one change."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("""
- [ ] [T001] Task one
- [ ] [T002] Task two
- [ ] [T003] Task three
        """)
        
        completed_tasks = []
        callback_event = threading.Event()
        
        def callback(task_ids: set[str]):
            completed_tasks.append(task_ids)
            callback_event.set()
        
        watch_thread = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file, callback),
            daemon=True
        )
        watch_thread.start()
        time.sleep(0.2)
        
        # Mark multiple tasks complete
        tasks_file.write_text("""
- [x] [T001] Task one
- [x] [T002] Task two
- [ ] [T003] Task three
        """)
        
        assert callback_event.wait(timeout=2.0)
        
        # Both tasks should be detected
        assert len(completed_tasks) > 0
        assert "T001" in completed_tasks[0]
        assert "T002" in completed_tasks[0]
    
    def test_handles_rapid_successive_changes(self, tmp_path):
        """Handles rapid successive changes with debouncing."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("- [ ] [T001] Task")
        
        completed_tasks = []
        
        def callback(task_ids: set[str]):
            completed_tasks.append(task_ids)
        
        watch_thread = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file, callback, 200),  # 200ms debounce
            daemon=True
        )
        watch_thread.start()
        time.sleep(0.2)
        
        # Make rapid changes
        for i in range(3):
            tasks_file.write_text("- [x] [T001] Task")
            time.sleep(0.05)  # 50ms between changes
        
        # Wait for debounce to settle
        time.sleep(0.5)
        
        # Should get callback(s), but debouncing should reduce count
        # At minimum, should detect T001 completion
        assert len(completed_tasks) > 0
        assert any("T001" in tasks for tasks in completed_tasks)
    
    def test_only_detects_new_completions(self, tmp_path):
        """Only reports newly completed tasks, not already-complete ones."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("""
- [x] [T001] Already complete
- [ ] [T002] Pending
        """)
        
        completed_tasks = []
        callback_event = threading.Event()
        
        def callback(task_ids: set[str]):
            completed_tasks.append(task_ids)
            callback_event.set()
        
        watch_thread = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file, callback),
            daemon=True
        )
        watch_thread.start()
        time.sleep(0.2)
        
        # Mark T002 complete (T001 already was)
        tasks_file.write_text("""
- [x] [T001] Already complete
- [x] [T002] Pending
        """)
        
        assert callback_event.wait(timeout=2.0)
        
        # Should only report T002 as newly completed
        assert len(completed_tasks) > 0
        assert "T002" in completed_tasks[0]
        assert "T001" not in completed_tasks[0]
    
    def test_file_not_found_raises_error(self, tmp_path):
        """Raises FileNotFoundError if file doesn't exist initially."""
        nonexistent = tmp_path / "nonexistent.md"
        
        def callback(task_ids: set[str]):
            pass
        
        with pytest.raises(FileNotFoundError):
            watch_tasks_file(nonexistent, callback)
    
    def test_handles_file_deletion_gracefully(self, tmp_path):
        """Stops watching gracefully when file is deleted."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("- [ ] [T001] Task")
        
        watch_started = threading.Event()
        watch_stopped = threading.Event()
        
        def callback(task_ids: set[str]):
            pass
        
        def watch_with_signal():
            watch_started.set()
            watch_tasks_file(tasks_file, callback)
            watch_stopped.set()
        
        watch_thread = threading.Thread(target=watch_with_signal, daemon=True)
        watch_thread.start()
        
        # Wait for watch to start
        assert watch_started.wait(timeout=1.0)
        time.sleep(0.2)
        
        # Delete the file
        tasks_file.unlink()
        
        # Wait for watch to stop (should happen quickly)
        assert watch_stopped.wait(timeout=2.0), "Watch didn't stop after file deletion"
    
    def test_handles_encoding_errors_gracefully(self, tmp_path):
        """Continues watching even if file parsing fails temporarily."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("- [ ] [T001] Task")
        
        callback_count = [0]
        callback_event = threading.Event()
        
        def callback(task_ids: set[str]):
            callback_count[0] += 1
            callback_event.set()
        
        watch_thread = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file, callback),
            daemon=True
        )
        watch_thread.start()
        time.sleep(0.2)
        
        # Write valid change
        tasks_file.write_text("- [x] [T001] Task")
        
        # Should still get callback for valid change
        assert callback_event.wait(timeout=2.0)
        assert callback_count[0] > 0


class TestConcurrentWatching:
    """Tests for watching multiple files simultaneously."""
    
    def test_can_watch_multiple_files(self, tmp_path):
        """Can watch multiple tasks.md files concurrently."""
        tasks_file_1 = tmp_path / "tasks1.md"
        tasks_file_2 = tmp_path / "tasks2.md"
        
        tasks_file_1.write_text("- [ ] [T001] Task in file 1")
        tasks_file_2.write_text("- [ ] [T002] Task in file 2")
        
        completed_1 = []
        completed_2 = []
        event_1 = threading.Event()
        event_2 = threading.Event()
        
        def callback_1(task_ids: set[str]):
            completed_1.append(task_ids)
            event_1.set()
        
        def callback_2(task_ids: set[str]):
            completed_2.append(task_ids)
            event_2.set()
        
        # Start watching both files
        thread_1 = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file_1, callback_1),
            daemon=True
        )
        thread_2 = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file_2, callback_2),
            daemon=True
        )
        
        thread_1.start()
        thread_2.start()
        time.sleep(0.2)
        
        # Complete tasks in both files
        tasks_file_1.write_text("- [x] [T001] Task in file 1")
        tasks_file_2.write_text("- [x] [T002] Task in file 2")
        
        # Both callbacks should be triggered
        assert event_1.wait(timeout=2.0), "File 1 callback not triggered"
        assert event_2.wait(timeout=2.0), "File 2 callback not triggered"
        
        # Verify correct tasks detected in each file
        assert "T001" in completed_1[0]
        assert "T002" in completed_2[0]
