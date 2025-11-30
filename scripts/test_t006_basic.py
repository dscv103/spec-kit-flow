#!/usr/bin/env python3
"""
Quick test runner for T006 implementation.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

def main():
    print("Testing T006 implementation...")
    print("=" * 60)
    print()
    
    # Test 1: Import the module
    try:
        from speckit_core.tasks import parse_task_line, parse_tasks_file
        print("✓ Module imports successfully")
    except ImportError as e:
        print(f"✗ Failed to import module: {e}")
        return 1
    
    # Test 2: Parse a simple task
    try:
        line = "- [ ] [T001] Simple task"
        task = parse_task_line(line)
        assert task is not None
        assert task.id == "T001"
        assert task.name == "Simple task"
        print("✓ Basic task parsing works")
    except Exception as e:
        print(f"✗ Basic parsing failed: {e}")
        return 1
    
    # Test 3: Parse extended format with deps
    try:
        line = "- [ ] [T002] [P] [US1] [deps:T001] Extended task"
        task = parse_task_line(line)
        assert task is not None
        assert task.id == "T002"
        assert task.parallelizable is True
        assert task.story == "US1"
        assert task.dependencies == ["T001"]
        print("✓ Extended format parsing works")
    except Exception as e:
        print(f"✗ Extended parsing failed: {e}")
        return 1
    
    # Test 4: Parse completed task
    try:
        line = "- [x] [T003] Completed task"
        task = parse_task_line(line)
        assert task is not None
        assert task.completed is True
        print("✓ Completed task parsing works")
    except Exception as e:
        print(f"✗ Completed task parsing failed: {e}")
        return 1
    
    # Test 5: Parse actual tasks.md
    try:
        tasks_path = repo_root / "specs" / "speckit-flow" / "tasks.md"
        tasks = parse_tasks_file(tasks_path)
        assert len(tasks) > 0
        
        # Find T006 (current task)
        t006 = next((t for t in tasks if t.id == "T006"), None)
        assert t006 is not None
        assert t006.completed is True  # Should be marked complete
        
        print(f"✓ Parsed {len(tasks)} tasks from tasks.md")
        print(f"  - T006 status: {'✓ Complete' if t006.completed else '○ Pending'}")
    except Exception as e:
        print(f"✗ Real file parsing failed: {e}")
        return 1
    
    # Test 6: File path extraction
    try:
        line = "- [ ] [T007] Implement `src/file.py` and `tests/test.py`"
        task = parse_task_line(line)
        assert task is not None
        assert "src/file.py" in task.files
        assert "tests/test.py" in task.files
        print("✓ File path extraction works")
    except Exception as e:
        print(f"✗ File extraction failed: {e}")
        return 1
    
    print()
    print("=" * 60)
    print("✅ All T006 tests passed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
