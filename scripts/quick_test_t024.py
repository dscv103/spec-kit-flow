#!/usr/bin/env python3
"""Quick test for T024 - verify --sessions flag and visualization."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.models import TaskInfo
from speckit_flow.orchestration.dag_engine import DAGEngine

def test_sessions_assignment():
    """Test that --sessions assigns tasks correctly."""
    print("\n=== Testing session assignment ===")
    
    # Create test tasks
    tasks = [
        TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
        TaskInfo(id="T002", name="Feature A", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T003", name="Feature B", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T004", name="Feature C", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T005", name="Feature D", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T006", name="Feature E", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T007", name="Integration", dependencies=["T002", "T003", "T004", "T005", "T006"], parallelizable=False),
    ]
    
    # Create engine and assign to 5 sessions
    engine = DAGEngine(tasks)
    engine.validate()
    engine.assign_sessions(5)
    
    # Check assignments
    print(f"\nTask assignments with 5 sessions:")
    sessions_used = set()
    for task in tasks:
        print(f"  {task.id}: Session {task.session} {'[P]' if task.parallelizable else ''}")
        sessions_used.add(task.session)
    
    print(f"\nSessions used: {sorted(sessions_used)}")
    
    # Verify parallel tasks are distributed
    parallel_tasks = [t for t in tasks if t.parallelizable]
    parallel_sessions = set(t.session for t in parallel_tasks)
    
    print(f"Parallel tasks distributed across: {sorted(parallel_sessions)}")
    
    # Check that we use multiple sessions for parallel tasks
    if len(parallel_sessions) > 1:
        print("✓ Parallel tasks distributed across multiple sessions")
        return True
    else:
        print("✗ All parallel tasks in same session")
        return False


def test_yaml_includes_sessions():
    """Test that to_yaml includes num_sessions field."""
    print("\n=== Testing YAML output ===")
    
    tasks = [
        TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
        TaskInfo(id="T002", name="Task A", dependencies=["T001"], parallelizable=True),
    ]
    
    engine = DAGEngine(tasks)
    engine.validate()
    engine.assign_sessions(5)
    
    yaml_output = engine.to_yaml("001-test", 5)
    
    print("\nGenerated YAML snippet:")
    for line in yaml_output.split('\n')[:10]:
        print(f"  {line}")
    
    if "num_sessions: 5" in yaml_output:
        print("\n✓ YAML includes num_sessions: 5")
        return True
    else:
        print("\n✗ YAML missing num_sessions field")
        return False


def test_visualization_mock():
    """Test that visualization would show sessions."""
    print("\n=== Testing visualization format ===")
    
    tasks = [
        TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
        TaskInfo(id="T002", name="Task A", dependencies=["T001"], parallelizable=True),
        TaskInfo(id="T003", name="Task B", dependencies=["T001"], parallelizable=True),
    ]
    
    engine = DAGEngine(tasks)
    engine.validate()
    engine.assign_sessions(2)
    
    print("\nTask information for visualization:")
    phases = engine.get_phases()
    for phase_idx, phase_task_ids in enumerate(phases):
        print(f"\n  Phase {phase_idx}:")
        for task_id in phase_task_ids:
            task = engine.get_task(task_id)
            parts = [task_id]
            if task.parallelizable:
                parts.append("[P]")
            parts.append(task.name)
            if task.session is not None:
                parts.append(f"[Session {task.session}]")
            if task.dependencies:
                parts.append(f"(deps: {', '.join(task.dependencies)})")
            print(f"    {' '.join(parts)}")
    
    # Check that tasks have session info
    all_have_sessions = all(t.session is not None for t in tasks)
    
    if all_have_sessions:
        print("\n✓ All tasks have session assignments")
        return True
    else:
        print("\n✗ Some tasks missing session assignments")
        return False


def main():
    """Run all quick tests."""
    print("\n" + "="*60)
    print("T024 Quick Test: --sessions option and visualization")
    print("="*60)
    
    results = []
    results.append(test_sessions_assignment())
    results.append(test_yaml_includes_sessions())
    results.append(test_visualization_mock())
    
    print("\n" + "="*60)
    passed = sum(results)
    print(f"Results: {passed}/{len(results)} tests passed")
    print("="*60)
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
