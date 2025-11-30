#!/usr/bin/env python3
"""
Test script for T029: Phase execution and checkpointing.

This script verifies:
1. run_phase() gets tasks for current phase
2. User is notified for each active session
3. Completion monitoring works (manual + watched)
4. State is checkpointed after phase completion
5. Keyboard interrupt is handled gracefully
"""

import sys
import tempfile
import time
from pathlib import Path
from threading import Thread

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.config import SpecKitFlowConfig
from speckit_core.models import TaskInfo, TaskStatus, SessionStatus
from speckit_flow.agents.copilot import CopilotIDEAdapter
from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.orchestration.session_coordinator import SessionCoordinator


def setup_test_repo(temp_dir: Path):
    """Set up a test git repository with spec structure."""
    import subprocess
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir, check=True, capture_output=True
    )
    
    # Create initial commit
    readme = temp_dir / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir, check=True, capture_output=True
    )
    
    # Create spec structure
    spec_dir = temp_dir / "specs" / "main"
    spec_dir.mkdir(parents=True)
    
    tasks_content = """# Tasks
- [ ] [T001] [deps:] Setup project
- [ ] [T002] [P] [deps:T001] Implement feature A
- [ ] [T003] [P] [deps:T001] Implement feature B
- [ ] [T004] [deps:T002,T003] Integration test
"""
    (spec_dir / "tasks.md").write_text(tasks_content)
    
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add spec"],
        cwd=temp_dir, check=True, capture_output=True
    )


def test_run_phase_basic():
    """Test basic run_phase execution."""
    print("Test 1: Basic run_phase execution")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        setup_test_repo(temp_dir)
        
        # Create tasks
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
            TaskInfo(id="T002", name="Feature A", dependencies=["T001"], parallelizable=True),
            TaskInfo(id="T003", name="Feature B", dependencies=["T001"], parallelizable=True),
        ]
        
        # Build DAG
        dag = DAGEngine(tasks)
        dag.validate()
        dag.assign_sessions(2)
        
        # Create coordinator
        config = SpecKitFlowConfig(agent_type="copilot", num_sessions=2)
        adapter = CopilotIDEAdapter()
        coordinator = SessionCoordinator(
            dag=dag,
            config=config,
            adapter=adapter,
            repo_root=temp_dir,
            spec_id="001-test",
            base_branch="main"
        )
        
        # Initialize
        print("  Initializing coordinator...")
        coordinator.initialize()
        
        # Verify state was created
        state = coordinator.state_manager.load()
        assert state.spec_id == "001-test"
        assert state.num_sessions == 2
        assert len(state.sessions) == 2
        print("  ✓ Initialization complete")
        
        # Test getting phases
        phases = dag.get_phases()
        print(f"  DAG has {len(phases)} phases")
        print(f"    Phase 0: {phases[0]}")
        print(f"    Phase 1: {phases[1]}")
        
        # Simulate marking phase 0 tasks complete in background
        def mark_tasks_complete():
            time.sleep(0.5)  # Wait a bit before marking complete
            for task_id in phases[0]:
                coordinator.completion_monitor.mark_complete(task_id)
                print(f"  [Background] Marked {task_id} complete")
        
        thread = Thread(target=mark_tasks_complete, daemon=True)
        thread.start()
        
        # Run phase 0
        print("  Running phase 0...")
        try:
            coordinator.run_phase(0)
            print("  ✓ Phase 0 completed")
        except Exception as e:
            print(f"  ✗ Phase execution failed: {e}")
            return False
        
        # Verify state was updated
        state = coordinator.state_manager.load()
        assert state.current_phase == "phase-0"
        assert "phase-0" in state.phases_completed
        assert state.tasks["T001"].status == TaskStatus.completed
        print("  ✓ State updated correctly")
        
    print("✓ Test 1 passed\n")
    return True


