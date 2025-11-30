#!/usr/bin/env python3
"""
Validation script for T014, T015, T016: Phase generation, session assignment, and DAG serialization.

This script validates that the DAG engine correctly:
- Generates phases using topological generations (T014)
- Identifies critical paths (T014)
- Assigns tasks to sessions round-robin (T015)
- Serializes to/from YAML matching schema (T016)
"""

import sys
from pathlib import Path
import tempfile

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from speckit_core.models import TaskInfo
from speckit_flow.orchestration.dag_engine import DAGEngine
import yaml


def test_phase_generation():
    """Test T014: Phase generation with topological generations."""
    print("Testing T014: Phase Generation...")
    
    # Test 1: Empty task list
    engine = DAGEngine([])
    assert engine.get_phases() == [], "Empty tasks should return empty phases"
    assert engine.phase_count == 0, "Empty tasks should have 0 phases"
    print("  ✓ Empty task list handled")
    
    # Test 2: Tasks with no dependencies in phase 0
    tasks = [
        TaskInfo(id="T001", name="A", dependencies=[]),
        TaskInfo(id="T002", name="B", dependencies=[]),
    ]
    engine = DAGEngine(tasks)
    phases = engine.get_phases()
    assert len(phases) == 1, "All no-dep tasks should be in phase 0"
    assert set(phases[0]) == {"T001", "T002"}, "Phase 0 should contain both tasks"
    print("  ✓ Tasks with no dependencies in phase 0")
    
    # Test 3: Linear dependencies create separate phases
    tasks = [
        TaskInfo(id="T001", name="A", dependencies=[]),
        TaskInfo(id="T002", name="B", dependencies=["T001"]),
        TaskInfo(id="T003", name="C", dependencies=["T002"]),
    ]
    engine = DAGEngine(tasks)
    phases = engine.get_phases()
    assert len(phases) == 3, "Linear chain should have 3 phases"
    assert phases[0] == ["T001"], "Phase 0 should have T001"
    assert phases[1] == ["T002"], "Phase 1 should have T002"
    assert phases[2] == ["T003"], "Phase 2 should have T003"
    print("  ✓ Linear dependencies create separate phases")
    
    # Test 4: Parallel branches
    tasks = [
        TaskInfo(id="T001", name="Root", dependencies=[]),
        TaskInfo(id="T002", name="A", dependencies=["T001"]),
        TaskInfo(id="T003", name="B", dependencies=["T001"]),
    ]
    engine = DAGEngine(tasks)
    phases = engine.get_phases()
    assert len(phases) == 2, "Should have 2 phases"
    assert phases[0] == ["T001"], "Phase 0 should have root"
    assert set(phases[1]) == {"T002", "T003"}, "Phase 1 should have parallel tasks"
    print("  ✓ Parallel branches in same phase")
    
    print("✅ T014 Phase Generation: ALL TESTS PASSED\n")


def test_critical_path():
    """Test T014: Critical path identification."""
    print("Testing T014: Critical Path...")
    
    # Test 1: Empty task list
    engine = DAGEngine([])
    assert engine.get_critical_path() == [], "Empty tasks should return empty path"
    print("  ✓ Empty task list handled")
    
    # Test 2: Single task
    tasks = [TaskInfo(id="T001", name="Only", dependencies=[])]
    engine = DAGEngine(tasks)
    path = engine.get_critical_path()
    assert path == ["T001"], "Single task should be the critical path"
    print("  ✓ Single task critical path")
    
    # Test 3: Linear chain is full critical path
    tasks = [
        TaskInfo(id="T001", name="A", dependencies=[]),
        TaskInfo(id="T002", name="B", dependencies=["T001"]),
        TaskInfo(id="T003", name="C", dependencies=["T002"]),
    ]
    engine = DAGEngine(tasks)
    path = engine.get_critical_path()
    assert path == ["T001", "T002", "T003"], "Linear chain is critical path"
    print("  ✓ Linear chain critical path")
    
    # Test 4: Chooses longest branch
    tasks = [
        TaskInfo(id="T001", name="Root", dependencies=[]),
        TaskInfo(id="T002", name="Short", dependencies=["T001"]),
        TaskInfo(id="T003", name="Long A", dependencies=["T001"]),
        TaskInfo(id="T004", name="Long B", dependencies=["T003"]),
        TaskInfo(id="T005", name="Long C", dependencies=["T004"]),
    ]
    engine = DAGEngine(tasks)
    path = engine.get_critical_path()
    assert path == ["T001", "T003", "T004", "T005"], "Should choose longest path"
    print("  ✓ Critical path identifies longest branch")
    
    print("✅ T014 Critical Path: ALL TESTS PASSED\n")


