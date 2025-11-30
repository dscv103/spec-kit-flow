"""
Unit tests for T027: Unified completion checking.

Tests verify get_completed_tasks() and wait_for_completion() methods
that combine manual completions (done files) with watched completions
(tasks.md checkboxes).
"""

import time
import threading
from pathlib import Path
import pytest

from speckit_flow.orchestration.completion import CompletionMonitor


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository directory."""
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()
    return repo_dir


@pytest.fixture
def tasks_file(temp_repo):
    """Create a tasks.md file in the repository."""
    specs_dir = temp_repo / "specs" / "test-feature"
    specs_dir.mkdir(parents=True)
    tasks_path = specs_dir / "tasks.md"
    tasks_path.write_text("""
# Tasks

## Phase 1
- [ ] [T001] Task 1
- [ ] [T002] Task 2
- [ ] [T003] Task 3
- [ ] [T004] Task 4
    """)
    return tasks_path


class TestGetCompletedTasks:
    """Tests for get_completed_tasks() method."""
    
    def test_returns_manual_completions_only_when_no_tasks_file(self, temp_repo):
        """Returns only manual completions when tasks_file is None."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark some tasks manually
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        
        # Call without tasks_file
        completed = monitor.get_completed_tasks()
        
        assert completed == {"T001", "T002"}
    
    def test_returns_union_of_manual_and_watched(self, temp_repo, tasks_file):
        """Returns union of manual completions and tasks.md checkboxes."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark T001 manually
        monitor.mark_complete("T001")
        
        # Mark T002 in tasks.md
        tasks_file.write_text("""
# Tasks
- [ ] [T001] Task 1
- [x] [T002] Task 2 - completed in file
- [ ] [T003] Task 3
        """)
        
        completed = monitor.get_completed_tasks(tasks_file)
        
        # Should contain both T001 (manual) and T002 (watched)
        assert completed == {"T001", "T002"}
    
    def test_returns_empty_set_when_nothing_complete(self, temp_repo, tasks_file):
        """Returns empty set when no tasks are complete."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        completed = monitor.get_completed_tasks(tasks_file)
        
        assert completed == set()
    
    def test_handles_overlapping_completions(self, temp_repo, tasks_file):
        """Handles task completed in both manual and watched."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark T001 manually
        monitor.mark_complete("T001")
        
        # Also mark T001 in tasks.md
        tasks_file.write_text("""
# Tasks
- [x] [T001] Task 1 - completed in both places
- [ ] [T002] Task 2
        """)
        
        completed = monitor.get_completed_tasks(tasks_file)
        
        # Should contain T001 only once (set semantics)
        assert completed == {"T001"}
    
    def test_handles_nonexistent_tasks_file(self, temp_repo):
        """Handles gracefully when tasks_file doesn't exist."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        monitor.mark_complete("T001")
        
        # Pass path to nonexistent file
        nonexistent = temp_repo / "nonexistent.md"
        completed = monitor.get_completed_tasks(nonexistent)
        
        # Should return only manual completions
        assert completed == {"T001"}
    
    def test_handles_corrupted_tasks_file(self, temp_repo, tasks_file):
        """Handles corrupted tasks.md gracefully."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        monitor.mark_complete("T001")
        
        # Write invalid binary content
        tasks_file.write_bytes(b"\xFF\xFE\x00\x00Invalid binary data")
        
        completed = monitor.get_completed_tasks(tasks_file)
        
        # Should fall back to manual completions only
        assert completed == {"T001"}
    
    def test_handles_multiple_tasks_from_both_sources(self, temp_repo, tasks_file):
        """Handles multiple tasks from both sources."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Manual completions
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        monitor.mark_complete("T005")
        
        # Watched completions
        tasks_file.write_text("""
# Tasks
- [x] [T002] Task 2 - in both
- [x] [T003] Task 3 - watched only
- [ ] [T004] Task 4
- [x] [T005] Task 5 - in both
- [x] [T006] Task 6 - watched only
        """)
        
        completed = monitor.get_completed_tasks(tasks_file)
        
        # Union: T001, T002, T003, T005, T006
        assert completed == {"T001", "T002", "T003", "T005", "T006"}
    
    def test_updates_with_new_completions(self, temp_repo, tasks_file):
        """get_completed_tasks reflects current state on each call."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Initially only T001
        monitor.mark_complete("T001")
        completed = monitor.get_completed_tasks(tasks_file)
        assert completed == {"T001"}
        
        # Add T002
        monitor.mark_complete("T002")
        completed = monitor.get_completed_tasks(tasks_file)
        assert completed == {"T001", "T002"}
        
        # Add T003 to tasks.md
        tasks_file.write_text("""
