"""
Integration tests for skf abort command.

Tests the complete abort workflow including:
- Confirmation prompting
- Worktree cleanup
- State deletion
- Summary reporting
"""

import subprocess
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from speckit_flow import app
from speckit_flow.state.manager import StateManager
from speckit_flow.state.models import (
    OrchestrationState,
    SessionState,
    SessionStatus,
    TaskState,
    TaskStatus,
)
from speckit_flow.worktree.manager import WorktreeManager


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def repo_with_orchestration(temp_repo):
    """Create a repo with active orchestration state and worktrees."""
    spec_id = "001-test-feature"
    
    # Create state file
    state = OrchestrationState(
        version="1.0",
        spec_id=spec_id,
        agent_type="copilot",
        num_sessions=2,
        base_branch="main",
        current_phase="phase-1",
        phases_completed=["phase-0"],
        sessions=[
            SessionState(
                session_id=0,
                status=SessionStatus.executing,
                worktree_path=str(temp_repo / f".worktrees-{spec_id}" / "session-0-task-a"),
                branch_name=f"impl-{spec_id}-session-0",
                current_task="T001",
                completed_tasks=[]
            ),
            SessionState(
                session_id=1,
                status=SessionStatus.executing,
                worktree_path=str(temp_repo / f".worktrees-{spec_id}" / "session-1-task-b"),
                branch_name=f"impl-{spec_id}-session-1",
                current_task="T002",
                completed_tasks=[]
            ),
        ],
        tasks={
            "T001": TaskState(status=TaskStatus.in_progress, session=0),
            "T002": TaskState(status=TaskStatus.in_progress, session=1),
        }
    )
    
    state_manager = StateManager(temp_repo)
    state_manager.save(state)
    
    # Create worktrees
    manager = WorktreeManager(temp_repo)
    worktree1 = manager.create(spec_id, 0, "task-a")
    worktree2 = manager.create(spec_id, 1, "task-b")
    
    # Add some files to worktrees to make them "dirty"
    (worktree1 / "test1.txt").write_text("Test content 1")
    (worktree2 / "test2.txt").write_text("Test content 2")
    
    return temp_repo, spec_id, state_manager, manager