def test_session_assignment():
    """Test T015: Session assignment."""
    print("Testing T015: Session Assignment...")
    
    # Test 1: Invalid num_sessions raises ValueError
    tasks = [TaskInfo(id="T001", name="A", dependencies=[])]
    engine = DAGEngine(tasks)
    try:
        engine.assign_sessions(0)
        assert False, "Should raise ValueError for num_sessions=0"
    except ValueError as e:
        assert "num_sessions must be >= 1" in str(e)
    print("  ✓ Validates num_sessions >= 1")
    
    # Test 2: Sequential tasks to session 0
    tasks = [
        TaskInfo(id="T001", name="A", dependencies=[], parallelizable=False),
        TaskInfo(id="T002", name="B", dependencies=["T001"], parallelizable=False),
    ]
    engine = DAGEngine(tasks)
    engine.assign_sessions(3)
    assert engine.get_task("T001").session == 0, "Sequential task should be session 0"
    assert engine.get_task("T002").session == 0, "Sequential task should be session 0"
    print("  ✓ Sequential tasks assigned to session 0")
    
    # Test 3: Round-robin distribution
    tasks = [
        TaskInfo(id="T001", name="Root", dependencies=[]),
        TaskInfo(id="T002", name="A", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T003", name="B", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T004", name="C", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T005", name="D", dependencies=["T001"], parallelizable=True),
    ]
    engine = DAGEngine(tasks)
    engine.assign_sessions(2)
    
    # T001 should be session 0 (only task in phase)
    assert engine.get_task("T001").session == 0
    
    # T002-T005 distributed round-robin: 0, 1, 0, 1
    assert engine.get_task("T002").session == 0
    assert engine.get_task("T003").session == 1
    assert engine.get_task("T004").session == 0
    assert engine.get_task("T005").session == 1
    print("  ✓ Parallel tasks distributed round-robin")
    
    # Test 4: No task assigned to multiple sessions
    tasks = [
        TaskInfo(id=f"T{i:03d}", name=f"Task {i}", dependencies=[], parallelizable=True)
        for i in range(1, 11)
    ]
    engine = DAGEngine(tasks)
    engine.assign_sessions(3)
    
    sessions = [engine.get_task(f"T{i:03d}").session for i in range(1, 11)]
    assert all(s is not None for s in sessions), "All tasks should have a session"
    assert len(sessions) == 10, "Should have 10 task assignments"
    print("  ✓ Each task assigned to exactly one session")
    
    # Test 5: get_session_tasks returns correct tasks
    tasks = [
        TaskInfo(id="T001", name="Root", dependencies=[]),
        TaskInfo(id="T002", name="A", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T003", name="B", dependencies=["T001"], parallelizable=True),
    ]
    engine = DAGEngine(tasks)
    engine.assign_sessions(2)
    
    session_0_tasks = engine.get_session_tasks(0)
    session_1_tasks = engine.get_session_tasks(1)
    
    assert len(session_0_tasks) == 2, "Session 0 should have 2 tasks"
    assert len(session_1_tasks) == 1, "Session 1 should have 1 task"
    print("  ✓ get_session_tasks returns correct tasks")
    
    print("✅ T015 Session Assignment: ALL TESTS PASSED\n")


def test_dag_serialization():
    """Test T016: DAG serialization."""
    print("Testing T016: DAG Serialization...")
    
    # Test 1: to_yaml generates valid YAML
    tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
    engine = DAGEngine(tasks)
    engine.assign_sessions(1)
    
    yaml_str = engine.to_yaml("001-test", 1)
    data = yaml.safe_load(yaml_str)
    assert isinstance(data, dict), "YAML should parse to dict"
    print("  ✓ Generates valid YAML")
    
    # Test 2: Includes required metadata fields
    assert data["version"] == "1.0", "Should have version field"
    assert data["spec_id"] == "001-test", "Should have spec_id field"
    assert "generated_at" in data, "Should have generated_at field"
    assert data["num_sessions"] == 1, "Should have num_sessions field"
    assert "phases" in data, "Should have phases field"
    print("  ✓ Includes all required metadata fields")
    
    # Test 3: Phase structure matches schema
    tasks = [
        TaskInfo(id="T001", name="Setup", dependencies=[]),
        TaskInfo(id="T002", name="Build", dependencies=["T001"]),
    ]
    engine = DAGEngine(tasks)
    engine.assign_sessions(1)
    
    yaml_str = engine.to_yaml("001-test", 1)
    data = yaml.safe_load(yaml_str)
    
    assert len(data["phases"]) == 2, "Should have 2 phases"
    assert data["phases"][0]["name"] == "phase-0", "Phase should have name"
    assert "tasks" in data["phases"][0], "Phase should have tasks"
    print("  ✓ Phase structure matches schema")
    
    # Test 4: Task fields match schema
    task = data["phases"][0]["tasks"][0]
    required_fields = ["id", "name", "description", "files", "dependencies", "session", "parallelizable", "story"]
    for field in required_fields:
        assert field in task, f"Task should have {field} field"
    print("  ✓ Task fields match schema")
    
    # Test 5: save() creates file
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "dag.yaml"
        engine.save(path, "001-test", 1)
        assert path.exists(), "save() should create file"
        
        # Verify content
        content = path.read_text()
        data = yaml.safe_load(content)
        assert data["spec_id"] == "001-test", "Saved file should have correct spec_id"
    print("  ✓ save() creates valid file")
    
    # Test 6: Round-trip preserves data
    tasks = [
        TaskInfo(id="T001", name="Root", dependencies=[]),
        TaskInfo(id="T002", name="A", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T003", name="B", dependencies=["T001"], parallelizable=True),
    ]
    original_engine = DAGEngine(tasks)
    original_engine.assign_sessions(2)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "dag.yaml"
        original_engine.save(path, "001-test", 2)
        
        loaded_engine = DAGEngine.load(path)
        
        assert loaded_engine.task_count == original_engine.task_count, "Task count should match"
        assert loaded_engine.phase_count == original_engine.phase_count, "Phase count should match"
        
        # Verify task details
        for task_id in ["T001", "T002", "T003"]:
            orig = original_engine.get_task(task_id)
            loaded = loaded_engine.get_task(task_id)
            assert loaded.id == orig.id, "Task ID should match"
            assert loaded.name == orig.name, "Task name should match"
            assert loaded.dependencies == orig.dependencies, "Dependencies should match"
            assert loaded.session == orig.session, "Session should match"
    print("  ✓ Round-trip preserves all data")
    
    print("✅ T016 DAG Serialization: ALL TESTS PASSED\n")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Validating T014, T015, T016 Implementation")
    print("=" * 60)
    print()
    
    try:
        test_phase_generation()
        test_critical_path()
        test_session_assignment()
        test_dag_serialization()
        
        print("=" * 60)
        print("🎉 ALL VALIDATION TESTS PASSED!")
        print("=" * 60)
        print()
        print("Summary:")
        print("  ✅ T014: Phase generation using topological_generations")
        print("  ✅ T014: Critical path identification")
        print("  ✅ T015: Session assignment with round-robin distribution")
        print("  ✅ T016: DAG serialization to/from YAML")
        print()
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print("❌ VALIDATION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ UNEXPECTED ERROR")
        print("=" * 60)
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
