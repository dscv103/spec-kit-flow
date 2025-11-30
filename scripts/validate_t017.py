#!/usr/bin/env python3
"""
Validation script for T017 - WorktreeManager core.

This script verifies all acceptance criteria for T017:
1. Creates worktree directory and git branch
2. Returns Path to created worktree
3. Raises WorktreeExistsError if already exists
4. Works with long spec_id and task names (truncation)
"""

import subprocess
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "speckit_flow"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "speckit_core"))

from speckit_flow.worktree.manager import WorktreeManager
from speckit_flow.exceptions import WorktreeExistsError


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
    # Initial commit required for worktrees
    (path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path, check=True, capture_output=True
    )


def test_ac1_creates_worktree_and_branch():
    """AC1: Creates worktree directory and git branch."""
    print("Testing AC1: Creates worktree directory and git branch...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        worktree_path = manager.create("001-test", 0, "setup-database")
        
        # Verify directory exists
        assert worktree_path.exists(), "Worktree directory not created"
        assert worktree_path.is_dir(), "Worktree is not a directory"
        
        # Verify git directory
        assert (worktree_path / ".git").exists(), "Git directory not found in worktree"
        
        # Verify branch exists and is checked out
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        branch_name = result.stdout.strip()
        assert branch_name == "impl-001-test-session-0", f"Wrong branch: {branch_name}"
        
        print("  ✓ Worktree directory created")
        print("  ✓ Git directory exists")
        print("  ✓ Branch created and checked out")


def test_ac2_returns_path():
    """AC2: Returns Path to created worktree."""
    print("\nTesting AC2: Returns Path to created worktree...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        result = manager.create("001-test", 0, "setup")
        
        # Verify return type
        assert isinstance(result, Path), f"Expected Path, got {type(result)}"
        
        # Verify path is correct
        expected = repo / ".worktrees-001-test" / "session-0-setup"
        assert result == expected, f"Expected {expected}, got {result}"
        
        print("  ✓ Returns Path object")
        print("  ✓ Path is correct")


def test_ac3_raises_if_exists():
    """AC3: Raises WorktreeExistsError if already exists."""
    print("\nTesting AC3: Raises WorktreeExistsError if already exists...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        
        # Create first worktree
        manager.create("001-test", 0, "setup")
        
        # Try to create again
        try:
            manager.create("001-test", 0, "setup")
            assert False, "Should have raised WorktreeExistsError"
        except WorktreeExistsError as e:
            assert "already exists" in str(e).lower(), f"Wrong error message: {e}"
            print("  ✓ Raises WorktreeExistsError")
            print("  ✓ Error message is helpful")


def test_ac4_long_names():
    """AC4: Works with long spec_id and task names (truncation)."""
    print("\nTesting AC4: Works with long spec_id and task names...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        
        # Long spec_id (should be preserved)
        long_spec_id = "001-very-long-feature-name-that-exceeds-normal-length"
        
        # Long task name (should be truncated)
        long_task_name = "Implement a very very very very long task name that should definitely be truncated"
        
        worktree_path = manager.create(long_spec_id, 0, long_task_name)
        
        # Verify it was created
        assert worktree_path.exists(), "Worktree not created"
        
        # Verify spec_id is preserved
        assert long_spec_id in str(worktree_path.parent), "Spec ID not preserved"
        
        # Verify task name is truncated
        task_part = worktree_path.name.replace("session-0-", "")
        assert len(task_part) <= 50, f"Task name not truncated: length={len(task_part)}"
        
        # Verify it still works
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip().startswith("impl-"), "Branch not created properly"
        
        print("  ✓ Long spec_id preserved")
        print("  ✓ Long task name truncated")
        print("  ✓ Worktree still functions correctly")


def test_sanitization():
    """Additional test: Verify task name sanitization."""
    print("\nTesting task name sanitization...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        create_test_repo(repo)
        
        manager = WorktreeManager(repo)
        
        # Test with special characters
        worktree_path = manager.create("001-test", 0, "Setup Database (PostgreSQL) @#$%")
        
        # Verify special chars removed
        assert "(" not in str(worktree_path), "Parentheses not removed"
        assert "@" not in str(worktree_path), "Special chars not removed"
        assert "setup-database-postgresql" in str(worktree_path).lower(), "Sanitization failed"
        
        print("  ✓ Special characters removed")
        print("  ✓ Name is filesystem-safe")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("T017 Validation: WorktreeManager Core")
    print("=" * 60)
    
    try:
        test_ac1_creates_worktree_and_branch()
        test_ac2_returns_path()
        test_ac3_raises_if_exists()
        test_ac4_long_names()
        test_sanitization()
        
        print("\n" + "=" * 60)
        print("✅ ALL ACCEPTANCE CRITERIA PASSED")
        print("=" * 60)
        return 0
    
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ VALIDATION FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
