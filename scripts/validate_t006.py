#!/usr/bin/env python3
"""
Validation script for T006 implementation.

Tests that task parsing works correctly with all acceptance criteria.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.tasks import parse_task_line, parse_tasks_file
from speckit_core.models import TaskInfo


def test_ac1_standard_format():
    """AC1: Parses standard format: - [ ] [T001] [P] [US1] Description"""
    line = "- [ ] [T001] [P] [US1] Implement User model"
    task = parse_task_line(line)
    
    assert task is not None, "Failed to parse standard format"
    assert task.id == "T001", f"Expected T001, got {task.id}"
    assert task.parallelizable is True, "Should be parallelizable"
    assert task.story == "US1", f"Expected US1, got {task.story}"
    assert task.name == "Implement User model", f"Unexpected name: {task.name}"
    print("✓ AC1: Standard format parsing works")


def test_ac2_extended_format():
    """AC2: Parses extended format: - [ ] [T001] [P] [US1] [deps:T000] Description"""
    line = "- [ ] [T002] [P] [US1] [deps:T001] Add validation"
    task = parse_task_line(line)
    
    assert task is not None, "Failed to parse extended format"
    assert task.id == "T002", f"Expected T002, got {task.id}"
    assert task.dependencies == ["T001"], f"Expected ['T001'], got {task.dependencies}"
    assert task.parallelizable is True, "Should be parallelizable"
    assert task.story == "US1", f"Expected US1, got {task.story}"
    print("✓ AC2: Extended format with dependencies works")


def test_ac3_completed_tasks():
    """AC3: Handles completed tasks: - [x] [T001] ..."""
    line = "- [x] [T001] Completed task"
    task = parse_task_line(line)
    
    assert task is not None, "Failed to parse completed task"
    assert task.id == "T001", f"Expected T001, got {task.id}"
    assert task.completed is True, f"Task should be marked completed"
    print("✓ AC3: Completed task parsing works")


def test_ac4_optional_markers():
    """AC4: Handles tasks without optional markers"""
    # No [P], no [US#], no [deps:]
    line = "- [ ] [T001] Simple task"
    task = parse_task_line(line)
    
    assert task is not None, "Failed to parse minimal task"
    assert task.id == "T001", f"Expected T001, got {task.id}"
    assert task.parallelizable is False, "Should not be parallelizable"
    assert task.story is None, "Should have no story"
    assert task.dependencies == [], "Should have no dependencies"
    print("✓ AC4: Tasks without optional markers work")


def test_ac5_empty_file():
    """AC5: Returns empty list for invalid/empty files"""
    import tempfile
    
    # Test empty file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        tasks = parse_tasks_file(temp_path)
        assert tasks == [], f"Expected empty list, got {tasks}"
        print("✓ AC5: Empty file returns empty list")
    finally:
        temp_path.unlink()


def test_ac6_file_extraction():
    """AC6: Extracts file paths from description if present"""
    line = "- [ ] [T001] Implement `src/models/User.ts` and `tests/user.test.ts`"
    task = parse_task_line(line)
    
    assert task is not None, "Failed to parse task with files"
    assert "src/models/User.ts" in task.files, "Should extract first file"
    assert "tests/user.test.ts" in task.files, "Should extract second file"
    print("✓ AC6: File path extraction works")


def test_real_tasks_file():
    """Test parsing the actual tasks.md file"""
    tasks_path = Path(__file__).parent.parent / "specs" / "speckit-flow" / "tasks.md"
    
    if not tasks_path.exists():
        print("⚠ Warning: tasks.md not found, skipping real file test")
        return
    
    tasks = parse_tasks_file(tasks_path)
    
    assert len(tasks) > 0, "Should parse tasks from tasks.md"
    
    # Check some known tasks
    task_ids = [t.id for t in tasks]
    assert "T001" in task_ids, "Should find T001"
    assert "T006" in task_ids, "Should find T006 (current task)"
    
    # Find T001 and verify it's marked completed
    t001 = next((t for t in tasks if t.id == "T001"), None)
    assert t001 is not None, "T001 should exist"
    assert t001.completed is True, "T001 should be marked completed"
    
    # Find T006 and verify its dependencies
    t006 = next((t for t in tasks if t.id == "T006"), None)
    assert t006 is not None, "T006 should exist"
    assert "T003" in t006.dependencies, "T006 should depend on T003"
    assert "T005" in t006.dependencies, "T006 should depend on T005"
    
    print(f"✓ Real file test: Parsed {len(tasks)} tasks from tasks.md")


def main():
    """Run all validation tests."""
    print("Validating T006 implementation...")
    print()
    
    try:
        test_ac1_standard_format()
        test_ac2_extended_format()
        test_ac3_completed_tasks()
        test_ac4_optional_markers()
        test_ac5_empty_file()
        test_ac6_file_extraction()
        test_real_tasks_file()
        
        print()
        print("=" * 60)
        print("✅ ALL ACCEPTANCE CRITERIA PASSED")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ VALIDATION FAILED: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
