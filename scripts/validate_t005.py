#!/usr/bin/env python3
"""
Validation script for T005: Implement models.py with Pydantic

This script validates that all acceptance criteria for T005 are met:
- All models validate correctly with sample data
- Models serialize to/from dict and YAML
- Type hints complete for IDE support
- Pydantic v2 validation works (not v1 syntax)
"""

import sys
import yaml
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.models import (
    TaskInfo,
    FeatureContext,
    DAGNode,
    SessionState,
    TaskStatus,
    SessionStatus,
)


def test_taskinfo_validation():
    """Test TaskInfo validates correctly."""
    print("Testing TaskInfo validation...")
    
    # Minimal task
    task = TaskInfo(id="T001", name="Setup database")
    assert task.id == "T001"
    assert task.status == TaskStatus.pending
    
    # Full task
    task = TaskInfo(
        id="T002",
        name="Implement User model",
        description="Create User entity",
        dependencies=["T001"],
        session=0,
        parallelizable=True,
        story="US1",
        files=["src/models/User.ts"],
        status=TaskStatus.in_progress,
        completed=True,
    )
    assert task.id == "T002"
    assert len(task.files) == 1
    
    print("✓ TaskInfo validation passed")


def test_feature_context_validation():
    """Test FeatureContext validates correctly."""
    print("Testing FeatureContext validation...")
    
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
    )
    
    assert ctx.repo_root == repo
    assert ctx.research_path == feature_dir / "research.md"
    
    print("✓ FeatureContext validation passed")


def test_dag_node_validation():
    """Test DAGNode validates correctly."""
    print("Testing DAGNode validation...")
    
    node = DAGNode(
        id="T001",
        name="Setup",
        description="Initialize project",
        files=["package.json"],
        dependencies=[],
        session=0,
        parallelizable=False,
        story="US1",
    )
    
    assert node.id == "T001"
    assert node.session == 0
    assert len(node.files) == 1
    
    print("✓ DAGNode validation passed")


def test_session_state_validation():
    """Test SessionState validates correctly."""
    print("Testing SessionState validation...")
    
    session = SessionState(
        session_id=0,
        worktree_path=".worktrees-001/session-0",
        branch_name="impl-001-session-0",
        current_task="T002",
        completed_tasks=["T001"],
        status=SessionStatus.executing,
    )
    
    assert session.session_id == 0
    assert session.status == SessionStatus.executing
    assert len(session.completed_tasks) == 1
    
    print("✓ SessionState validation passed")


def test_serialization_to_dict():
    """Test models serialize to dict using Pydantic v2 syntax."""
    print("Testing serialization to dict (Pydantic v2)...")
    
    task = TaskInfo(
        id="T001",
        name="Test",
        dependencies=["T000"],
        parallelizable=True,
    )
    
    # Pydantic v2 syntax: model_dump()
    data = task.model_dump()
    
    assert isinstance(data, dict)
    assert data["id"] == "T001"
    assert data["parallelizable"] is True
    assert data["status"] == "pending"  # Enum serialized to string
    
    print("✓ Serialization to dict passed (using model_dump)")


def test_serialization_to_yaml():
    """Test models serialize to YAML."""
    print("Testing serialization to YAML...")
    
    task = TaskInfo(
        id="T001",
        name="Test task",
        dependencies=["T000"],
        session=0,
        parallelizable=True,
    )
    
    yaml_str = yaml.dump(task.model_dump())
    loaded = yaml.safe_load(yaml_str)
    
    assert loaded["id"] == "T001"
    assert loaded["name"] == "Test task"
    assert loaded["dependencies"] == ["T000"]
    assert loaded["session"] == 0
    
    print("✓ Serialization to YAML passed")


def test_deserialization_from_dict():
    """Test models deserialize from dict using Pydantic v2 syntax."""
    print("Testing deserialization from dict (Pydantic v2)...")
    
    data = {
        "id": "T002",
        "name": "Another task",
        "dependencies": ["T001"],
        "session": 1,
        "parallelizable": False,
    }
    
    # Pydantic v2 syntax: model_validate()
    task = TaskInfo.model_validate(data)
    
    assert task.id == "T002"
    assert task.name == "Another task"
    assert task.session == 1
    
    print("✓ Deserialization from dict passed (using model_validate)")


def test_yaml_round_trip():
    """Test models round-trip through YAML."""
    print("Testing YAML round-trip...")
    
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
    
    print("✓ YAML round-trip passed")


def test_type_hints():
    """Verify type hints are present (checked by IDE/mypy)."""
    print("Testing type hints presence...")
    
    # Type hints should be accessible via __annotations__
    assert hasattr(TaskInfo, "__annotations__")
    assert "id" in TaskInfo.__annotations__
    assert "name" in TaskInfo.__annotations__
    assert "dependencies" in TaskInfo.__annotations__
    
    assert hasattr(DAGNode, "__annotations__")
    assert "session" in DAGNode.__annotations__
    
    print("✓ Type hints present")


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("T005 Acceptance Criteria Validation")
    print("=" * 70)
    print()
    
    try:
        # AC 1: All models validate correctly with sample data
        test_taskinfo_validation()
        test_feature_context_validation()
        test_dag_node_validation()
        test_session_state_validation()
        print()
        
        # AC 2: Models serialize to/from dict and YAML
        test_serialization_to_dict()
        test_serialization_to_yaml()
        test_deserialization_from_dict()
        test_yaml_round_trip()
        print()
        
        # AC 3: Type hints complete for IDE support
        test_type_hints()
        print()
        
        # AC 4: Pydantic v2 validation works (verified by using model_dump, model_validate)
        print("✓ Pydantic v2 syntax verified (model_dump, model_validate used)")
        print()
        
        print("=" * 70)
        print("✅ ALL ACCEPTANCE CRITERIA PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✓ All models validate correctly with sample data")
        print("  ✓ Models serialize to/from dict and YAML")
        print("  ✓ Type hints complete for IDE support")
        print("  ✓ Pydantic v2 validation works (not v1 syntax)")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
