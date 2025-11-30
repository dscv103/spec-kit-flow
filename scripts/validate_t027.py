#!/usr/bin/env python3
"""
Validation script for T027: Unified completion checking.

Tests the implementation of get_completed_tasks() and wait_for_completion().
"""

import sys
import time
import tempfile
import threading
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_flow.orchestration.completion import CompletionMonitor


def test_get_completed_tasks():
    """Test get_completed_tasks() method."""
    print("Testing get_completed_tasks()...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        # Test 1: Manual completions only
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        completed = monitor.get_completed_tasks()
        assert completed == {"T001", "T002"}, f"Expected {{'T001', 'T002'}}, got {completed}"
        print("  ✓ Manual completions only")
        
        # Test 2: Union with tasks.md
        tasks_file = repo_root / "tasks.md"
        tasks_file.write_text("""
- [x] [T002] Task 2
- [x] [T003] Task 3
        """)
        completed = monitor.get_completed_tasks(tasks_file)
        assert completed == {"T001", "T002", "T003"}, f"Expected {{'T001', 'T002', 'T003'}}, got {completed}"
        print("  ✓ Union of manual and watched completions")
        
        # Test 3: Nonexistent file
        nonexistent = repo_root / "nonexistent.md"
        completed = monitor.get_completed_tasks(nonexistent)
        assert completed == {"T001", "T002"}, f"Expected {{'T001', 'T002'}}, got {completed}"
        print("  ✓ Handles nonexistent tasks file")
    
    print("✅ get_completed_tasks() tests passed!")


def test_wait_for_completion():
    """Test wait_for_completion() method."""
    print("\nTesting wait_for_completion()...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        # Test 1: Already complete
        monitor.mark_complete("T001")
        start = time.time()
        completed = monitor.wait_for_completion({"T001"})
        elapsed = time.time() - start
        assert completed == {"T001"}, f"Expected {{'T001'}}, got {completed}"
        assert elapsed < 0.1, f"Should return immediately, took {elapsed}s"
        print("  ✓ Returns immediately for already complete tasks")
        
        # Test 2: Empty set
        completed = monitor.wait_for_completion(set())
        assert completed == set(), f"Expected empty set, got {completed}"
        print("  ✓ Returns empty set for empty input")
        
        # Test 3: Wait for delayed completion
        def mark_after_delay():
            time.sleep(0.2)
            monitor.mark_complete("T002")
        
        thread = threading.Thread(target=mark_after_delay)
        thread.start()
        
        start = time.time()
        completed = monitor.wait_for_completion({"T002"}, poll_interval=0.05)
        elapsed = time.time() - start
        thread.join()
        
        assert completed == {"T002"}, f"Expected {{'T002'}}, got {completed}"
        assert 0.15 < elapsed < 0.5, f"Should wait ~0.2s, took {elapsed}s"
        print("  ✓ Waits for delayed completion")
        
        # Test 4: Timeout
        try:
            monitor.wait_for_completion({"T999"}, timeout=0.2, poll_interval=0.05)
            assert False, "Should have raised TimeoutError"
        except TimeoutError as e:
            error_msg = str(e)
            assert "T999" in error_msg, f"Error should mention T999: {error_msg}"
            print("  ✓ Raises TimeoutError on timeout")
        
        # Test 5: Mixed sources
        tasks_file = repo_root / "tasks.md"
        tasks_file.write_text("- [ ] [T003] Task 3")
        
        def complete_mixed():
            time.sleep(0.1)
            monitor.mark_complete("T004")  # Manual
            time.sleep(0.1)
            tasks_file.write_text("- [x] [T003] Task 3")  # Watched
        
        thread = threading.Thread(target=complete_mixed)
        thread.start()
        
        completed = monitor.wait_for_completion(
            {"T003", "T004"},
            tasks_file=tasks_file,
            poll_interval=0.05
        )
        thread.join()
        
        assert completed == {"T003", "T004"}, f"Expected {{'T003', 'T004'}}, got {completed}"
        print("  ✓ Waits for mixed manual and watched completions")
    
    print("✅ wait_for_completion() tests passed!")


def test_acceptance_criteria():
    """Verify all acceptance criteria for T027."""
    print("\n" + "="*60)
    print("Verifying T027 Acceptance Criteria")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        tasks_file = repo_root / "tasks.md"
        
        # AC 1: Union correctly combines both sources
        print("\n[AC 1] Union correctly combines both sources")
        monitor.mark_complete("T001")
        tasks_file.write_text("- [x] [T002] Task 2")
        completed = monitor.get_completed_tasks(tasks_file)
        assert "T001" in completed and "T002" in completed
        print("  ✅ Pass: Union includes both manual (T001) and watched (T002)")
        
        # AC 2: wait_for_completion blocks until all tasks done or timeout
        print("\n[AC 2] wait_for_completion blocks until all tasks done or timeout")
        
        # Test blocking until complete
        def mark_delayed():
            time.sleep(0.15)
            monitor.mark_complete("T003")
        
        thread = threading.Thread(target=mark_delayed)
        thread.start()
        start = time.time()
        completed = monitor.wait_for_completion({"T003"}, poll_interval=0.05)
        elapsed = time.time() - start
        thread.join()
        assert elapsed >= 0.1
        print(f"  ✅ Pass: Blocked for {elapsed:.2f}s until T003 complete")
        
        # Test timeout
        try:
            monitor.wait_for_completion({"T999"}, timeout=0.2, poll_interval=0.05)
            assert False, "Should timeout"
        except TimeoutError:
            print("  ✅ Pass: TimeoutError raised after timeout")
        
        # AC 3: Handles partial completion (some tasks done, some pending)
        print("\n[AC 3] Handles partial completion (some tasks done, some pending)")
        monitor.mark_complete("T010")
        monitor.mark_complete("T011")
        # T012 is pending
        try:
            monitor.wait_for_completion({"T010", "T011", "T012"}, timeout=0.2)
            assert False, "Should timeout"
        except TimeoutError as e:
            error_msg = str(e)
            assert "T012" in error_msg  # Pending
            assert "T010" in error_msg or "T011" in error_msg  # Completed
            print(f"  ✅ Pass: Partial completion handled, error shows pending and completed tasks")
    
    print("\n" + "="*60)
    print("✅ All acceptance criteria verified!")
    print("="*60)


def main():
    """Run all validation tests."""
    print("="*60)
    print("T027 Validation: Unified Completion Checking")
    print("="*60)
    
    try:
        test_get_completed_tasks()
        test_wait_for_completion()
        test_acceptance_criteria()
        
        print("\n" + "="*60)
        print("🎉 T027 Implementation Verified Successfully!")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
