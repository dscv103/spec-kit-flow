"""
Unit tests for speckit_flow.worktree.merger module.

Tests the MergeOrchestrator class for analyzing branch changes and
detecting potential merge conflicts.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from speckit_flow.worktree.merger import (
    MergeAnalysis,
    MergeOrchestrator,
    MergeResult,
    SessionChanges,
)


class TestSessionChanges:
    """Tests for SessionChanges dataclass."""
    
    def test_all_changed_files_union(self):
        """all_changed_files returns union of all change types."""
        changes = SessionChanges(
            session_id=0,
            branch_name="impl-001-session-0",
            added_files={"new.py", "added.txt"},
            modified_files={"main.py", "README.md"},
            deleted_files={"old.py"},
        )
        
        expected = {"new.py", "added.txt", "main.py", "README.md", "old.py"}
        assert changes.all_changed_files == expected
    
    def test_all_changed_files_empty(self):
        """all_changed_files returns empty set when no changes."""
        changes = SessionChanges(
            session_id=0,
            branch_name="impl-001-session-0",
        )
        
        assert changes.all_changed_files == set()


class TestMergeAnalysis:
    """Tests for MergeAnalysis dataclass."""
    
    def test_safe_to_merge_no_overlaps(self):
        """safe_to_merge is True when no overlapping files."""
        analysis = MergeAnalysis(
            base_branch="main",
            session_changes=[
                SessionChanges(0, "branch-0", modified_files={"file1.py"}),
                SessionChanges(1, "branch-1", modified_files={"file2.py"}),
            ],
            overlapping_files={},
        )
        
        assert analysis.safe_to_merge is True
    
    def test_safe_to_merge_with_overlaps(self):
        """safe_to_merge is False when overlapping files exist."""
        analysis = MergeAnalysis(
            base_branch="main",
            session_changes=[],
            overlapping_files={"shared.py": [0, 1]},
        )
        
        assert analysis.safe_to_merge is False
    
    def test_total_files_changed(self):
        """total_files_changed counts unique files across sessions."""
        analysis = MergeAnalysis(
            base_branch="main",
            session_changes=[
                SessionChanges(
                    0,
                    "branch-0",
                    added_files={"new.py"},
                    modified_files={"shared.py", "file1.py"},
                ),
                SessionChanges(
                    1,
                    "branch-1",
                    modified_files={"shared.py", "file2.py"},
                    deleted_files={"old.py"},
                ),
            ],
            overlapping_files={},
        )
        
        # Unique files: new.py, shared.py, file1.py, file2.py, old.py = 5
        assert analysis.total_files_changed == 5
    
    def test_total_files_changed_empty(self):
        """total_files_changed returns 0 when no changes."""
        analysis = MergeAnalysis(
            base_branch="main",
            session_changes=[],
            overlapping_files={},
        )
        
        assert analysis.total_files_changed == 0


class TestMergeOrchestrator:
    """Tests for MergeOrchestrator class."""
    
    def test_init(self, tmp_path):
        """Constructor initializes with spec_id and repo_root."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        assert orchestrator.spec_id == "001-test"
        assert orchestrator.repo_root == tmp_path.resolve()
    
    def test_get_current_branch(self, tmp_path):
        """_get_current_branch returns current branch name."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="feature-branch\n",
                returncode=0,
            )
            
            result = orchestrator._get_current_branch()
            
            assert result == "feature-branch"
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == [
                "git",
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
            ]
    
    def test_get_current_branch_detached_head(self, tmp_path):
        """_get_current_branch returns 'main' when in detached HEAD."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="HEAD\n", returncode=0)
            
            result = orchestrator._get_current_branch()
            
            assert result == "main"
    
    def test_get_current_branch_git_error(self, tmp_path):
        """_get_current_branch raises RuntimeError on git failure."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["git"], stderr="fatal: not a git repository"
            )
            
            with pytest.raises(RuntimeError, match="Failed to get current branch"):
                orchestrator._get_current_branch()
    
    def test_find_session_branches(self, tmp_path):
        """_find_session_branches finds all session branches for spec."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=(
                    "  impl-001-auth-session-0\n"
                    "* impl-001-auth-session-1\n"
                    "  impl-001-auth-session-2\n"
                ),
                returncode=0,
            )
            
            result = orchestrator._find_session_branches()
            
            assert result == {
                0: "impl-001-auth-session-0",
                1: "impl-001-auth-session-1",
                2: "impl-001-auth-session-2",
            }
    
    def test_find_session_branches_no_matches(self, tmp_path):
        """_find_session_branches returns empty dict when no branches found."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)
            
            result = orchestrator._find_session_branches()
            
            assert result == {}
    
    def test_find_session_branches_filters_unrelated(self, tmp_path):
        """_find_session_branches ignores branches from other specs."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=(
                    "  impl-001-auth-session-0\n"
                    "  impl-002-other-session-0\n"  # Different spec
                    "  feature-branch\n"  # Unrelated branch
                ),
                returncode=0,
            )
            
            result = orchestrator._find_session_branches()
            
            assert result == {0: "impl-001-auth-session-0"}
    
    def test_find_session_branches_git_error(self, tmp_path):
        """_find_session_branches returns empty dict on git error."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])
            
            result = orchestrator._find_session_branches()
            
            assert result == {}
    
    def test_get_branch_changes_added_files(self, tmp_path):
        """_get_branch_changes correctly identifies added files."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="A\tnew_file.py\nA\tanother.txt\n",
                returncode=0,
            )
            
            result = orchestrator._get_branch_changes("main", "feature", 0)
            
            assert result.session_id == 0
            assert result.branch_name == "feature"
            assert result.added_files == {"new_file.py", "another.txt"}
            assert result.modified_files == set()
            assert result.deleted_files == set()
    
    def test_get_branch_changes_modified_files(self, tmp_path):
        """_get_branch_changes correctly identifies modified files."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="M\texisting.py\nM\tREADME.md\n",
                returncode=0,
            )
            
            result = orchestrator._get_branch_changes("main", "feature", 0)
            
            assert result.modified_files == {"existing.py", "README.md"}
            assert result.added_files == set()
            assert result.deleted_files == set()
    
    def test_get_branch_changes_deleted_files(self, tmp_path):
        """_get_branch_changes correctly identifies deleted files."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="D\told_file.py\nD\tdeprecated.txt\n",
                returncode=0,
            )
            
            result = orchestrator._get_branch_changes("main", "feature", 0)
            
            assert result.deleted_files == {"old_file.py", "deprecated.txt"}
            assert result.added_files == set()
            assert result.modified_files == set()
    
    def test_get_branch_changes_renamed_files(self, tmp_path):
        """_get_branch_changes treats renamed files as modified."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="R100\told_name.py\tnew_name.py\n",
                returncode=0,
            )
            
            result = orchestrator._get_branch_changes("main", "feature", 0)
            
            # Renamed files treated as modified (new path)
            assert result.modified_files == {"new_name.py"}
    
    def test_get_branch_changes_mixed_types(self, tmp_path):
        """_get_branch_changes handles mixed change types."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=(
                    "A\tnew.py\n"
                    "M\tmodified.py\n"
                    "D\tdeleted.py\n"
                    "M\tanother_mod.py\n"
                ),
                returncode=0,
            )
            
            result = orchestrator._get_branch_changes("main", "feature", 0)
            
            assert result.added_files == {"new.py"}
            assert result.modified_files == {"modified.py", "another_mod.py"}
            assert result.deleted_files == {"deleted.py"}
    
    def test_get_branch_changes_empty_diff(self, tmp_path):
        """_get_branch_changes handles empty diff (no changes)."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)
            
            result = orchestrator._get_branch_changes("main", "feature", 0)
            
            assert result.added_files == set()
            assert result.modified_files == set()
            assert result.deleted_files == set()
    
    def test_get_branch_changes_git_error(self, tmp_path):
        """_get_branch_changes raises RuntimeError on git failure."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["git"], stderr="fatal: branch not found"
            )
            
            with pytest.raises(RuntimeError, match="Failed to get changes"):
                orchestrator._get_branch_changes("main", "nonexistent", 0)
    
    def test_detect_overlaps_no_overlaps(self, tmp_path):
        """_detect_overlaps returns empty dict when no files overlap."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        session_changes = [
            SessionChanges(0, "branch-0", modified_files={"file1.py"}),
            SessionChanges(1, "branch-1", modified_files={"file2.py"}),
            SessionChanges(2, "branch-2", modified_files={"file3.py"}),
        ]
        
        result = orchestrator._detect_overlaps(session_changes)
        
        assert result == {}
    
    def test_detect_overlaps_single_overlap(self, tmp_path):
        """_detect_overlaps identifies single overlapping file."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        session_changes = [
            SessionChanges(0, "branch-0", modified_files={"shared.py", "file1.py"}),
            SessionChanges(1, "branch-1", modified_files={"shared.py", "file2.py"}),
        ]
        
        result = orchestrator._detect_overlaps(session_changes)
        
        assert result == {"shared.py": [0, 1]}
    
    def test_detect_overlaps_multiple_overlaps(self, tmp_path):
        """_detect_overlaps identifies multiple overlapping files."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        session_changes = [
            SessionChanges(0, "branch-0", modified_files={"shared1.py", "shared2.py"}),
            SessionChanges(1, "branch-1", modified_files={"shared1.py", "file2.py"}),
            SessionChanges(2, "branch-2", modified_files={"shared2.py", "file3.py"}),
        ]
        
        result = orchestrator._detect_overlaps(session_changes)
        
        assert result == {
            "shared1.py": [0, 1],
            "shared2.py": [0, 2],
        }
    
    def test_detect_overlaps_three_way(self, tmp_path):
        """_detect_overlaps handles files modified by 3+ sessions."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        session_changes = [
            SessionChanges(0, "branch-0", modified_files={"README.md"}),
            SessionChanges(1, "branch-1", modified_files={"README.md"}),
            SessionChanges(2, "branch-2", modified_files={"README.md"}),
        ]
        
        result = orchestrator._detect_overlaps(session_changes)
        
        assert result == {"README.md": [0, 1, 2]}
    
    def test_detect_overlaps_mixed_change_types(self, tmp_path):
        """_detect_overlaps detects overlaps across different change types."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        session_changes = [
            SessionChanges(0, "branch-0", added_files={"new.py"}),
            SessionChanges(1, "branch-1", modified_files={"new.py"}),  # Conflict!
        ]
        
        result = orchestrator._detect_overlaps(session_changes)
        
        # One session added, another modified - still a conflict
        assert result == {"new.py": [0, 1]}
    
    def test_analyze_success(self, tmp_path):
        """analyze() performs full analysis successfully."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-auth-session-0",
                 1: "impl-001-auth-session-1",
             }), \
             patch.object(orchestrator, "_get_branch_changes") as mock_changes:
            
            # Mock changes for each session
            mock_changes.side_effect = [
                SessionChanges(0, "impl-001-auth-session-0", modified_files={"auth.py"}),
                SessionChanges(1, "impl-001-auth-session-1", modified_files={"login.py"}),
            ]
            
            result = orchestrator.analyze()
            
            assert isinstance(result, MergeAnalysis)
            assert result.base_branch == "main"
            assert len(result.session_changes) == 2
            assert result.safe_to_merge is True
            assert result.total_files_changed == 2
    
    def test_analyze_with_conflicts(self, tmp_path):
        """analyze() detects conflicts between sessions."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-auth-session-0",
                 1: "impl-001-auth-session-1",
             }), \
             patch.object(orchestrator, "_get_branch_changes") as mock_changes:
            
            # Mock overlapping changes
            mock_changes.side_effect = [
                SessionChanges(0, "impl-001-auth-session-0", modified_files={"shared.py"}),
                SessionChanges(1, "impl-001-auth-session-1", modified_files={"shared.py"}),
            ]
            
            result = orchestrator.analyze()
            
            assert result.safe_to_merge is False
            assert "shared.py" in result.overlapping_files
            assert result.overlapping_files["shared.py"] == [0, 1]
    
    def test_analyze_explicit_base_branch(self, tmp_path):
        """analyze() uses explicitly provided base_branch."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-auth-session-0",
             }), \
             patch.object(orchestrator, "_get_branch_changes") as mock_changes:
            
            mock_changes.return_value = SessionChanges(0, "impl-001-auth-session-0")
            
            result = orchestrator.analyze(base_branch="develop")
            
            assert result.base_branch == "develop"
            # Verify _get_branch_changes was called with correct base
            assert mock_changes.call_args[0][0] == "develop"
    
    def test_analyze_no_session_branches(self, tmp_path):
        """analyze() raises RuntimeError when no session branches found."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={}):
            
            with pytest.raises(RuntimeError, match="No session branches found"):
                orchestrator.analyze()
    
    def test_analyze_sorts_sessions(self, tmp_path):
        """analyze() processes sessions in sorted order."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 2: "impl-001-auth-session-2",
                 0: "impl-001-auth-session-0",
                 1: "impl-001-auth-session-1",
             }), \
             patch.object(orchestrator, "_get_branch_changes") as mock_changes:
            
            mock_changes.side_effect = [
                SessionChanges(0, "impl-001-auth-session-0"),
                SessionChanges(1, "impl-001-auth-session-1"),
                SessionChanges(2, "impl-001-auth-session-2"),
            ]
            
            result = orchestrator.analyze()
            
            # Verify sessions are in order
            assert [s.session_id for s in result.session_changes] == [0, 1, 2]


