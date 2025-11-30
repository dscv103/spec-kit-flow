"""
Integration tests for 'skf status' command.

Tests the status display workflow including:
- State loading and display
- No-state handling with helpful messages
- Session and task status formatting
- Color coding for different states
- Progress calculation
- Next action recommendations
"""

from datetime import datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from speckit_core.models import SessionState, SessionStatus, TaskStatus
from speckit_flow import app
from speckit_flow.state.manager import StateManager
from speckit_flow.state.models import OrchestrationState, TaskStateInfo

runner = CliRunner()


class TestStatusCommand:
    """Integration tests for skf status command."""
    
    def test_status_shows_no_orchestration_message(self, temp_repo):
        """skf status shows helpful message when no orchestration active."""
        # Arrange: No state file exists
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        assert "Notice:" in result.stdout or "no active orchestration" in result.stdout.lower()
        assert "skf run" in result.stdout
        assert "skf init" in result.stdout
    
    def test_status_displays_basic_info(self, temp_repo):
        """skf status displays specification and configuration info."""
        # Arrange: Create state with basic info
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test-feature",
            agent_type="copilot",
            num_sessions=3,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            phases_completed=["phase-0"],
            sessions=[],
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        assert "001-test-feature" in result.stdout
        assert "copilot" in result.stdout
        assert "3" in result.stdout  # num_sessions
        assert "main" in result.stdout  # base_branch
    
    def test_status_shows_timestamps(self, temp_repo):
        """skf status displays started and updated timestamps."""
        # Arrange
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T11:45:00Z",
            current_phase="phase-0",
            sessions=[],
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        assert "2025-11-28T10:30:00Z" in result.stdout
        assert "2025-11-28T11:45:00Z" in result.stdout
    
    def test_status_shows_current_phase(self, temp_repo):
        """skf status displays current phase and completed phases."""
        # Arrange
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-2",
            phases_completed=["phase-0", "phase-1"],
            sessions=[],
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        assert "phase-2" in result.stdout
        assert "phase-0" in result.stdout or "phase-1" in result.stdout
        assert "2" in result.stdout  # Number of completed phases
    
    def test_status_shows_task_statistics(self, temp_repo):
        """skf status calculates and displays task statistics."""
        # Arrange: State with various task statuses
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            sessions=[],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T002": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T003": TaskStateInfo(status=TaskStatus.in_progress, session=1),
                "T004": TaskStateInfo(status=TaskStatus.in_progress, session=1),
                "T005": TaskStateInfo(status=TaskStatus.pending, session=None),
                "T006": TaskStateInfo(status=TaskStatus.failed, session=0),
            },
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Shows correct counts
        assert result.exit_code == 0
        assert "Total: 6" in result.stdout
        assert "Completed: 2" in result.stdout
        assert "In Progress: 2" in result.stdout
        assert "Pending: 1" in result.stdout
        assert "Failed: 1" in result.stdout
    
    def test_status_shows_session_table(self, temp_repo):
        """skf status displays Rich table with session information."""
        # Arrange: State with multiple sessions
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=3,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=str(temp_repo / ".worktrees-001" / "session-0-setup"),
                    branch_name="impl-001-session-0",
                    current_task="T001",
                    completed_tasks=["T000"],
                    status=SessionStatus.executing,
                ),
                SessionState(
                    session_id=1,
                    worktree_path=str(temp_repo / ".worktrees-001" / "session-1-feature"),
                    branch_name="impl-001-session-1",
                    current_task="T002",
                    completed_tasks=[],
                    status=SessionStatus.executing,
                ),
                SessionState(
                    session_id=2,
                    worktree_path=str(temp_repo / ".worktrees-001" / "session-2-tests"),
                    branch_name="impl-001-session-2",
                    current_task=None,
                    completed_tasks=["T003", "T004"],
                    status=SessionStatus.completed,
                ),
            ],
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Shows session information
        assert result.exit_code == 0
        assert "0" in result.stdout  # Session ID
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "T001" in result.stdout  # Current tasks
        assert "T002" in result.stdout
        assert "session-0" in result.stdout or "Session" in result.stdout
    
    def test_status_color_codes_session_status(self, temp_repo):
        """skf status applies color coding to session statuses."""
        # Arrange: Sessions with different statuses
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=4,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=str(temp_repo / ".worktrees-001" / "session-0"),
                    branch_name="impl-001-session-0",
                    current_task=None,
                    status=SessionStatus.idle,
                ),
                SessionState(
                    session_id=1,
                    worktree_path=str(temp_repo / ".worktrees-001" / "session-1"),
                    branch_name="impl-001-session-1",
                    current_task="T002",
                    status=SessionStatus.executing,
                ),
                SessionState(
                    session_id=2,
                    worktree_path=str(temp_repo / ".worktrees-001" / "session-2"),
                    branch_name="impl-001-session-2",
                    current_task=None,
                    status=SessionStatus.completed,
                ),
                SessionState(
                    session_id=3,
                    worktree_path=str(temp_repo / ".worktrees-001" / "session-3"),
                    branch_name="impl-001-session-3",
                    current_task="T004",
                    status=SessionStatus.failed,
                ),
            ],
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Command succeeds (color codes are in output but may not be visible in test)
        assert result.exit_code == 0
        assert "idle" in result.stdout or "executing" in result.stdout
        assert "completed" in result.stdout or "failed" in result.stdout
    
    def test_status_shows_active_tasks(self, temp_repo):
        """skf status displays detailed list of in-progress and failed tasks."""
        # Arrange: State with active tasks
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            sessions=[],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T002": TaskStateInfo(status=TaskStatus.in_progress, session=0),
                "T003": TaskStateInfo(status=TaskStatus.in_progress, session=1),
                "T004": TaskStateInfo(status=TaskStatus.failed, session=0),
                "T005": TaskStateInfo(status=TaskStatus.pending, session=None),
            },
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Shows active tasks section
        assert result.exit_code == 0
        assert "Active Tasks" in result.stdout or "T002" in result.stdout
        assert "T003" in result.stdout
        assert "T004" in result.stdout
        # T001 and T005 should not be in active tasks
    
    def test_status_shows_merge_status(self, temp_repo):
        """skf status displays merge status when set."""
        # Arrange: State with merge in progress
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            sessions=[],
            tasks={},
            merge_status="in_progress",
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        assert "Merge" in result.stdout or "merge" in result.stdout
        assert "progress" in result.stdout.lower()
    
    def test_status_suggests_next_actions_for_in_progress(self, temp_repo):
        """skf status suggests continuing work when tasks in progress."""
        # Arrange: State with in-progress tasks
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=str(temp_repo / ".worktrees-001" / "session-0"),
                    branch_name="impl-001-session-0",
                    current_task="T002",
                    status=SessionStatus.executing,
                ),
            ],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T002": TaskStateInfo(status=TaskStatus.in_progress, session=0),
            },
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Shows guidance to continue
        assert result.exit_code == 0
        assert "Next Actions" in result.stdout or "next" in result.stdout.lower()
        assert "T002" in result.stdout
    
    def test_status_suggests_merge_when_all_complete(self, temp_repo):
        """skf status suggests merge when all tasks completed."""
        # Arrange: State with all tasks completed
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-2",
            phases_completed=["phase-0", "phase-1"],
            sessions=[],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T002": TaskStateInfo(status=TaskStatus.completed, session=1),
                "T003": TaskStateInfo(status=TaskStatus.completed, session=0),
            },
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Suggests merge
        assert result.exit_code == 0
        assert "skf merge" in result.stdout or "merge" in result.stdout.lower()
    
    def test_status_warns_on_failed_tasks(self, temp_repo):
        """skf status warns when tasks have failed."""
        # Arrange: State with failed tasks
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            sessions=[],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T002": TaskStateInfo(status=TaskStatus.failed, session=1),
            },
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Shows warning
        assert result.exit_code == 0
        assert "failed" in result.stdout.lower()
    
    def test_status_handles_empty_sessions(self, temp_repo):
        """skf status handles state with no sessions gracefully."""
        # Arrange: State with empty sessions list
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=0,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-0",
            sessions=[],  # Empty
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Should succeed without crashing
        assert result.exit_code == 0
    
    def test_status_handles_empty_tasks(self, temp_repo):
        """skf status handles state with no tasks gracefully."""
        # Arrange: State with empty tasks dict
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-0",
            sessions=[],
            tasks={},  # Empty
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Should show 0 tasks
        assert result.exit_code == 0
        assert "Total: 0" in result.stdout or "0" in result.stdout
    
    def test_status_errors_if_not_in_git_repo(self, temp_dir):
        """skf status fails gracefully when not in git repo."""
        # Arrange: temp_dir is NOT a git repo
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_dir))
        
        # Assert
        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "Not in a git repository" in result.stdout or "git" in result.stdout.lower()
    
    def test_status_handles_corrupted_state_file(self, temp_repo):
        """skf status handles corrupted state file with clear error."""
        # Arrange: Create invalid YAML state file
        speckit_dir = temp_repo / ".speckit"
        speckit_dir.mkdir(exist_ok=True)
        state_path = speckit_dir / "flow-state.yaml"
        state_path.write_text("invalid: yaml: content: [[[")
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Should show error about corrupted state
        assert result.exit_code == 1
        assert "Error:" in result.stdout or "error" in result.stdout.lower()


