#!/usr/bin/env python3
"""
Comparison test: Verify Python paths.py matches bash common.sh behavior.

This script compares the output of the Python implementation with the bash
implementation to ensure they produce equivalent results.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src" / "speckit_core"))

from speckit_core.paths import get_repo_root, get_current_branch


def get_bash_repo_root():
    """Get repo root using bash script."""
    script = repo_root / "scripts" / "bash" / "common.sh"
    result = subprocess.run(
        ["bash", "-c", f"source {script} && get_repo_root"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def get_bash_current_branch():
    """Get current branch using bash script."""
    script = repo_root / "scripts" / "bash" / "common.sh"
    result = subprocess.run(
        ["bash", "-c", f"source {script} && get_current_branch"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main():
    print("=" * 70)
    print("Comparing Python paths.py with Bash common.sh")
    print("=" * 70)
    print()
    
    # Test 1: Compare repo root
    print("[1/2] Comparing get_repo_root()...")
    try:
        python_root = get_repo_root()
        bash_root = get_bash_repo_root()
        
        if python_root == bash_root:
            print(f"  ✓ MATCH: {python_root}")
        else:
            print(f"  ✗ MISMATCH:")
            print(f"    Python: {python_root}")
            print(f"    Bash:   {bash_root}")
            return 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    # Test 2: Compare current branch
    print()
    print("[2/2] Comparing get_current_branch()...")
    try:
        python_branch = get_current_branch()
        bash_branch = get_bash_current_branch()
        
        if python_branch == bash_branch:
            print(f"  ✓ MATCH: {python_branch}")
        else:
            print(f"  ✗ MISMATCH:")
            print(f"    Python: {python_branch}")
            print(f"    Bash:   {bash_branch}")
            return 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    # Test 3: Test with SPECIFY_FEATURE env var
    print()
    print("[3/3] Testing SPECIFY_FEATURE environment variable...")
    try:
        os.environ["SPECIFY_FEATURE"] = "test-branch"
        
        python_branch = get_current_branch()
        bash_branch = get_bash_current_branch()
        
        if python_branch == bash_branch == "test-branch":
            print(f"  ✓ MATCH: Both use SPECIFY_FEATURE = {python_branch}")
        else:
            print(f"  ✗ MISMATCH:")
            print(f"    Python: {python_branch}")
            print(f"    Bash:   {bash_branch}")
            return 1
        
        del os.environ["SPECIFY_FEATURE"]
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    print()
    print("=" * 70)
    print("✓ Python implementation matches bash behavior!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
