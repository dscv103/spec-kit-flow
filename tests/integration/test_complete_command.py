"""
Integration tests for skf complete command.

Tests the complete command's behavior including task ID validation,
duplicate completion warnings, and DAG validation.
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from speckit_flow import app
from speckit_flow.orchestration.completion import CompletionMonitor

runner = CliRunner()


class TestCompleteCommand:
    """Integration tests for skf complete command."""
    
    def test_complete_valid_task(self, temp_repo_with_spec):
        """Complete command creates completion marker for valid task."""
        # Arrange: Create DAG with task T001
        dag_content = """
version: "1.0"
spec_id: "001-test-feature"
generated_at: "2025-11-29T10:00:00Z"
num_sessions: 2

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Setup project"
        description: "Initialize project structure"
        files: []
        dependencies: []
        session: 0
        parallelizable: false
        story: null
"""
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        dag_path.write_text(dag_content)
        
        # Act: Mark task as complete
        result = runner.invoke(app, ["complete", "T001"], catch_exceptions=False)
        
        # Assert: Command succeeds
        assert result.exit_code == 0
        assert "✓" in result.stdout
        assert "T001 marked as complete" in result.stdout
        
        # Verify completion marker created
        monitor = CompletionMonitor("001-test-feature", temp_repo_with_spec)
        assert monitor.is_complete("T001")
        done_file = temp_repo_with_spec / ".speckit" / "completions" / "T001.done"
        assert done_file.exists()
    
    def test_complete_invalid_task_format(self, temp_repo_with_spec):
        """Complete command rejects invalid task ID format."""
        # Arrange: Various invalid formats
        invalid_ids = ["T1", "T0001", "task001", "001", "T"]
        
        for invalid_id in invalid_ids:
            # Act: Try to mark invalid task
            result = runner.invoke(app, ["complete", invalid_id])
            
            # Assert: Command fails with error
            assert result.exit_code == 1
            assert "Invalid task ID format" in result.stdout
            assert "T###" in result.stdout
    
    def test_complete_task_not_in_dag(self, temp_repo_with_spec):
        """Complete command errors for task ID not in DAG."""
        # Arrange: Create DAG with only T001
        dag_content = """
version: "1.0"
spec_id: "001-test-feature"
generated_at: "2025-11-29T10:00:00Z"
num_sessions: 2

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Setup project"
        description: "Initialize project structure"
        files: []
        dependencies: []
        session: 0
        parallelizable: false
        story: null
"""
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        dag_path.write_text(dag_content)
        
        # Act: Try to mark T999 as complete (not in DAG)
        result = runner.invoke(app, ["complete", "T999"])
        
        # Assert: Command fails with error
        assert result.exit_code == 1
        assert "not found in DAG" in result.stdout
        assert "Valid task IDs" in result.stdout
    
    def test_complete_already_complete(self, temp_repo_with_spec):
        """Complete command warns if task already complete."""
        # Arrange: Create DAG and mark T001 complete
        dag_content = """
version: "1.0"
spec_id: "001-test-feature"
generated_at: "2025-11-29T10:00:00Z"
num_sessions: 2

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Setup project"
        description: "Initialize project structure"
        files: []
        dependencies: []
        session: 0
        parallelizable: false
        story: null
"""
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        dag_path.write_text(dag_content)
        
        monitor = CompletionMonitor("001-test-feature", temp_repo_with_spec)
        monitor.mark_complete("T001")
        
        # Act: Try to mark T001 complete again
        result = runner.invoke(app, ["complete", "T001"])
        
        # Assert: Command exits cleanly with warning
        assert result.exit_code == 0
        assert "Warning" in result.stdout
        assert "already marked complete" in result.stdout
    
    def test_complete_without_dag(self, temp_repo_with_spec):
        """Complete command works without DAG (with notice)."""
        # Arrange: No DAG file exists
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        if dag_path.exists():
            dag_path.unlink()
        
        # Act: Mark task complete without DAG
        result = runner.invoke(app, ["complete", "T001"], catch_exceptions=False)
        
        # Assert: Command succeeds with notice
        assert result.exit_code == 0
        assert "Notice" in result.stdout
        assert "No DAG found" in result.stdout
        assert "✓" in result.stdout
        assert "T001 marked as complete" in result.stdout
        
        # Verify completion marker created
        monitor = CompletionMonitor("001-test-feature", temp_repo_with_spec)
        assert monitor.is_complete("T001")
    
    def test_complete_case_insensitive(self, temp_repo_with_spec):
        """Complete command normalizes task ID to uppercase."""
        # Arrange: Create DAG with T001
        dag_content = """
version: "1.0"
spec_id: "001-test-feature"
generated_at: "2025-11-29T10:00:00Z"
num_sessions: 2

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Setup project"
        description: "Initialize project structure"
        files: []
        dependencies: []
        session: 0
        parallelizable: false
        story: null
"""
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        dag_path.write_text(dag_content)
        
        # Act: Mark task with lowercase
        result = runner.invoke(app, ["complete", "t001"], catch_exceptions=False)
        
        # Assert: Command succeeds (normalized to T001)
        assert result.exit_code == 0
        assert "T001 marked as complete" in result.stdout
        
        # Verify uppercase completion marker
        monitor = CompletionMonitor("001-test-feature", temp_repo_with_spec)
        assert monitor.is_complete("T001")
    
    def test_complete_creates_completions_directory(self, temp_repo_with_spec):
        """Complete command creates completions directory if missing."""
        # Arrange: Ensure completions directory doesn't exist
        completions_dir = temp_repo_with_spec / ".speckit" / "completions"
        if completions_dir.exists():
            for file in completions_dir.glob("*"):
                file.unlink()
            completions_dir.rmdir()
        
        # Create DAG
        dag_content = """
