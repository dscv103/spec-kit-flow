#!/usr/bin/env python3
"""
Verification script for T006 Acceptance Criteria.
Tests each AC individually and reports pass/fail.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.tasks import parse_task_line, parse_tasks_file


def test_ac1():
    """AC1: Parses standard format: - [ ] [T001] [P] [US1] Description"""
    print("Testing AC1: Standard format parsing...")
    
    line = "- [ ] [T001] [P] [US1] Implement User model"
    task = parse_task_line(line)
    
    checks = [
        (task is not None, "Task should parse"),
        (task.id == "T001", f"ID should be T001, got {task.id if task else None}"),
        (task.parallelizable is True, "Should be parallelizable"),
        (task.story == "US1", f"Story should be US1, got {task.story if task else None}"),
        (task.name == "Implement User model", f"Name mismatch: {task.name if task else None}"),
    ]
    
    for check, msg in checks:
        if not check:
            print(f"  ✗ FAIL: {msg}")
            return False
    
    print("  ✓ PASS: Standard format works")
    return True


def test_ac2():
    """AC2: Parses extended format: - [ ] [T001] [P] [US1] [deps:T000] Description"""
    print("Testing AC2: Extended format with dependencies...")
    
    line = "- [ ] [T002] [P] [US1] [deps:T001] Add validation"
    task = parse_task_line(line)
    
    checks = [
        (task is not None, "Task should parse"),
        (task.id == "T002", f"ID should be T002, got {task.id if task else None}"),
        (task.parallelizable is True, "Should be parallelizable"),
        (task.story == "US1", f"Story should be US1, got {task.story if task else None}"),
        (task.dependencies == ["T001"], f"Dependencies should be ['T001'], got {task.dependencies if task else None}"),
    ]
    
    for check, msg in checks:
        if not check:
            print(f"  ✗ FAIL: {msg}")
            return False
    
    print("  ✓ PASS: Extended format with dependencies works")
    return True


def test_ac3():
    """AC3: Handles completed tasks: - [x] [T001] ..."""
    print("Testing AC3: Completed task parsing...")
    
    test_cases = [
        ("- [x] [T001] Completed task", True, "lowercase x"),
        ("- [X] [T002] Also completed", True, "uppercase X"),
        ("- [ ] [T003] Not completed", False, "empty checkbox"),
    ]
    
    for line, expected_completed, desc in test_cases:
        task = parse_task_line(line)
        if task is None:
            print(f"  ✗ FAIL: Failed to parse {desc}")
            return False
        if task.completed != expected_completed:
            print(f"  ✗ FAIL: {desc} - expected completed={expected_completed}, got {task.completed}")
            return False
    
    print("  ✓ PASS: Completed task detection works")
    return True


def test_ac4():
    """AC4: Handles tasks without optional markers"""
    print("Testing AC4: Tasks without optional markers...")
    
    test_cases = [
        ("- [ ] [T001] Simple task", {
            "parallelizable": False,
            "story": None,
            "dependencies": [],
        }),
        ("- [ ] [T002] [P] With P only", {
            "parallelizable": True,
            "story": None,
            "dependencies": [],
        }),
        ("- [ ] [T003] [US1] With story only", {
            "parallelizable": False,
            "story": "US1",
            "dependencies": [],
        }),
    ]
    
    for line, expected in test_cases:
        task = parse_task_line(line)
        if task is None:
            print(f"  ✗ FAIL: Failed to parse: {line}")
            return False
        
        for attr, value in expected.items():
            if getattr(task, attr) != value:
                print(f"  ✗ FAIL: {line}")
                print(f"    Expected {attr}={value}, got {getattr(task, attr)}")
                return False
    
    print("  ✓ PASS: Tasks without optional markers work")
    return True


def test_ac5():
    """AC5: Returns empty list for invalid/empty files"""
    print("Testing AC5: Empty/invalid file handling...")
    
    # Test empty file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        tasks = parse_tasks_file(temp_path)
        if tasks != []:
            print(f"  ✗ FAIL: Empty file should return empty list, got {len(tasks)} tasks")
            return False
    finally:
        temp_path.unlink()
    
    # Test file with no tasks
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Just a header\n\nSome text\n- Regular bullet\n")
        temp_path = Path(f.name)
    
    try:
        tasks = parse_tasks_file(temp_path)
        if tasks != []:
            print(f"  ✗ FAIL: File with no tasks should return empty list, got {len(tasks)} tasks")
            return False
    finally:
        temp_path.unlink()
    
    # Test missing file
    try:
        parse_tasks_file(Path("/tmp/nonexistent-file-xyz.md"))
        print("  ✗ FAIL: Should raise FileNotFoundError for missing file")
        return False
    except FileNotFoundError:
        pass  # Expected
    
    print("  ✓ PASS: Empty/invalid file handling works")
    return True


def test_ac6():
    """AC6: Extracts file paths from description if present"""
    print("Testing AC6: File path extraction...")
    
    test_cases = [
        ("- [ ] [T001] Implement `src/models/User.ts` model", ["src/models/User.ts"]),
        ("- [ ] [T002] Files: `a.py`, `b.js`, `c.ts`", ["a.py", "b.js", "c.ts"]),
        ("- [ ] [T003] No files here", []),
        ("- [ ] [T004] Path `tests/unit/test.py` and `src/main.py`", ["tests/unit/test.py", "src/main.py"]),
    ]
    
    for line, expected_files in test_cases:
        task = parse_task_line(line)
        if task is None:
            print(f"  ✗ FAIL: Failed to parse: {line}")
            return False
        
        if task.files != expected_files:
            print(f"  ✗ FAIL: {line}")
            print(f"    Expected files={expected_files}, got {task.files}")
            return False
    
    print("  ✓ PASS: File path extraction works")
    return True


def test_real_tasks_file():
    """Bonus: Test parsing actual tasks.md file"""
    print("Testing: Real tasks.md file parsing...")
    
    tasks_path = Path(__file__).parent.parent / "specs" / "speckit-flow" / "tasks.md"
    
    if not tasks_path.exists():
        print("  ⚠ SKIP: tasks.md not found")
        return True
    
    tasks = parse_tasks_file(tasks_path)
    
    if len(tasks) == 0:
        print("  ✗ FAIL: Should parse tasks from tasks.md")
        return False
    
    # Verify T006 exists and is marked complete
    t006 = next((t for t in tasks if t.id == "T006"), None)
    if t006 is None:
        print("  ✗ FAIL: T006 should exist in tasks.md")
        return False
    
    if not t006.completed:
        print("  ⚠ WARNING: T006 should be marked complete")
    
    # Verify T006 has correct dependencies
    expected_deps = ["T003", "T005"]
    if set(t006.dependencies) != set(expected_deps):
        print(f"  ✗ FAIL: T006 dependencies should be {expected_deps}, got {t006.dependencies}")
        return False
    
    print(f"  ✓ PASS: Parsed {len(tasks)} tasks from tasks.md")
    print(f"    - T006 status: {'✓ Complete' if t006.completed else '○ Pending'}")
    print(f"    - T006 dependencies: {t006.dependencies}")
    return True


def main():
    """Run all acceptance criteria tests."""
    print("=" * 70)
    print("T006 ACCEPTANCE CRITERIA VERIFICATION")
    print("=" * 70)
    print()
    
    tests = [
        ("AC1", test_ac1),
        ("AC2", test_ac2),
        ("AC3", test_ac3),
        ("AC4", test_ac4),
        ("AC5", test_ac5),
        ("AC6", test_ac6),
        ("Bonus", test_real_tasks_file),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            print()
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
            print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print()
    if all_passed:
        print("🎉 ALL ACCEPTANCE CRITERIA PASSED - T006 IS COMPLETE")
        return 0
    else:
        print("❌ SOME ACCEPTANCE CRITERIA FAILED - REVIEW NEEDED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
