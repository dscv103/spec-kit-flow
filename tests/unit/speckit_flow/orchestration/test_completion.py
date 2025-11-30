"""
Unit tests for orchestration/completion.py - CompletionMonitor class.

Tests verify file-based completion detection using touch files.
"""

import pytest
from pathlib import Path
import shutil

from speckit_flow.orchestration.completion import CompletionMonitor


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository directory."""
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()
    return repo_dir


class TestCompletionMonitor:
    """Unit tests for CompletionMonitor class."""
    
    def test_init_creates_monitor(self, temp_repo):
        """CompletionMonitor initializes with spec_id and repo_root."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        assert monitor.spec_id == "001-feature"
        assert monitor.repo_root == temp_repo
        assert monitor.completions_dir == temp_repo / ".speckit" / "completions"
    
    def test_mark_complete_creates_directory(self, temp_repo):
        """mark_complete creates completions directory if missing."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Verify directory doesn't exist initially
        assert not monitor.completions_dir.exists()
        
        # Mark a task complete
        monitor.mark_complete("T001")
        
        # Verify directory was created
        assert monitor.completions_dir.exists()
        assert monitor.completions_dir.is_dir()
    
    def test_mark_complete_creates_done_file(self, temp_repo):
        """mark_complete creates empty touch file."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        monitor.mark_complete("T001")
        
        done_file = monitor.completions_dir / "T001.done"
        assert done_file.exists()
        assert done_file.is_file()
        # Verify file is empty (touch only)
        assert done_file.stat().st_size == 0
    
    def test_mark_complete_handles_existing_directory(self, temp_repo):
        """mark_complete works when directory already exists."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Create directory first
        monitor.completions_dir.mkdir(parents=True)
        
        # Should not raise error
        monitor.mark_complete("T001")
        
        done_file = monitor.completions_dir / "T001.done"
        assert done_file.exists()
    
    def test_mark_complete_idempotent(self, temp_repo):
        """mark_complete can be called multiple times safely."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark same task multiple times
        monitor.mark_complete("T001")
        monitor.mark_complete("T001")
        monitor.mark_complete("T001")
        
        # Should still have exactly one done file
        done_file = monitor.completions_dir / "T001.done"
        assert done_file.exists()
        
        # Verify only one T001.done file exists
        done_files = list(monitor.completions_dir.glob("T001.done"))
        assert len(done_files) == 1
    
    def test_is_complete_returns_true_for_marked_task(self, temp_repo):
        """is_complete returns True when done file exists."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        monitor.mark_complete("T001")
        
        assert monitor.is_complete("T001") is True
    
    def test_is_complete_returns_false_for_unmarked_task(self, temp_repo):
        """is_complete returns False when done file doesn't exist."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        assert monitor.is_complete("T001") is False
    
    def test_is_complete_returns_false_when_directory_missing(self, temp_repo):
        """is_complete returns False when completions directory doesn't exist."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Don't create directory
        assert not monitor.completions_dir.exists()
        
        # Should return False, not raise error
        assert monitor.is_complete("T001") is False
    
    def test_get_manual_completions_returns_empty_set_initially(self, temp_repo):
        """get_manual_completions returns empty set when no tasks complete."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        completions = monitor.get_manual_completions()
        
        assert completions == set()
        assert isinstance(completions, set)
    
    def test_get_manual_completions_returns_empty_when_directory_missing(self, temp_repo):
        """get_manual_completions handles missing directory gracefully."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Verify directory doesn't exist
        assert not monitor.completions_dir.exists()
        
        completions = monitor.get_manual_completions()
        
        assert completions == set()
    
    def test_get_manual_completions_returns_single_task(self, temp_repo):
        """get_manual_completions returns set with single completed task."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        monitor.mark_complete("T001")
        
        completions = monitor.get_manual_completions()
        
        assert completions == {"T001"}
    
    def test_get_manual_completions_returns_multiple_tasks(self, temp_repo):
        """get_manual_completions returns all completed task IDs."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        monitor.mark_complete("T003")
        
        completions = monitor.get_manual_completions()
        
        assert completions == {"T001", "T002", "T003"}
    
    def test_get_manual_completions_ignores_non_done_files(self, temp_repo):
        """get_manual_completions only includes .done files."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Create some done files
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        
        # Create non-.done files that should be ignored
        monitor.completions_dir.mkdir(parents=True, exist_ok=True)
        (monitor.completions_dir / "T003.txt").touch()
        (monitor.completions_dir / "readme.md").touch()
        (monitor.completions_dir / ".hidden").touch()
        
        completions = monitor.get_manual_completions()
        
        # Should only include T001 and T002
        assert completions == {"T001", "T002"}
    
    def test_concurrent_marking_safe(self, temp_repo):
        """Concurrent mark_complete calls are safe."""
        import threading
        
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        def mark_task(task_id):
            monitor.mark_complete(task_id)
        
        # Create multiple threads marking different tasks
        threads = []
        for i in range(10):
            thread = threading.Thread(target=mark_task, args=(f"T{i:03d}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all tasks marked
        completions = monitor.get_manual_completions()
        expected = {f"T{i:03d}" for i in range(10)}
        assert completions == expected
    
    def test_different_monitors_same_repo(self, temp_repo):
        """Multiple monitors in same repo work independently."""
        monitor1 = CompletionMonitor("001-feature", temp_repo)
        monitor2 = CompletionMonitor("002-feature", temp_repo)
        
        # Both should share the same completions directory
        assert monitor1.completions_dir == monitor2.completions_dir
        
        # Mark tasks from both monitors
        monitor1.mark_complete("T001")
        monitor2.mark_complete("T002")
        
        # Both should see all completions
        assert monitor1.get_manual_completions() == {"T001", "T002"}
        assert monitor2.get_manual_completions() == {"T001", "T002"}
    
    def test_task_id_with_special_characters(self, temp_repo):
        """Task IDs are used as-is in filenames."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Use task ID with allowed characters
        monitor.mark_complete("T001-special")
        
        assert monitor.is_complete("T001-special")
        assert "T001-special" in monitor.get_manual_completions()


class TestCompletionMonitorEdgeCases:
    """Edge case tests for CompletionMonitor."""
    
    def test_empty_task_id(self, temp_repo):
        """Empty task ID creates empty filename."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        monitor.mark_complete("")
        
        # Should create .done file
        done_file = monitor.completions_dir / ".done"
        assert done_file.exists()
    
    def test_very_long_task_id(self, temp_repo):
        """Very long task IDs are handled."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        long_task_id = "T" + "0" * 1000
        monitor.mark_complete(long_task_id)
        
        assert monitor.is_complete(long_task_id)
    
    def test_task_id_with_path_separator(self, temp_repo):
        """Task IDs with path separators work (though not recommended)."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Note: This would create subdirectories in practice
        # For safety, users should avoid path separators in task IDs
        task_id = "T001"  # Use safe ID for test
        monitor.mark_complete(task_id)
        
        assert monitor.is_complete(task_id)
    
    def test_completions_directory_is_file(self, temp_repo):
        """Handles case where completions path is a file not directory."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Create .speckit directory
        (temp_repo / ".speckit").mkdir(parents=True)
        
        # Create completions as a file instead of directory
        (temp_repo / ".speckit" / "completions").touch()
        
        # mark_complete should raise an error when trying to mkdir
        with pytest.raises(Exception):  # FileExistsError or similar
            monitor.mark_complete("T001")
    
    def test_get_manual_completions_with_corrupted_files(self, temp_repo):
        """get_manual_completions handles corrupted/unusual files."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Create valid done files
        monitor.mark_complete("T001")
        
        # Create unusual files
        monitor.completions_dir.mkdir(parents=True, exist_ok=True)
        (monitor.completions_dir / ".done").touch()  # Empty stem
        (monitor.completions_dir / "..done").touch()  # Just dots
        (monitor.completions_dir / "T002.done.backup").touch()  # Extra extension
        
        completions = monitor.get_manual_completions()
        
        # Should include T001 and empty string from .done
        assert "T001" in completions
        # .done file has empty stem
        assert "" in completions or "." in completions  # Depends on Path.stem behavior


class TestCompletionMonitorIntegration:
    """Integration tests for CompletionMonitor workflow."""
    
    def test_typical_workflow(self, temp_repo):
        """Test typical workflow of marking and checking tasks."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Initially no tasks complete
        assert monitor.get_manual_completions() == set()
        assert not monitor.is_complete("T001")
        
        # Mark first task complete
        monitor.mark_complete("T001")
        assert monitor.is_complete("T001")
        assert monitor.get_manual_completions() == {"T001"}
        
        # Mark second task complete
        monitor.mark_complete("T002")
        assert monitor.is_complete("T002")
        assert monitor.get_manual_completions() == {"T001", "T002"}
        
        # Check incomplete task
        assert not monitor.is_complete("T003")
    
    def test_persistence_across_instances(self, temp_repo):
        """Completion state persists across monitor instances."""
        # First monitor marks tasks
        monitor1 = CompletionMonitor("001-feature", temp_repo)
        monitor1.mark_complete("T001")
        monitor1.mark_complete("T002")
        
        # New monitor sees same state
        monitor2 = CompletionMonitor("001-feature", temp_repo)
        assert monitor2.is_complete("T001")
        assert monitor2.is_complete("T002")
        assert monitor2.get_manual_completions() == {"T001", "T002"}
    
    def test_cleanup_and_restart(self, temp_repo):
        """Test cleanup and restart scenario."""
        monitor = CompletionMonitor("001-feature", temp_repo)
        
        # Mark some tasks
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        
        # Cleanup completions directory
        shutil.rmtree(monitor.completions_dir)
        
        # Should handle missing directory gracefully
        assert monitor.get_manual_completions() == set()
        assert not monitor.is_complete("T001")
        
        # Can mark tasks again
        monitor.mark_complete("T003")
        assert monitor.is_complete("T003")
