"""
Example usage of DAGEngine for task dependency analysis.

This script demonstrates how to use the DAGEngine class to build
and validate task dependency graphs.
"""

from speckit_core.models import TaskInfo
from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.exceptions import CyclicDependencyError


def example_basic_usage():
    """Basic DAG construction and validation."""
    print("=" * 60)
    print("Example 1: Basic DAG Construction")
    print("=" * 60)
    
    # Define tasks with dependencies
    tasks = [
        TaskInfo(id="T001", name="Setup database", dependencies=[]),
        TaskInfo(id="T002", name="Create tables", dependencies=["T001"]),
        TaskInfo(id="T003", name="Seed data", dependencies=["T002"]),
    ]
    
    # Create engine and build graph
    engine = DAGEngine(tasks)
    graph = engine.build_graph()
    
    print(f"Task count: {engine.task_count}")
    print(f"Graph nodes: {list(graph.nodes)}")
    print(f"Graph edges: {list(graph.edges)}")
    print(f"Valid DAG: {engine.validate()}")
    print()


def example_parallel_tasks():
    """Tasks with parallel execution potential."""
    print("=" * 60)
    print("Example 2: Parallel Task Structure")
    print("=" * 60)
    
    tasks = [
        TaskInfo(id="T001", name="Setup", dependencies=[]),
        TaskInfo(id="T002", name="Feature A", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T003", name="Feature B", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T004", name="Integration", dependencies=["T002", "T003"]),
    ]
    
    engine = DAGEngine(tasks)
    graph = engine.build_graph()
    
    print(f"Task count: {engine.task_count}")
    print(f"\nTask breakdown:")
    for task in tasks:
        deps_str = ", ".join(task.dependencies) if task.dependencies else "None"
        parallel = "[P]" if task.parallelizable else ""
        print(f"  {task.id} {parallel}: {task.name} (deps: {deps_str})")
    
    print(f"\nGraph structure:")
    print(f"  Phase 0: T001 (no dependencies)")
    print(f"  Phase 1: T002, T003 (parallel, depend on T001)")
    print(f"  Phase 2: T004 (depends on T002 and T003)")
    print()


def example_cycle_detection():
    """Detecting circular dependencies."""
    print("=" * 60)
    print("Example 3: Cycle Detection")
    print("=" * 60)
    
    # Create tasks with circular dependency
    tasks = [
        TaskInfo(id="T001", name="Task A", dependencies=["T003"]),
        TaskInfo(id="T002", name="Task B", dependencies=["T001"]),
        TaskInfo(id="T003", name="Task C", dependencies=["T002"]),
    ]
    
    engine = DAGEngine(tasks)
    
    print("Attempting to build graph with cycle: T001 → T003 → T002 → T001")
    try:
        engine.build_graph()
        print("ERROR: Cycle not detected!")
    except CyclicDependencyError as e:
        print(f"✓ Cycle detected: {' → '.join(e.cycle)}")
        print(f"  Error message: {e}")
    print()


def example_accessing_task_data():
    """Accessing task information from the graph."""
    print("=" * 60)
    print("Example 4: Accessing Task Data")
    print("=" * 60)
    
    tasks = [
        TaskInfo(
            id="T001",
            name="Implement User model",
            description="Create User entity with validation",
            dependencies=[],
            parallelizable=False,
            files=["src/models/User.ts", "src/models/__tests__/User.test.ts"],
            story="US1",
        ),
        TaskInfo(
            id="T002",
            name="Add User service",
            description="Create UserService for business logic",
            dependencies=["T001"],
            files=["src/services/UserService.ts"],
            story="US1",
        ),
    ]
    
    engine = DAGEngine(tasks)
    graph = engine.build_graph()
    
    print("Task details from graph nodes:")
    for node_id in graph.nodes:
        task = graph.nodes[node_id]["task"]
        print(f"\n  {task.id}: {task.name}")
        print(f"    Description: {task.description}")
        print(f"    Files: {', '.join(task.files)}")
        print(f"    Story: {task.story}")
        print(f"    Dependencies: {', '.join(task.dependencies) or 'None'}")
    
    # Can also use get_task() method
    print(f"\nDirect access via get_task('T002'):")
    task2 = engine.get_task("T002")
    print(f"  Name: {task2.name}")
    print(f"  Depends on: {task2.dependencies}")
    print()


def example_empty_graph():
    """Handling edge case of empty task list."""
    print("=" * 60)
    print("Example 5: Empty Task List")
    print("=" * 60)
    
    engine = DAGEngine([])
    graph = engine.build_graph()
    
    print(f"Task count: {engine.task_count}")
    print(f"Graph nodes: {list(graph.nodes)}")
    print(f"Graph edges: {list(graph.edges)}")
    print(f"Valid DAG: {engine.validate()}")
    print()


if __name__ == "__main__":
    example_basic_usage()
    example_parallel_tasks()
    example_cycle_detection()
    example_accessing_task_data()
    example_empty_graph()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
