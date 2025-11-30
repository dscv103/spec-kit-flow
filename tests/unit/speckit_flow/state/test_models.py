"""
Unit tests for state/models.py (T010).

Tests the Pydantic models for orchestration state including:
- TaskStateInfo model
- OrchestrationState model
- Schema validation
- YAML serialization
"""

import pytest
import yaml
from speckit_core.models import SessionState, SessionStatus, TaskStatus
from speckit_flow.state.models import OrchestrationState, TaskStateInfo


class TestTaskStateInfo:
    """Unit tests for TaskStateInfo model."""
    
    def test_creates_with_required_fields(self):
        """TaskStateInfo validates with only required status field."""
        # Arrange & Act
        info = TaskStateInfo(status=TaskStatus.pending)
        
        # Assert
        assert info.status == TaskStatus.pending
        assert info.session is None
        assert info.started_at is None
        assert info.completed_at is None
    
    def test_accepts_all_fields(self):
        """TaskStateInfo accepts all optional fields."""
        # Arrange & Act
        info = TaskStateInfo(
            status=TaskStatus.completed,
            session=0,
            started_at="2025-11-28T10:30:00Z",
            completed_at="2025-11-28T10:45:00Z"
        )
        
        # Assert
        assert info.status == TaskStatus.completed
        assert info.session == 0
        assert info.started_at == "2025-11-28T10:30:00Z"
        assert info.completed_at == "2025-11-28T10:45:00Z"
    
    def test_serializes_to_dict(self):
        """TaskStateInfo serializes to dictionary correctly."""
        # Arrange
        info = TaskStateInfo(
            status=TaskStatus.in_progress,
            session=1,
            started_at="2025-11-28T10:30:00Z"
        )
        
        # Act
        data = info.model_dump()
        
        # Assert
        assert data["status"] == "in_progress"
        assert data["session"] == 1
        assert data["started_at"] == "2025-11-28T10:30:00Z"
        assert data["completed_at"] is None


class TestOrchestrationState:
    """Unit tests for OrchestrationState model."""
    
    def test_creates_with_minimal_fields(self):
        """OrchestrationState validates with required fields only."""
        # Arrange & Act
        state = OrchestrationState(
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=3,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:30:00Z",
            current_phase="phase-0"
        )
        
        # Assert
        assert state.version == "1.0"  # Default
        assert state.spec_id == "001-test"
        assert state.agent_type == "copilot"
        assert state.num_sessions == 3
        assert state.base_branch == "main"
        assert state.current_phase == "phase-0"
        assert state.phases_completed == []
        assert state.sessions == []
        assert state.tasks == {}
        assert state.merge_status is None
    
    def test_validates_num_sessions_positive(self):
        """OrchestrationState requires num_sessions >= 1."""
        # Arrange & Act & Assert
        with pytest.raises(Exception):  # Pydantic validation error
            OrchestrationState(
                spec_id="001-test",
                agent_type="copilot",
                num_sessions=0,  # Invalid
                base_branch="main",
                started_at="2025-11-28T10:30:00Z",
                updated_at="2025-11-28T10:30:00Z",
                current_phase="phase-0"
            )
    
    def test_serializes_to_yaml(self):
        """OrchestrationState serializes to YAML matching schema."""
        # Arrange
        state = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:30:00Z",
            current_phase="phase-0",
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
            ],
            tasks={
                "T001": TaskStateInfo(
                    status=TaskStatus.in_progress,
                    session=0,
                    started_at="2025-11-28T10:31:00Z"
                )
            }
        )
        
        # Act
        yaml_str = yaml.dump(state.model_dump())
        
        # Assert - check key fields in YAML
        assert "spec_id" in yaml_str
        assert "001-test" in yaml_str
        assert "num_sessions: 2" in yaml_str
        assert "phase-0" in yaml_str
    
    def test_round_trip_serialization(self):
        """OrchestrationState round-trip preserves all data."""
        # Arrange
        original = OrchestrationState(
            version="1.0",
            spec_id="001-feature",
            agent_type="copilot",
            num_sessions=3,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            phases_completed=["phase-0"],
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=".worktrees-001/session-0",
                    branch_name="impl-001-session-0",
                    current_task="T002",
                    completed_tasks=["T001"],
                    status=SessionStatus.executing
                ),
                SessionState(
                    session_id=1,
                    worktree_path=".worktrees-001/session-1",
                    branch_name="impl-001-session-1",
                    current_task="T003",
                    completed_tasks=["T001"],
                    status=SessionStatus.executing
                )
            ],
            tasks={
                "T001": TaskStateInfo(
                    status=TaskStatus.completed,
                    session=0,
                    started_at="2025-11-28T10:31:00Z",
                    completed_at="2025-11-28T10:40:00Z"
                ),
                "T002": TaskStateInfo(
                    status=TaskStatus.in_progress,
                    session=0,
                    started_at="2025-11-28T10:41:00Z"
                ),
                "T003": TaskStateInfo(
                    status=TaskStatus.in_progress,
                    session=1,
                    started_at="2025-11-28T10:41:00Z"
                )
            }
        )
        
        # Act - serialize to dict and back
        data = original.model_dump()
        restored = OrchestrationState.model_validate(data)
        
        # Assert - all fields preserved
        assert restored.version == original.version
        assert restored.spec_id == original.spec_id
        assert restored.agent_type == original.agent_type
        assert restored.num_sessions == original.num_sessions
        assert restored.base_branch == original.base_branch
        assert restored.started_at == original.started_at
        assert restored.updated_at == original.updated_at
        assert restored.current_phase == original.current_phase
        assert restored.phases_completed == original.phases_completed
        assert len(restored.sessions) == len(original.sessions)
        assert len(restored.tasks) == len(original.tasks)
        assert restored.tasks["T001"].status == TaskStatus.completed
    
    def test_mark_updated_changes_timestamp(self):
        """mark_updated() updates the updated_at timestamp."""
        # Arrange
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
        state.mark_updated()
        
        # Assert
        assert state.updated_at != original_timestamp
        # Timestamp should be in ISO 8601 format
        assert "T" in state.updated_at
        assert "Z" in state.updated_at
    
    def test_get_current_timestamp_returns_iso8601(self):
        """get_current_timestamp() returns ISO 8601 format."""
        # Arrange
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
        timestamp = state.get_current_timestamp()
        
        # Assert - ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
        assert len(timestamp) == 20
        assert timestamp[10] == "T"
        assert timestamp[-1] == "Z"
