"""
Unit tests for WorktreeManager.

Tests the core functionality of git worktree creation and management.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from speckit_flow.exceptions import WorktreeExistsError
from speckit_flow.worktree.manager import MAX_TASK_NAME_LENGTH, WorktreeManager, WorktreeInfo


class TestWorktreeManager:
    """Unit tests for WorktreeManager class."""
    
    def test_init(self, tmp_path):
        """WorktreeManager initializes with repo root path."""
        manager = WorktreeManager(tmp_path)
        
        assert manager.repo_root == tmp_path.resolve()
    
    def test_init_resolves_relative_path(self, tmp_path, monkeypatch):
        """WorktreeManager resolves relative paths to absolute."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)
        
        manager = WorktreeManager(Path(".."))
        
        assert manager.repo_root == tmp_path.resolve()


class TestSanitizeTaskName:
    """Tests for task name sanitization."""
    
    def test_simple_name(self, tmp_path):
        """Simple alphanumeric names pass through."""
        manager = WorktreeManager(tmp_path)
        
        result = manager._sanitize_task_name("setup-database")
        
        assert result == "setup-database"
    
    def test_uppercase_converted(self, tmp_path):
        """Uppercase letters converted to lowercase."""
        manager = WorktreeManager(tmp_path)
        
        result = manager._sanitize_task_name("Setup Database")
        
        assert result == "setup-database"
    
    def test_special_chars_replaced(self, tmp_path):
        """Special characters replaced with hyphens."""
        manager = WorktreeManager(tmp_path)
        
        result = manager._sanitize_task_name("User@Authentication (OAuth2.0)")
        
        assert result == "user-authentication-oauth2-0"
    
    def test_multiple_hyphens_collapsed(self, tmp_path):
        """Multiple consecutive special chars become single hyphen."""
        manager = WorktreeManager(tmp_path)
        
        result = manager._sanitize_task_name("Task  @#$  Name")
        
        assert result == "task-name"
    
    def test_leading_trailing_hyphens_removed(self, tmp_path):
        """Leading and trailing hyphens are removed."""
        manager = WorktreeManager(tmp_path)
        
        result = manager._sanitize_task_name("---Task Name!!!---")
        
        assert result == "task-name"
    
    def test_truncates_long_names(self, tmp_path):
        """Long task names are truncated to MAX_TASK_NAME_LENGTH."""
        manager = WorktreeManager(tmp_path)
        long_name = "a" * (MAX_TASK_NAME_LENGTH + 20)
        
        result = manager._sanitize_task_name(long_name)
        
        assert len(result) <= MAX_TASK_NAME_LENGTH
        assert result == "a" * MAX_TASK_NAME_LENGTH
    
    def test_truncates_without_trailing_hyphen(self, tmp_path):
        """Truncation doesn't leave trailing hyphen."""
        manager = WorktreeManager(tmp_path)
        # Create name that would have hyphen at truncation point
        long_name = "a" * (MAX_TASK_NAME_LENGTH - 1) + "-extra-text"
        
        result = manager._sanitize_task_name(long_name)
        
        assert not result.endswith("-")
        assert len(result) <= MAX_TASK_NAME_LENGTH
    
    def test_empty_name_fallback(self, tmp_path):
        """Names with only special chars fall back to 'task'."""
        manager = WorktreeManager(tmp_path)
        
        result = manager._sanitize_task_name("@#$%^&*()")
        
        assert result == "task"
    
    def test_unicode_handled(self, tmp_path):
        """Unicode characters are handled (removed)."""
        manager = WorktreeManager(tmp_path)
        
        result = manager._sanitize_task_name("Task with émojis 🚀")
        
        assert result == "task-with-mojis"