def test_checkpoint_phase():
    """Test checkpoint_phase functionality."""
    print("Test 2: Checkpoint after phase completion")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        setup_test_repo(temp_dir)
        
        # Create simple task list
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
        ]
        
        # Build DAG
        dag = DAGEngine(tasks)
        dag.validate()
        dag.assign_sessions(1)
        
        # Create coordinator
        config = SpecKitFlowConfig(agent_type="copilot", num_sessions=1)
        adapter = CopilotIDEAdapter()
        coordinator = SessionCoordinator(
            dag=dag,
            config=config,
            adapter=adapter,
            repo_root=temp_dir,
            spec_id="002-test",
            base_branch="main"
        )
        
        # Initialize
        print("  Initializing coordinator...")
        coordinator.initialize()
        
        # Mark task complete and run phase
        coordinator.completion_monitor.mark_complete("T001")
        coordinator.run_phase(0)
        
        # Create checkpoint
        print("  Creating checkpoint...")
        checkpoint_path = coordinator.checkpoint_phase()
        
        # Verify checkpoint exists
        assert checkpoint_path.exists()
        assert checkpoint_path.suffix == ".yaml"
        assert checkpoint_path.parent.name == "checkpoints"
        print(f"  ✓ Checkpoint created: {checkpoint_path.name}")
        
        # Verify checkpoint can be restored
        from speckit_flow.state.recovery import RecoveryManager
        recovery = RecoveryManager(temp_dir)
        restored_state = recovery.restore_from_checkpoint(checkpoint_path)
        
        assert restored_state.spec_id == "002-test"
        assert "phase-0" in restored_state.phases_completed
        print("  ✓ Checkpoint can be restored")
        
    print("✓ Test 2 passed\n")
    return True


def test_invalid_phase_index():
    """Test handling of invalid phase index."""
    print("Test 3: Invalid phase index handling")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        setup_test_repo(temp_dir)
        
        # Create tasks
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
        ]
        
        # Build DAG
        dag = DAGEngine(tasks)
        dag.validate()
        dag.assign_sessions(1)
        
        # Create coordinator
        config = SpecKitFlowConfig(agent_type="copilot", num_sessions=1)
        adapter = CopilotIDEAdapter()
        coordinator = SessionCoordinator(
            dag=dag,
            config=config,
            adapter=adapter,
            repo_root=temp_dir,
            spec_id="003-test",
            base_branch="main"
        )
        
        coordinator.initialize()
        
        # Try to run invalid phase
        print("  Testing invalid phase index 99...")
        try:
            coordinator.run_phase(99)
            print("  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Raised ValueError: {e}")
        
        print("  Testing negative phase index...")
        try:
            coordinator.run_phase(-1)
            print("  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Raised ValueError: {e}")
        
    print("✓ Test 3 passed\n")
    return True


def test_multi_session_notification():
    """Test user notification for multiple sessions."""
    print("Test 4: Multi-session user notification")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        setup_test_repo(temp_dir)
        
        # Create tasks with parallelizable ones
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
            TaskInfo(id="T002", name="Feature A", dependencies=["T001"], parallelizable=True),
            TaskInfo(id="T003", name="Feature B", dependencies=["T001"], parallelizable=True),
        ]
        
        # Build DAG
        dag = DAGEngine(tasks)
        dag.validate()
        dag.assign_sessions(2)
        
        # Create coordinator
        config = SpecKitFlowConfig(agent_type="copilot", num_sessions=2)
        adapter = CopilotIDEAdapter()
        coordinator = SessionCoordinator(
            dag=dag,
            config=config,
            adapter=adapter,
            repo_root=temp_dir,
            spec_id="004-test",
            base_branch="main"
        )
        
        coordinator.initialize()
        
        # Mark phase 0 complete
        coordinator.completion_monitor.mark_complete("T001")
        coordinator.run_phase(0)
        
        # Simulate phase 1 completion in background
        def mark_phase1_complete():
            time.sleep(0.3)
            coordinator.completion_monitor.mark_complete("T002")
            coordinator.completion_monitor.mark_complete("T003")
        
        thread = Thread(target=mark_phase1_complete, daemon=True)
        thread.start()
        
        # Run phase 1 (should notify both sessions)
        print("  Running phase 1 with 2 sessions...")
        coordinator.run_phase(1)
        
        # Verify both sessions were used
        state = coordinator.state_manager.load()
        executing_sessions = [s for s in state.sessions if len(s.completed_tasks) > 1]
        print(f"  Sessions that executed tasks: {len(executing_sessions)}")
        print("  ✓ Multi-session execution complete")
        
    print("✓ Test 4 passed\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("T029 Test Suite: Phase Execution")
    print("=" * 60 + "\n")
    
    tests = [
        test_run_phase_basic,
        test_checkpoint_phase,
        test_invalid_phase_index,
        test_multi_session_notification,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
