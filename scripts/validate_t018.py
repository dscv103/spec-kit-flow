#!/usr/bin/env python3
"""
Validation script for T018: Worktree listing and removal.

Tests that WorktreeManager correctly implements list(), remove(), and remove_force().
"""

import subprocess
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_flow.worktree.manager import WorktreeManager, WorktreeInfo


def create_test_repo(path: Path) -> None:
    """Create a test git repository."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path, check=True, capture_output=True
    )
    
    # Initial commit
    readme = path / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path, check=True, capture_output=True
    )


def test_worktree_info_dataclass():
    """Test WorktreeInfo dataclass."""
    print("Testing WorktreeInfo dataclass...")
    
    info = WorktreeInfo(
        path=Path("/test/path"),
        branch="main",
        commit="abc123",
        locked=False
    )
    
    assert info.path == Path("/test/path")
    assert info.branch == "main"
    assert info.commit == "abc123"
    assert info.locked is False
    
    print("  ✓ WorktreeInfo dataclass works")


def test_list_parses_porcelain():
    """Test parsing of git worktree list --porcelain output."""
    print("\nTesting porcelain parser...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        manager = WorktreeManager(repo)
        
        porcelain = """worktree /path/to/repo
HEAD abc123def456
branch refs/heads/main

worktree /path/to/repo/.worktrees/session-0
HEAD 789ghi012
branch refs/heads/impl-session-0

worktree /path/to/detached
HEAD 345jkl678
detached

worktree /path/to/locked
HEAD 901mno234
branch refs/heads/feature
locked reason
"""
        
        result = manager._parse_worktree_list(porcelain)
        
        assert len(result) == 4, f"Expected 4 worktrees, got {len(result)}"
        
        # Check first worktree
        assert result[0].path == Path("/path/to/repo")
        assert result[0].branch == "main"
        assert result[0].commit == "abc123def456"
        assert result[0].locked is False
        
        # Check second worktree
        assert result[1].branch == "impl-session-0"
        assert result[1].locked is False
        
        # Check detached worktree
        assert result[2].branch == "(detached)"
        
        # Check locked worktree
        assert result[3].locked is True
        
        print("  ✓ Porcelain parser works correctly")


def test_list_integration():
    """Test list() with real git repository."""
    print("\nTesting list() integration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        
        # List should include main worktree
        worktrees = manager.list()
        assert len(worktrees) >= 1, "Should have at least main worktree"
        assert worktrees[0].path == repo, f"First worktree should be {repo}"
        
        # Create a worktree
        wt_path = manager.create("001-test", 0, "setup")
        
        # List should now include the new worktree
        worktrees = manager.list()
        assert len(worktrees) == 2, f"Should have 2 worktrees, got {len(worktrees)}"
        
        paths = [wt.path for wt in worktrees]
        assert wt_path in paths, "Created worktree should be in list"
        
        # Check branch name
        wt_info = next(wt for wt in worktrees if wt.path == wt_path)
        assert wt_info.branch == "impl-001-test-session-0"
        assert len(wt_info.commit) >= 7, "Should have commit SHA"
        
        print("  ✓ list() includes main and created worktrees")


def test_remove_integration():
    """Test remove() with real git repository."""
    print("\nTesting remove() integration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        
        # Create worktree
        wt_path = manager.create("001-test", 0, "setup")
        assert wt_path.exists(), "Worktree should exist after creation"
        
        # Remove it
        manager.remove(wt_path)
        assert not wt_path.exists(), "Worktree should be removed"
        
        # Should not be in list
        worktrees = manager.list()
        paths = [wt.path for wt in worktrees]
        assert wt_path not in paths, "Removed worktree should not be in list"
        
        print("  ✓ remove() successfully deletes clean worktree")


def test_remove_dirty_fails():
    """Test that remove() fails for dirty worktree."""
    print("\nTesting remove() on dirty worktree...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        
        # Create worktree and make it dirty
        wt_path = manager.create("001-test", 0, "setup")
        test_file = wt_path / "test.txt"
        test_file.write_text("uncommitted change")
        
        # Remove should fail
        try:
            manager.remove(wt_path)
            print("  ✗ remove() should have failed on dirty worktree")
            sys.exit(1)
        except subprocess.CalledProcessError:
            # Expected
            pass
        
        # Worktree should still exist
        assert wt_path.exists(), "Worktree should still exist after failed remove"
        
        print("  ✓ remove() fails on dirty worktree as expected")


def test_remove_force_integration():
    """Test remove_force() with real git repository."""
    print("\nTesting remove_force() integration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        
        # Create worktree and make it dirty
        wt_path = manager.create("001-test", 0, "setup")
        test_file = wt_path / "test.txt"
        test_file.write_text("uncommitted change")
        
        # Force remove should work
        manager.remove_force(wt_path)
        assert not wt_path.exists(), "Worktree should be removed even when dirty"
        
        print("  ✓ remove_force() successfully deletes dirty worktree")


def test_acceptance_criteria():
    """Verify all acceptance criteria for T018."""
    print("\n" + "="*60)
    print("ACCEPTANCE CRITERIA VERIFICATION")
    print("="*60)
    
    criteria = [
        "Lists all worktrees including main",
        "Correctly parses porcelain output",
        "Remove works for clean worktrees",
        "Force remove works for dirty worktrees",
    ]
    
    for criterion in criteria:
        print(f"  ✓ {criterion}")
    
    print("\n" + "="*60)
    print("ALL ACCEPTANCE CRITERIA MET ✓")
    print("="*60)


def main():
    """Run all validation tests."""
    print("Validating T018: Worktree listing and removal")
    print("="*60)
    
    try:
        test_worktree_info_dataclass()
        test_list_parses_porcelain()
        test_list_integration()
        test_remove_integration()
        test_remove_dirty_fails()
        test_remove_force_integration()
        test_acceptance_criteria()
        
        print("\n✅ All T018 validations passed!")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Validation failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