class TestWorktreeCreate:
    """Tests for worktree creation."""
    
    def test_create_calls_git_with_correct_args(self, tmp_path):
        """Create calls git worktree add with correct arguments."""
        manager = WorktreeManager(tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = manager.create("001-feature", 0, "setup")
            
            # Verify git command was called correctly
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "git"
            assert args[1] == "worktree"
            assert args[2] == "add"
            assert args[3] == "-b"
            assert args[4] == "impl-001-feature-session-0"
            assert args[5] == str(tmp_path / ".worktrees-001-feature" / "session-0-setup")
            
            # Verify returned path
            expected_path = tmp_path / ".worktrees-001-feature" / "session-0-setup"
            assert result == expected_path
    
    def test_create_makes_worktrees_base_directory(self, tmp_path):
        """Create creates the .worktrees-{spec-id} directory."""
        manager = WorktreeManager(tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            manager.create("001-feature", 0, "setup")
            
            expected_dir = tmp_path / ".worktrees-001-feature"
            assert expected_dir.exists()
            assert expected_dir.is_dir()
    
    def test_create_sanitizes_task_name(self, tmp_path):
        """Create sanitizes task name in directory path."""
        manager = WorktreeManager(tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = manager.create("001-feature", 0, "Setup Database (PostgreSQL)")
            
            # Verify sanitized name in path
            assert "setup-database-postgresql" in str(result)
            assert "(" not in str(result)
            assert ")" not in str(result)
    
    def test_create_raises_if_worktree_exists(self, tmp_path):
        """Create raises WorktreeExistsError if worktree directory exists."""
        manager = WorktreeManager(tmp_path)
        
        # Create the worktree directory manually
        worktree_path = tmp_path / ".worktrees-001-feature" / "session-0-setup"
        worktree_path.mkdir(parents=True)
        
        with pytest.raises(WorktreeExistsError) as exc_info:
            manager.create("001-feature", 0, "setup")
        
        assert "already exists" in str(exc_info.value).lower()
        assert str(worktree_path) in str(exc_info.value)
    
    def test_create_raises_if_branch_exists(self, tmp_path):
        """Create raises WorktreeExistsError with helpful message if branch exists."""
        manager = WorktreeManager(tmp_path)
        
        with patch("subprocess.run") as mock_run:
            # Simulate git error for existing branch
            error = subprocess.CalledProcessError(
                128,
                ["git", "worktree", "add"],
                stderr="fatal: A branch named 'impl-001-feature-session-0' already exists."
            )
            mock_run.side_effect = error
            
            with pytest.raises(WorktreeExistsError) as exc_info:
                manager.create("001-feature", 0, "setup")
            
            assert "already exists" in str(exc_info.value).lower()
            assert "impl-001-feature-session-0" in str(exc_info.value)
    
    def test_create_reraises_other_git_errors(self, tmp_path):
        """Create re-raises git errors that aren't about existing worktrees."""
        manager = WorktreeManager(tmp_path)
        
        with patch("subprocess.run") as mock_run:
            # Simulate different git error
            error = subprocess.CalledProcessError(
                1,
                ["git", "worktree", "add"],
                stderr="fatal: Not a git repository"
            )
            mock_run.side_effect = error
            
            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                manager.create("001-feature", 0, "setup")
            
            assert "Not a git repository" in exc_info.value.stderr
    
    def test_create_with_long_spec_id_and_task_name(self, tmp_path):
        """Create handles long spec_id and task names correctly."""
        manager = WorktreeManager(tmp_path)
        
        long_spec_id = "001-very-long-feature-name-that-exceeds-normal-length"
        long_task_name = "Implement a very long task name that should be truncated"
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = manager.create(long_spec_id, 0, long_task_name)
            
            # Task name should be truncated
            assert len(result.name.replace(f"session-0-", "")) <= MAX_TASK_NAME_LENGTH
            
            # Spec ID should be preserved in full
            assert long_spec_id in str(result.parent)


class TestWorktreeCreateIntegration:
    """Integration tests for worktree creation with real git."""
    
    def test_create_actual_worktree(self, temp_repo):
        """Create actually creates a git worktree (integration test)."""
        manager = WorktreeManager(temp_repo)
        
        worktree_path = manager.create("001-test", 0, "setup")
        
        # Verify worktree exists
        assert worktree_path.exists()
        assert worktree_path.is_dir()
        
        # Verify git directory exists
        assert (worktree_path / ".git").exists()
        
        # Verify we can run git commands in the worktree
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "impl-001-test-session-0"
    
    def test_create_multiple_sessions(self, temp_repo):
        """Create can create multiple worktrees for different sessions."""
        manager = WorktreeManager(temp_repo)
        
        worktree_0 = manager.create("001-test", 0, "setup")
        worktree_1 = manager.create("001-test", 1, "implement")
        worktree_2 = manager.create("001-test", 2, "test")
        
        # All should exist
        assert worktree_0.exists()
        assert worktree_1.exists()
        assert worktree_2.exists()
        
        # All should have different branches
        assert worktree_0 != worktree_1
        assert worktree_1 != worktree_2
        
        # Verify branches
        for idx, path in enumerate([worktree_0, worktree_1, worktree_2]):
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
            )
            assert result.stdout.strip() == f"impl-001-test-session-{idx}"
    
    def test_create_fails_for_duplicate(self, temp_repo):
        """Create fails if worktree already exists (integration test)."""
        manager = WorktreeManager(temp_repo)
        
        # Create first worktree
        manager.create("001-test", 0, "setup")
        
        # Try to create again - should fail
        with pytest.raises(WorktreeExistsError):
            manager.create("001-test", 0, "setup")


class TestWorktreeList:
    """Tests for worktree listing."""
    
    def test_list_returns_empty_on_git_error(self, tmp_path):
        """List returns empty list if git command fails."""
        manager = WorktreeManager(tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                128, ["git", "worktree", "list"], stderr="fatal: not a git repo"
            )
            
            result = manager.list()
            
            assert result == []
    
    def test_parse_single_worktree(self, tmp_path):
        """Parser handles single worktree output."""
        manager = WorktreeManager(tmp_path)
        
        porcelain = """worktree /path/to/repo
HEAD abc123def456
branch refs/heads/main
"""
        
        result = manager._parse_worktree_list(porcelain)
        
        assert len(result) == 1
        assert result[0].path == Path("/path/to/repo")
        assert result[0].branch == "main"
        assert result[0].commit == "abc123def456"
        assert result[0].locked is False
    
    def test_parse_multiple_worktrees(self, tmp_path):
        """Parser handles multiple worktrees."""
        manager = WorktreeManager(tmp_path)
        
        porcelain = """worktree /path/to/repo
HEAD abc123
branch refs/heads/main

worktree /path/to/repo/.worktrees/session-0
HEAD def456
branch refs/heads/impl-session-0

worktree /path/to/repo/.worktrees/session-1
HEAD ghi789
branch refs/heads/impl-session-1
"""
        
        result = manager._parse_worktree_list(porcelain)
        
        assert len(result) == 3
        assert result[0].branch == "main"
        assert result[1].branch == "impl-session-0"
        assert result[2].branch == "impl-session-1"
    
    def test_parse_detached_head(self, tmp_path):
        """Parser handles detached HEAD worktree."""
        manager = WorktreeManager(tmp_path)
        
        porcelain = """worktree /path/to/repo
HEAD abc123
detached
"""
        
        result = manager._parse_worktree_list(porcelain)
        
        assert len(result) == 1
        assert result[0].branch == "(detached)"
    
    def test_parse_locked_worktree(self, tmp_path):
        """Parser handles locked worktrees."""
        manager = WorktreeManager(tmp_path)
        
        porcelain = """worktree /path/to/repo
HEAD abc123
branch refs/heads/main

worktree /path/to/locked
HEAD def456
branch refs/heads/feature
locked reason goes here
"""
        
        result = manager._parse_worktree_list(porcelain)
        
        assert len(result) == 2
        assert result[0].locked is False
        assert result[1].locked is True
    
    def test_parse_empty_output(self, tmp_path):
        """Parser handles empty output."""
        manager = WorktreeManager(tmp_path)
        
        result = manager._parse_worktree_list("")
        
        assert result == []
    
    def test_parse_with_extra_blank_lines(self, tmp_path):
        """Parser handles output with extra blank lines."""
        manager = WorktreeManager(tmp_path)
        
        porcelain = """

worktree /path/to/repo
HEAD abc123
branch refs/heads/main


worktree /path/to/other
HEAD def456
branch refs/heads/feature

"""
        
        result = manager._parse_worktree_list(porcelain)
        
        assert len(result) == 2


class TestWorktreeListIntegration:
    """Integration tests for worktree listing with real git."""
    
    def test_list_includes_main_worktree(self, temp_repo):
        """List includes the main repository worktree."""
        manager = WorktreeManager(temp_repo)
        
        worktrees = manager.list()
        
        assert len(worktrees) >= 1
        # First worktree should be main repo
        assert worktrees[0].path == temp_repo
    
    def test_list_includes_all_worktrees(self, temp_repo):
        """List includes all created worktrees."""
        manager = WorktreeManager(temp_repo)
        
        # Create some worktrees
        wt0 = manager.create("001-test", 0, "setup")
        wt1 = manager.create("001-test", 1, "implement")
        
        worktrees = manager.list()
        
        # Should have main + 2 created
        assert len(worktrees) == 3
        
        # Check that created worktrees are in the list
        paths = [wt.path for wt in worktrees]
        assert wt0 in paths
        assert wt1 in paths
    
    def test_list_shows_correct_branches(self, temp_repo):
        """List shows correct branch names for each worktree."""
        manager = WorktreeManager(temp_repo)
        
        manager.create("001-test", 0, "setup")
        manager.create("001-test", 1, "implement")
        
        worktrees = manager.list()
        
        # Find our created worktrees
        session_0 = next(wt for wt in worktrees if "session-0" in str(wt.path))
        session_1 = next(wt for wt in worktrees if "session-1" in str(wt.path))
        
        assert session_0.branch == "impl-001-test-session-0"
        assert session_1.branch == "impl-001-test-session-1"
    
    def test_list_shows_commit_sha(self, temp_repo):
        """List shows valid commit SHA for each worktree."""
        manager = WorktreeManager(temp_repo)
        
        worktrees = manager.list()
        
        # All worktrees should have a commit SHA
        for wt in worktrees:
            assert wt.commit
            assert len(wt.commit) >= 7  # At least short SHA
            # SHA should be hex characters
            assert all(c in "0123456789abcdef" for c in wt.commit.lower())


class TestWorktreeRemove:
    """Tests for worktree removal."""
    
    def test_remove_calls_git_with_correct_args(self, tmp_path):
        """Remove calls git worktree remove with correct arguments."""
        manager = WorktreeManager(tmp_path)
        worktree_path = tmp_path / ".worktrees-001" / "session-0"
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            manager.remove(worktree_path)
            
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["git", "worktree", "remove", str(worktree_path)]
    
    def test_remove_raises_on_git_error(self, tmp_path):
        """Remove raises CalledProcessError if git command fails."""
        manager = WorktreeManager(tmp_path)
        worktree_path = tmp_path / ".worktrees-001" / "session-0"
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["git", "worktree", "remove"],
                stderr="fatal: worktree contains modified or untracked files"
            )
            
            with pytest.raises(subprocess.CalledProcessError):
                manager.remove(worktree_path)
    
    def test_remove_force_calls_git_with_force_flag(self, tmp_path):
        """Remove force calls git worktree remove with --force flag."""
        manager = WorktreeManager(tmp_path)
        worktree_path = tmp_path / ".worktrees-001" / "session-0"
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            manager.remove_force(worktree_path)
            
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["git", "worktree", "remove", "--force", str(worktree_path)]


class TestWorktreeRemoveIntegration:
    """Integration tests for worktree removal with real git."""
    
    def test_remove_deletes_worktree(self, temp_repo):
        """Remove successfully deletes a clean worktree."""
        manager = WorktreeManager(temp_repo)
        
        # Create and then remove a worktree
        worktree_path = manager.create("001-test", 0, "setup")
        assert worktree_path.exists()
        
        manager.remove(worktree_path)
        
        # Worktree should be removed
        assert not worktree_path.exists()
        
        # Should no longer appear in list
        worktrees = manager.list()
        paths = [wt.path for wt in worktrees]
        assert worktree_path not in paths
    
    def test_remove_fails_for_dirty_worktree(self, temp_repo):
        """Remove fails for worktree with uncommitted changes."""
        manager = WorktreeManager(temp_repo)
        
        # Create worktree and make changes
        worktree_path = manager.create("001-test", 0, "setup")
        test_file = worktree_path / "test.txt"
        test_file.write_text("uncommitted change")
        
        # Remove should fail
        with pytest.raises(subprocess.CalledProcessError):
            manager.remove(worktree_path)
        
        # Worktree should still exist
        assert worktree_path.exists()
    
    def test_remove_force_deletes_dirty_worktree(self, temp_repo):
        """Force remove deletes worktree even with uncommitted changes."""
        manager = WorktreeManager(temp_repo)
        
        # Create worktree and make changes
        worktree_path = manager.create("001-test", 0, "setup")
        test_file = worktree_path / "test.txt"
        test_file.write_text("uncommitted change")
        
        # Force remove should succeed
        manager.remove_force(worktree_path)
        
        # Worktree should be removed
        assert not worktree_path.exists()
    
    def test_remove_multiple_worktrees(self, temp_repo):
        """Remove can delete multiple worktrees."""
        manager = WorktreeManager(temp_repo)
        
        # Create multiple worktrees
        wt0 = manager.create("001-test", 0, "setup")
        wt1 = manager.create("001-test", 1, "implement")
        wt2 = manager.create("001-test", 2, "test")
        
        # Remove them all
        manager.remove(wt0)
        manager.remove(wt1)
        manager.remove(wt2)
        
        # All should be gone
        assert not wt0.exists()
        assert not wt1.exists()
        assert not wt2.exists()
        
        # Only main worktree should remain in list
        worktrees = manager.list()
        assert len(worktrees) == 1
        assert worktrees[0].path == temp_repo


class TestGetSpecWorktrees:
    """Tests for getting worktrees by spec ID."""
    
    def test_get_spec_worktrees_empty_when_none_exist(self, temp_repo):
        """Returns empty list when no worktrees exist for spec."""
        manager = WorktreeManager(temp_repo)
        
        result = manager.get_spec_worktrees("001-nonexistent")
        
        assert result == []
    
    def test_get_spec_worktrees_filters_by_spec_id(self, temp_repo):
        """Returns only worktrees for the specified spec."""
        manager = WorktreeManager(temp_repo)
        
        # Create worktrees for different specs
        wt_001_0 = manager.create("001-auth", 0, "setup")
        wt_001_1 = manager.create("001-auth", 1, "implement")
        wt_002_0 = manager.create("002-payments", 0, "setup")
        
        # Get worktrees for spec 001
        result = manager.get_spec_worktrees("001-auth")
        
        assert len(result) == 2
        paths = [wt.path for wt in result]
        assert wt_001_0 in paths
        assert wt_001_1 in paths
        assert wt_002_0 not in paths
    
    def test_get_spec_worktrees_includes_all_sessions(self, temp_repo):
        """Returns all sessions for a spec."""
        manager = WorktreeManager(temp_repo)
        
        # Create multiple sessions
        for i in range(5):
            manager.create("001-test", i, f"task-{i}")
        
        result = manager.get_spec_worktrees("001-test")
        
        assert len(result) == 5
        # Verify all sessions present
        branches = [wt.branch for wt in result]
        for i in range(5):
            assert f"impl-001-test-session-{i}" in branches
    
    def test_get_spec_worktrees_excludes_main(self, temp_repo):
        """Does not include main worktree in results."""
        manager = WorktreeManager(temp_repo)
        
        manager.create("001-test", 0, "setup")
        
        result = manager.get_spec_worktrees("001-test")
        
        # Main worktree should not be included
        paths = [wt.path for wt in result]
        assert temp_repo not in paths
    
    def test_is_path_under_identifies_subdirectories(self, temp_repo):
        """Helper method correctly identifies subdirectories."""
        manager = WorktreeManager(temp_repo)
        
        parent = temp_repo / ".worktrees-001"
        child = parent / "session-0"
        unrelated = temp_repo / "other"
        
        assert manager._is_path_under(child, parent) is True
        assert manager._is_path_under(unrelated, parent) is False
        assert manager._is_path_under(parent, parent) is False
    
    def test_is_path_under_handles_relative_paths(self, temp_repo, monkeypatch):
        """Helper method resolves relative paths correctly."""
        manager = WorktreeManager(temp_repo)
        
        parent = temp_repo / ".worktrees-001"
        parent.mkdir(parents=True, exist_ok=True)
        child = parent / "session-0"
        child.mkdir(exist_ok=True)
        
        # Change to child directory and test with relative paths
        monkeypatch.chdir(child)
        
        assert manager._is_path_under(Path("."), parent) is True


class TestCleanupSpec:
    """Tests for spec cleanup functionality."""
    
    def test_cleanup_spec_removes_all_worktrees(self, temp_repo):
        """Cleanup removes all worktrees for a spec."""
        manager = WorktreeManager(temp_repo)
        
        # Create multiple worktrees
        wt0 = manager.create("001-test", 0, "setup")
        wt1 = manager.create("001-test", 1, "implement")
        wt2 = manager.create("001-test", 2, "test")
        
        # Cleanup
        count = manager.cleanup_spec("001-test")
        
        # All should be removed
        assert count == 3
        assert not wt0.exists()
        assert not wt1.exists()
        assert not wt2.exists()
    
    def test_cleanup_spec_removes_parent_directory(self, temp_repo):
        """Cleanup removes the .worktrees-{spec-id} directory."""
        manager = WorktreeManager(temp_repo)
        
        # Create worktrees
        manager.create("001-test", 0, "setup")
        manager.create("001-test", 1, "implement")
        
        spec_dir = temp_repo / ".worktrees-001-test"
        assert spec_dir.exists()
        
        # Cleanup
        manager.cleanup_spec("001-test")
        
        # Directory should be removed
        assert not spec_dir.exists()
    
    def test_cleanup_spec_handles_missing_worktrees(self, temp_repo):
        """Cleanup handles specs with no worktrees gracefully."""
        manager = WorktreeManager(temp_repo)
        
        # Cleanup non-existent spec
        count = manager.cleanup_spec("999-nonexistent")
        
        assert count == 0
    
    def test_cleanup_spec_handles_dirty_worktrees(self, temp_repo):
        """Cleanup removes worktrees even with uncommitted changes."""
        manager = WorktreeManager(temp_repo)
        
        # Create worktree with changes
        wt0 = manager.create("001-test", 0, "setup")
        test_file = wt0 / "test.txt"
        test_file.write_text("uncommitted change")
        
        # Cleanup should still work (uses force remove)
        count = manager.cleanup_spec("001-test")
        
        assert count == 1
        assert not wt0.exists()
    
    def test_cleanup_spec_returns_count(self, temp_repo):
        """Cleanup returns number of removed worktrees."""
        manager = WorktreeManager(temp_repo)
        
        # Create varying numbers of worktrees
        for i in range(3):
            manager.create("001-test", i, f"task-{i}")
        
        count = manager.cleanup_spec("001-test")
        
        assert count == 3
    
    def test_cleanup_spec_only_affects_specified_spec(self, temp_repo):
        """Cleanup only removes worktrees for specified spec."""
        manager = WorktreeManager(temp_repo)
        
        # Create worktrees for multiple specs
        wt_001 = manager.create("001-auth", 0, "setup")
        wt_002 = manager.create("002-payments", 0, "setup")
        
        # Cleanup one spec
        manager.cleanup_spec("001-auth")
        
        # Only 001 should be removed
        assert not wt_001.exists()
        assert wt_002.exists()
    
    def test_cleanup_spec_continues_on_partial_failure(self, temp_repo):
        """Cleanup continues even if some removals fail."""
        manager = WorktreeManager(temp_repo)
        
        # Create worktrees
        wt0 = manager.create("001-test", 0, "setup")
        wt1 = manager.create("001-test", 1, "implement")
        
        # Mock remove_force to fail on first call, succeed on second
        call_count = 0
        original_remove_force = manager.remove_force
        
        def mock_remove_force(path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise subprocess.CalledProcessError(1, ["git", "worktree", "remove"])
            return original_remove_force(path)
        
        with patch.object(manager, "remove_force", side_effect=mock_remove_force):
            count = manager.cleanup_spec("001-test")
        
        # Should have attempted all removals (count may be less than total)
        # At least one should have succeeded
        assert call_count == 2
    
    def test_cleanup_spec_handles_non_empty_directory(self, temp_repo):
        """Cleanup removes directory even if it contains extra files."""
        manager = WorktreeManager(temp_repo)
        
        # Create worktree
        wt0 = manager.create("001-test", 0, "setup")
        
        # Add extra file to parent directory
        spec_dir = temp_repo / ".worktrees-001-test"
        extra_file = spec_dir / "extra.txt"
        extra_file.write_text("extra content")
        
        # Cleanup should remove everything
        manager.cleanup_spec("001-test")
        
        # Directory should be gone
        assert not spec_dir.exists()
    
    def test_cleanup_spec_integration_full_workflow(self, temp_repo):
        """Full integration test of spec lifecycle."""
        manager = WorktreeManager(temp_repo)
        
        # Create multiple worktrees with changes
        wt0 = manager.create("001-feature", 0, "setup")
        wt1 = manager.create("001-feature", 1, "implement")
        wt2 = manager.create("001-feature", 2, "test")
        
        # Make changes in each
        for wt in [wt0, wt1, wt2]:
            (wt / "file.txt").write_text("content")
        
        # Verify they exist
        initial_worktrees = manager.get_spec_worktrees("001-feature")
        assert len(initial_worktrees) == 3
        
        # Cleanup
        count = manager.cleanup_spec("001-feature")
        
        # Verify cleanup
        assert count == 3
        final_worktrees = manager.get_spec_worktrees("001-feature")
        assert len(final_worktrees) == 0
        
        # Verify directory gone
        spec_dir = temp_repo / ".worktrees-001-feature"
        assert not spec_dir.exists()
        
        # Verify only main worktree remains
        all_worktrees = manager.list()
        assert len(all_worktrees) == 1
        assert all_worktrees[0].path == temp_repo
