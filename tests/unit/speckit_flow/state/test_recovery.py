"""
Unit tests for state/recovery.py (T012).

Tests the RecoveryManager class including:
- Checkpoint creation
- Checkpoint listing and retrieval
- State restoration
- Cleanup of old checkpoints
"""

import time

import pytest
from speckit_flow.state.models import OrchestrationState
from speckit_flow.state.recovery import RecoveryManager


class TestRecoveryManager:
    """Unit tests for RecoveryManager class."""
    
    def test_initializes_with_repo_root(self, temp_dir):
        """RecoveryManager initializes with correct paths."""
        # Arrange & Act
        manager = RecoveryManager(temp_dir)
        
        # Assert
        assert manager.repo_root == temp_dir
        assert manager.checkpoints_dir == temp_dir / ".speckit" / "checkpoints"
    
    def test_checkpoint_creates_directory(self, temp_dir):
        """checkpoint() creates checkpoints directory if missing."""
        # Arrange
        manager = RecoveryManager(temp_dir)
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
        checkpoint_path = manager.checkpoint(state)
        
        # Assert
        assert manager.checkpoints_dir.exists()
        assert manager.checkpoints_dir.is_dir()
        assert checkpoint_path.parent == manager.checkpoints_dir
    
    def test_checkpoint_creates_file_with_iso8601_timestamp(self, temp_dir):
        """checkpoint() creates file with ISO 8601 timestamp filename."""
        # Arrange
        manager = RecoveryManager(temp_dir)
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
        checkpoint_path = manager.checkpoint(state)
        
        # Assert
        filename = checkpoint_path.name
        assert filename.endswith(".yaml")
        # ISO 8601 format: YYYY-MM-DDTHH-MM-SSZ.yaml
        assert "T" in filename  # Date-time separator
        assert filename.count("-") >= 4  # Date hyphens + time hyphens
    
    def test_restore_from_checkpoint_returns_state(self, temp_dir):
        """restore_from_checkpoint() returns valid OrchestrationState."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        original = OrchestrationState(
            spec_id="001-feature",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-1",
            phases_completed=["phase-0"]
        )
        checkpoint_path = manager.checkpoint(original)
        
        # Act
        restored = manager.restore_from_checkpoint(checkpoint_path)
        
        # Assert
        assert isinstance(restored, OrchestrationState)
        assert restored.spec_id == original.spec_id
        assert restored.num_sessions == original.num_sessions
        assert restored.current_phase == original.current_phase
        assert restored.phases_completed == original.phases_completed
    
    def test_restore_raises_when_file_not_found(self, temp_dir):
        """restore_from_checkpoint() raises FileNotFoundError for missing file."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        nonexistent = temp_dir / "nonexistent.yaml"
        
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            manager.restore_from_checkpoint(nonexistent)
    
    def test_list_checkpoints_returns_empty_when_none_exist(self, temp_dir):
        """list_checkpoints() returns empty list when no checkpoints exist."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        
        # Act
        checkpoints = manager.list_checkpoints()
        
        # Assert
        assert checkpoints == []
    
    def test_list_checkpoints_returns_all_checkpoints(self, temp_dir):
        """list_checkpoints() returns all checkpoint files."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        
        # Create multiple checkpoints
        cp1 = manager.checkpoint(state)
        time.sleep(0.01)  # Ensure different timestamps
        cp2 = manager.checkpoint(state)
        time.sleep(0.01)
        cp3 = manager.checkpoint(state)
        
        # Act
        checkpoints = manager.list_checkpoints()
        
        # Assert
        assert len(checkpoints) == 3
        assert cp1 in checkpoints
        assert cp2 in checkpoints
        assert cp3 in checkpoints
    
    def test_list_checkpoints_sorted_newest_first(self, temp_dir):
        """list_checkpoints() sorts by modification time (newest first)."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        
        # Create checkpoints with delays to ensure ordering
        cp1 = manager.checkpoint(state)
        time.sleep(0.01)
        cp2 = manager.checkpoint(state)
        time.sleep(0.01)
        cp3 = manager.checkpoint(state)
        
        # Act
        checkpoints = manager.list_checkpoints()
        
        # Assert - newest first
        assert checkpoints[0] == cp3
        assert checkpoints[1] == cp2
        assert checkpoints[2] == cp1
    
    def test_get_latest_checkpoint_returns_most_recent(self, temp_dir):
        """get_latest_checkpoint() returns most recent checkpoint."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        
        manager.checkpoint(state)
        time.sleep(0.01)
        manager.checkpoint(state)
        time.sleep(0.01)
        latest_cp = manager.checkpoint(state)
        
        # Act
        latest = manager.get_latest_checkpoint()
        
        # Assert
        assert latest == latest_cp
    
    def test_get_latest_checkpoint_returns_none_when_empty(self, temp_dir):
        """get_latest_checkpoint() returns None when no checkpoints exist."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        
        # Act
        latest = manager.get_latest_checkpoint()
        
        # Assert
        assert latest is None
    
    def test_cleanup_old_checkpoints_preserves_n_recent(self, temp_dir):
        """cleanup_old_checkpoints() preserves N most recent checkpoints."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        
        # Create 15 checkpoints
        for i in range(15):
            manager.checkpoint(state)
            time.sleep(0.01)
        
        # Act
        deleted = manager.cleanup_old_checkpoints(keep=10)
        
        # Assert
        assert deleted == 5
        remaining = manager.list_checkpoints()
        assert len(remaining) == 10
    
    def test_cleanup_returns_zero_when_under_threshold(self, temp_dir):
        """cleanup_old_checkpoints() returns 0 when fewer than keep exist."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:00:00Z",
            updated_at="2025-11-28T10:00:00Z",
            current_phase="phase-0"
        )
        
        # Create only 5 checkpoints
        for i in range(5):
            manager.checkpoint(state)
        
        # Act
        deleted = manager.cleanup_old_checkpoints(keep=10)
        
        # Assert
        assert deleted == 0
        remaining = manager.list_checkpoints()
        assert len(remaining) == 5
    
    def test_cleanup_handles_empty_directory(self, temp_dir):
        """cleanup_old_checkpoints() handles empty checkpoints directory."""
        # Arrange
        manager = RecoveryManager(temp_dir)
        
        # Act
        deleted = manager.cleanup_old_checkpoints(keep=10)
        
        # Assert
        assert deleted == 0
