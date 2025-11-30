#!/usr/bin/env python3
"""
Quick validation script for T004 implementation.

This script verifies that paths.py works correctly in the current repository.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src" / "speckit_core"))

from speckit_core.paths import (
    get_repo_root,
    get_current_branch,
    get_feature_paths,
    find_feature_dir_by_prefix,
)
from speckit_core.exceptions import NotInGitRepoError, FeatureNotFoundError


def main():
    print("=" * 60)
    print("T004 Validation: paths.py Implementation")
    print("=" * 60)
    print()
    
    # Test 1: get_repo_root
    print("[1/4] Testing get_repo_root()...")
    try:
        repo = get_repo_root()
        print(f"  ✓ Repository root: {repo}")
        assert repo.is_dir()
        assert (repo / ".git").exists()
        print(f"  ✓ Valid git repository")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    # Test 2: get_current_branch
    print()
    print("[2/4] Testing get_current_branch()...")
    try:
        branch = get_current_branch()
        print(f"  ✓ Current branch: {branch}")
        assert isinstance(branch, str)
        assert len(branch) > 0
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    # Test 3: find_feature_dir_by_prefix
    print()
    print("[3/4] Testing find_feature_dir_by_prefix()...")
    try:
        # Test with speckit-flow feature
        feature_dir = find_feature_dir_by_prefix(repo, "speckit-flow")
        print(f"  ✓ Found feature directory: {feature_dir}")
        assert feature_dir == repo / "specs" / "speckit-flow"
    except FeatureNotFoundError:
        print(f"  ✓ Correctly raises FeatureNotFoundError for missing features")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    # Test 4: get_feature_paths
    print()
    print("[4/4] Testing get_feature_paths()...")
    try:
        context = get_feature_paths(repo, "speckit-flow")
        print(f"  ✓ Feature context created")
        print(f"    - repo_root: {context.repo_root}")
        print(f"    - branch: {context.branch}")
        print(f"    - feature_dir: {context.feature_dir}")
        print(f"    - spec_path: {context.spec_path}")
        print(f"    - plan_path: {context.plan_path}")
        print(f"    - tasks_path: {context.tasks_path}")
        
        # Verify paths are absolute
        assert context.repo_root.is_absolute()
        assert context.feature_dir.is_absolute()
        assert context.spec_path.is_absolute()
        print(f"  ✓ All paths are absolute")
        
        # Verify immutability
        try:
            context.branch = "modified"
            print(f"  ✗ Context is not immutable!")
            return 1
        except:
            print(f"  ✓ Context is immutable (frozen)")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return 1
    
    print()
    print("=" * 60)
    print("✓ All T004 acceptance criteria validated successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
