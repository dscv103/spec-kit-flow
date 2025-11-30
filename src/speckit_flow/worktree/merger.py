"""
Branch merge orchestration for SpecKitFlow.

This module provides the MergeOrchestrator class for analyzing and merging
session branches created during parallel implementation. It detects potential
conflicts before merging and provides detailed analysis of changes.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__all__ = ["MergeOrchestrator", "MergeAnalysis", "SessionChanges", "MergeResult"]


@dataclass
class SessionChanges:
    """File changes for a single session branch.
    
    Attributes:
        session_id: Session number (0-based)
        branch_name: Git branch name
        added_files: Set of file paths added in this session
        modified_files: Set of file paths modified in this session
        deleted_files: Set of file paths deleted in this session
        all_changed_files: Set of all changed file paths (union of above)
    """
    session_id: int
    branch_name: str
    added_files: set[str] = field(default_factory=set)
    modified_files: set[str] = field(default_factory=set)
    deleted_files: set[str] = field(default_factory=set)
    
    @property
    def all_changed_files(self) -> set[str]:
        """Get all changed files across all change types."""
        return self.added_files | self.modified_files | self.deleted_files


@dataclass
class MergeAnalysis:
    """Analysis of changes across session branches.
    
    Provides detailed information about file changes per session and
    identifies potential merge conflicts where multiple sessions modified
    the same files.
    
    Attributes:
        base_branch: Base branch used for comparison
        session_changes: List of SessionChanges for each session
        overlapping_files: Dict mapping file paths to list of session IDs that modified them
        safe_to_merge: True if no overlapping changes detected
        total_files_changed: Total number of unique files changed across all sessions
    """
    base_branch: str
    session_changes: list[SessionChanges]
    overlapping_files: dict[str, list[int]] = field(default_factory=dict)
    
    @property
    def safe_to_merge(self) -> bool:
        """Check if merge is safe (no overlapping changes)."""
        return len(self.overlapping_files) == 0
    
    @property
    def total_files_changed(self) -> int:
        """Get total number of unique files changed across all sessions."""
        all_files: set[str] = set()
        for session in self.session_changes:
            all_files.update(session.all_changed_files)
        return len(all_files)


@dataclass
class MergeResult:
    """Result of merge operation.
    
    Captures the outcome of merging session branches into an integration branch.
    
    Attributes:
        success: True if merge completed successfully
        integration_branch: Name of the integration branch created
        merged_sessions: List of session IDs that were successfully merged
        conflict_session: Session ID where conflict occurred (None if no conflict)
        conflicting_files: List of files with merge conflicts (empty if no conflicts)
        error_message: Human-readable error message (None if successful)
    """
    success: bool
    integration_branch: str
    merged_sessions: list[int] = field(default_factory=list)
    conflict_session: Optional[int] = None
    conflicting_files: list[str] = field(default_factory=list)
    error_message: Optional[str] = None


class MergeOrchestrator:
    """Orchestrates merging of session branches after parallel implementation.
    
    This class analyzes changes across session branches to detect potential
    conflicts before merging. It identifies files modified by multiple sessions
    and categorizes changes as safe or requiring manual review.
    
    Attributes:
        spec_id: Specification identifier (e.g., "001-feature-name")
        repo_root: Path to the repository root
        
    Example:
        >>> orchestrator = MergeOrchestrator("001-auth", Path("/path/to/repo"))
        >>> analysis = orchestrator.analyze()
        >>> if analysis.safe_to_merge:
        ...     print("Safe to merge!")
        ... else:
        ...     print(f"Conflicts in: {list(analysis.overlapping_files.keys())}")
    """
    
    def __init__(self, spec_id: str, repo_root: Path):
        """Initialize merge orchestrator.
        
        Args:
            spec_id: Specification identifier (e.g., "001-feature-name")
            repo_root: Path to the repository root
        """
        self.spec_id = spec_id
        self.repo_root = Path(repo_root).resolve()
    
    def analyze(self, base_branch: Optional[str] = None) -> MergeAnalysis:
        """Analyze changes across session branches.
        
        Compares each session branch against the base branch to identify:
        - Which files were added, modified, or deleted per session
        - Which files were modified by multiple sessions (potential conflicts)
        - Whether the merge is safe to proceed automatically
        
        Args:
            base_branch: Base branch to compare against (default: current branch or "main")
            
        Returns:
            MergeAnalysis with detailed change information
            
        Raises:
            subprocess.CalledProcessError: If git commands fail
            RuntimeError: If no session branches found for spec_id
            
        Example:
            >>> orchestrator = MergeOrchestrator("001-auth", Path("/repo"))
            >>> analysis = orchestrator.analyze()
            >>> for session in analysis.session_changes:
            ...     print(f"Session {session.session_id}: {len(session.all_changed_files)} files")
        """
        # Determine base branch
        if base_branch is None:
            base_branch = self._get_current_branch()
        
        # Find all session branches for this spec
        session_branches = self._find_session_branches()
        
        if not session_branches:
            raise RuntimeError(
                f"No session branches found for spec '{self.spec_id}'. "
                f"Expected branches matching pattern: impl-{self.spec_id}-session-*"
            )
        
        # Analyze changes for each session
        session_changes_list: list[SessionChanges] = []
        for session_id, branch_name in sorted(session_branches.items()):
            changes = self._get_branch_changes(base_branch, branch_name, session_id)
            session_changes_list.append(changes)
        
        # Detect overlapping file modifications
        overlapping_files = self._detect_overlaps(session_changes_list)
        
        return MergeAnalysis(
            base_branch=base_branch,
            session_changes=session_changes_list,
            overlapping_files=overlapping_files,
        )
    
    def _get_current_branch(self) -> str:
        """Get the current git branch name.
        
        Returns:
            Current branch name
            
        Raises:
            subprocess.CalledProcessError: If git command fails
            RuntimeError: If in detached HEAD state
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            branch = result.stdout.strip()
            
            if branch == "HEAD":
                # Detached HEAD state - use main as fallback
                return "main"
            
            return branch
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get current branch: {e.stderr}") from e
    
    def _find_session_branches(self) -> dict[int, str]:
        """Find all session branches for this spec.
        
        Looks for branches matching the pattern: impl-{spec_id}-session-{N}
        
        Returns:
            Dictionary mapping session_id to branch_name
            
        Example:
            >>> orchestrator._find_session_branches()
            {0: "impl-001-auth-session-0", 1: "impl-001-auth-session-1"}
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--list", f"impl-{self.spec_id}-session-*"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            return {}
        
        branches: dict[int, str] = {}
        prefix = f"impl-{self.spec_id}-session-"
        
        for line in result.stdout.splitlines():
            branch = line.strip().lstrip("* ").strip()
            if branch.startswith(prefix):
                # Extract session number
                try:
                    session_id = int(branch[len(prefix):])
                    branches[session_id] = branch
                except ValueError:
                    # Skip branches that don't match the expected pattern
                    continue
        
        return branches
    
    def _get_branch_changes(
        self,
        base_branch: str,
        compare_branch: str,
        session_id: int,
    ) -> SessionChanges:
        """Get file changes between base and compare branches.
        
        Uses git diff to identify added, modified, and deleted files.
        
        Args:
            base_branch: Base branch for comparison
            compare_branch: Branch to compare against base
            session_id: Session ID for this branch
            
        Returns:
            SessionChanges with categorized file changes
            
        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        # Get diff between branches
        # Format: --name-status shows file status (A/M/D) and path
        try:
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--name-status",
                    f"{base_branch}...{compare_branch}",
                ],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            # Branch might not exist or other git error
            raise RuntimeError(
                f"Failed to get changes for branch '{compare_branch}': {e.stderr}"
            ) from e
        
        changes = SessionChanges(
            session_id=session_id,
            branch_name=compare_branch,
        )
        
        # Parse diff output
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            
            status, filepath = parts
            
            # Categorize by status
            if status.startswith("A"):
                changes.added_files.add(filepath)
            elif status.startswith("M"):
                changes.modified_files.add(filepath)
            elif status.startswith("D"):
                changes.deleted_files.add(filepath)
            elif status.startswith("R"):
                # Renamed files - treat as modified
                # Format is "R100\told\tnew" - extract new path
                if "\t" in filepath:
                    new_path = filepath.split("\t")[-1]
                    changes.modified_files.add(new_path)
                else:
                    changes.modified_files.add(filepath)
        
        return changes
    
    def _detect_overlaps(
        self,
        session_changes_list: list[SessionChanges],
    ) -> dict[str, list[int]]:
        """Detect files modified by multiple sessions.
        
        Args:
            session_changes_list: List of changes for each session
            
        Returns:
            Dictionary mapping file paths to list of session IDs that modified them.
            Only includes files modified by 2+ sessions.
            
        Example:
            >>> overlaps = orchestrator._detect_overlaps(session_changes)
            >>> print(overlaps)
            {"src/auth.py": [0, 1], "README.md": [0, 2]}
        """
        # Build mapping of file -> list of session IDs that touched it
        file_to_sessions: dict[str, list[int]] = {}
        
        for session in session_changes_list:
            for filepath in session.all_changed_files:
                if filepath not in file_to_sessions:
                    file_to_sessions[filepath] = []
                file_to_sessions[filepath].append(session.session_id)
        
        # Filter to only files modified by multiple sessions
        overlapping = {
            filepath: session_ids
            for filepath, session_ids in file_to_sessions.items()
            if len(session_ids) > 1
        }
        
        return overlapping
    
    def merge_sequential(
        self,
        base_branch: Optional[str] = None,
    ) -> MergeResult:
        """Merge session branches sequentially into integration branch.
        
        Creates an integration branch from the base branch and merges each
        session branch in order (0, 1, 2, ...). Uses --no-ff to preserve
        branch history. If a merge conflict occurs, stops and returns details
        about the conflict.
        
        The repository is left in a clean state on failure (integration branch
        is deleted if merge fails).
        
        Args:
            base_branch: Base branch to merge from (default: current branch or "main")
            
        Returns:
            MergeResult with success status and merge details
            
        Raises:
            RuntimeError: If no session branches found or git operations fail
            
        Example:
            >>> orchestrator = MergeOrchestrator("001-auth", Path("/repo"))
            >>> result = orchestrator.merge_sequential()
            >>> if result.success:
            ...     print(f"Merged {len(result.merged_sessions)} sessions")
            ... else:
            ...     print(f"Conflict in session {result.conflict_session}")
        """
        # Determine base branch
        if base_branch is None:
            base_branch = self._get_current_branch()
        
        # Find all session branches for this spec
        session_branches = self._find_session_branches()
        
        if not session_branches:
            raise RuntimeError(
                f"No session branches found for spec '{self.spec_id}'. "
                f"Expected branches matching pattern: impl-{self.spec_id}-session-*"
            )
        
        # Create integration branch name
        integration_branch = f"impl-{self.spec_id}-integrated"
        
        # Check if integration branch already exists
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", integration_branch],
                cwd=self.repo_root,
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                raise RuntimeError(
                    f"Integration branch '{integration_branch}' already exists. "
                    "Delete it first or use a different spec_id."
                )
        except Exception as e:
            if "already exists" in str(e):
                raise
            # Other errors are fine (branch doesn't exist)
        
        # Create integration branch from base
        try:
            subprocess.run(
                ["git", "checkout", "-b", integration_branch, base_branch],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to create integration branch '{integration_branch}': {e.stderr}"
            ) from e
        
        # Track successfully merged sessions
        merged_sessions: list[int] = []
        
        # Merge each session branch in order
        for session_id, branch_name in sorted(session_branches.items()):
            try:
                # Attempt merge with --no-ff to preserve history
                result = subprocess.run(
                    [
                        "git",
                        "merge",
                        "--no-ff",
                        "-m",
                        f"Merge session {session_id} ({branch_name})",
                        branch_name,
                    ],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,  # Don't raise on non-zero exit
                )
                
                if result.returncode != 0:
                    # Merge conflict occurred
                    conflicting_files = self._get_conflicting_files()
                    
                    # Abort the merge to leave repo in clean state
                    subprocess.run(
                        ["git", "merge", "--abort"],
                        cwd=self.repo_root,
                        capture_output=True,
                        check=False,
                    )
                    
                    # Delete integration branch (checkout base first)
                    subprocess.run(
                        ["git", "checkout", base_branch],
                        cwd=self.repo_root,
                        capture_output=True,
                        check=False,
                    )
                    subprocess.run(
                        ["git", "branch", "-D", integration_branch],
                        cwd=self.repo_root,
                        capture_output=True,
                        check=False,
                    )
                    
                    return MergeResult(
                        success=False,
                        integration_branch=integration_branch,
                        merged_sessions=merged_sessions,
                        conflict_session=session_id,
                        conflicting_files=conflicting_files,
                        error_message=(
                            f"Merge conflict occurred when merging session {session_id} "
                            f"({branch_name}). Conflicting files: {', '.join(conflicting_files)}"
                        ),
                    )
                
                # Merge succeeded
                merged_sessions.append(session_id)
                
            except subprocess.CalledProcessError as e:
                # Unexpected git error (not a conflict)
                # Clean up integration branch
                subprocess.run(
                    ["git", "checkout", base_branch],
                    cwd=self.repo_root,
                    capture_output=True,
                    check=False,
                )
                subprocess.run(
                    ["git", "branch", "-D", integration_branch],
                    cwd=self.repo_root,
                    capture_output=True,
                    check=False,
                )
                
                raise RuntimeError(
                    f"Git error during merge of session {session_id}: {e.stderr}"
                ) from e
        
        # All merges successful
        return MergeResult(
            success=True,
            integration_branch=integration_branch,
            merged_sessions=merged_sessions,
        )
    
    def _get_conflicting_files(self) -> list[str]:
        """Get list of files with merge conflicts.
        
        Returns:
            List of file paths with unresolved conflicts
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            
            files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return files
        except subprocess.CalledProcessError:
            # If command fails, return empty list
            return []
    
    def validate(self, test_cmd: Optional[str] = None) -> tuple[bool, str]:
        """Run validation tests in the integration branch.
        
        Executes a test command in the integration branch to verify
        that the merged code is correct. If no test command is provided,
        validation is considered successful.
        
        Args:
            test_cmd: Shell command to run for validation (e.g., "pytest", "npm test").
                     None skips validation.
                     
        Returns:
            Tuple of (success, output):
                - success: True if tests passed or no test_cmd provided
                - output: Command output (stdout + stderr combined)
                
        Example:
            >>> orchestrator = MergeOrchestrator("001-auth", Path("/repo"))
            >>> result = orchestrator.merge_sequential()
            >>> if result.success:
            ...     success, output = orchestrator.validate("pytest tests/")
            ...     if success:
            ...         print("All tests passed!")
        """
        if test_cmd is None:
            # No validation requested - consider it successful
            return (True, "No validation command provided - skipping tests")
        
        integration_branch = f"impl-{self.spec_id}-integrated"
        
        try:
            # Ensure we're on the integration branch
            subprocess.run(
                ["git", "checkout", integration_branch],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            
            # Run the test command using shell=True to support complex commands
            result = subprocess.run(
                test_cmd,
                cwd=self.repo_root,
                shell=True,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
            )
            
            # Combine stdout and stderr for output
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            
            success = result.returncode == 0
            
            return (success, output)
            
        except subprocess.CalledProcessError as e:
            # Git checkout failed
            error_output = f"Failed to checkout integration branch: {e.stderr}"
            return (False, error_output)
        except Exception as e:
            # Other unexpected error
            error_output = f"Unexpected error during validation: {str(e)}"
            return (False, error_output)
    
    def finalize(self, keep_worktrees: bool = False) -> dict[str, int | str]:
        """Finalize the merge by cleaning up worktrees and generating summary.
        
        Removes session worktrees (unless keep_worktrees=True) and the parent
        .worktrees-{spec_id}/ directory. Generates a summary of the merge
        including file statistics.
        
        Args:
            keep_worktrees: If True, preserve worktrees instead of deleting them.
                           Useful for debugging or manual inspection.
                           
        Returns:
            Dictionary with merge summary:
                - worktrees_removed: Number of worktrees deleted (0 if kept)
                - files_changed: Number of unique files changed
                - lines_added: Total lines added across all changes
                - lines_deleted: Total lines deleted across all changes
                - integration_branch: Name of the integration branch
                
        Example:
            >>> orchestrator = MergeOrchestrator("001-auth", Path("/repo"))
            >>> result = orchestrator.merge_sequential()
            >>> if result.success:
            ...     summary = orchestrator.finalize(keep_worktrees=False)
            ...     print(f"Merged {summary['files_changed']} files")
        """
        integration_branch = f"impl-{self.spec_id}-integrated"
        
        # Get statistics before cleanup
        stats = self._get_merge_statistics(integration_branch)
        
        # Clean up worktrees unless user wants to keep them
        worktrees_removed = 0
        if not keep_worktrees:
            worktrees_removed = self._cleanup_worktrees()
        
        return {
            "worktrees_removed": worktrees_removed,
            "files_changed": stats["files_changed"],
            "lines_added": stats["lines_added"],
            "lines_deleted": stats["lines_deleted"],
            "integration_branch": integration_branch,
        }
    
    def _get_merge_statistics(self, integration_branch: str) -> dict[str, int]:
        """Get statistics about the merged changes.
        
        Uses git diff to calculate the number of files changed and
        lines added/deleted in the integration branch compared to base.
        
        Args:
            integration_branch: Name of the integration branch
            
        Returns:
            Dictionary with statistics:
                - files_changed: Number of unique files changed
                - lines_added: Total lines added
                - lines_deleted: Total lines deleted
        """
        try:
            # Get base branch by finding the merge-base
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", f"{integration_branch}@{{u}}"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                # Has upstream tracking branch
                base_branch = result.stdout.strip().split("/")[-1]
            else:
                # No tracking branch, use the current branch or main
                base_branch = self._get_current_branch()
            
            # Get merge-base to compare from common ancestor
            merge_base_result = subprocess.run(
                ["git", "merge-base", base_branch, integration_branch],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            
            if merge_base_result.returncode == 0:
                base_ref = merge_base_result.stdout.strip()
            else:
                # Fallback to base branch name
                base_ref = base_branch
            
            # Get diff statistics
            diff_result = subprocess.run(
                ["git", "diff", "--shortstat", base_ref, integration_branch],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            
            # Parse shortstat output: "N files changed, X insertions(+), Y deletions(-)"
            stats = {
                "files_changed": 0,
                "lines_added": 0,
                "lines_deleted": 0,
            }
            
            if diff_result.returncode == 0 and diff_result.stdout.strip():
                shortstat = diff_result.stdout.strip()
                
                # Extract files changed
                if "file" in shortstat:
                    parts = shortstat.split(",")
                    files_part = parts[0].strip()
                    stats["files_changed"] = int(files_part.split()[0])
                
                # Extract insertions
                if "insertion" in shortstat:
                    for part in shortstat.split(","):
                        if "insertion" in part:
                            stats["lines_added"] = int(part.strip().split()[0])
                            break
                
                # Extract deletions
                if "deletion" in shortstat:
                    for part in shortstat.split(","):
                        if "deletion" in part:
                            stats["lines_deleted"] = int(part.strip().split()[0])
                            break
            
            return stats
            
        except Exception:
            # If statistics gathering fails, return zeros
            return {
                "files_changed": 0,
                "lines_added": 0,
                "lines_deleted": 0,
            }
    
    def _cleanup_worktrees(self) -> int:
        """Remove all worktrees for this spec.
        
        Uses WorktreeManager to clean up all session worktrees and
        the parent .worktrees-{spec_id}/ directory.
        
        Returns:
            Number of worktrees removed
        """
        # Import here to avoid circular dependency
        from speckit_flow.worktree.manager import WorktreeManager
        
        manager = WorktreeManager(self.repo_root)
        return manager.cleanup_spec(self.spec_id)