- [x] [T003] Task 3
        """)
        completed = monitor.get_completed_tasks(tasks_file)
        assert completed == {"T001", "T002", "T003"}


class TestWaitForCompletion:
    """Tests for wait_for_completion() method."""
    
    def test_returns_immediately_when_tasks_already_complete(self, temp_repo):
        """Returns immediately if all tasks are already complete."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        
        start = time.time()
        completed = monitor.wait_for_completion({"T001", "T002"})
        elapsed = time.time() - start
        
        assert completed == {"T001", "T002"}
        assert elapsed < 0.1  # Should be nearly instant
    
    def test_returns_empty_set_for_empty_task_ids(self, temp_repo):
        """Returns empty set immediately when no tasks to wait for."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        completed = monitor.wait_for_completion(set())
        
        assert completed == set()
    
    def test_waits_until_tasks_complete(self, temp_repo):
        """Blocks until all tasks are marked complete."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark T001 initially
        monitor.mark_complete("T001")
        
        # Start thread that will mark T002 after delay
        def mark_after_delay():
            time.sleep(0.2)
            monitor.mark_complete("T002")
        
        thread = threading.Thread(target=mark_after_delay)
        thread.start()
        
        start = time.time()
        completed = monitor.wait_for_completion({"T001", "T002"}, poll_interval=0.05)
        elapsed = time.time() - start
        
        thread.join()
        
        assert completed == {"T001", "T002"}
        assert 0.15 < elapsed < 0.5  # Should wait ~0.2 seconds
    
    def test_raises_timeout_error_when_timeout_exceeded(self, temp_repo):
        """Raises TimeoutError when timeout is reached."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Only mark T001, leaving T002 incomplete
        monitor.mark_complete("T001")
        
        start = time.time()
        with pytest.raises(TimeoutError) as exc_info:
            monitor.wait_for_completion(
                {"T001", "T002"},
                timeout=0.3,
                poll_interval=0.05
            )
        elapsed = time.time() - start
        
        # Check error message contains useful info
        error_msg = str(exc_info.value)
        assert "T002" in error_msg  # Pending task
        assert "T001" in error_msg  # Completed task
        
        # Should wait approximately the timeout duration
        assert 0.25 < elapsed < 0.5
    
    def test_timeout_error_includes_partial_completion(self, temp_repo):
        """TimeoutError message shows which tasks completed and which didn't."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark some tasks but not all
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        
        with pytest.raises(TimeoutError) as exc_info:
            monitor.wait_for_completion(
                {"T001", "T002", "T003", "T004"},
                timeout=0.2
            )
        
        error_msg = str(exc_info.value)
        # Should mention pending tasks
        assert "T003" in error_msg
        assert "T004" in error_msg
        # Should mention completed tasks
        assert "T001" in error_msg or "T002" in error_msg
    
    def test_waits_for_tasks_file_completions(self, temp_repo, tasks_file):
        """Waits for tasks marked complete in tasks.md."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Start thread that will update tasks.md after delay
        def update_after_delay():
            time.sleep(0.2)
            tasks_file.write_text("""
