#!/usr/bin/env python3
"""
Validation script for T013: DAG Engine Core

This script validates that the DAG engine implementation meets all
acceptance criteria from tasks.md.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.models import TaskInfo
from speckit_flow.exceptions import CyclicDependencyError
from speckit_flow.orchestration.dag_engine import DAGEngine


def test_ac1_creates_valid_digraph():
    """AC1: Creates valid networkx DiGraph from task list."""
    print("Testing AC1: Creates valid networkx DiGraph from task list...")
    
    tasks = [
        TaskInfo(id="T001", name="Task 1", dependencies=[]),
        TaskInfo(id="T002", name="Task 2", dependencies=["T001"]),
        TaskInfo(id="T003", name="Task 3", dependencies=["T001"]),
    ]
    
    engine = DAGEngine(tasks)
    graph = engine.build_graph()
    
    # Verify it's a DiGraph
    assert hasattr(graph, 'nodes'), "Graph should have nodes"
    assert hasattr(graph, 'edges'), "Graph should have edges"
    assert len(graph.nodes) == 3, f"Expected 3 nodes, got {len(graph.nodes)}"
    assert graph.has_edge("T001", "T002"), "Missing edge T001 -> T002"
    assert graph.has_edge("T001", "T003"), "Missing edge T001 -> T003"
    
    print("  ✓ Creates valid networkx DiGraph")
    return True


def test_ac2_node_attributes():
    """AC2: Node attributes contain full TaskInfo data."""
    print("Testing AC2: Node attributes contain full TaskInfo data...")
    
    task = TaskInfo(
        id="T001",
        name="Test Task",
        description="Test description",
        dependencies=[],
        parallelizable=True,
        story="US1",
        files=["test.py"],
    )
    
    engine = DAGEngine([task])
    graph = engine.build_graph()
    
    stored_task = graph.nodes["T001"]["task"]
    assert stored_task.id == "T001", "Task ID mismatch"
    assert stored_task.name == "Test Task", "Task name mismatch"
    assert stored_task.description == "Test description", "Description mismatch"
    assert stored_task.parallelizable is True, "Parallelizable mismatch"
    assert stored_task.story == "US1", "Story mismatch"
    assert stored_task.files == ["test.py"], "Files mismatch"
    
    print("  ✓ Node attributes contain full TaskInfo data")
    return True


def test_ac3_detects_circular_dependencies():
    """AC3: Detects and reports circular dependencies."""
    print("Testing AC3: Detects and reports circular dependencies...")
    
    # Test direct cycle
    tasks = [
        TaskInfo(id="T001", name="A", dependencies=["T002"]),
        TaskInfo(id="T002", name="B", dependencies=["T001"]),
    ]
    
    engine = DAGEngine(tasks)
    
    try:
        engine.build_graph()
        print("  ✗ Failed to detect circular dependency")
        return False
    except CyclicDependencyError as e:
        assert "T001" in e.cycle, "Cycle should contain T001"
        assert "T002" in e.cycle, "Cycle should contain T002"
        assert "Circular dependency detected" in str(e), "Error message should be clear"
        print(f"  ✓ Detects circular dependencies: {e}")
    
    # Test indirect cycle
    tasks2 = [
        TaskInfo(id="T001", name="A", dependencies=["T003"]),
        TaskInfo(id="T002", name="B", dependencies=["T001"]),
        TaskInfo(id="T003", name="C", dependencies=["T002"]),
    ]
    
    engine2 = DAGEngine(tasks2)
    
    try:
        engine2.build_graph()
        print("  ✗ Failed to detect indirect circular dependency")
        return False
    except CyclicDependencyError as e:
        print(f"  ✓ Detects indirect cycles: {' → '.join(e.cycle)}")
    
    return True


def test_ac4_handles_empty_list():
    """AC4: Handles empty task list gracefully."""
    print("Testing AC4: Handles empty task list gracefully...")
    
    engine = DAGEngine([])
    graph = engine.build_graph()
    
    assert len(graph.nodes) == 0, "Empty task list should produce empty graph"
    assert len(graph.edges) == 0, "Empty task list should have no edges"
    assert engine.validate() is True, "Empty graph should be valid"
    
    print("  ✓ Handles empty task list gracefully")
    return True


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("T013 Acceptance Criteria Validation")
    print("=" * 60)
    print()
    
    tests = [
        test_ac1_creates_valid_digraph,
        test_ac2_node_attributes,
        test_ac3_detects_circular_dependencies,
        test_ac4_handles_empty_list,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"  ✗ Test failed with exception: {e}")
            results.append(False)
            print()
    
    print("=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ All acceptance criteria verified!")
        return 0
    else:
        print("\n❌ Some acceptance criteria failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
