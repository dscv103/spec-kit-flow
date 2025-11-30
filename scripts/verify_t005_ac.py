#!/usr/bin/env python3
"""
T005 Acceptance Criteria Verification

This script programmatically verifies each acceptance criterion for T005.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml
from speckit_core.models import (
    TaskInfo,
    FeatureContext,
    DAGNode,
    SessionState,
    TaskStatus,
    SessionStatus,
)


def verify_ac1_models_validate():
    """AC1: All models validate correctly with sample data"""
    print("\n" + "="*70)
    print("AC1: All models validate correctly with sample data")
    print("="*70)
    
    results = []
    
    # Test TaskInfo validation
    try:
        task = TaskInfo(
            id="T001",
            name="Test task",
            description="Test description",
            dependencies=["T000"],
            session=0,
            parallelizable=True,
            story="US1",
            files=["test.py"],
            status=TaskStatus.in_progress,
            completed=True,
        )
        assert task.id == "T001"
        assert task.session == 0
        print("  ✓ TaskInfo validates with all fields")
        results.append(True)
    except Exception as e:
        print(f"  ✗ TaskInfo validation failed: {e}")
        results.append(False)
    
    # Test FeatureContext validation
    try:
        ctx = FeatureContext(
            repo_root=Path("/repo"),
            branch="test",
            feature_dir=Path("/repo/specs/test"),
            spec_path=Path("/repo/specs/test/spec.md"),
            plan_path=Path("/repo/specs/test/plan.md"),
            tasks_path=Path("/repo/specs/test/tasks.md"),
            research_path=Path("/repo/specs/test/research.md"),
        )
        assert ctx.branch == "test"
        assert ctx.research_path is not None
        print("  ✓ FeatureContext validates with all fields")
        results.append(True)
    except Exception as e:
        print(f"  ✗ FeatureContext validation failed: {e}")
        results.append(False)
    
    # Test DAGNode validation
    try:
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
        print("  ✓ DAGNode validates with all fields")
        results.append(True)
    except Exception as e:
        print(f"  ✗ DAGNode validation failed: {e}")
        results.append(False)
    
    # Test SessionState validation
    try:
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
        print("  ✓ SessionState validates with all fields")
        results.append(True)
    except Exception as e:
        print(f"  ✗ SessionState validation failed: {e}")
        results.append(False)
    
    # Test validation rules
    try:
        # Task ID pattern validation
        try:
            TaskInfo(id="INVALID", name="Test")
            print("  ✗ Task ID pattern validation failed (accepted invalid ID)")
            results.append(False)
        except ValueError:
            print("  ✓ Task ID pattern validation works")
            results.append(True)
        
        # Session non-negative validation
        try:
            TaskInfo(id="T001", name="Test", session=-1)
            print("  ✗ Session validation failed (accepted negative)")
            results.append(False)
        except ValueError:
            print("  ✓ Session non-negative validation works")
            results.append(True)
    except Exception as e:
        print(f"  ✗ Validation rules failed: {e}")
        results.append(False)
    
    return all(results)


def verify_ac2_serialization():
    """AC2: Models serialize to/from dict and YAML"""
    print("\n" + "="*70)
    print("AC2: Models serialize to/from dict and YAML")
    print("="*70)
    
    results = []
    
    # Test dict serialization (Pydantic v2: model_dump)
    try:
        task = TaskInfo(
            id="T001",
            name="Test",
            dependencies=["T000"],
            parallelizable=True,
        )
        
        # Pydantic v2 syntax check
        if not hasattr(task, 'model_dump'):
            print("  ✗ Missing model_dump() method (not Pydantic v2)")
            results.append(False)
        else:
            data = task.model_dump()
            assert isinstance(data, dict)
            assert data["id"] == "T001"
            assert data["parallelizable"] is True
            print("  ✓ Serialization to dict works (using model_dump)")
            results.append(True)
    except Exception as e:
        print(f"  ✗ Dict serialization failed: {e}")
        results.append(False)
    
    # Test YAML serialization
    try:
        task = TaskInfo(
            id="T002",
            name="Test task",
            dependencies=["T001"],
            session=0,
        )
        
        yaml_str = yaml.dump(task.model_dump())
        loaded = yaml.safe_load(yaml_str)
        
        assert loaded["id"] == "T002"
        assert loaded["name"] == "Test task"
        assert loaded["session"] == 0
        print("  ✓ YAML serialization works")
        results.append(True)
    except Exception as e:
        print(f"  ✗ YAML serialization failed: {e}")
        results.append(False)
    
    # Test dict deserialization (Pydantic v2: model_validate)
    try:
        data = {
            "id": "T003",
            "name": "Another task",
            "dependencies": ["T001", "T002"],
            "session": 1,
        }
        
        # Pydantic v2 syntax check
        if not hasattr(TaskInfo, 'model_validate'):
            print("  ✗ Missing model_validate() method (not Pydantic v2)")
            results.append(False)
        else:
            task = TaskInfo.model_validate(data)
            assert task.id == "T003"
            assert task.session == 1
            print("  ✓ Deserialization from dict works (using model_validate)")
            results.append(True)
    except Exception as e:
        print(f"  ✗ Dict deserialization failed: {e}")
        results.append(False)
    
    # Test YAML round-trip
    try:
        original = TaskInfo(
            id="T004",
            name="Complex task",
            description="With description",
            dependencies=["T001", "T002", "T003"],
            session=2,
            parallelizable=True,
            story="US2",
            files=["file1.py", "file2.py"],
            status=TaskStatus.completed,
            completed=True,
        )
        
        # Serialize
        yaml_str = yaml.dump(original.model_dump())
        
        # Deserialize
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
        
        print("  ✓ YAML round-trip preserves all fields")
        results.append(True)
    except Exception as e:
        print(f"  ✗ YAML round-trip failed: {e}")
        results.append(False)
    
    return all(results)


def verify_ac3_type_hints():
    """AC3: Type hints complete for IDE support"""
    print("\n" + "="*70)
    print("AC3: Type hints complete for IDE support")
    print("="*70)
    
    results = []
    
    # Check TaskInfo annotations
    try:
        assert hasattr(TaskInfo, "__annotations__")
        annotations = TaskInfo.__annotations__
        
        required_fields = ["id", "name", "dependencies", "session", "parallelizable", 
                          "story", "files", "status", "completed"]
        
        for field in required_fields:
            if field not in annotations:
                print(f"  ✗ Missing type hint for TaskInfo.{field}")
                results.append(False)
            else:
                results.append(True)
        
        print(f"  ✓ TaskInfo has type hints for {len(required_fields)} fields")
    except Exception as e:
        print(f"  ✗ TaskInfo type hints check failed: {e}")
        results.append(False)
    
    # Check DAGNode annotations
    try:
        assert hasattr(DAGNode, "__annotations__")
        annotations = DAGNode.__annotations__
        
        required_fields = ["id", "name", "description", "files", "dependencies", 
                          "session", "parallelizable", "story"]
        
        for field in required_fields:
            if field not in annotations:
                print(f"  ✗ Missing type hint for DAGNode.{field}")
                results.append(False)
            else:
                results.append(True)
        
        print(f"  ✓ DAGNode has type hints for {len(required_fields)} fields")
    except Exception as e:
        print(f"  ✗ DAGNode type hints check failed: {e}")
        results.append(False)
    
    # Check SessionState annotations
    try:
        assert hasattr(SessionState, "__annotations__")
        annotations = SessionState.__annotations__
        
        required_fields = ["session_id", "worktree_path", "branch_name", 
                          "current_task", "completed_tasks", "status"]
        
        for field in required_fields:
            if field not in annotations:
                print(f"  ✗ Missing type hint for SessionState.{field}")
                results.append(False)
            else:
                results.append(True)
        
        print(f"  ✓ SessionState has type hints for {len(required_fields)} fields")
    except Exception as e:
        print(f"  ✗ SessionState type hints check failed: {e}")
        results.append(False)
    
    return all(results)


def verify_ac4_pydantic_v2():
    """AC4: Pydantic v2 validation works (not v1 syntax)"""
    print("\n" + "="*70)
    print("AC4: Pydantic v2 validation works (not v1 syntax)")
    print("="*70)
    
    results = []
    
    # Check for Pydantic v2 methods (not v1)
    v2_methods = {
        'model_dump': 'replaces dict() from v1',
        'model_validate': 'replaces parse_obj() from v1',
        'model_dump_json': 'replaces json() from v1',
    }
    
    for method, description in v2_methods.items():
        if hasattr(TaskInfo, method):
            print(f"  ✓ TaskInfo has {method}() - {description}")
            results.append(True)
        else:
            print(f"  ✗ TaskInfo missing {method}() - {description}")
            results.append(False)
    
    # Check for model_config (v2) instead of Config class (v1)
    try:
        # In Pydantic v2, configuration is via model_config attribute
        task = TaskInfo(id="T001", name="Test")
        
        # Check that model_config exists (v2 pattern)
        if hasattr(TaskInfo, 'model_config'):
            print("  ✓ Uses model_config dictionary (Pydantic v2 pattern)")
            results.append(True)
        else:
            print("  ✗ Missing model_config (should use v2 pattern)")
            results.append(False)
        
        # Verify no nested Config class (v1 pattern)
        if hasattr(TaskInfo, 'Config'):
            print("  ✗ Has nested Config class (Pydantic v1 pattern)")
            results.append(False)
        else:
            print("  ✓ No nested Config class (correctly avoids v1 pattern)")
            results.append(True)
            
    except Exception as e:
        print(f"  ✗ Configuration pattern check failed: {e}")
        results.append(False)
    
    # Test enum serialization (should serialize to string in v2)
    try:
        task = TaskInfo(id="T001", name="Test", status=TaskStatus.completed)
        data = task.model_dump()
        
        # In Pydantic v2, enums serialize to their value
        if data["status"] == "completed":
            print("  ✓ Enum serialization works correctly (v2 pattern)")
            results.append(True)
        else:
            print(f"  ✗ Enum serialization incorrect: {data['status']}")
            results.append(False)
    except Exception as e:
        print(f"  ✗ Enum serialization check failed: {e}")
        results.append(False)
    
    return all(results)


def main():
    """Run all acceptance criteria verifications"""
    print("\n" + "="*70)
    print("T005 ACCEPTANCE CRITERIA VERIFICATION")
    print("="*70)
    
    results = {
        "AC1": verify_ac1_models_validate(),
        "AC2": verify_ac2_serialization(),
        "AC3": verify_ac3_type_hints(),
        "AC4": verify_ac4_pydantic_v2(),
    }
    
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    for ac, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        descriptions = {
            "AC1": "All models validate correctly with sample data",
            "AC2": "Models serialize to/from dict and YAML",
            "AC3": "Type hints complete for IDE support",
            "AC4": "Pydantic v2 validation works (not v1 syntax)",
        }
        print(f"{status} - {ac}: {descriptions[ac]}")
    
    print("="*70)
    
    if all(results.values()):
        print("\n✅ ALL ACCEPTANCE CRITERIA VERIFIED - T005 IS COMPLETE\n")
        return 0
    else:
        print("\n❌ SOME ACCEPTANCE CRITERIA FAILED - T005 NEEDS FIXES\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