- [x] [T001] Task 1 - completed
            """)
        
        thread = threading.Thread(target=update_after_delay)
        thread.start()
        
        start = time.time()
        completed = monitor.wait_for_completion(
            {"T001"},
            tasks_file=tasks_file,
            poll_interval=0.05
        )
        elapsed = time.time() - start
        
        thread.join()
        
        assert completed == {"T001"}
        assert 0.15 < elapsed < 0.5
    
    def test_waits_for_mixed_completion_sources(self, temp_repo, tasks_file):
        """Waits for tasks from both manual and watched sources."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Start thread that marks tasks from different sources
        def complete_tasks():
            time.sleep(0.1)
            monitor.mark_complete("T001")  # Manual
            time.sleep(0.1)
            tasks_file.write_text("- [x] [T002] Task 2")  # Watched
        
        thread = threading.Thread(target=complete_tasks)
        thread.start()
        
        completed = monitor.wait_for_completion(
            {"T001", "T002"},
            tasks_file=tasks_file,
            poll_interval=0.05
        )
        
        thread.join()
        
        assert completed == {"T001", "T002"}
    
    def test_handles_partial_completion_before_timeout(self, temp_repo):
        """Handles scenario where some but not all tasks complete before timeout."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Complete T001 and T002, but leave T003 and T004 incomplete
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        
        with pytest.raises(TimeoutError):
            monitor.wait_for_completion(
                {"T001", "T002", "T003", "T004"},
                timeout=0.2
            )
        
        # Verify completed tasks are correct
        completed = monitor.get_completed_tasks()
        assert completed == {"T001", "T002"}
    
    def test_poll_interval_affects_check_frequency(self, temp_repo):
        """Poll interval controls how often completion is checked."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        check_count = [0]
        original_get = monitor.get_completed_tasks
        
        def counting_get(*args, **kwargs):
            check_count[0] += 1
            return original_get(*args, **kwargs)
        
        monitor.get_completed_tasks = counting_get
        
        # Mark task after delay
        def mark_after_delay():
            time.sleep(0.25)
            monitor.mark_complete("T001")
        
        thread = threading.Thread(target=mark_after_delay)
        thread.start()
        
        # Use 0.1 second poll interval
        monitor.wait_for_completion({"T001"}, poll_interval=0.1)
        
        thread.join()
        
        # Should check approximately 2-4 times (0.25s / 0.1s)
        assert 2 <= check_count[0] <= 5
    
    def test_no_timeout_waits_indefinitely(self, temp_repo):
        """When timeout is None, waits indefinitely until completion."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark task after short delay
        def mark_after_delay():
            time.sleep(0.3)
            monitor.mark_complete("T001")
        
        thread = threading.Thread(target=mark_after_delay)
        thread.start()
        
        # No timeout - should wait until task is complete
        start = time.time()
        completed = monitor.wait_for_completion(
            {"T001"},
            timeout=None,
            poll_interval=0.05
        )
        elapsed = time.time() - start
        
        thread.join()
        
        assert completed == {"T001"}
        assert elapsed >= 0.25  # Should have waited


class TestUnifiedCompletionEdgeCases:
    """Edge case tests for unified completion checking."""
    
    def test_concurrent_completions_from_multiple_sources(self, temp_repo, tasks_file):
        """Handles concurrent updates from manual and watched sources."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        def mark_manual():
            for i in range(5):
                monitor.mark_complete(f"T{i:03d}")
                time.sleep(0.02)
        
        def update_file():
            for i in range(5, 10):
                tasks_file.write_text(f"- [x] [T{i:03d}] Task {i}")
                time.sleep(0.02)
        
        thread1 = threading.Thread(target=mark_manual)
        thread2 = threading.Thread(target=update_file)
        
        thread1.start()
        thread2.start()
        
        # Wait for all tasks
        completed = monitor.wait_for_completion(
            {f"T{i:03d}" for i in range(10)},
            tasks_file=tasks_file,
            timeout=2.0,
            poll_interval=0.05
        )
        
        thread1.join()
        thread2.join()
        
        assert len(completed) == 10
    
    def test_wait_for_completion_with_immediate_timeout(self, temp_repo):
        """Handles zero or very small timeout."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Tasks not complete, timeout immediately
        with pytest.raises(TimeoutError):
            monitor.wait_for_completion(
                {"T001"},
                timeout=0.0
            )
    
    def test_very_large_task_set(self, temp_repo):
        """Handles waiting for large number of tasks."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark 100 tasks
        large_task_set = {f"T{i:03d}" for i in range(100)}
        for task_id in large_task_set:
            monitor.mark_complete(task_id)
        
        # Should complete immediately
        start = time.time()
        completed = monitor.wait_for_completion(large_task_set)
        elapsed = time.time() - start
        
        assert completed == large_task_set
        assert elapsed < 0.5  # Should be fast
    
    def test_get_completed_with_deleted_and_recreated_file(self, temp_repo, tasks_file):
        """Handles tasks.md being deleted and recreated."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Initial state
        tasks_file.write_text("- [x] [T001] Task 1")
        completed = monitor.get_completed_tasks(tasks_file)
        assert "T001" in completed
        
        # Delete file
        tasks_file.unlink()
        completed = monitor.get_completed_tasks(tasks_file)
        assert "T001" not in completed  # File doesn't exist
        
        # Recreate with different content
        tasks_file.write_text("- [x] [T002] Task 2")
        completed = monitor.get_completed_tasks(tasks_file)
        assert "T002" in completed
        assert "T001" not in completed


class TestUnifiedCompletionIntegration:
    """Integration tests for unified completion checking workflow."""
    
    def test_typical_orchestration_workflow(self, temp_repo, tasks_file):
        """Test typical workflow during orchestration."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Phase 1: Wait for T001 (completed manually via CLI)
        def complete_t001():
            time.sleep(0.1)
            monitor.mark_complete("T001")
        
        thread = threading.Thread(target=complete_t001)
        thread.start()
        
        completed = monitor.wait_for_completion(
            {"T001"},
            tasks_file=tasks_file,
            timeout=1.0
        )
        thread.join()
        assert "T001" in completed
        
        # Phase 2: Wait for T002 and T003 (completed in tasks.md by agent)
        def complete_in_file():
            time.sleep(0.1)
            tasks_file.write_text("""
- [x] [T001] Task 1
- [x] [T002] Task 2
- [x] [T003] Task 3
            """)
        
        thread = threading.Thread(target=complete_in_file)
        thread.start()
        
        completed = monitor.wait_for_completion(
            {"T002", "T003"},
            tasks_file=tasks_file,
            timeout=1.0
        )
        thread.join()
        assert completed == {"T002", "T003"}
        
        # Verify all tasks show as complete
        all_completed = monitor.get_completed_tasks(tasks_file)
        assert all_completed == {"T001", "T002", "T003"}
    
    def test_recovery_from_interrupted_orchestration(self, temp_repo, tasks_file):
        """Test resuming after orchestration interruption."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Simulate previous run that completed some tasks
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        tasks_file.write_text("""
- [x] [T001] Task 1
- [x] [T002] Task 2
- [ ] [T003] Task 3
- [ ] [T004] Task 4
        """)
        
        # Check what's already complete before resuming
        completed = monitor.get_completed_tasks(tasks_file)
        assert completed == {"T001", "T002"}
        
        # Only wait for incomplete tasks
        remaining = {"T003", "T004"} - completed
        assert remaining == {"T003", "T004"}
        
        # Complete remaining tasks
        monitor.mark_complete("T003")
        monitor.mark_complete("T004")
        
        # Verify all complete
        all_completed = monitor.get_completed_tasks(tasks_file)
        assert all_completed == {"T001", "T002", "T003", "T004"}
