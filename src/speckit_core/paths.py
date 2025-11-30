"""
Repository and feature path utilities.

This module provides functions for discovering git repository roots,
current branches, and feature directory structures used by SpecKit.
"""

import os
import re
import subprocess
from pathlib import Path

from .exceptions import NotInGitRepoError, FeatureNotFoundError
from .models import FeatureContext

__all__ = [
    "get_repo_root",
    "get_current_branch",
    "get_feature_paths",
    "find_feature_dir_by_prefix",
]


def get_repo_root() -> Path:
    """Get the root directory of the current git repository.
    
    Uses `git rev-parse --show-toplevel` to find the repository root.
    
    Returns:
        Path to the repository root.
        
    Raises:
        NotInGitRepoError: If not inside a git repository or git is not available.
        
    Example:
        >>> repo_root = get_repo_root()
        >>> assert repo_root.is_dir()
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise NotInGitRepoError(
            "Not inside a git repository. Run 'git init' to create one."
        ) from e
    except FileNotFoundError as e:
        raise NotInGitRepoError(
            "Git command not found. Please install git and try again."
        ) from e


def get_current_branch() -> str:
    """Get the current git branch name.
    
    First checks the SPECIFY_FEATURE environment variable, then falls back
    to git. If neither is available, returns "main" as a default.
    
    Returns:
        Current branch name.
        
    Raises:
        NotInGitRepoError: If not inside a git repository and SPECIFY_FEATURE is not set.
        
    Example:
        >>> branch = get_current_branch()
        >>> assert isinstance(branch, str)
    """
    # First check environment variable
    specify_feature = os.environ.get("SPECIFY_FEATURE", "").strip()
    if specify_feature:
        return specify_feature
    
    # Try git
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise NotInGitRepoError(
            "Not inside a git repository and SPECIFY_FEATURE environment variable not set."
        ) from e
    except FileNotFoundError as e:
        raise NotInGitRepoError(
            "Git command not found and SPECIFY_FEATURE environment variable not set."
        ) from e


def get_feature_paths(repo_root: Path, branch: str) -> FeatureContext:
    """Get all standard paths for a feature.
    
    Uses prefix-based lookup to support multiple branches working on the same spec
    (e.g., "004-fix-bug" and "004-add-feature" both map to "004-feature-name").
    
    Args:
        repo_root: Repository root directory.
        branch: Branch/feature name.
        
    Returns:
        FeatureContext with all standard paths including:
        - repo_root: Repository root
        - branch: Branch name
        - feature_dir: Feature directory path
        - spec_path: spec.md path
        - plan_path: plan.md path
        - tasks_path: tasks.md path
        - research_path: research.md path (optional)
        - data_model_path: data-model.md path (optional)
        - quickstart_path: quickstart.md path (optional)
        - contracts_dir: contracts/ directory path (optional)
        
    Example:
        >>> repo = Path("/path/to/repo")
        >>> context = get_feature_paths(repo, "001-my-feature")
        >>> assert context.spec_path == repo / "specs" / "001-my-feature" / "spec.md"
    """
    # Use prefix-based lookup for the feature directory
    feature_dir = find_feature_dir_by_prefix(repo_root, branch)
    
    return FeatureContext(
        repo_root=repo_root,
        branch=branch,
        feature_dir=feature_dir,
        spec_path=feature_dir / "spec.md",
        plan_path=feature_dir / "plan.md",
        tasks_path=feature_dir / "tasks.md",
        research_path=feature_dir / "research.md",
        data_model_path=feature_dir / "data-model.md",
        quickstart_path=feature_dir / "quickstart.md",
        contracts_dir=feature_dir / "contracts",
    )


def find_feature_dir_by_prefix(repo_root: Path, branch: str) -> Path:
    """Find feature directory by numeric prefix.
    
    Allows multiple branches to work on the same spec by matching the numeric
    prefix (e.g., "004-fix-bug" and "004-add-feature" both map to "004-feature-name").
    
    If the branch name doesn't have a numeric prefix, returns the exact match.
    If multiple directories match the prefix, raises an error.
    
    Args:
        repo_root: Repository root directory.
        branch: Branch name, optionally with numeric prefix (e.g., "004-feature-name").
        
    Returns:
        Path to matching feature directory.
        
    Raises:
        FeatureNotFoundError: If no matching feature directory found.
        ValueError: If multiple directories match the same numeric prefix.
        
    Example:
        >>> repo = Path("/path/to/repo")
        >>> # Exact match if no prefix
        >>> path = find_feature_dir_by_prefix(repo, "my-feature")
        >>> assert path == repo / "specs" / "my-feature"
        >>> 
        >>> # Prefix match with numeric prefix
        >>> path = find_feature_dir_by_prefix(repo, "004-fix-bug")
        >>> # Returns first match like "004-feature-name"
    """
    specs_dir = repo_root / "specs"
    
    # Extract numeric prefix (e.g., "004" from "004-whatever")
    prefix_match = re.match(r"^(\d{3})-", branch)
    
    if not prefix_match:
        # No numeric prefix - return exact match path
        return specs_dir / branch
    
    prefix = prefix_match.group(1)
    
    # Search for directories with this prefix
    matches: list[Path] = []
    if specs_dir.exists():
        for item in specs_dir.iterdir():
            if item.is_dir() and item.name.startswith(f"{prefix}-"):
                matches.append(item)
    
    # Handle results
    if len(matches) == 0:
        # No match found
        raise FeatureNotFoundError(
            f"No feature directory found with prefix '{prefix}' in {specs_dir}.\n"
            f"Looking for directories matching pattern: {prefix}-*\n"
            f"Available directories: {', '.join(d.name for d in specs_dir.iterdir() if d.is_dir()) if specs_dir.exists() else 'none'}"
        )
    elif len(matches) == 1:
        # Exactly one match - perfect!
        return matches[0]
    else:
        # Multiple matches - this shouldn't happen with proper naming convention
        raise ValueError(
            f"Multiple spec directories found with prefix '{prefix}': {', '.join(m.name for m in matches)}.\n"
            "Please ensure only one spec directory exists per numeric prefix."
        )
