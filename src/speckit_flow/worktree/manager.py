"""
Git worktree management for SpecKitFlow.

This module provides the WorktreeManager class for creating and managing
git worktrees used for parallel implementation sessions.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from speckit_flow.exceptions import WorktreeExistsError

__all__ = ["WorktreeManager", "WorktreeInfo"]


# Maximum length for directory name components to avoid filesystem issues
MAX_TASK_NAME_LENGTH = 50


@dataclass
class WorktreeInfo:
    """Information about a git worktree.
    
    Attributes:
        path: Path to the worktree directory
        branch: Branch name checked out in the worktree
        commit: SHA of the HEAD commit in the worktree
        locked: Whether the worktree is locked
    """
    path: Path
    branch: str
    commit: str
    locked: bool


class WorktreeManager:
    """Manages git worktrees for parallel implementation sessions.
    
    This class handles creation, listing, and removal of git worktrees
    that isolate each parallel session's work. Each worktree gets its
    own branch and directory under .worktrees-{spec-id}/.
    
    Attributes:
        repo_root: Path to the repository root directory
        
    Example:
        >>> manager = WorktreeManager(Path("/path/to/repo"))
        >>> worktree_path = manager.create("001-feature", 0, "setup-database")
        >>> print(worktree_path)
        /path/to/repo/.worktrees-001-feature/session-0-setup-database
    """
    
    def __init__(self, repo_root: Path):
        """Initialize worktree manager.
        
        Args:
            repo_root: Path to the repository root
        """
        self.repo_root = Path(repo_root).resolve()
    
    def create(self, spec_id: str, session_id: int, task_name: str) -> Path:
        """Create a new git worktree for a session.
        
        Creates a new git worktree at .worktrees-{spec_id}/session-{session_id}-{task_name}/
        with a corresponding branch impl-{spec_id}-session-{session_id}.
        
        The task_name is sanitized to remove special characters and truncated
        if necessary to avoid filesystem path length issues.
        
        Args:
            spec_id: Specification identifier (e.g., "001-feature-name")
            session_id: Session number (0-based)
            task_name: Human-readable task name for directory
            
        Returns:
            Path to the created worktree directory
            
        Raises:
            WorktreeExistsError: If worktree already exists at the target path
            subprocess.CalledProcessError: If git command fails
            
        Example:
            >>> manager = WorktreeManager(Path("/repo"))
            >>> path = manager.create("001-auth", 0, "implement-login")
            >>> assert path.exists()
            >>> assert (path / ".git").exists()
        """
        # Sanitize task name for filesystem
        safe_task_name = self._sanitize_task_name(task_name)
        
        # Create worktree and branch names
        branch_name = f"impl-{spec_id}-session-{session_id}"
        worktree_dirname = f"session-{session_id}-{safe_task_name}"
        worktrees_base = self.repo_root / f".worktrees-{spec_id}"
        worktree_path = worktrees_base / worktree_dirname
        
        # Check if worktree already exists
        if worktree_path.exists():
            raise WorktreeExistsError(
                f"Worktree already exists at: {worktree_path}\n"
                f"Remove it first with: git worktree remove {worktree_path}"
            )
        
        # Create worktrees base directory if needed
        worktrees_base.mkdir(parents=True, exist_ok=True)
        
        # Create the worktree with new branch
        # Use -b to create a new branch from current HEAD
        try:
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    branch_name,
                    str(worktree_path),
                ],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            # Provide helpful error message
            error_msg = e.stderr.strip() if e.stderr else str(e)
            if "already exists" in error_msg.lower():
                # Branch exists - this might be a resume scenario
                # For now, raise with clear message
                raise WorktreeExistsError(
                    f"Branch '{branch_name}' already exists.\n"
                    f"If resuming, use git worktree add without -b flag.\n"
                    f"To start fresh, delete the branch first: git branch -D {branch_name}"
                ) from e
            else:
                # Re-raise with original error for other git failures
                raise
        
        return worktree_path
    
    def _sanitize_task_name(self, task_name: str) -> str:
        """Sanitize task name for use in filesystem paths.
        
        Removes special characters, converts to lowercase, and truncates
        to a reasonable length to avoid path issues.
        
        Args:
            task_name: Original task name
            
        Returns:
            Sanitized task name safe for filesystem use
            
        Example:
            >>> manager = WorktreeManager(Path("/repo"))
            >>> manager._sanitize_task_name("Implement User Authentication (OAuth)")
            'implement-user-authentication-oauth'
            >>> manager._sanitize_task_name("Very " * 20 + "Long Task Name")
            'very-very-very-very-very-very-very-very-very-very'
        """
        # Convert to lowercase
        name = task_name.lower()
        
        # Replace non-alphanumeric characters with hyphens
        name = re.sub(r"[^a-z0-9]+", "-", name)
        
        # Remove leading/trailing hyphens
        name = name.strip("-")
        
        # Truncate to maximum length
        if len(name) > MAX_TASK_NAME_LENGTH:
            name = name[:MAX_TASK_NAME_LENGTH].rstrip("-")
        
        # Ensure we have a valid name (fallback if sanitization removed everything)
        if not name:
            name = "task"
        
        return name
    
    def list(self) -> list[WorktreeInfo]:
        """List all git worktrees in the repository.
        
        Parses the output of `git worktree list --porcelain` to extract
        information about all worktrees, including the main worktree.
        
        Returns:
            List of WorktreeInfo objects for all worktrees
            
        Raises:
            subprocess.CalledProcessError: If git command fails
            
        Example:
            >>> manager = WorktreeManager(Path("/repo"))
            >>> worktrees = manager.list()
            >>> for wt in worktrees:
            ...     print(f"{wt.branch} at {wt.path}")
        """
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            # If git worktree list fails, return empty list
            # (might not be in a git repo or git version too old)
            return []
        
        return self._parse_worktree_list(result.stdout)
    
    def _parse_worktree_list(self, porcelain_output: str) -> list[WorktreeInfo]:
        """Parse git worktree list --porcelain output.
        
        The porcelain format outputs one worktree per block, separated by
        blank lines. Each block contains key-value pairs:
        
        worktree /path/to/worktree
        HEAD abc123...
        branch refs/heads/branch-name
        
        Or for detached HEAD:
        
        worktree /path/to/worktree
        HEAD abc123...
        detached
        
        Locked worktrees have an additional line:
        locked reason for locking
        
        Args:
            porcelain_output: Output from git worktree list --porcelain
            
        Returns:
            List of parsed WorktreeInfo objects
        """
        worktrees = []
        lines = porcelain_output.strip().split("\n")
        
        i = 0
        while i < len(lines):
            # Skip blank lines
            if not lines[i].strip():
                i += 1
                continue
            
            # Parse a worktree block
            worktree_path: Optional[Path] = None
            commit: Optional[str] = None
            branch: Optional[str] = None
            locked = False
            
            # Process lines until we hit a blank line or EOF
            while i < len(lines) and lines[i].strip():
                line = lines[i].strip()
                
                if line.startswith("worktree "):
                    worktree_path = Path(line[9:])  # Remove "worktree " prefix
                elif line.startswith("HEAD "):
                    commit = line[5:]  # Remove "HEAD " prefix
                elif line.startswith("branch "):
                    # Extract branch name from refs/heads/branch-name
                    branch_ref = line[7:]  # Remove "branch " prefix
                    if branch_ref.startswith("refs/heads/"):
                        branch = branch_ref[11:]  # Remove "refs/heads/" prefix
                    else:
                        branch = branch_ref
                elif line == "detached":
                    branch = "(detached)"
                elif line.startswith("locked"):
                    locked = True
                
                i += 1
            
            # Create WorktreeInfo if we have all required fields
            if worktree_path and commit:
                worktrees.append(WorktreeInfo(
                    path=worktree_path,
                    branch=branch or "(unknown)",
                    commit=commit,
                    locked=locked,
                ))
            
            # Move to next block
            i += 1
        
        return worktrees
    
    def remove(self, path: Path) -> None:
        """Remove a git worktree.
        
        Removes the worktree at the specified path. The worktree must be
        clean (no uncommitted changes) for this to succeed.
        
        Args:
            path: Path to the worktree to remove
            
        Raises:
            subprocess.CalledProcessError: If git command fails (e.g., dirty worktree)
            
        Example:
            >>> manager = WorktreeManager(Path("/repo"))
            >>> manager.remove(Path("/repo/.worktrees-001/session-0-setup"))
        """
        subprocess.run(
            ["git", "worktree", "remove", str(path)],
            cwd=self.repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    
    def remove_force(self, path: Path) -> None:
        """Force remove a git worktree.
        
        Removes the worktree even if it has uncommitted changes or other
        issues. Use with caution as this can lose work.
        
        Args:
            path: Path to the worktree to remove
            
        Raises:
            subprocess.CalledProcessError: If git command fails
            
        Example:
            >>> manager = WorktreeManager(Path("/repo"))
            >>> manager.remove_force(Path("/repo/.worktrees-001/session-0-setup"))
        """
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(path)],
            cwd=self.repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    
    def get_spec_worktrees(self, spec_id: str) -> list[WorktreeInfo]:
        """Get all worktrees for a specific spec.
        
        Filters the list of all worktrees to return only those belonging
        to the specified spec_id (those in .worktrees-{spec_id}/ directory).
        
        Args:
            spec_id: Specification identifier (e.g., "001-feature-name")
            
        Returns:
            List of WorktreeInfo objects for the spec's worktrees
            
        Example:
            >>> manager = WorktreeManager(Path("/repo"))
            >>> spec_worktrees = manager.get_spec_worktrees("001-auth")
            >>> print(f"Found {len(spec_worktrees)} worktrees for spec 001-auth")
        """
        all_worktrees = self.list()
        spec_base = self.repo_root / f".worktrees-{spec_id}"
        
        # Filter worktrees that are under the spec's directory
        spec_worktrees = [
            wt for wt in all_worktrees
            if self._is_path_under(wt.path, spec_base)
        ]
        
        return spec_worktrees
    
    def _is_path_under(self, path: Path, parent: Path) -> bool:
        """Check if a path is under a parent directory.
        
        Args:
            path: Path to check
            parent: Potential parent directory
            
        Returns:
            True if path is under parent, False otherwise
        """
        try:
            path.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False
    
    def cleanup_spec(self, spec_id: str) -> int:
        """Remove all worktrees for a specific spec.
        
        Removes all worktrees under .worktrees-{spec_id}/ and then deletes
        the parent directory. Worktrees are removed forcefully to ensure
        cleanup succeeds even if there are uncommitted changes.
        
        Args:
            spec_id: Specification identifier (e.g., "001-feature-name")
            
        Returns:
            Number of worktrees removed
            
        Example:
            >>> manager = WorktreeManager(Path("/repo"))
            >>> count = manager.cleanup_spec("001-auth")
            >>> print(f"Removed {count} worktrees for spec 001-auth")
        """
        spec_worktrees = self.get_spec_worktrees(spec_id)
        removed_count = 0
        
        # Remove each worktree (force to ensure cleanup)
        for worktree in spec_worktrees:
            try:
                self.remove_force(worktree.path)
                removed_count += 1
            except subprocess.CalledProcessError:
                # Continue even if one fails - try to clean up as much as possible
                pass
        
        # Remove the parent directory if it exists and is empty (or force remove contents)
        spec_base = self.repo_root / f".worktrees-{spec_id}"
        if spec_base.exists():
            try:
                # Try to remove directory - will work if empty
                spec_base.rmdir()
            except OSError:
                # Directory not empty or other error - try to remove recursively
                import shutil
                try:
                    shutil.rmtree(spec_base)
                except Exception:
                    # If we can't remove the directory, that's okay
                    # The worktrees themselves are gone which is most important
                    pass
        
        return removed_count