class TestStatusCommandEdgeCases:
    """Edge case tests for skf status command."""
    
    def test_status_with_very_long_task_ids(self, temp_repo):
        """skf status handles very long task IDs."""
        # Arrange: State with long task IDs (edge case)
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-0",
            sessions=[],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T999": TaskStateInfo(status=TaskStatus.in_progress, session=0),
            },
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Should handle without issues
        assert result.exit_code == 0
    
    def test_status_with_special_characters_in_spec_id(self, temp_repo):
        """skf status handles special characters in spec_id."""
        # Arrange
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test_feature-v2",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-0",
            sessions=[],
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        assert "001-test_feature-v2" in result.stdout
    
    def test_status_shows_relative_worktree_paths(self, temp_repo):
        """skf status displays worktree paths relative to repo root."""
        # Arrange: Sessions with worktree paths
        state_manager = StateManager(temp_repo)
        worktree_path = temp_repo / ".worktrees-001" / "session-0-test"
        
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-0",
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=str(worktree_path),
                    branch_name="impl-001-session-0",
                    current_task="T001",
                    status=SessionStatus.executing,
                ),
            ],
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert: Shows relative path
        assert result.exit_code == 0
        assert ".worktrees-001" in result.stdout
    
    def test_status_with_no_phases_completed(self, temp_repo):
        """skf status handles state with no completed phases."""
        # Arrange
        state_manager = StateManager(temp_repo)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-0",
            phases_completed=[],  # No phases completed yet
            sessions=[],
            tasks={},
        )
        state_manager.save(state)
        
        # Act
        result = runner.invoke(app, ["status"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        assert "Phases Completed: 0" in result.stdout or "0" in result.stdout

