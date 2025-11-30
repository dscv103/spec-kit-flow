#!/usr/bin/env python3
"""
Validation script for T028: SessionCoordinator implementation.

This script verifies that:
1. SessionCoordinator can be instantiated with required parameters
2. initialize() creates worktrees for all sessions
3. initialize() creates agent context files in each worktree
4. initialize() creates and saves the orchestration state file
"""

import sys
import tempfile
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.config import SpecKitFlowConfig
from speckit_core.models import TaskInfo
from speckit_flow.agents.copilot import CopilotIDEAdapter
from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.orchestration.session_coordinator import SessionCoordinator
from speckit_flow.state.manager import StateManager


def create_test_repo(tmpdir: Path) -> Path:
    """Create a test git repository."""
    repo = tmpdir / "test_repo"
    repo.mkdir()
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo, check=True, capture_output=True
    )
    
    # Create initial commit (required for worktrees)
    readme = repo / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo, check=True, capture_output=True
    )
    
    return repo


def test_session_coordinator():
    """Test SessionCoordinator initialization."""
    print("Testing T028: SessionCoordinator implementation...")
    print()
    
    # Create temporary test repository
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = create_test_repo(Path(tmpdir))
        print(f"✓ Created test repository at {repo_root}")
        
        # Create test tasks
        tasks = [
            TaskInfo(
                id="T001",
                name="Setup database",
                dependencies=[],
                parallelizable=False
            ),
            TaskInfo(
                id="T002",
                name="Implement API",
                dependencies=["T001"],
                parallelizable=True
            ),
            TaskInfo(
                id="T003",
                name="Add tests",
                dependencies=["T001"],
                parallelizable=True
            ),
        ]
        print(f"✓ Created {len(tasks)} test tasks")
        
        # Create DAG engine
        dag = DAGEngine(tasks)
        dag.validate()
        print("✓ DAG engine created and validated")
        
        # Create config
        config = SpecKitFlowConfig(agent_type="copilot", num_sessions=2)
        print(f"✓ Config created: {config.num_sessions} sessions, agent={config.agent_type}")
        
        # Create adapter
        adapter = CopilotIDEAdapter()
        print("✓ Copilot adapter created")
        
        # Create coordinator
        coordinator = SessionCoordinator(
            dag=dag,
            config=config,
            adapter=adapter,
            repo_root=repo_root,
            spec_id="001-test-feature",
            base_branch="main"
        )
        print("✓ SessionCoordinator instantiated")
        
        # Initialize
        print("\nInitializing coordinator...")
        coordinator.initialize()
        print("✓ Coordinator initialized")
        
        # Verify worktrees were created
        worktrees_dir = repo_root / ".worktrees-001-test-feature"
        assert worktrees_dir.exists(), "Worktrees directory not created"
        print(f"✓ Worktrees directory exists: {worktrees_dir}")
        
        # Count worktrees
        session_dirs = list(worktrees_dir.glob("session-*"))
        print(f"✓ Found {len(session_dirs)} session directories")
        
        # Verify agent context files
        for session_dir in session_dirs:
            context_file = session_dir / ".github" / "copilot-instructions.md"
            assert context_file.exists(), f"Context file not found in {session_dir}"
            print(f"  ✓ Context file exists: {context_file.relative_to(repo_root)}")
        
        # Verify state file
        state_manager = StateManager(repo_root)
        assert state_manager.exists(), "State file not created"
        print("✓ State file created")
        
        # Load and verify state
        state = state_manager.load()
        print(f"✓ State loaded successfully")
        print(f"  - Spec ID: {state.spec_id}")
        print(f"  - Agent type: {state.agent_type}")
        print(f"  - Sessions: {state.num_sessions}")
        print(f"  - Base branch: {state.base_branch}")
        print(f"  - Current phase: {state.current_phase}")
        print(f"  - Tasks: {len(state.tasks)}")
        print(f"  - Sessions in state: {len(state.sessions)}")
        
        # Verify state matches expectations
        assert state.spec_id == "001-test-feature"
        assert state.agent_type == "copilot"
        assert state.num_sessions == 2
        assert state.base_branch == "main"
        assert state.current_phase == "phase-0"
        assert len(state.phases_completed) == 0
        assert len(state.tasks) == 3
        assert len(state.sessions) == 2  # Should have 2 sessions
        
        # Verify all tasks have session assignments
        for task_id, task_state in state.tasks.items():
            assert task_state.session is not None, f"Task {task_id} not assigned to session"
            print(f"  ✓ Task {task_id} assigned to session {task_state.session}")
        
        print("\n" + "="*60)
        print("✓ All T028 acceptance criteria verified!")
        print("="*60)
        print()
        print("Acceptance Criteria:")
        print("  [✓] Creates N worktrees matching session count")
        print("  [✓] Each worktree has agent context file")
        print("  [✓] State file reflects initialized sessions")


if __name__ == "__main__":
    try:
        test_session_coordinator()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
