#!/usr/bin/env python3
"""
Validation script for T025: CompletionMonitor implementation.

This script validates all acceptance criteria for T025.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_flow.orchestration.completion import CompletionMonitor


def test_ac1_creates_directory():
    """AC1: Creates completions directory if missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        # Directory shouldn't exist initially
        assert not monitor.completions_dir.exists()
        
        # Mark a task complete
        monitor.mark_complete("T001")
        
        # Directory should now exist
        assert monitor.completions_dir.exists()
        assert monitor.completions_dir.is_dir()
        
        print("✓ AC1: Creates completions directory if missing")


def test_ac2_done_files_empty():
    """AC2: Done files are empty (touch only)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        monitor.mark_complete("T001")
        
        done_file = monitor.completions_dir / "T001.done"
        assert done_file.exists()
        # Verify file is empty
        assert done_file.stat().st_size == 0
        
        print("✓ AC2: Done files are empty (touch only)")


def test_ac3_concurrent_marking_safe():
    """AC3: Handles concurrent marking safely."""
    import threading
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        def mark_tasks():
            for i in range(10):
                monitor.mark_complete(f"T{i:03d}")
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=mark_tasks)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all tasks marked
        completions = monitor.get_manual_completions()
        expected = {f"T{i:03d}" for i in range(10)}
        assert completions == expected
        
        print("✓ AC3: Handles concurrent marking safely")


def test_basic_functionality():
    """Test basic CompletionMonitor functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        # Test mark_complete
        monitor.mark_complete("T001")
        monitor.mark_complete("T002")
        monitor.mark_complete("T003")
        
        # Test is_complete
        assert monitor.is_complete("T001")
        assert monitor.is_complete("T002")
        assert monitor.is_complete("T003")
        assert not monitor.is_complete("T004")
        
        # Test get_manual_completions
        completions = monitor.get_manual_completions()
        assert completions == {"T001", "T002", "T003"}
        
        print("✓ Basic functionality: mark_complete, is_complete, get_manual_completions")


def test_empty_directory_handling():
    """Test handling of missing directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        # Should handle missing directory gracefully
        assert monitor.get_manual_completions() == set()
        assert not monitor.is_complete("T001")
        
        print("✓ Handles missing completions directory gracefully")


def test_idempotent_marking():
    """Test that marking the same task multiple times is safe."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        # Mark same task multiple times
        monitor.mark_complete("T001")
        monitor.mark_complete("T001")
        monitor.mark_complete("T001")
        
        # Should still have exactly one completion
        completions = monitor.get_manual_completions()
        assert completions == {"T001"}
        
        print("✓ Idempotent marking works correctly")


def test_persistence():
    """Test that completions persist across monitor instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        
        # First monitor marks tasks
        monitor1 = CompletionMonitor("001-test", repo_root)
        monitor1.mark_complete("T001")
        monitor1.mark_complete("T002")
        
        # Second monitor sees same state
        monitor2 = CompletionMonitor("001-test", repo_root)
        assert monitor2.is_complete("T001")
        assert monitor2.is_complete("T002")
        assert monitor2.get_manual_completions() == {"T001", "T002"}
        
        print("✓ Completions persist across monitor instances")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("T025 Validation: CompletionMonitor")
    print("=" * 60)
    print()
    
    try:
        # Test acceptance criteria
        test_ac1_creates_directory()
        test_ac2_done_files_empty()
        test_ac3_concurrent_marking_safe()
        
        print()
        print("Additional functionality tests:")
        print()
        
        # Test basic functionality
        test_basic_functionality()
        test_empty_directory_handling()
        test_idempotent_marking()
        test_persistence()
        
        print()
        print("=" * 60)
        print("✅ All T025 acceptance criteria PASSED")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ FAILED: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