class TestMergeAnalysisProperties:
    """Tests for MergeAnalysis computed properties."""
    
    def test_safe_to_merge_property(self):
        """safe_to_merge correctly reflects overlapping files state."""
        # Safe case
        analysis = MergeAnalysis(
            base_branch="main",
            session_changes=[],
            overlapping_files={},
        )
        assert analysis.safe_to_merge is True
        
        # Unsafe case
        analysis.overlapping_files["file.py"] = [0, 1]
        assert analysis.safe_to_merge is False
    
    def test_total_files_changed_with_duplicates(self):
        """total_files_changed counts each file only once."""
        # Same file in multiple sessions
        analysis = MergeAnalysis(
            base_branch="main",
            session_changes=[
                SessionChanges(0, "br0", modified_files={"shared.py"}),
                SessionChanges(1, "br1", modified_files={"shared.py"}),
                SessionChanges(2, "br2", modified_files={"shared.py"}),
            ],
            overlapping_files={},
        )
        
        # Should count shared.py only once
        assert analysis.total_files_changed == 1


class TestMergeResult:
    """Tests for MergeResult dataclass."""
    
    def test_successful_merge(self):
        """MergeResult represents successful merge."""
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
    
    def test_failed_merge_with_conflict(self):
        """MergeResult represents merge failure with conflict details."""
        result = MergeResult(
            success=False,
            integration_branch="impl-001-integrated",
            merged_sessions=[0, 1],
            conflict_session=2,
            conflicting_files=["src/main.py", "README.md"],
            error_message="Merge conflict in session 2",
        )
        
        assert result.success is False
        assert result.merged_sessions == [0, 1]
        assert result.conflict_session == 2
        assert result.conflicting_files == ["src/main.py", "README.md"]
        assert result.error_message == "Merge conflict in session 2"


