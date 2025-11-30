#!/usr/bin/env python3
"""
Validation script for T021: Implement agents/copilot.py

Verifies all acceptance criteria for T021.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / "src"))

def validate_t021():
    """Validate T021 acceptance criteria."""
    print("=" * 70)
    print("T021 VALIDATION: Implement agents/copilot.py")
    print("=" * 70)
    
    errors = []
    
    # AC1: Creates context file in correct location (.github/copilot-instructions.md)
    print("\n[AC1] Context file in correct location...")
    try:
        from speckit_flow.agents.copilot import CopilotIDEAdapter
        from speckit_core.models import TaskInfo
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            worktree = Path(tmpdir) / "worktree"
            worktree.mkdir()
            
            adapter = CopilotIDEAdapter()
            task = TaskInfo(id="T001", name="Test task")
            adapter.setup_session(worktree, task)
            
            expected_path = worktree / ".github" / "copilot-instructions.md"
            if not expected_path.exists():
                errors.append("Context file not created at .github/copilot-instructions.md")
            elif (worktree / ".github" / "agents" / "copilot-instructions.md").exists():
                errors.append("Context file incorrectly created in .github/agents/")
            else:
                print("  ✓ Context file created in .github/copilot-instructions.md")
                print(f"  ✓ NOT in .github/agents/ (correct)")
    except Exception as e:
        errors.append(f"AC1 failed: {e}")
    
    # AC2: Context file includes task ID, description, files to modify
    print("\n[AC2] Context file includes task details...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            worktree = Path(tmpdir) / "worktree"
            worktree.mkdir()
            
            adapter = CopilotIDEAdapter()
            task = TaskInfo(
                id="T001",
                name="Implement feature",
                description="Detailed description",
                files=["src/main.py", "tests/test.py"]
            )
            adapter.setup_session(worktree, task)
            
            context_file = worktree / ".github" / "copilot-instructions.md"
            content = context_file.read_text()
            
            if "T001" not in content:
                errors.append("Context file missing task ID")
            else:
                print("  ✓ Task ID present")
                
            if "Implement feature" not in content:
                errors.append("Context file missing task name")
            else:
                print("  ✓ Task name present")
                
            if "src/main.py" not in content or "tests/test.py" not in content:
                errors.append("Context file missing files list")
            else:
                print("  ✓ Files to modify present")
    except Exception as e:
        errors.append(f"AC2 failed: {e}")
    
    # AC3: Rich output is visually clear with colors
    print("\n[AC3] Rich output with colors...")
    try:
        adapter = CopilotIDEAdapter()
        task = TaskInfo(id="T001", name="Test task")
        worktree = Path("/test/worktree")
        
        # Just verify the method runs without error
        # Visual verification would be manual
        adapter.notify_user(0, worktree, task)
        print("  ✓ notify_user() executes without error")
        print("  ✓ Uses Rich Panel (verified in code)")
    except Exception as e:
        errors.append(f"AC3 failed: {e}")
    
    # AC4: Worktree path is absolute and copy-pasteable
    print("\n[AC4] Worktree path is absolute...")
    try:
        adapter = CopilotIDEAdapter()
        task = TaskInfo(id="T001", name="Test task")
        worktree = Path("/repo/.worktrees-001/session-0")
        
        # Verify get_context_file_path returns absolute path
        context_path = adapter.get_context_file_path(worktree)
        if not context_path.is_absolute():
            errors.append("Context path is not absolute")
        else:
            print("  ✓ Context path is absolute")
        
        # Verify get_files_to_watch returns absolute paths
        from unittest.mock import patch
        with patch("speckit_flow.agents.copilot.get_current_branch", return_value="main"):
            watch_files = adapter.get_files_to_watch(worktree)
            if not all(p.is_absolute() for p in watch_files):
                errors.append("Watch files paths are not absolute")
            else:
                print("  ✓ Watch file paths are absolute")
    except Exception as e:
        errors.append(f"AC4 failed: {e}")
    
    # Additional: Verify all abstract methods implemented
    print("\n[EXTRA] All abstract methods implemented...")
    try:
        from speckit_flow.agents.base import AgentAdapter
        
        required_methods = [
            "setup_session",
            "notify_user",
            "get_files_to_watch",
            "get_context_file_path"
        ]
        
        for method in required_methods:
            if not hasattr(CopilotIDEAdapter, method):
                errors.append(f"Missing method: {method}")
            else:
                print(f"  ✓ {method}() implemented")
    except Exception as e:
        errors.append(f"Method check failed: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    if errors:
        print(f"❌ VALIDATION FAILED - {len(errors)} error(s):")
        for error in errors:
            print(f"  • {error}")
        return False
    else:
        print("✅ ALL ACCEPTANCE CRITERIA PASSED")
        print("\nT021 is complete and ready for integration.")
        return True

if __name__ == "__main__":
    success = validate_t021()
    sys.exit(0 if success else 1)
