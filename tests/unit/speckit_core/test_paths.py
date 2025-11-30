"""
Unit tests for speckit_core.paths module.

Tests path utilities for repository discovery, branch detection,
and feature directory resolution.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from speckit_core.paths import (
    get_repo_root,
    get_current_branch,
    get_feature_paths,
    find_feature_dir_by_prefix,
)
from speckit_core.exceptions import NotInGitRepoError, FeatureNotFoundError


class TestGetRepoRoot:
    """Unit tests for get_repo_root function."""
    
    def test_returns_path_in_git_repo(self, temp_repo):
        """Returns correct path when inside a git repository."""
        # Act
        result = get_repo_root()
        
        # Assert
        assert isinstance(result, Path)
        assert result.is_dir()
        assert (result / ".git").exists()
    
    def test_raises_error_outside_git_repo(self, temp_dir):
        """Raises NotInGitRepoError when not in a git repository."""
        # Arrange: Change to non-git directory
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)
            
            # Act & Assert
            with pytest.raises(NotInGitRepoError) as exc_info:
                get_repo_root()
            
            assert "not inside a git repository" in str(exc_info.value).lower()
        finally:
            os.chdir(original_cwd)
    
    def test_works_from_subdirectory(self, temp_repo):
        """Returns repo root even when called from subdirectory."""
        # Arrange: Create and enter subdirectory
        subdir = temp_repo / "some" / "nested" / "directory"
        subdir.mkdir(parents=True)
        
        original_cwd = Path.cwd()
        try:
            os.chdir(subdir)
            
            # Act
            result = get_repo_root()
            
            # Assert
            assert result == temp_repo
        finally:
            os.chdir(original_cwd)


class TestGetCurrentBranch:
    """Unit tests for get_current_branch function."""
    
    def test_returns_branch_name_in_git_repo(self, temp_repo):
        """Returns current git branch name."""
        # Act
        branch = get_current_branch()
        
        # Assert
        assert isinstance(branch, str)
        assert len(branch) > 0
        # Default branch is usually "main" or "master"
        assert branch in ("main", "master")
    
    def test_prefers_specify_feature_env_var(self, temp_repo, monkeypatch):
        """Prefers SPECIFY_FEATURE environment variable over git."""
        # Arrange
        monkeypatch.setenv("SPECIFY_FEATURE", "001-test-feature")
        
        # Act
        branch = get_current_branch()
        
        # Assert
        assert branch == "001-test-feature"
    
    def test_returns_git_branch_when_env_not_set(self, temp_repo, monkeypatch):
        """Falls back to git when SPECIFY_FEATURE not set."""
        # Arrange
        monkeypatch.delenv("SPECIFY_FEATURE", raising=False)
        
        # Act
        branch = get_current_branch()
        
        # Assert
        assert isinstance(branch, str)
        assert len(branch) > 0
    
    def test_ignores_empty_specify_feature_env_var(self, temp_repo, monkeypatch):
        """Ignores SPECIFY_FEATURE if it's empty or whitespace."""
        # Arrange
        monkeypatch.setenv("SPECIFY_FEATURE", "   ")
        
        # Act
        branch = get_current_branch()
        
        # Assert - should fall back to git
        assert branch in ("main", "master")
    
    def test_raises_error_outside_git_repo_without_env(self, temp_dir, monkeypatch):
        """Raises NotInGitRepoError when not in git repo and no env var."""
        # Arrange
        monkeypatch.delenv("SPECIFY_FEATURE", raising=False)
        original_cwd = Path.cwd()
        
        try:
            os.chdir(temp_dir)
            
            # Act & Assert
            with pytest.raises(NotInGitRepoError):
                get_current_branch()
        finally:
            os.chdir(original_cwd)
    
    def test_works_with_feature_branch(self, temp_repo):
        """Returns correct branch name for feature branches."""
        # Arrange: Create and checkout a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "001-my-feature"],
            cwd=temp_repo,
            check=True,
            capture_output=True,
        )
        
        # Act
        branch = get_current_branch()
        
        # Assert
        assert branch == "001-my-feature"