version: "1.0"
spec_id: "001-test-feature"
generated_at: "2025-11-29T10:00:00Z"
num_sessions: 2

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Setup project"
        description: "Initialize project structure"
        files: []
        dependencies: []
        session: 0
        parallelizable: false
        story: null
"""
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        dag_path.write_text(dag_content)
        
        # Act: Mark task complete
        result = runner.invoke(app, ["complete", "T001"], catch_exceptions=False)
        
        # Assert: Command succeeds and directory created
        assert result.exit_code == 0
        assert completions_dir.exists()
        assert completions_dir.is_dir()
        assert (completions_dir / "T001.done").exists()
    
    def test_complete_multiple_tasks_sequential(self, temp_repo_with_spec):
        """Complete command can mark multiple tasks sequentially."""
        # Arrange: Create DAG with multiple tasks
        dag_content = """
version: "1.0"
spec_id: "001-test-feature"
generated_at: "2025-11-29T10:00:00Z"
num_sessions: 2

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Task 1"
        description: "First task"
        files: []
        dependencies: []
        session: 0
        parallelizable: true
        story: null
      - id: "T002"
        name: "Task 2"
        description: "Second task"
        files: []
        dependencies: []
        session: 1
        parallelizable: true
        story: null
      - id: "T003"
        name: "Task 3"
        description: "Third task"
        files: []
        dependencies: ["T001", "T002"]
        session: 0
        parallelizable: false
        story: null
"""
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        dag_path.write_text(dag_content)
        
        # Act: Mark all three tasks complete
        result1 = runner.invoke(app, ["complete", "T001"], catch_exceptions=False)
        result2 = runner.invoke(app, ["complete", "T002"], catch_exceptions=False)
        result3 = runner.invoke(app, ["complete", "T003"], catch_exceptions=False)
        
        # Assert: All commands succeed
        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert result3.exit_code == 0
        
        # Verify all completion markers created
        monitor = CompletionMonitor("001-test-feature", temp_repo_with_spec)
        assert monitor.is_complete("T001")
        assert monitor.is_complete("T002")
        assert monitor.is_complete("T003")
        
        # Verify all are in manual completions set
        completions = monitor.get_manual_completions()
        assert completions == {"T001", "T002", "T003"}
    
    def test_complete_not_in_git_repo(self, temp_dir):
        """Complete command errors when not in git repository."""
        # Arrange: Non-git directory (temp_dir is not a repo)
        
        # Act: Try to mark task complete
        result = runner.invoke(app, ["complete", "T001"], cwd=str(temp_dir))
        
        # Assert: Command fails with appropriate error
        assert result.exit_code == 1
        assert "Not in a git repository" in result.stdout


class TestCompleteIntegrationWithMonitoring:
    """Test complete command integration with completion monitoring."""
    
    def test_complete_detected_by_monitor(self, temp_repo_with_spec):
        """Completion marker is detected by CompletionMonitor."""
        # Arrange: Create DAG and monitor
        dag_content = """
version: "1.0"
spec_id: "001-test-feature"
generated_at: "2025-11-29T10:00:00Z"
num_sessions: 2

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Setup project"
        description: "Initialize project structure"
        files: []
        dependencies: []
        session: 0
        parallelizable: false
        story: null
"""
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        dag_path.write_text(dag_content)
        
        monitor = CompletionMonitor("001-test-feature", temp_repo_with_spec)
        
        # Verify not complete initially
        assert not monitor.is_complete("T001")
        
        # Act: Mark complete via CLI
        result = runner.invoke(app, ["complete", "T001"], catch_exceptions=False)
        assert result.exit_code == 0
        
        # Assert: Monitor detects completion
        assert monitor.is_complete("T001")
        assert "T001" in monitor.get_manual_completions()
        assert "T001" in monitor.get_completed_tasks()
    
    def test_complete_works_with_wait_for_completion(self, temp_repo_with_spec):
        """Complete command integrates with wait_for_completion."""
        # Arrange: Create DAG
        dag_content = """
version: "1.0"
spec_id: "001-test-feature"
generated_at: "2025-11-29T10:00:00Z"
num_sessions: 2

phases:
  - name: "phase-0"
    tasks:
      - id: "T001"
        name: "Setup project"
        description: "Initialize project structure"
        files: []
        dependencies: []
        session: 0
        parallelizable: false
        story: null
"""
        spec_dir = temp_repo_with_spec / "specs" / "001-test-feature"
        dag_path = spec_dir / "dag.yaml"
        dag_path.write_text(dag_content)
        
        monitor = CompletionMonitor("001-test-feature", temp_repo_with_spec)
        
        # Mark task complete
        runner.invoke(app, ["complete", "T001"], catch_exceptions=False)
        
        # Act: Wait for completion with short timeout
        completed = monitor.wait_for_completion(
            {"T001"},
            timeout=0.5,
            poll_interval=0.1
        )
        
        # Assert: Task detected as complete immediately
        assert completed == {"T001"}
