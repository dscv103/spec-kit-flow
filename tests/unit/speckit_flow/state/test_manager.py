"""
Unit tests for state/manager.py (T011).

Tests the StateManager class including:
- Atomic write patterns
- File locking
- State persistence
- Error handling
"""

import pytest
from speckit_core.models import SessionState, SessionStatus
from speckit_flow.exceptions import StateNotFoundError
from speckit_flow.state.manager import StateManager
from speckit_flow.state.models import OrchestrationState


class TestStateManager:
    """Unit tests for StateManager class."""
    
    def test_initializes_with_repo_root(self, temp_dir):
        """StateManager initializes with correct paths."""
        # Arrange & Act
        manager = StateManager(temp_dir)
        
        # Assert
        assert manager.repo_root == temp_dir
        assert manager.speckit_dir == temp_dir / ".speckit"
        assert manager.state_path == temp_dir / ".speckit" / "flow-state.yaml"
        assert str(manager.lock_path).endswith(".lock")
    
    def test_exists_returns_false_before_save(self, temp_dir):
        """exists() returns False when state file doesn't exist."""
        # Arrange
        manager = StateManager(temp_dir)
        
        # Act
        result = manager.exists()
        
        # Assert
        assert result is False
    
    def test_save_creates_speckit_directory(self, temp_dir):
        """save() creates .speckit/ directory if missing."""
        # Arrange
        manager = StateManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        
        # Act
        manager.save(state)
        
        # Assert
        assert manager.speckit_dir.exists()
        assert manager.speckit_dir.is_dir()
    
    def test_save_creates_state_file(self, temp_dir):
        """save() creates flow-state.yaml file."""
        # Arrange
        manager = StateManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        
        # Act
        manager.save(state)
        
        # Assert
        assert manager.state_path.exists()
        assert manager.state_path.is_file()
        assert manager.exists()
    
    def test_save_updates_timestamp(self, temp_dir):
        """save() updates the updated_at timestamp."""
        # Arrange
        manager = StateManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        original_timestamp = state.updated_at
        
        # Act
        manager.save(state)
        
        # Assert
        assert state.updated_at != original_timestamp
    
    def test_save_atomic_write_completes(self, temp_dir):
        """save() completes atomic write (no temp files left)."""
        # Arrange
        manager = StateManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        
        # Act
        manager.save(state)
        
        # Assert - no temp files should remain
        temp_files = list(manager.speckit_dir.glob("*.tmp"))
        assert len(temp_files) == 0
        assert manager.state_path.exists()
    
    def test_load_returns_saved_state(self, temp_dir):
        """load() returns the previously saved state."""
        # Arrange
        manager = StateManager(temp_dir)
        original = OrchestrationState(
            spec_id="001-feature",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-1",
            phases_completed=["phase-0"],
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=".worktrees-001/session-0",
                    branch_name="impl-001-session-0",
                    current_task="T001",
                    completed_tasks=[],
                    status=SessionStatus.executing
                )
            ]
        )
        manager.save(original)
        
        # Act
        loaded = manager.load()
        
        # Assert
        assert loaded.spec_id == original.spec_id
        assert loaded.num_sessions == original.num_sessions
        assert loaded.current_phase == original.current_phase
        assert len(loaded.sessions) == len(original.sessions)
        assert loaded.sessions[0].session_id == 0
    
    def test_load_raises_when_state_not_found(self, temp_dir):
        """load() raises StateNotFoundError when state file doesn't exist."""
        # Arrange
        manager = StateManager(temp_dir)
        
        # Act & Assert
        with pytest.raises(StateNotFoundError) as exc_info:
            manager.load()
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_delete_removes_state_file(self, temp_dir):
        """delete() removes the state file."""
        # Arrange
        manager = StateManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        manager.save(state)
        assert manager.exists()
        
        # Act
        manager.delete()
        
        # Assert
        assert not manager.exists()
        assert not manager.state_path.exists()
    
    def test_delete_safe_when_no_file(self, temp_dir):
        """delete() is safe to call when state file doesn't exist."""
        # Arrange
        manager = StateManager(temp_dir)
        
        # Act & Assert - should not raise
        manager.delete()
    
    def test_save_load_round_trip(self, temp_dir):
        """save() and load() preserve all state data."""
        # Arrange
        manager = StateManager(temp_dir)
        original = OrchestrationState(
            version="1.0",
            spec_id="001-complex",
            agent_type="copilot",
            num_sessions=3,
            base_branch="develop",
            started_at="2025-11-28T09:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-2",
            phases_completed=["phase-0", "phase-1"],
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=".worktrees-001/session-0",
                    branch_name="impl-001-session-0",
                    current_task="T005",
                    completed_tasks=["T001", "T002"],
                    status=SessionStatus.completed
                ),
                SessionState(
                    session_id=1,
                    worktree_path=".worktrees-001/session-1",
                    branch_name="impl-001-session-1",
                    current_task=None,
                    completed_tasks=["T003", "T004"],
                    status=SessionStatus.idle
                )
            ],
            merge_status="completed"
        )
        
        # Act
        manager.save(original)
        loaded = manager.load()
        
        # Assert - comprehensive field checks
        assert loaded.version == original.version
        assert loaded.spec_id == original.spec_id
        assert loaded.agent_type == original.agent_type
        assert loaded.num_sessions == original.num_sessions
        assert loaded.base_branch == original.base_branch
        assert loaded.current_phase == original.current_phase
        assert loaded.phases_completed == original.phases_completed
        assert len(loaded.sessions) == 2
        assert loaded.sessions[0].completed_tasks == ["T001", "T002"]
        assert loaded.merge_status == "completed"
