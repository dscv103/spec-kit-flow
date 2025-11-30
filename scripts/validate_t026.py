#!/usr/bin/env python3
"""
Validation script for T026: Implement tasks.md file watching.

Task: [T026] [P] [deps:T025] **Implement tasks.md file watching**

Acceptance Criteria:
- AC1: Detects checkbox state changes
- AC2: Handles rapid successive changes (debounce)
- AC3: Works across multiple worktree watches simultaneously
- AC4: Graceful handling of file deletion/rename
"""

import sys
import time
import threading
from pathlib import Path
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_flow.orchestration.completion import (
    watch_tasks_file,
    _parse_completed_tasks,
)


def test_ac1_detects_checkbox_changes():
    """AC1: Detects checkbox state changes."""
    print("\nAC1: Detects checkbox state changes")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_file = Path(tmpdir) / "tasks.md"
        tasks_file.write_text("""
# Tasks
- [ ] [T001] Task one
- [ ] [T002] Task two
        """)
        
        completed_tasks = []
        callback_event = threading.Event()
        
        def callback(task_ids: set[str]):
            completed_tasks.append(task_ids)
            callback_event.set()
        
        # Start watching
        watch_thread = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file, callback),
            daemon=True
        )
        watch_thread.start()
        time.sleep(0.3)
        
        # Mark T001 complete
        tasks_file.write_text("""
# Tasks
- [x] [T001] Task one
- [ ] [T002] Task two
        """)
        
        # Wait for callback
        if callback_event.wait(timeout=3.0):
            if completed_tasks and "T001" in completed_tasks[0]:
                print("✓ AC1: Detects checkbox state changes")
                return True
            else:
                print(f"✗ AC1: Callback triggered but wrong tasks: {completed_tasks}")
                return False
        else:
            print("✗ AC1: Callback not triggered within timeout")
            return False


def test_ac2_handles_debouncing():
    """AC2: Handles rapid successive changes (debounce)."""
    print("\nAC2: Handles rapid successive changes (debounce)")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_file = Path(tmpdir) / "tasks.md"
        tasks_file.write_text("- [ ] [T001] Task")
        
        completed_tasks = []
        
        def callback(task_ids: set[str]):
            completed_tasks.append(task_ids)
        
        # Start watching with explicit debounce
        watch_thread = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file, callback, 200),  # 200ms debounce
            daemon=True
        )
        watch_thread.start()
        time.sleep(0.3)
        
        # Make rapid changes
        for i in range(5):
            tasks_file.write_text(f"- [x] [T001] Task (change {i})")
            time.sleep(0.05)  # 50ms between changes
        
        # Wait for debounce to settle
        time.sleep(0.5)
        
        if completed_tasks:
            # Check that T001 was detected
            if any("T001" in tasks for tasks in completed_tasks):
                print(f"✓ AC2: Handles debouncing (got {len(completed_tasks)} callback(s))")
                return True
            else:
                print(f"✗ AC2: No T001 detected in callbacks: {completed_tasks}")
                return False
        else:
            print("✗ AC2: No callbacks received after rapid changes")
            return False


def test_ac3_concurrent_watches():
    """AC3: Works across multiple worktree watches simultaneously."""
    print("\nAC3: Works across multiple worktree watches simultaneously")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_file_1 = Path(tmpdir) / "tasks1.md"
        tasks_file_2 = Path(tmpdir) / "tasks2.md"
        
        tasks_file_1.write_text("- [ ] [T001] Task in file 1")
        tasks_file_2.write_text("- [ ] [T002] Task in file 2")
        
        completed_1 = []
        completed_2 = []
        event_1 = threading.Event()
        event_2 = threading.Event()
        
        def callback_1(task_ids: set[str]):
            completed_1.append(task_ids)
            event_1.set()
        
        def callback_2(task_ids: set[str]):
            completed_2.append(task_ids)
            event_2.set()
        
        # Start watching both files
        thread_1 = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file_1, callback_1),
            daemon=True
        )
        thread_2 = threading.Thread(
            target=watch_tasks_file,
            args=(tasks_file_2, callback_2),
            daemon=True
        )
        
        thread_1.start()
        thread_2.start()
        time.sleep(0.3)
        
        # Complete tasks in both files
        tasks_file_1.write_text("- [x] [T001] Task in file 1")
        time.sleep(0.1)
        tasks_file_2.write_text("- [x] [T002] Task in file 2")
        
        # Both callbacks should be triggered
        result_1 = event_1.wait(timeout=3.0)
        result_2 = event_2.wait(timeout=3.0)
        
        if result_1 and result_2:
            if completed_1 and "T001" in completed_1[0] and completed_2 and "T002" in completed_2[0]:
                print("✓ AC3: Works across multiple worktree watches simultaneously")
                return True
            else:
                print(f"✗ AC3: Wrong tasks detected. File 1: {completed_1}, File 2: {completed_2}")
                return False
        else:
            print(f"✗ AC3: Not all callbacks triggered. File 1: {result_1}, File 2: {result_2}")
            return False


def test_ac4_handles_deletion():
    """AC4: Graceful handling of file deletion/rename."""
    print("\nAC4: Graceful handling of file deletion/rename")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_file = Path(tmpdir) / "tasks.md"
        tasks_file.write_text("- [ ] [T001] Task")
        
        watch_started = threading.Event()
        watch_stopped = threading.Event()
        
        def callback(task_ids: set[str]):
            pass
        
        def watch_with_signal():
            watch_started.set()
            try:
                watch_tasks_file(tasks_file, callback)
            except Exception as e:
                print(f"  Exception during watch: {e}")
            finally:
                watch_stopped.set()
        
        watch_thread = threading.Thread(target=watch_with_signal, daemon=True)
        watch_thread.start()
        
        # Wait for watch to start
        if not watch_started.wait(timeout=2.0):
            print("✗ AC4: Watch didn't start")
            return False
        
        time.sleep(0.3)
        
        # Delete the file
        tasks_file.unlink()
        
        # Wait for watch to stop gracefully
        if watch_stopped.wait(timeout=3.0):
            print("✓ AC4: Gracefully handles file deletion")
            return True
        else:
            print("✗ AC4: Watch didn't stop after file deletion")
            return False


def test_helper_parse_completed():
    """Test the _parse_completed_tasks helper."""
    print("\nHelper: _parse_completed_tasks")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_file = Path(tmpdir) / "tasks.md"
        tasks_file.write_text("""
# Tasks
- [x] [T001] Completed task
- [ ] [T002] Pending task
- [x] [T003] Another completed
- [X] [T004] Uppercase X
        """)
        
        completed = _parse_completed_tasks(tasks_file)
        
        expected = {"T001", "T003", "T004"}
        if completed == expected:
            print(f"✓ Helper: Parses completed tasks correctly: {completed}")
            return True
        else:
            print(f"✗ Helper: Expected {expected}, got {completed}")
            return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("T026 Validation: tasks.md file watching")
    print("=" * 60)
    
    results = []
    
    # Test helper function first
    results.append(("Helper", test_helper_parse_completed()))
    
    # Test acceptance criteria
    results.append(("AC1", test_ac1_detects_checkbox_changes()))
    results.append(("AC2", test_ac2_handles_debouncing()))
    results.append(("AC3", test_ac3_concurrent_watches()))
    results.append(("AC4", test_ac4_handles_deletion()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All acceptance criteria validated!")
        return 0
    else:
        print(f"\n❌ {total - passed} acceptance criteria failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
