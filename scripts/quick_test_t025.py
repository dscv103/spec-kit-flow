#!/usr/bin/env python3
"""
Quick test for T025: CompletionMonitor basic functionality.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_flow.orchestration.completion import CompletionMonitor


def main():
    print("Testing T025: CompletionMonitor")
    print("-" * 40)
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        monitor = CompletionMonitor("001-test", repo_root)
        
        print(f"✓ Created monitor with spec_id='001-test'")
        print(f"  Completions dir: {monitor.completions_dir}")
        
        # Test marking complete
        monitor.mark_complete("T001")
        print(f"✓ Marked T001 as complete")
        
        # Test is_complete
        assert monitor.is_complete("T001")
        print(f"✓ is_complete('T001') = True")
        
        assert not monitor.is_complete("T002")
        print(f"✓ is_complete('T002') = False")
        
        # Test get_manual_completions
        completions = monitor.get_manual_completions()
        assert completions == {"T001"}
        print(f"✓ get_manual_completions() = {completions}")
        
        # Test multiple completions
        monitor.mark_complete("T002")
        monitor.mark_complete("T003")
        completions = monitor.get_manual_completions()
        assert completions == {"T001", "T002", "T003"}
        print(f"✓ Multiple completions work: {completions}")
        
        print()
        print("✅ All basic tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
