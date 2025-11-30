#!/usr/bin/env python3
"""Quick test for T026 implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that all components can be imported."""
    print("Testing imports...")
    try:
        from speckit_flow.orchestration.completion import (
            watch_tasks_file,
            _parse_completed_tasks,
            COMPLETED_TASK_PATTERN,
        )
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_parse_completed():
    """Test the parsing helper."""
    print("\nTesting _parse_completed_tasks...")
    try:
        from speckit_flow.orchestration.completion import _parse_completed_tasks
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""
# Tasks
- [x] [T001] Completed task
- [ ] [T002] Pending task
- [X] [T003] Uppercase X
            """)
            path = Path(f.name)
        
        try:
            completed = _parse_completed_tasks(path)
            expected = {"T001", "T003"}
            
            if completed == expected:
                print(f"✓ Parsing works: {completed}")
                return True
            else:
                print(f"✗ Expected {expected}, got {completed}")
                return False
        finally:
            path.unlink()
            
    except Exception as e:
        print(f"✗ Parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_watch_basic():
    """Test basic watching functionality."""
    print("\nTesting watch_tasks_file (basic)...")
    try:
        from speckit_flow.orchestration.completion import watch_tasks_file
        import tempfile
        import threading
        import time
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("- [ ] [T001] Task\n")
            path = Path(f.name)
        
        try:
            completed = []
            event = threading.Event()
            
            def callback(tasks):
                completed.append(tasks)
                event.set()
            
            # Start watching in thread
            thread = threading.Thread(
                target=watch_tasks_file,
                args=(path, callback),
                daemon=True
            )
            thread.start()
            time.sleep(0.3)
            
            # Modify file
            path.write_text("- [x] [T001] Task\n")
            
            # Wait for callback
            if event.wait(timeout=3.0):
                if completed and "T001" in completed[0]:
                    print(f"✓ Watch detected completion: {completed[0]}")
                    return True
                else:
                    print(f"✗ Wrong tasks detected: {completed}")
                    return False
            else:
                print("✗ Callback not triggered")
                return False
        finally:
            path.unlink()
            
    except Exception as e:
        print(f"✗ Watch test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all quick tests."""
    print("=" * 60)
    print("T026 Quick Test")
    print("=" * 60)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Parse", test_parse_completed()))
    results.append(("Watch", test_watch_basic()))
    
    print("\n" + "=" * 60)
    print("Results")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
