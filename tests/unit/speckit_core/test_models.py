"""
Unit tests for speckit_core.models.

Tests all Pydantic models including validation, serialization,
and YAML round-trip operations.
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime

from speckit_core.models import (
    TaskInfo,
    FeatureContext,
    DAGNode,
    SessionState,
    TaskStatus,
    SessionStatus,
)


# ============================================================================
# TaskInfo Tests
# ============================================================================

class TestTaskInfo:
    """Unit tests for TaskInfo model."""
    
    def test_minimal_task(self):
        """Creates task with only required fields."""
        task = TaskInfo(id="T001", name="Setup database")
        
        assert task.id == "T001"
        assert task.name == "Setup database"
        assert task.dependencies == []
        assert task.session is None
        assert task.parallelizable is False
        assert task.story is None
        assert task.files == []
        assert task.status == TaskStatus.pending
        assert task.completed is False
    
    def test_full_task(self):
        """Creates task with all fields populated."""
        task = TaskInfo(
            id="T002",
            name="Implement User model",
            description="Create User entity with validation",
            dependencies=["T001"],
            session=0,
            parallelizable=True,
            story="US1",
            files=["src/models/User.ts", "src/models/__tests__/User.test.ts"],
            status=TaskStatus.in_progress,
            completed=False,
        )
        
        assert task.id == "T002"
        assert task.name == "Implement User model"
        assert task.description == "Create User entity with validation"
        assert task.dependencies == ["T001"]
        assert task.session == 0
        assert task.parallelizable is True
        assert task.story == "US1"
        assert len(task.files) == 2
        assert task.status == TaskStatus.in_progress
        assert task.completed is False
    
    def test_task_id_validation(self):
        """Validates task ID format."""
        # Valid IDs
        TaskInfo(id="T001", name="Test")
        TaskInfo(id="T999", name="Test")
        
        # Invalid IDs
        with pytest.raises(ValueError):
            TaskInfo(id="T1", name="Test")  # Too short
        with pytest.raises(ValueError):
            TaskInfo(id="T0001", name="Test")  # Too long
        with pytest.raises(ValueError):
            TaskInfo(id="001", name="Test")  # Missing T prefix
        with pytest.raises(ValueError):
            TaskInfo(id="TASK001", name="Test")  # Wrong prefix
    
    def test_task_name_required(self):
        """Name field is required and non-empty."""
        with pytest.raises(ValueError):
            TaskInfo(id="T001", name="")
    
    def test_session_validation(self):
        """Session ID must be non-negative."""
        TaskInfo(id="T001", name="Test", session=0)  # Valid
        TaskInfo(id="T001", name="Test", session=5)  # Valid
        
        with pytest.raises(ValueError):
            TaskInfo(id="T001", name="Test", session=-1)  # Invalid
    
    def test_task_status_enum(self):
        """Status uses enum values correctly."""
        task = TaskInfo(id="T001", name="Test")
        assert task.status == TaskStatus.pending
        
        task = TaskInfo(id="T001", name="Test", status=TaskStatus.completed)
        assert task.status == TaskStatus.completed
        assert task.status.value == "completed"
    
    def test_task_serialization_to_dict(self):
        """Serializes to dictionary with Pydantic v2."""
        task = TaskInfo(
            id="T001",
            name="Test task",
            dependencies=["T000"],
            parallelizable=True,
        )
        
        data = task.model_dump()
        
        assert data["id"] == "T001"
        assert data["name"] == "Test task"
        assert data["dependencies"] == ["T000"]
        assert data["parallelizable"] is True
        assert data["status"] == "pending"
    
    def test_task_serialization_to_yaml(self):
        """Serializes to YAML correctly."""
        task = TaskInfo(
            id="T001",
            name="Test task",
            dependencies=["T000"],
            session=0,
            parallelizable=True,
            story="US1",
        )
        
        yaml_str = yaml.dump(task.model_dump())
        loaded = yaml.safe_load(yaml_str)
        
        assert loaded["id"] == "T001"
        assert loaded["name"] == "Test task"
        assert loaded["dependencies"] == ["T000"]
        assert loaded["session"] == 0
        assert loaded["parallelizable"] is True
        assert loaded["story"] == "US1"
    
    def test_task_deserialization_from_dict(self):
        """Deserializes from dictionary with Pydantic v2."""
        data = {
            "id": "T002",
            "name": "Another task",
            "dependencies": ["T001"],
            "session": 1,
            "parallelizable": False,
        }
        
        task = TaskInfo.model_validate(data)
        
        assert task.id == "T002"
        assert task.name == "Another task"
        assert task.dependencies == ["T001"]
        assert task.session == 1
        assert task.parallelizable is False
    
    def test_task_round_trip_yaml(self):
        """Round-trip through YAML preserves data."""
        original = TaskInfo(
            id="T003",
            name="Complex task",
            description="With description",
            dependencies=["T001", "T002"],
            session=2,
            parallelizable=True,
            story="US2",
            files=["file1.py", "file2.py"],
            status=TaskStatus.completed,
            completed=True,
        )
        
        # Serialize to YAML
        yaml_str = yaml.dump(original.model_dump())
        
        # Deserialize back
        data = yaml.safe_load(yaml_str)
        restored = TaskInfo.model_validate(data)
        
        # Verify all fields preserved
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.dependencies == original.dependencies
        assert restored.session == original.session
        assert restored.parallelizable == original.parallelizable
        assert restored.story == original.story
        assert restored.files == original.files
        assert restored.status == original.status
        assert restored.completed == original.completed
    
    def test_task_mutation_allowed(self):
        """Task fields can be mutated (not frozen)."""
        task = TaskInfo(id="T001", name="Test")
        
        # Should allow assignment
        task.session = 0
        task.status = TaskStatus.in_progress
        task.completed = True
        
        assert task.session == 0
        assert task.status == TaskStatus.in_progress
        assert task.completed is True


# ============================================================================
# FeatureContext Tests
# ============================================================================

class TestFeatureContext:
    """Unit tests for FeatureContext model."""
    
    def test_feature_context_creation(self):
        """Creates FeatureContext with all paths."""
        repo = Path("/repo")
        feature_dir = repo / "specs" / "001-feature"
        
        ctx = FeatureContext(
            repo_root=repo,
            branch="001-feature",
            feature_dir=feature_dir,
            spec_path=feature_dir / "spec.md",
            plan_path=feature_dir / "plan.md",
            tasks_path=feature_dir / "tasks.md",
        )
        
        assert ctx.repo_root == repo
        assert ctx.branch == "001-feature"
        assert ctx.feature_dir == feature_dir
        assert ctx.spec_path == feature_dir / "spec.md"
        assert ctx.plan_path == feature_dir / "plan.md"
        assert ctx.tasks_path == feature_dir / "tasks.md"
        assert ctx.research_path is None
    
    def test_feature_context_with_optional_paths(self):
        """Creates FeatureContext with optional paths."""
        repo = Path("/repo")
        feature_dir = repo / "specs" / "001-feature"
        
        ctx = FeatureContext(
            repo_root=repo,
            branch="001-feature",
            feature_dir=feature_dir,
            spec_path=feature_dir / "spec.md",
            plan_path=feature_dir / "plan.md",
            tasks_path=feature_dir / "tasks.md",
            research_path=feature_dir / "research.md",
            data_model_path=feature_dir / "data-model.md",
        )
        
        assert ctx.research_path == feature_dir / "research.md"
        assert ctx.data_model_path == feature_dir / "data-model.md"
    
    def test_feature_context_is_frozen(self):
        """FeatureContext is immutable."""
        ctx = FeatureContext(
            repo_root=Path("/repo"),
            branch="test",
            feature_dir=Path("/repo/specs/test"),
            spec_path=Path("/repo/specs/test/spec.md"),
            plan_path=Path("/repo/specs/test/plan.md"),
            tasks_path=Path("/repo/specs/test/tasks.md"),
        )
        
        with pytest.raises(ValueError):
            ctx.branch = "other-branch"


# ============================================================================
# DAGNode Tests
# ============================================================================

class TestDAGNode:
    """Unit tests for DAGNode model."""
    
    def test_minimal_dag_node(self):
        """Creates DAGNode with minimal fields."""
        node = DAGNode(
            id="T001",
            name="Setup",
            description="Initialize project",
            dependencies=[],
            session=0,
            parallelizable=False,
        )
        
        assert node.id == "T001"
        assert node.name == "Setup"
        assert node.description == "Initialize project"
        assert node.files == []
        assert node.dependencies == []
        assert node.session == 0
        assert node.parallelizable is False
        assert node.story is None
    
    def test_full_dag_node(self):
        """Creates DAGNode with all fields."""
        node = DAGNode(
            id="T002",
            name="Implement User model",
            description="Create User entity with validation",
            files=["src/models/User.ts", "src/models/__tests__/User.test.ts"],
            dependencies=["T001"],
            session=0,
            parallelizable=True,
            story="US1",
        )
        
        assert node.id == "T002"
        assert node.name == "Implement User model"
        assert len(node.files) == 2
        assert node.dependencies == ["T001"]
        assert node.session == 0
        assert node.parallelizable is True
        assert node.story == "US1"
    
    def test_dag_node_serialization(self):
        """Serializes DAGNode for dag.yaml."""
        node = DAGNode(
            id="T001",
            name="Test",
            description="Test task",
            files=["test.py"],
            dependencies=[],
            session=0,
            parallelizable=True,
            story="US1",
        )
        
        data = node.model_dump()
        
        assert data["id"] == "T001"
        assert data["name"] == "Test"
        assert data["description"] == "Test task"
        assert data["files"] == ["test.py"]
        assert data["session"] == 0
        assert data["parallelizable"] is True
        assert data["story"] == "US1"
    
    def test_dag_node_yaml_round_trip(self):
        """Round-trip through YAML preserves DAGNode data."""
        original = DAGNode(
            id="T003",
            name="Complex task",
            description="Detailed description",
            files=["file1.py", "file2.py"],
            dependencies=["T001", "T002"],
            session=1,
            parallelizable=True,
            story="US2",
        )
        
        yaml_str = yaml.dump(original.model_dump())
        data = yaml.safe_load(yaml_str)
        restored = DAGNode.model_validate(data)
        
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.files == original.files
        assert restored.dependencies == original.dependencies
        assert restored.session == original.session
        assert restored.parallelizable == original.parallelizable
        assert restored.story == original.story
    
    def test_dag_node_is_frozen(self):
        """DAGNode is immutable."""
        node = DAGNode(
            id="T001",
            name="Test",
            description="Test",
            session=0,
            parallelizable=False,
        )
        
        with pytest.raises(ValueError):
            node.session = 1


# ============================================================================
# SessionState Tests
# ============================================================================

class TestSessionState:
    """Unit tests for SessionState model."""
    
    def test_minimal_session_state(self):
        """Creates SessionState with minimal fields."""
        session = SessionState(
            session_id=0,
            worktree_path=".worktrees-001/session-0",
            branch_name="impl-001-session-0",
        )
        
        assert session.session_id == 0
        assert session.worktree_path == ".worktrees-001/session-0"
        assert session.branch_name == "impl-001-session-0"
        assert session.current_task is None
        assert session.completed_tasks == []
        assert session.status == SessionStatus.idle
    
    def test_full_session_state(self):
        """Creates SessionState with all fields."""
        session = SessionState(
            session_id=1,
            worktree_path=".worktrees-001/session-1-user-model",
            branch_name="impl-001-session-1",
            current_task="T003",
            completed_tasks=["T001", "T002"],
            status=SessionStatus.executing,
        )
        
        assert session.session_id == 1
        assert session.current_task == "T003"
        assert session.completed_tasks == ["T001", "T002"]
        assert session.status == SessionStatus.executing
    
    def test_session_status_enum(self):
        """Status uses enum values correctly."""
        session = SessionState(
            session_id=0,
            worktree_path="path",
            branch_name="branch",
        )
        
        assert session.status == SessionStatus.idle
        
        session = SessionState(
            session_id=0,
            worktree_path="path",
            branch_name="branch",
            status=SessionStatus.completed,
        )
        
        assert session.status == SessionStatus.completed
        assert session.status.value == "completed"
    
    def test_session_state_serialization(self):
        """Serializes SessionState for flow-state.yaml."""
        session = SessionState(
            session_id=0,
            worktree_path=".worktrees-001/session-0-setup",
            branch_name="impl-001-session-0",
            current_task="T002",
            completed_tasks=["T001"],
            status=SessionStatus.executing,
        )
        
        data = session.model_dump()
        
        assert data["session_id"] == 0
        assert data["worktree_path"] == ".worktrees-001/session-0-setup"
        assert data["branch_name"] == "impl-001-session-0"
        assert data["current_task"] == "T002"
        assert data["completed_tasks"] == ["T001"]
        assert data["status"] == "executing"
    
    def test_session_state_yaml_round_trip(self):
        """Round-trip through YAML preserves SessionState data."""
        original = SessionState(
            session_id=2,
            worktree_path=".worktrees-001/session-2",
            branch_name="impl-001-session-2",
            current_task="T005",
            completed_tasks=["T003", "T004"],
            status=SessionStatus.waiting,
        )
        
        yaml_str = yaml.dump(original.model_dump())
        data = yaml.safe_load(yaml_str)
        restored = SessionState.model_validate(data)
        
        assert restored.session_id == original.session_id
        assert restored.worktree_path == original.worktree_path
        assert restored.branch_name == original.branch_name
        assert restored.current_task == original.current_task
        assert restored.completed_tasks == original.completed_tasks
        assert restored.status == original.status
    
    def test_session_state_mutation_allowed(self):
        """SessionState fields can be mutated (not frozen)."""
        session = SessionState(
            session_id=0,
            worktree_path="path",
            branch_name="branch",
        )
        
        # Should allow assignment
        session.current_task = "T001"
        session.status = SessionStatus.executing
        session.completed_tasks.append("T001")
        
        assert session.current_task == "T001"
        assert session.status == SessionStatus.executing
        assert "T001" in session.completed_tasks


# ============================================================================
# Integration Tests
# ============================================================================

class TestModelIntegration:
    """Integration tests for model interactions."""
    
    def test_task_to_dag_node_conversion(self):
        """TaskInfo can be converted to DAGNode."""
        task = TaskInfo(
            id="T001",
            name="Test task",
            description="Test description",
            dependencies=["T000"],
            session=0,
            parallelizable=True,
            story="US1",
            files=["test.py"],
        )
        
        # Manual conversion (will be in DAGEngine)
        node = DAGNode(
            id=task.id,
            name=task.name,
            description=task.description or task.name,
            files=task.files,
            dependencies=task.dependencies,
            session=task.session or 0,
            parallelizable=task.parallelizable,
            story=task.story,
        )
        
        assert node.id == task.id
        assert node.name == task.name
        assert node.dependencies == task.dependencies
        assert node.session == task.session
    
    def test_multiple_models_yaml_serialization(self):
        """Multiple models can be serialized to YAML together."""
        tasks = [
            TaskInfo(id="T001", name="Task 1", parallelizable=False),
            TaskInfo(id="T002", name="Task 2", dependencies=["T001"], parallelizable=True),
        ]
        
        sessions = [
            SessionState(session_id=0, worktree_path="path0", branch_name="branch0"),
            SessionState(session_id=1, worktree_path="path1", branch_name="branch1"),
        ]
        
        data = {
            "tasks": [t.model_dump() for t in tasks],
            "sessions": [s.model_dump() for s in sessions],
        }
        
        yaml_str = yaml.dump(data)
        loaded = yaml.safe_load(yaml_str)
        
        assert len(loaded["tasks"]) == 2
        assert len(loaded["sessions"]) == 2
        assert loaded["tasks"][0]["id"] == "T001"
        assert loaded["sessions"][0]["session_id"] == 0
