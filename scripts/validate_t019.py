#!/usr/bin/env python3
"""
Validation script for T019: Implement spec cleanup.

This script verifies all acceptance criteria for T019:
- Removes all session worktrees for spec
- Removes parent directory
- Handles missing worktrees gracefully
- Reports which worktrees were removed
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return result."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result


def setup_test_repo():
    """Create a temporary git repository for testing."""
    temp_dir = tempfile.mkdtemp(prefix="t019_test_")
    repo_path = Path(temp_dir)
    
    # Initialize git repo
    run_command(["git", "init"], cwd=repo_path)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=repo_path)
    run_command(["git", "config", "user.name", "Test User"], cwd=repo_path)
    
    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo")
    run_command(["git", "add", "."], cwd=repo_path)
    run_command(["git", "commit", "-m", "Initial commit"], cwd=repo_path)
    
    return repo_path


def test_ac1_removes_all_worktrees():
    """AC: Removes all session worktrees for spec."""
    print("\n[TEST] AC1: Removes all session worktrees for spec")
    
    repo_path = setup_test_repo()
    
    try:
        # Add src to path
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from speckit_flow.worktree.manager import WorktreeManager
        
        manager = WorktreeManager(repo_path)
        
        # Create multiple worktrees
        wt0 = manager.create("001-test", 0, "setup")
        wt1 = manager.create("001-test", 1, "implement")
        wt2 = manager.create("001-test", 2, "test")
        
        # Verify they exist
        assert wt0.exists(), "Worktree 0 should exist"
        assert wt1.exists(), "Worktree 1 should exist"
        assert wt2.exists(), "Worktree 2 should exist"
        
        # Cleanup
        count = manager.cleanup_spec("001-test")
        
        # Verify all removed
        assert not wt0.exists(), "Worktree 0 should be removed"
        assert not wt1.exists(), "Worktree 1 should be removed"
        assert not wt2.exists(), "Worktree 2 should be removed"
        assert count == 3, f"Should report 3 worktrees removed, got {count}"
        
        print("  ✓ All session worktrees removed successfully")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)


def test_ac2_removes_parent_directory():
    """AC: Removes parent directory."""
    print("\n[TEST] AC2: Removes parent directory")
    
    repo_path = setup_test_repo()
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from speckit_flow.worktree.manager import WorktreeManager
        
        manager = WorktreeManager(repo_path)
        
        # Create worktrees
        manager.create("001-test", 0, "setup")
        manager.create("001-test", 1, "implement")
        
        spec_dir = repo_path / ".worktrees-001-test"
        assert spec_dir.exists(), "Spec directory should exist"
        
        # Cleanup
        manager.cleanup_spec("001-test")
        
        # Verify directory removed
        assert not spec_dir.exists(), "Spec directory should be removed"
        
        print("  ✓ Parent directory removed successfully")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)


def test_ac3_handles_missing_worktrees():
    """AC: Handles missing worktrees gracefully."""
    print("\n[TEST] AC3: Handles missing worktrees gracefully")
    
    repo_path = setup_test_repo()
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from speckit_flow.worktree.manager import WorktreeManager
        
        manager = WorktreeManager(repo_path)
        
        # Cleanup non-existent spec (should not raise exception)
        count = manager.cleanup_spec("999-nonexistent")
        
        assert count == 0, f"Should report 0 worktrees removed, got {count}"
        
        print("  ✓ Missing worktrees handled gracefully")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)


def test_ac4_reports_removed_worktrees():
    """AC: Reports which worktrees were removed."""
    print("\n[TEST] AC4: Reports which worktrees were removed")
    
    repo_path = setup_test_repo()
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from speckit_flow.worktree.manager import WorktreeManager
        
        manager = WorktreeManager(repo_path)
        
        # Create varying numbers of worktrees
        for i in range(3):
            manager.create("001-test", i, f"task-{i}")
        
        # Cleanup and verify count
        count = manager.cleanup_spec("001-test")
        
        assert count == 3, f"Should report exactly 3 worktrees removed, got {count}"
        
        # Test with different number
        for i in range(5):
            manager.create("002-test", i, f"task-{i}")
        
        count = manager.cleanup_spec("002-test")
        assert count == 5, f"Should report exactly 5 worktrees removed, got {count}"
        
        print("  ✓ Correctly reports number of removed worktrees")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)


def test_get_spec_worktrees():
    """Test get_spec_worktrees helper method."""
    print("\n[TEST] Helper: get_spec_worktrees filters correctly")
    
    repo_path = setup_test_repo()
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from speckit_flow.worktree.manager import WorktreeManager
        
        manager = WorktreeManager(repo_path)
        
        # Create worktrees for different specs
        manager.create("001-auth", 0, "setup")
        manager.create("001-auth", 1, "implement")
        manager.create("002-payments", 0, "setup")
        
        # Get worktrees for spec 001
        result = manager.get_spec_worktrees("001-auth")
        
        assert len(result) == 2, f"Should find 2 worktrees for 001-auth, got {len(result)}"
        
        # Verify correct worktrees returned
        branches = [wt.branch for wt in result]
        assert "impl-001-auth-session-0" in branches
        assert "impl-001-auth-session-1" in branches
        assert "impl-002-payments-session-0" not in branches
        
        print("  ✓ get_spec_worktrees filters correctly")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("T019 Validation: Implement spec cleanup")
    print("=" * 60)
    
    tests = [
        test_ac1_removes_all_worktrees,
        test_ac2_removes_parent_directory,
        test_ac3_handles_missing_worktrees,
        test_ac4_reports_removed_worktrees,
        test_get_spec_worktrees,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if all(results):
        print("\n✓ All acceptance criteria verified!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
