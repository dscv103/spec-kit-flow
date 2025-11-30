#!/usr/bin/env python3
"""
Quick test script for T033 (validate and finalize methods).

Tests the new validate() and finalize() methods in MergeOrchestrator.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_flow.worktree.merger import MergeOrchestrator


def test_validate_no_command():
    """Test validate with no command returns success."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orchestrator = MergeOrchestrator("001-test", Path(tmpdir))
        success, output = orchestrator.validate(test_cmd=None)
        
        assert success is True
        assert "No validation command" in output
        print("✓ validate() with no command works")


def test_validate_with_command():
    """Test validate with command calls subprocess correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orchestrator = MergeOrchestrator("001-test", Path(tmpdir))
        
        with patch("subprocess.run") as mock_run:
            # Mock checkout success
            checkout_result = Mock(returncode=0, stdout="", stderr="")
            # Mock test command success
            test_result = Mock(
                returncode=0,
                stdout="All tests passed!\n",
                stderr="",
            )
            mock_run.side_effect = [checkout_result, test_result]
            
            success, output = orchestrator.validate("pytest tests/")
            
            assert success is True
            assert "All tests passed!" in output
            print("✓ validate() with command works")


def test_finalize_without_cleanup():
    """Test finalize returns summary without cleaning up."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orchestrator = MergeOrchestrator("001-test", Path(tmpdir))
        
        with patch.object(orchestrator, "_get_merge_statistics") as mock_stats, \
             patch.object(orchestrator, "_cleanup_worktrees") as mock_cleanup:
            
            mock_stats.return_value = {
                "files_changed": 5,
                "lines_added": 120,
                "lines_deleted": 30,
            }
            
            result = orchestrator.finalize(keep_worktrees=True)
            
            assert isinstance(result, dict)
            assert result["worktrees_removed"] == 0
            assert result["files_changed"] == 5
            assert result["lines_added"] == 120
            assert result["lines_deleted"] == 30
            assert result["integration_branch"] == "impl-001-test-integrated"
            mock_cleanup.assert_not_called()
            print("✓ finalize() with keep_worktrees=True works")


def test_finalize_with_cleanup():
    """Test finalize cleans up worktrees by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orchestrator = MergeOrchestrator("001-test", Path(tmpdir))
        
        with patch.object(orchestrator, "_get_merge_statistics") as mock_stats, \
             patch.object(orchestrator, "_cleanup_worktrees") as mock_cleanup:
            
            mock_stats.return_value = {
                "files_changed": 3,
                "lines_added": 50,
                "lines_deleted": 10,
            }
            mock_cleanup.return_value = 2
            
            result = orchestrator.finalize()
            
            assert result["worktrees_removed"] == 2
            mock_cleanup.assert_called_once()
            print("✓ finalize() with default cleanup works")


def test_get_merge_statistics():
    """Test _get_merge_statistics parses git shortstat."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orchestrator = MergeOrchestrator("001-test", Path(tmpdir))
        
        with patch("subprocess.run") as mock_run:
            # Mock git commands
            def run_side_effect(cmd, **kwargs):
                if "abbrev-ref" in cmd and "@{u}" in cmd:
                    return Mock(returncode=1, stdout="", stderr="")
                elif "merge-base" in cmd:
                    return Mock(returncode=0, stdout="abc123\n", stderr="")
                elif "--shortstat" in cmd:
                    return Mock(
                        returncode=0,
                        stdout="10 files changed, 150 insertions(+), 25 deletions(-)\n",
                        stderr="",
                    )
                return Mock(returncode=0, stdout="main\n", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            stats = orchestrator._get_merge_statistics("impl-001-test-integrated")
            
            assert stats["files_changed"] == 10
            assert stats["lines_added"] == 150
            assert stats["lines_deleted"] == 25
            print("✓ _get_merge_statistics() works")


def test_cleanup_worktrees():
    """Test _cleanup_worktrees delegates to WorktreeManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orchestrator = MergeOrchestrator("001-test", Path(tmpdir))
        
        with patch("speckit_flow.worktree.merger.WorktreeManager") as MockManager:
            mock_instance = Mock()
            mock_instance.cleanup_spec.return_value = 4
            MockManager.return_value = mock_instance
            
            result = orchestrator._cleanup_worktrees()
            
            assert result == 4
            mock_instance.cleanup_spec.assert_called_once_with("001-test")
            print("✓ _cleanup_worktrees() works")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Testing T033: validate() and finalize() methods")
    print("=" * 60 + "\n")
    
    try:
        test_validate_no_command()
        test_validate_with_command()
        test_finalize_without_cleanup()
        test_finalize_with_cleanup()
        test_get_merge_statistics()
        test_cleanup_worktrees()
        
        print("\n" + "=" * 60)
        print("✅ All T033 tests passed!")
        print("=" * 60 + "\n")
        
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