class TestMergeSequential:
    """Tests for merge_sequential() method."""
    
    def test_successful_merge_all_sessions(self, tmp_path):
        """merge_sequential() successfully merges all sessions."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
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
            assert result.conflicting_files == []
            assert result.error_message is None
    
    def test_merge_with_conflict_stops_and_cleans_up(self, tmp_path):
        """merge_sequential() stops on conflict and cleans up."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-test-session-0",
                 1: "impl-001-test-session-1",
                 2: "impl-001-test-session-2",
             }), \
             patch.object(orchestrator, "_get_conflicting_files", return_value=[
                 "src/conflict.py",
                 "README.md",
             ]), \
             patch("subprocess.run") as mock_run:
            
            merge_call_count = 0
            
            def run_side_effect(cmd, **kwargs):
                nonlocal merge_call_count
                
                if cmd[1] == "rev-parse":
                    # Integration branch doesn't exist yet
                    return Mock(returncode=1, stdout="", stderr="")
                elif cmd[1] == "checkout" and "-b" in cmd:
                    # Create integration branch
                    return Mock(returncode=0, stdout="", stderr="")
                elif cmd[1] == "merge" and "--no-ff" in cmd:
                    # First two merges succeed, third fails
                    merge_call_count += 1
                    if merge_call_count <= 2:
                        return Mock(returncode=0, stdout="", stderr="")
                    else:
                        return Mock(returncode=1, stdout="", stderr="CONFLICT")
                elif cmd[1] == "merge" and "--abort" in cmd:
                    # Abort merge
                    return Mock(returncode=0, stdout="", stderr="")
                elif cmd[1] == "checkout" and "-b" not in cmd:
                    # Checkout base branch
                    return Mock(returncode=0, stdout="", stderr="")
                elif cmd[1] == "branch" and "-D" in cmd:
                    # Delete integration branch
                    return Mock(returncode=0, stdout="", stderr="")
                return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            result = orchestrator.merge_sequential()
            
            assert result.success is False
            assert result.integration_branch == "impl-001-test-integrated"
            assert result.merged_sessions == [0, 1]
            assert result.conflict_session == 2
            assert result.conflicting_files == ["src/conflict.py", "README.md"]
            assert "Merge conflict occurred" in result.error_message
            assert "session 2" in result.error_message
    
    def test_merge_uses_explicit_base_branch(self, tmp_path):
        """merge_sequential() uses explicitly provided base_branch."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-test-session-0",
             }), \
             patch("subprocess.run") as mock_run:
            
            def run_side_effect(cmd, **kwargs):
                if cmd[1] == "rev-parse":
                    return Mock(returncode=1, stdout="", stderr="")
                elif cmd[1] == "checkout" and "-b" in cmd:
                    # Verify correct base branch used
                    assert cmd[-1] == "develop"
                    return Mock(returncode=0, stdout="", stderr="")
                return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            result = orchestrator.merge_sequential(base_branch="develop")
            
            assert result.success is True
    
    def test_merge_no_session_branches_raises_error(self, tmp_path):
        """merge_sequential() raises RuntimeError when no session branches."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={}):
            
            with pytest.raises(RuntimeError, match="No session branches found"):
                orchestrator.merge_sequential()
    
    def test_merge_integration_branch_exists_raises_error(self, tmp_path):
        """merge_sequential() raises RuntimeError if integration branch exists."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-test-session-0",
             }), \
             patch("subprocess.run") as mock_run:
            
            # Mock integration branch already exists
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            with pytest.raises(RuntimeError, match="already exists"):
                orchestrator.merge_sequential()
    
    def test_merge_preserves_branch_history_with_no_ff(self, tmp_path):
        """merge_sequential() uses --no-ff to preserve branch history."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-test-session-0",
             }), \
             patch("subprocess.run") as mock_run:
            
            merge_calls = []
            
            def run_side_effect(cmd, **kwargs):
                if cmd[1] == "merge":
                    merge_calls.append(cmd)
                    return Mock(returncode=0, stdout="", stderr="")
                return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            orchestrator.merge_sequential()
            
            # Verify --no-ff was used
            assert len(merge_calls) == 1
            assert "--no-ff" in merge_calls[0]
    
    def test_merge_sessions_in_order(self, tmp_path):
        """merge_sequential() merges sessions in numeric order."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 2: "impl-001-test-session-2",
                 0: "impl-001-test-session-0",
                 1: "impl-001-test-session-1",
             }), \
             patch("subprocess.run") as mock_run:
            
            merged_branches = []
            
            def run_side_effect(cmd, **kwargs):
                if cmd[1] == "merge" and "--no-ff" in cmd:
                    # Extract branch name from command
                    merged_branches.append(cmd[-1])
                    return Mock(returncode=0, stdout="", stderr="")
                return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            result = orchestrator.merge_sequential()
            
            # Verify order: session 0, 1, 2
            assert merged_branches == [
                "impl-001-test-session-0",
                "impl-001-test-session-1",
                "impl-001-test-session-2",
            ]
            assert result.merged_sessions == [0, 1, 2]
    
    def test_merge_creates_descriptive_commit_messages(self, tmp_path):
        """merge_sequential() creates descriptive merge commit messages."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-test-session-0",
             }), \
             patch("subprocess.run") as mock_run:
            
            merge_messages = []
            
            def run_side_effect(cmd, **kwargs):
                if cmd[1] == "merge" and "-m" in cmd:
                    # Extract commit message
                    msg_idx = cmd.index("-m") + 1
                    merge_messages.append(cmd[msg_idx])
                    return Mock(returncode=0, stdout="", stderr="")
                return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            orchestrator.merge_sequential()
            
            # Verify descriptive message
            assert len(merge_messages) == 1
            assert "session 0" in merge_messages[0]
            assert "impl-001-test-session-0" in merge_messages[0]
    
    def test_get_conflicting_files(self, tmp_path):
        """_get_conflicting_files() returns list of conflicted files."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="src/main.py\nREADME.md\ntests/test_main.py\n",
                stderr="",
            )
            
            result = orchestrator._get_conflicting_files()
            
            assert result == ["src/main.py", "README.md", "tests/test_main.py"]
            
            # Verify correct git command
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd == ["git", "diff", "--name-only", "--diff-filter=U"]
    
    def test_get_conflicting_files_empty(self, tmp_path):
        """_get_conflicting_files() returns empty list when no conflicts."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="",
                stderr="",
            )
            
            result = orchestrator._get_conflicting_files()
            
            assert result == []
    
    def test_get_conflicting_files_git_error(self, tmp_path):
        """_get_conflicting_files() returns empty list on git error."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["git"], stderr="error"
            )
            
            result = orchestrator._get_conflicting_files()
            
            # Should handle error gracefully
            assert result == []
    
    def test_merge_git_error_cleans_up_integration_branch(self, tmp_path):
        """merge_sequential() cleans up integration branch on git error."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch.object(orchestrator, "_find_session_branches", return_value={
                 0: "impl-001-test-session-0",
             }), \
             patch("subprocess.run") as mock_run:
            
            cleanup_calls = []
            
            def run_side_effect(cmd, **kwargs):
                if cmd[1] == "rev-parse":
                    return Mock(returncode=1, stdout="", stderr="")
                elif cmd[1] == "checkout" and "-b" in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif cmd[1] == "merge":
                    # Raise unexpected error
                    raise subprocess.CalledProcessError(
                        128, cmd, stderr="fatal: git error"
                    )
                elif cmd[1] == "checkout":
                    cleanup_calls.append("checkout")
                    return Mock(returncode=0, stdout="", stderr="")
                elif cmd[1] == "branch" and "-D" in cmd:
                    cleanup_calls.append("delete-branch")
                    return Mock(returncode=0, stdout="", stderr="")
                return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            with pytest.raises(RuntimeError, match="Git error during merge"):
                orchestrator.merge_sequential()
            
            # Verify cleanup was attempted
            assert "checkout" in cleanup_calls
            assert "delete-branch" in cleanup_calls


