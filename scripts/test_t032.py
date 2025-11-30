#!/usr/bin/env python3
"""
Quick test script for T032: Sequential merge strategy.

Verifies that the MergeOrchestrator.merge_sequential() method works correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_flow.worktree.merger import MergeOrchestrator, MergeResult
from unittest.mock import Mock, patch
import subprocess


def test_merge_result_dataclass():
    """Test MergeResult dataclass creation."""
    print("Testing MergeResult dataclass...")
    
    # Successful merge
    result = MergeResult(
        success=True,
        integration_branch="impl-001-integrated",
        merged_sessions=[0, 1, 2],
    )
    
    assert result.success is True
    assert result.integration_branch == "impl-001-integrated"
    assert result.merged_sessions == [0, 1, 2]
    assert result.conflict_session is None
    assert result.conflicting_files == []
    assert result.error_message is None
    
    # Failed merge
    result = MergeResult(
        success=False,
        integration_branch="impl-001-integrated",
        merged_sessions=[0],
        conflict_session=1,
        conflicting_files=["src/main.py"],
        error_message="Conflict in session 1",
    )
    
    assert result.success is False
    assert result.conflict_session == 1
    assert result.conflicting_files == ["src/main.py"]
    
    print("✓ MergeResult dataclass works correctly")


def test_merge_sequential_successful():
    """Test successful merge of all sessions."""
    print("\nTesting successful merge_sequential()...")
    
    orchestrator = MergeOrchestrator("001-test", Path("/tmp/test-repo"))
    
    with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
         patch.object(orchestrator, "_find_session_branches", return_value={
             0: "impl-001-test-session-0",
             1: "impl-001-test-session-1",
             2: "impl-001-test-session-2",
         }), \
         patch("subprocess.run") as mock_run:
        
        # Mock git commands
        def run_side_effect(cmd, **kwargs):
            if cmd[1] == "rev-parse":
                # Integration branch doesn't exist yet
                return Mock(returncode=1, stdout="", stderr="")
            elif cmd[1] == "checkout" and "-b" in cmd:
                # Create integration branch
                return Mock(returncode=0, stdout="", stderr="")
            elif cmd[1] == "merge":
                # All merges succeed
                return Mock(returncode=0, stdout="", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = run_side_effect
        
        result = orchestrator.merge_sequential()
        
        assert result.success is True
        assert result.integration_branch == "impl-001-test-integrated"
        assert result.merged_sessions == [0, 1, 2]
        assert result.conflict_session is None
        
        print("✓ merge_sequential() succeeds for non-conflicting branches")


def test_merge_sequential_with_conflict():
    """Test merge with conflict handling."""
    print("\nTesting merge_sequential() with conflict...")
    
    orchestrator = MergeOrchestrator("001-test", Path("/tmp/test-repo"))
    
    with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
         patch.object(orchestrator, "_find_session_branches", return_value={
             0: "impl-001-test-session-0",
             1: "impl-001-test-session-1",
             2: "impl-001-test-session-2",
         }), \
         patch.object(orchestrator, "_get_conflicting_files", return_value=[
             "src/conflict.py",
         ]), \
         patch("subprocess.run") as mock_run:
        
        merge_call_count = 0
        
        def run_side_effect(cmd, **kwargs):
            nonlocal merge_call_count
            
            if cmd[1] == "rev-parse":
                return Mock(returncode=1, stdout="", stderr="")
            elif cmd[1] == "checkout" and "-b" in cmd:
                return Mock(returncode=0, stdout="", stderr="")
            elif cmd[1] == "merge" and "--no-ff" in cmd:
                # First merge succeeds, second fails
                merge_call_count += 1
                if merge_call_count == 1:
                    return Mock(returncode=0, stdout="", stderr="")
                else:
                    return Mock(returncode=1, stdout="", stderr="CONFLICT")
            elif cmd[1] == "merge" and "--abort" in cmd:
                return Mock(returncode=0, stdout="", stderr="")
            elif cmd[1] == "checkout":
                return Mock(returncode=0, stdout="", stderr="")
            elif cmd[1] == "branch" and "-D" in cmd:
                return Mock(returncode=0, stdout="", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = run_side_effect
        
        result = orchestrator.merge_sequential()
        
        assert result.success is False
        assert result.merged_sessions == [0]  # Only first session merged
        assert result.conflict_session == 1
        assert result.conflicting_files == ["src/conflict.py"]
        assert "Merge conflict occurred" in result.error_message
        
        print("✓ merge_sequential() handles conflicts and cleans up")


def test_get_conflicting_files():
    """Test _get_conflicting_files() method."""
    print("\nTesting _get_conflicting_files()...")
    
    orchestrator = MergeOrchestrator("001-test", Path("/tmp/test-repo"))
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="src/main.py\nREADME.md\n",
            stderr="",
        )
        
        result = orchestrator._get_conflicting_files()
        
        assert result == ["src/main.py", "README.md"]
        
        # Verify correct command
        cmd = mock_run.call_args[0][0]
        assert cmd == ["git", "diff", "--name-only", "--diff-filter=U"]
    
    print("✓ _get_conflicting_files() works correctly")


def test_merge_uses_no_ff():
    """Test that merge uses --no-ff flag."""
    print("\nTesting --no-ff flag usage...")
    
    orchestrator = MergeOrchestrator("001-test", Path("/tmp/test-repo"))
    
    with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
         patch.object(orchestrator, "_find_session_branches", return_value={
             0: "impl-001-test-session-0",
         }), \
         patch("subprocess.run") as mock_run:
        
        merge_commands = []
        
        def run_side_effect(cmd, **kwargs):
            if cmd[1] == "merge":
                merge_commands.append(cmd)
                return Mock(returncode=0, stdout="", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = run_side_effect
        
        orchestrator.merge_sequential()
        
        # Verify --no-ff was used
        assert len(merge_commands) == 1
        assert "--no-ff" in merge_commands[0]
    
    print("✓ merge_sequential() uses --no-ff to preserve history")


def main():
    """Run all tests."""
    print("=" * 60)
    print("T032 Verification: Sequential Merge Strategy")
    print("=" * 60)
    
    try:
        test_merge_result_dataclass()
        test_merge_sequential_successful()
        test_merge_sequential_with_conflict()
        test_get_conflicting_files()
        test_merge_uses_no_ff()
        
        print("\n" + "=" * 60)
        print("✓ All T032 tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