class TestAbortCommand:
    """Tests for skf abort command."""
    
    def test_abort_with_no_orchestration(self, runner, temp_repo):
        """Abort command handles case where no orchestration exists."""
        result = runner.invoke(app, ["abort"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "No active orchestration or worktrees found" in result.output
        assert "Nothing to clean up" in result.output
    
    def test_abort_prompts_for_confirmation(self, runner, repo_with_orchestration):
        """Abort command prompts for confirmation by default."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        # Simulate user saying "no" to confirmation
        result = runner.invoke(app, ["abort"], input="n\n", cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "Continue with cleanup?" in result.output
        assert "Cleanup cancelled" in result.output
        
        # Verify nothing was deleted
        assert state_manager.exists()
        worktrees = manager.get_spec_worktrees(spec_id)
        assert len(worktrees) == 2
    
    def test_abort_force_skips_confirmation(self, runner, repo_with_orchestration):
        """Abort command with --force skips confirmation."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "Continue with cleanup?" not in result.output
        assert "Cleanup completed successfully" in result.output
        
        # Verify everything was deleted
        assert not state_manager.exists()
        worktrees = manager.get_spec_worktrees(spec_id)
        assert len(worktrees) == 0
    
    def test_abort_removes_worktrees(self, runner, repo_with_orchestration):
        """Abort command removes all session worktrees."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        # Get worktree paths before cleanup
        worktrees_before = manager.get_spec_worktrees(spec_id)
        assert len(worktrees_before) == 2
        
        worktree_paths = [wt.path for wt in worktrees_before]
        
        # Run abort with force
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "Worktrees removed: 2" in result.output
        
        # Verify worktrees are gone
        worktrees_after = manager.get_spec_worktrees(spec_id)
        assert len(worktrees_after) == 0
        
        # Verify worktree directories are gone
        for path in worktree_paths:
            assert not path.exists()
        
        # Verify worktrees base directory is gone
        worktrees_base = temp_repo / f".worktrees-{spec_id}"
        assert not worktrees_base.exists()
    
    def test_abort_deletes_state_file(self, runner, repo_with_orchestration):
        """Abort command deletes orchestration state."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        # Verify state exists before
        assert state_manager.exists()
        
        # Run abort with force
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "State file deleted" in result.output
        
        # Verify state is gone
        assert not state_manager.exists()
        assert not state_manager.state_path.exists()
        
        # Verify lock file is also gone
        assert not state_manager.lock_path.exists()
    
    def test_abort_displays_cleanup_summary(self, runner, repo_with_orchestration):
        """Abort command displays detailed cleanup summary."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "Cleanup Summary" in result.output
        assert "Worktrees removed: 2" in result.output
        assert "State file deleted" in result.output
        assert "Cleanup completed successfully" in result.output
    
    def test_abort_reports_cleanup_actions(self, runner, repo_with_orchestration):
        """Abort command reports what will be cleaned up before confirmation."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        # Run without force to see the prompt
        result = runner.invoke(app, ["abort"], input="n\n", cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "This will delete the following:" in result.output
        assert "Orchestration state file" in result.output
        assert "worktree(s):" in result.output
        assert "All uncommitted changes in worktrees will be lost!" in result.output
    
    def test_abort_preserves_branches(self, runner, repo_with_orchestration):
        """Abort command removes worktrees but preserves branches."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        # Get branch names before cleanup
        state = state_manager.load()
        branch_names = [session.branch_name for session in state.sessions]
        
        # Run abort with force
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        
        # Verify branches still exist
        for branch_name in branch_names:
            # Check if branch exists in git
            branch_result = subprocess.run(
                ["git", "rev-parse", "--verify", branch_name],
                cwd=temp_repo,
                capture_output=True,
            )
            assert branch_result.returncode == 0, f"Branch {branch_name} should still exist"
        
        # Verify output mentions preserved branches
        assert "Session branches preserved" in result.output
    
    def test_abort_handles_missing_state_with_worktrees(self, runner, temp_repo):
        """Abort command handles case where state is missing but worktrees exist."""
        spec_id = "001-orphan"
        
        # Create worktrees without state
        manager = WorktreeManager(temp_repo)
        manager.create(spec_id, 0, "orphan-task")
        
        # Create feature context to determine spec_id
        specs_dir = temp_repo / "specs" / spec_id
        specs_dir.mkdir(parents=True, exist_ok=True)
        
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "Worktrees removed:" in result.output
    
    def test_abort_handles_corrupted_state(self, runner, repo_with_orchestration):
        """Abort command handles corrupted state file gracefully."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        # Corrupt the state file
        state_manager.state_path.write_text("invalid: yaml: content: [[[")
        
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        # Should still succeed in cleanup
        assert result.exit_code == 0
        assert "Cleanup completed successfully" in result.output
        
        # Verify cleanup happened
        assert not state_manager.exists()
        worktrees = manager.get_spec_worktrees(spec_id)
        assert len(worktrees) == 0
    
    def test_abort_mentions_checkpoints_if_present(self, runner, repo_with_orchestration):
        """Abort command mentions checkpoints if they exist."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        # Create checkpoint directory with files
        checkpoints_dir = temp_repo / ".speckit" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        (checkpoints_dir / "2025-11-29T10-00-00.yaml").write_text("checkpoint: data")
        (checkpoints_dir / "2025-11-29T11-00-00.yaml").write_text("checkpoint: data")
        
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "Checkpoints found: 2" in result.output
        assert "delete the directory manually" in result.output
    
    def test_abort_provides_next_steps(self, runner, repo_with_orchestration):
        """Abort command provides helpful next steps."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "Next Steps" in result.output
        assert "Start a new orchestration: skf run" in result.output
        assert "Session branches preserved" in result.output
        assert f"impl-{spec_id}-session-*" in result.output


class TestAbortEdgeCases:
    """Edge case tests for abort command."""
    
    def test_abort_outside_git_repo(self, runner, temp_dir):
        """Abort command errors outside git repository."""
        result = runner.invoke(app, ["abort"], cwd=temp_dir)
        
        assert result.exit_code == 1
        assert "Not in a git repository" in result.output
    
    def test_abort_with_only_state_no_worktrees(self, runner, temp_repo):
        """Abort command handles state file without worktrees."""
        spec_id = "001-no-worktrees"
        
        # Create state file only
        state = OrchestrationState(
            version="1.0",
            spec_id=spec_id,
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            current_phase="phase-0",
            phases_completed=[],
            sessions=[],
            tasks={}
        )
        
        state_manager = StateManager(temp_repo)
        state_manager.save(state)
        
        result = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        
        assert result.exit_code == 0
        assert "State file deleted" in result.output
        assert not state_manager.exists()
    
    def test_abort_idempotent(self, runner, repo_with_orchestration):
        """Running abort multiple times is safe."""
        temp_repo, spec_id, state_manager, manager = repo_with_orchestration
        
        # Run abort first time
        result1 = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        assert result1.exit_code == 0
        
        # Run abort second time
        result2 = runner.invoke(app, ["abort", "--force"], cwd=temp_repo)
        assert result2.exit_code == 0
        assert "No active orchestration or worktrees found" in result2.output