class TestValidate:
    """Tests for validate() method."""
    
    def test_validate_no_command_returns_success(self, tmp_path):
        """validate() returns success when no test command provided."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        success, output = orchestrator.validate(test_cmd=None)
        
        assert success is True
        assert "No validation command" in output
        assert "skipping" in output
    
    def test_validate_successful_test_command(self, tmp_path):
        """validate() returns success when test command succeeds."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
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
    
    def test_validate_failed_test_command(self, tmp_path):
        """validate() returns failure when test command fails."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            # Mock checkout success
            checkout_result = Mock(returncode=0, stdout="", stderr="")
            # Mock test command failure
            test_result = Mock(
                returncode=1,
                stdout="FAILED tests/test_auth.py\n",
                stderr="2 tests failed\n",
            )
            mock_run.side_effect = [checkout_result, test_result]
            
            success, output = orchestrator.validate("pytest tests/")
            
            assert success is False
            assert "FAILED" in output
            assert "2 tests failed" in output
    
    def test_validate_combines_stdout_and_stderr(self, tmp_path):
        """validate() combines stdout and stderr in output."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            checkout_result = Mock(returncode=0, stdout="", stderr="")
            test_result = Mock(
                returncode=0,
                stdout="Test output line 1\n",
                stderr="Warning: deprecated\n",
            )
            mock_run.side_effect = [checkout_result, test_result]
            
            success, output = orchestrator.validate("npm test")
            
            assert success is True
            assert "Test output line 1" in output
            assert "Warning: deprecated" in output
    
    def test_validate_checks_out_integration_branch(self, tmp_path):
        """validate() checks out integration branch before running tests."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            checkout_result = Mock(returncode=0, stdout="", stderr="")
            test_result = Mock(returncode=0, stdout="", stderr="")
            mock_run.side_effect = [checkout_result, test_result]
            
            orchestrator.validate("pytest")
            
            # Verify checkout was called with correct branch
            checkout_call = mock_run.call_args_list[0]
            assert checkout_call[0][0] == [
                "git",
                "checkout",
                "impl-001-auth-integrated",
            ]
    
    def test_validate_uses_shell_for_complex_commands(self, tmp_path):
        """validate() uses shell=True to support complex commands."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            checkout_result = Mock(returncode=0, stdout="", stderr="")
            test_result = Mock(returncode=0, stdout="", stderr="")
            mock_run.side_effect = [checkout_result, test_result]
            
            orchestrator.validate("pytest && npm test")
            
            # Verify test command used shell=True
            test_call = mock_run.call_args_list[1]
            assert test_call[1]["shell"] is True
    
    def test_validate_checkout_failure(self, tmp_path):
        """validate() returns failure when checkout fails."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1,
                ["git", "checkout"],
                stderr="fatal: branch not found",
            )
            
            success, output = orchestrator.validate("pytest")
            
            assert success is False
            assert "Failed to checkout integration branch" in output
            assert "branch not found" in output
    
    def test_validate_unexpected_error(self, tmp_path):
        """validate() handles unexpected errors gracefully."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")
            
            success, output = orchestrator.validate("pytest")
            
            assert success is False
            assert "Unexpected error during validation" in output