class TestFindFeatureDirByPrefix:
    """Unit tests for find_feature_dir_by_prefix function."""
    
    def test_returns_exact_match_without_numeric_prefix(self, temp_repo):
        """Returns exact path when branch has no numeric prefix."""
        # Arrange
        branch = "my-feature"
        
        # Act
        result = find_feature_dir_by_prefix(temp_repo, branch)
        
        # Assert
        assert result == temp_repo / "specs" / "my-feature"
    
    def test_finds_single_matching_directory(self, temp_repo):
        """Finds directory matching numeric prefix."""
        # Arrange: Create a feature directory
        feature_dir = temp_repo / "specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)
        
        # Act
        result = find_feature_dir_by_prefix(temp_repo, "001-branch-name")
        
        # Assert
        assert result == feature_dir
    
    def test_raises_error_when_no_match_found(self, temp_repo):
        """Raises FeatureNotFoundError when no matching directory exists."""
        # Arrange: specs directory exists but no matching feature
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act & Assert
        with pytest.raises(FeatureNotFoundError) as exc_info:
            find_feature_dir_by_prefix(temp_repo, "999-nonexistent")
        
        assert "No feature directory found" in str(exc_info.value)
        assert "999" in str(exc_info.value)
    
    def test_raises_error_when_multiple_matches(self, temp_repo):
        """Raises ValueError when multiple directories match the prefix."""
        # Arrange: Create multiple directories with same prefix
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        (specs_dir / "001-feature-a").mkdir()
        (specs_dir / "001-feature-b").mkdir()
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            find_feature_dir_by_prefix(temp_repo, "001-branch")
        
        assert "Multiple spec directories found" in str(exc_info.value)
        assert "001" in str(exc_info.value)
    
    def test_handles_missing_specs_directory(self, temp_repo):
        """Raises FeatureNotFoundError when specs/ directory doesn't exist."""
        # Act & Assert
        with pytest.raises(FeatureNotFoundError):
            find_feature_dir_by_prefix(temp_repo, "001-feature")
    
    def test_matches_first_directory_with_prefix(self, temp_repo):
        """Returns the matching directory when prefix matches."""
        # Arrange: Create a feature directory with longer name
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        feature_dir = specs_dir / "004-complex-feature-name"
        feature_dir.mkdir()
        
        # Act
        result = find_feature_dir_by_prefix(temp_repo, "004-bug-fix")
        
        # Assert
        assert result == feature_dir
    
    def test_prefix_extraction_with_three_digits(self, temp_repo):
        """Correctly extracts three-digit prefix."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        (specs_dir / "042-feature").mkdir()
        
        # Act
        result = find_feature_dir_by_prefix(temp_repo, "042-different-branch")
        
        # Assert
        assert result == specs_dir / "042-feature"


class TestGetFeaturePaths:
    """Unit tests for get_feature_paths function."""
    
    def test_returns_feature_context_with_all_paths(self, temp_repo):
        """Returns FeatureContext with all standard paths."""
        # Arrange: Create a feature directory
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        feature_dir = specs_dir / "001-test-feature"
        feature_dir.mkdir()
        
        # Act
        context = get_feature_paths(temp_repo, "001-test-feature")
        
        # Assert
        assert context.repo_root == temp_repo
        assert context.branch == "001-test-feature"
        assert context.feature_dir == feature_dir
        assert context.spec_path == feature_dir / "spec.md"
        assert context.plan_path == feature_dir / "plan.md"
        assert context.tasks_path == feature_dir / "tasks.md"
        assert context.research_path == feature_dir / "research.md"
        assert context.data_model_path == feature_dir / "data-model.md"
        assert context.quickstart_path == feature_dir / "quickstart.md"
        assert context.contracts_dir == feature_dir / "contracts"
    
    def test_uses_prefix_based_lookup(self, temp_repo):
        """Uses prefix-based lookup to find feature directory."""
        # Arrange: Create feature with different branch name
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        feature_dir = specs_dir / "002-actual-feature"
        feature_dir.mkdir()
        
        # Act: Use different branch name with same prefix
        context = get_feature_paths(temp_repo, "002-working-branch")
        
        # Assert: Should find the feature directory by prefix
        assert context.feature_dir == feature_dir
        assert context.branch == "002-working-branch"
    
    def test_paths_are_absolute(self, temp_repo):
        """All returned paths are absolute."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        (specs_dir / "003-feature").mkdir()
        
        # Act
        context = get_feature_paths(temp_repo, "003-feature")
        
        # Assert
        assert context.repo_root.is_absolute()
        assert context.feature_dir.is_absolute()
        assert context.spec_path.is_absolute()
        assert context.plan_path.is_absolute()
        assert context.tasks_path.is_absolute()
    
    def test_context_is_immutable(self, temp_repo):
        """FeatureContext is frozen and cannot be modified."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        (specs_dir / "004-feature").mkdir()
        
        context = get_feature_paths(temp_repo, "004-feature")
        
        # Act & Assert
        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            context.branch = "modified"


class TestEdgeCases:
    """Edge case tests for path utilities."""
    
    def test_handles_unicode_in_branch_names(self, temp_repo):
        """Handles Unicode characters in branch names."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        unicode_feature = specs_dir / "001-feature-émojis-🚀"
        unicode_feature.mkdir()
        
        # Act
        result = find_feature_dir_by_prefix(temp_repo, "001-unicode-branch")
        
        # Assert
        assert result == unicode_feature
    
    def test_handles_very_long_branch_names(self, temp_repo):
        """Handles very long branch names."""
        # Arrange
        long_name = "001-" + "a" * 200
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        long_dir = specs_dir / long_name
        long_dir.mkdir()
        
        # Act
        result = find_feature_dir_by_prefix(temp_repo, "001-branch")
        
        # Assert
        assert result == long_dir
    
    def test_handles_paths_with_spaces(self, temp_dir):
        """Handles repository paths with spaces."""
        # Arrange: Create git repo in path with spaces
        repo_with_spaces = temp_dir / "repo with spaces"
        repo_with_spaces.mkdir()
        subprocess.run(["git", "init"], cwd=repo_with_spaces, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_with_spaces, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_with_spaces, check=True, capture_output=True)
        
        # Create initial commit
        (repo_with_spaces / "README.md").write_text("Test")
        subprocess.run(["git", "add", "."], cwd=repo_with_spaces, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo_with_spaces, check=True, capture_output=True)
        
        original_cwd = Path.cwd()
        try:
            os.chdir(repo_with_spaces)
            
            # Act
            result = get_repo_root()
            
            # Assert
            assert result == repo_with_spaces
        finally:
            os.chdir(original_cwd)
