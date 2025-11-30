#!/usr/bin/env python3
"""
Quick test script for T031 implementation.

Verifies that the merger module imports and basic functionality works.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

def test_imports():
    """Test that all merger classes can be imported."""
    print("Testing imports...")
    
    from speckit_flow.worktree.merger import (
        MergeOrchestrator,
        MergeAnalysis,
        SessionChanges,
    )
    
    print("✓ All classes imported successfully")
    return True

def test_session_changes():
    """Test SessionChanges dataclass."""
    print("\nTesting SessionChanges...")
    
    from speckit_flow.worktree.merger import SessionChanges
    
    changes = SessionChanges(
        session_id=0,
        branch_name="impl-001-session-0",
        added_files={"new.py"},
        modified_files={"main.py", "README.md"},
        deleted_files={"old.py"},
    )
    
    assert changes.session_id == 0
    assert changes.branch_name == "impl-001-session-0"
    assert len(changes.all_changed_files) == 4
    assert "new.py" in changes.all_changed_files
    assert "main.py" in changes.all_changed_files
    
    print("✓ SessionChanges works correctly")
    return True

def test_merge_analysis():
    """Test MergeAnalysis dataclass."""
    print("\nTesting MergeAnalysis...")
    
    from speckit_flow.worktree.merger import MergeAnalysis, SessionChanges
    
    # No overlaps - safe to merge
    analysis = MergeAnalysis(
        base_branch="main",
        session_changes=[
            SessionChanges(0, "branch-0", modified_files={"file1.py"}),
            SessionChanges(1, "branch-1", modified_files={"file2.py"}),
        ],
        overlapping_files={},
    )
    
    assert analysis.safe_to_merge is True
    assert analysis.total_files_changed == 2
    
    # With overlaps - not safe
    analysis_conflict = MergeAnalysis(
        base_branch="main",
        session_changes=[
            SessionChanges(0, "branch-0", modified_files={"shared.py"}),
            SessionChanges(1, "branch-1", modified_files={"shared.py"}),
        ],
        overlapping_files={"shared.py": [0, 1]},
    )
    
    assert analysis_conflict.safe_to_merge is False
    assert "shared.py" in analysis_conflict.overlapping_files
    
    print("✓ MergeAnalysis works correctly")
    return True

def test_merge_orchestrator_init():
    """Test MergeOrchestrator initialization."""
    print("\nTesting MergeOrchestrator initialization...")
    
    from speckit_flow.worktree.merger import MergeOrchestrator
    
    orchestrator = MergeOrchestrator("001-test", Path("/tmp"))
    
    assert orchestrator.spec_id == "001-test"
    assert orchestrator.repo_root == Path("/tmp").resolve()
    
    print("✓ MergeOrchestrator initializes correctly")
    return True

def test_detect_overlaps():
    """Test overlap detection logic."""
    print("\nTesting overlap detection...")
    
    from speckit_flow.worktree.merger import MergeOrchestrator, SessionChanges
    
    orchestrator = MergeOrchestrator("001-test", Path("/tmp"))
    
    # No overlaps
    session_changes = [
        SessionChanges(0, "branch-0", modified_files={"file1.py"}),
        SessionChanges(1, "branch-1", modified_files={"file2.py"}),
    ]
    overlaps = orchestrator._detect_overlaps(session_changes)
    assert overlaps == {}
    
    # With overlaps
    session_changes_conflict = [
        SessionChanges(0, "branch-0", modified_files={"shared.py", "file1.py"}),
        SessionChanges(1, "branch-1", modified_files={"shared.py", "file2.py"}),
    ]
    overlaps = orchestrator._detect_overlaps(session_changes_conflict)
    assert "shared.py" in overlaps
    assert overlaps["shared.py"] == [0, 1]
    
    print("✓ Overlap detection works correctly")
    return True

def main():
    """Run all tests."""
    print("="*60)
    print("T031 Implementation Test Suite")
    print("="*60)
    
    tests = [
        test_imports,
        test_session_changes,
        test_merge_analysis,
        test_merge_orchestrator_init,
        test_detect_overlaps,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed > 0:
        sys.exit(1)
    
    print("\n✅ All T031 acceptance criteria verified!")

if __name__ == "__main__":
    main()