class TestFinalize:
    """Tests for finalize() method."""
    
    def test_finalize_returns_summary_dict(self, tmp_path):
        """finalize() returns dictionary with merge summary."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_merge_statistics") as mock_stats, \
             patch.object(orchestrator, "_cleanup_worktrees") as mock_cleanup:
            
            mock_stats.return_value = {
                "files_changed": 5,
                "lines_added": 120,
                "lines_deleted": 30,
            }
            mock_cleanup.return_value = 3
            
            result = orchestrator.finalize()
            
            assert isinstance(result, dict)
            assert result["worktrees_removed"] == 3
            assert result["files_changed"] == 5
            assert result["lines_added"] == 120
            assert result["lines_deleted"] == 30
            assert result["integration_branch"] == "impl-001-test-integrated"
    
    def test_finalize_removes_worktrees_by_default(self, tmp_path):
        """finalize() removes worktrees by default."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_merge_statistics") as mock_stats, \
             patch.object(orchestrator, "_cleanup_worktrees") as mock_cleanup:
            
            mock_stats.return_value = {
                "files_changed": 0,
                "lines_added": 0,
                "lines_deleted": 0,
            }
            mock_cleanup.return_value = 2
            
            result = orchestrator.finalize()
            
            # Cleanup should be called
            mock_cleanup.assert_called_once()
            assert result["worktrees_removed"] == 2
    
    def test_finalize_keeps_worktrees_when_requested(self, tmp_path):
        """finalize() preserves worktrees when keep_worktrees=True."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_merge_statistics") as mock_stats, \
             patch.object(orchestrator, "_cleanup_worktrees") as mock_cleanup:
            
            mock_stats.return_value = {
                "files_changed": 0,
                "lines_added": 0,
                "lines_deleted": 0,
            }
            
            result = orchestrator.finalize(keep_worktrees=True)
            
            # Cleanup should NOT be called
            mock_cleanup.assert_not_called()
            assert result["worktrees_removed"] == 0
    
    def test_finalize_includes_integration_branch_name(self, tmp_path):
        """finalize() includes correct integration branch name."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch.object(orchestrator, "_get_merge_statistics") as mock_stats, \
             patch.object(orchestrator, "_cleanup_worktrees"):
            
            mock_stats.return_value = {
                "files_changed": 0,
                "lines_added": 0,
                "lines_deleted": 0,
            }
            
            result = orchestrator.finalize()
            
            assert result["integration_branch"] == "impl-001-auth-integrated"
    
    def test_get_merge_statistics_parses_shortstat(self, tmp_path):
        """_get_merge_statistics() parses git diff --shortstat output."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            # Mock finding tracking branch
            tracking_result = Mock(returncode=1, stdout="", stderr="")
            # Mock getting current branch
            # Mock merge-base
            merge_base_result = Mock(
                returncode=0,
                stdout="abc123def456\n",
                stderr="",
            )
            # Mock diff --shortstat
            diff_result = Mock(
                returncode=0,
                stdout="15 files changed, 230 insertions(+), 45 deletions(-)\n",
                stderr="",
            )
            
            def run_side_effect(cmd, **kwargs):
                if "abbrev-ref" in cmd:
                    return tracking_result
                elif "merge-base" in cmd:
                    return merge_base_result
                elif "--shortstat" in cmd:
                    return diff_result
                return Mock(returncode=0, stdout="main\n", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            stats = orchestrator._get_merge_statistics("impl-001-test-integrated")
            
            assert stats["files_changed"] == 15
            assert stats["lines_added"] == 230
            assert stats["lines_deleted"] == 45
    
    def test_get_merge_statistics_handles_no_deletions(self, tmp_path):
        """_get_merge_statistics() handles output without deletions."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            # Only insertions, no deletions
            diff_result = Mock(
                returncode=0,
                stdout="5 files changed, 100 insertions(+)\n",
                stderr="",
            )
            
            def run_side_effect(cmd, **kwargs):
                if "--shortstat" in cmd:
                    return diff_result
                return Mock(returncode=0, stdout="main\n", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            stats = orchestrator._get_merge_statistics("impl-001-test-integrated")
            
            assert stats["files_changed"] == 5
            assert stats["lines_added"] == 100
            assert stats["lines_deleted"] == 0
    
    def test_get_merge_statistics_handles_no_insertions(self, tmp_path):
        """_get_merge_statistics() handles output without insertions."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            # Only deletions, no insertions
            diff_result = Mock(
                returncode=0,
                stdout="3 files changed, 50 deletions(-)\n",
                stderr="",
            )
            
            def run_side_effect(cmd, **kwargs):
                if "--shortstat" in cmd:
                    return diff_result
                return Mock(returncode=0, stdout="main\n", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            stats = orchestrator._get_merge_statistics("impl-001-test-integrated")
            
            assert stats["files_changed"] == 3
            assert stats["lines_added"] == 0
            assert stats["lines_deleted"] == 50
    
    def test_get_merge_statistics_handles_empty_diff(self, tmp_path):
        """_get_merge_statistics() handles empty diff (no changes)."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            diff_result = Mock(returncode=0, stdout="", stderr="")
            
            def run_side_effect(cmd, **kwargs):
                if "--shortstat" in cmd:
                    return diff_result
                return Mock(returncode=0, stdout="main\n", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            stats = orchestrator._get_merge_statistics("impl-001-test-integrated")
            
            assert stats["files_changed"] == 0
            assert stats["lines_added"] == 0
            assert stats["lines_deleted"] == 0
    
    def test_get_merge_statistics_handles_git_error(self, tmp_path):
        """_get_merge_statistics() returns zeros on git error."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["git"], stderr="error"
            )
            
            stats = orchestrator._get_merge_statistics("impl-001-test-integrated")
            
            # Should return zeros on error
            assert stats["files_changed"] == 0
            assert stats["lines_added"] == 0
            assert stats["lines_deleted"] == 0
    
    def test_get_merge_statistics_uses_merge_base(self, tmp_path):
        """_get_merge_statistics() uses merge-base for accurate comparison."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch.object(orchestrator, "_get_current_branch", return_value="main"), \
             patch("subprocess.run") as mock_run:
            
            merge_base_commit = "abc123def456"
            
            def run_side_effect(cmd, **kwargs):
                if "abbrev-ref" in cmd and "@{u}" in cmd:
                    # No tracking branch
                    return Mock(returncode=1, stdout="", stderr="")
                elif "merge-base" in cmd:
                    return Mock(returncode=0, stdout=f"{merge_base_commit}\n", stderr="")
                elif "--shortstat" in cmd:
                    # Verify merge-base commit is used
                    assert merge_base_commit in cmd
                    return Mock(returncode=0, stdout="1 file changed, 10 insertions(+)\n", stderr="")
                return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = run_side_effect
            
            stats = orchestrator._get_merge_statistics("impl-001-test-integrated")
            
            assert stats["files_changed"] == 1
    
    def test_cleanup_worktrees_uses_worktree_manager(self, tmp_path):
        """_cleanup_worktrees() delegates to WorktreeManager."""
        orchestrator = MergeOrchestrator("001-test", tmp_path)
        
        with patch("speckit_flow.worktree.merger.WorktreeManager") as MockManager:
            mock_instance = Mock()
            mock_instance.cleanup_spec.return_value = 3
            MockManager.return_value = mock_instance
            
            result = orchestrator._cleanup_worktrees()
            
            # Verify WorktreeManager was instantiated correctly
            MockManager.assert_called_once_with(tmp_path)
            # Verify cleanup_spec was called with correct spec_id
            mock_instance.cleanup_spec.assert_called_once_with("001-test")
            assert result == 3
    
    def test_cleanup_worktrees_returns_count(self, tmp_path):
        """_cleanup_worktrees() returns number of removed worktrees."""
        orchestrator = MergeOrchestrator("001-auth", tmp_path)
        
        with patch("speckit_flow.worktree.merger.WorktreeManager") as MockManager:
            mock_instance = Mock()
            mock_instance.cleanup_spec.return_value = 5
            MockManager.return_value = mock_instance
            
            result = orchestrator._cleanup_worktrees()
            
            assert result == 5
