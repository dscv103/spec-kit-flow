#!/usr/bin/env python3
"""
Demo script for T031 - MergeOrchestrator usage example.

This demonstrates how to use the MergeOrchestrator to analyze
changes across session branches and detect potential conflicts.
"""

from pathlib import Path
from speckit_flow.worktree.merger import MergeOrchestrator, MergeAnalysis

def demo_basic_usage():
    """Demonstrate basic MergeOrchestrator usage."""
    print("="*70)
    print("MergeOrchestrator Demo - Basic Usage")
    print("="*70)
    print()
    
    # Initialize orchestrator
    print("1. Initialize MergeOrchestrator")
    print("   orchestrator = MergeOrchestrator('001-auth', Path('/repo'))")
    print()
    
    # Analyze changes
    print("2. Analyze session branches")
    print("   analysis = orchestrator.analyze()")
    print("   # This will:")
    print("   #  - Find all impl-001-auth-session-* branches")
    print("   #  - Compare each against base branch")
    print("   #  - Detect overlapping file changes")
    print()
    
    # Check results
    print("3. Check merge safety")
    print("   if analysis.safe_to_merge:")
    print("       print('✓ Safe to merge!')")
    print("   else:")
    print("       print('⚠ Conflicts detected')")
    print()

def demo_no_conflicts():
    """Demonstrate successful merge analysis (no conflicts)."""
    print("="*70)
    print("Example 1: No Conflicts - Safe to Merge")
    print("="*70)
    print()
    
    print("Session branches:")
    print("  impl-001-auth-session-0:")
    print("    - src/auth/login.py (modified)")
    print("    - src/auth/utils.py (added)")
    print()
    print("  impl-001-auth-session-1:")
    print("    - src/auth/signup.py (modified)")
    print("    - tests/test_signup.py (added)")
    print()
    
    print("Analysis result:")
    print("  ✓ safe_to_merge: True")
    print("  ✓ total_files_changed: 4")
    print("  ✓ overlapping_files: {}")
    print()
    print("Conclusion: ✓ Proceed with merge")
    print()

def demo_with_conflicts():
    """Demonstrate merge analysis with conflicts."""
    print("="*70)
    print("Example 2: With Conflicts - Review Required")
    print("="*70)
    print()
    
    print("Session branches:")
    print("  impl-001-auth-session-0:")
    print("    - src/auth/models.py (modified)")
    print("    - README.md (modified)")
    print()
    print("  impl-001-auth-session-1:")
    print("    - src/auth/models.py (modified)  ⚠ CONFLICT")
    print("    - src/auth/views.py (added)")
    print()
    print("  impl-001-auth-session-2:")
    print("    - README.md (modified)  ⚠ CONFLICT")
    print("    - tests/test_auth.py (added)")
    print()
    
    print("Analysis result:")
    print("  ✗ safe_to_merge: False")
    print("  ✓ total_files_changed: 5")
    print("  ⚠ overlapping_files:")
    print("      'src/auth/models.py': [0, 1]")
    print("      'README.md': [0, 2]")
    print()
    print("Conclusion: ⚠ Review conflicts before merging")
    print()

def demo_detailed_output():
    """Demonstrate detailed analysis output."""
    print("="*70)
    print("Example 3: Detailed Per-Session Analysis")
    print("="*70)
    print()
    
    print("Analysis breakdown by session:")
    print()
    
    print("Session 0:")
    print("  Branch: impl-001-auth-session-0")
    print("  Changes:")
    print("    Added:    2 files")
    print("    Modified: 3 files")
    print("    Deleted:  1 file")
    print("    Total:    6 files")
    print()
    
    print("Session 1:")
    print("  Branch: impl-001-auth-session-1")
    print("  Changes:")
    print("    Added:    1 file")
    print("    Modified: 2 files")
    print("    Deleted:  0 files")
    print("    Total:    3 files")
    print()
    
    print("Session 2:")
    print("  Branch: impl-001-auth-session-2")
    print("  Changes:")
    print("    Added:    3 files")
    print("    Modified: 1 file")
    print("    Deleted:  0 files")
    print("    Total:    4 files")
    print()
    
    print("Overall:")
    print("  Total unique files changed: 11")
    print("  Overlapping files: 0")
    print("  ✓ Safe to merge")
    print()

def demo_code_example():
    """Show actual code usage."""
    print("="*70)
    print("Code Example: Real Implementation")
    print("="*70)
    print()
    
    code = '''
from pathlib import Path
from speckit_flow.worktree.merger import MergeOrchestrator

# Initialize
orchestrator = MergeOrchestrator("001-auth", Path("/repo"))

# Analyze
analysis = orchestrator.analyze()

# Check safety
if analysis.safe_to_merge:
    print(f"✓ Safe to merge! {analysis.total_files_changed} files changed.")
    
    # Show per-session changes
    for session in analysis.session_changes:
        print(f"\\nSession {session.session_id}:")
        print(f"  Added:    {len(session.added_files)}")
        print(f"  Modified: {len(session.modified_files)}")
        print(f"  Deleted:  {len(session.deleted_files)}")
else:
    print("⚠ Conflicts detected!")
    print("\\nConflicting files:")
    
    for file, sessions in analysis.overlapping_files.items():
        print(f"  {file}")
        print(f"    Modified by sessions: {sessions}")
    
    print("\\nRecommendation: Review and resolve conflicts manually")
'''
    
    print(code)
    print()

def main():
    """Run all demos."""
    demo_basic_usage()
    input("Press Enter to continue...")
    print()
    
    demo_no_conflicts()
    input("Press Enter to continue...")
    print()
    
    demo_with_conflicts()
    input("Press Enter to continue...")
    print()
    
    demo_detailed_output()
    input("Press Enter to continue...")
    print()
    
    demo_code_example()
    
    print("="*70)
    print("Demo Complete!")
    print("="*70)
    print()
    print("Next: T032 will implement the actual merge logic using this analysis")
    print()

if __name__ == "__main__":
    main()
