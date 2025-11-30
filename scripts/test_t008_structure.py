#!/usr/bin/env python3
"""
Quick validation for T008 - tests what we can verify without dependencies installed.

This focuses on package structure and import mechanics.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))


def test_package_structure():
    """Verify all required directories and __init__.py files exist."""
    print("Testing package structure...")
    
    base_path = repo_root / "src" / "speckit_flow"
    required_items = [
        ("__init__.py", "file"),
        ("__main__.py", "file"),
        ("pyproject.toml", "file"),
        ("orchestration/__init__.py", "file"),
        ("agents/__init__.py", "file"),
        ("worktree/__init__.py", "file"),
        ("monitoring/__init__.py", "file"),
        ("state/__init__.py", "file"),
    ]
    
    all_exist = True
    for item, item_type in required_items:
        item_path = base_path / item
        exists = item_path.exists()
        
        if item_type == "file":
            exists = exists and item_path.is_file()
        
        status = "✓" if exists else "❌"
        print(f"  {status} {item}")
        
        if not exists:
            all_exist = False
    
    return all_exist


def test_subpackage_imports():
    """Test that subpackages can be imported."""
    print("\nTesting subpackage imports...")
    
    subpackages = [
        "speckit_flow.orchestration",
        "speckit_flow.agents",
        "speckit_flow.worktree",
        "speckit_flow.monitoring",
        "speckit_flow.state",
    ]
    
    all_passed = True
    for subpkg in subpackages:
        try:
            __import__(subpkg)
            print(f"  ✓ {subpkg}")
        except Exception as e:
            print(f"  ❌ {subpkg}: {e}")
            all_passed = False
    
    return all_passed


def test_version_and_exports():
    """Test basic exports from main package."""
    print("\nTesting main package exports...")
    
    try:
        from speckit_flow import __version__, app, main
        
        print(f"  ✓ __version__ = {__version__}")
        print(f"  ✓ app = {app}")
        print(f"  ✓ main = {main}")
        
        # Verify typer import in __init__.py
        print(f"  ℹ Note: Full CLI testing requires typer (installed in T009)")
        
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        print(f"  ℹ This is expected if typer is not installed (T009)")
        return True  # Don't fail on missing typer yet
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False


def test_entry_points_defined():
    """Verify entry points are defined in pyproject.toml."""
    print("\nTesting entry point definitions...")
    
    try:
        pyproject_path = repo_root / "src" / "speckit_flow" / "pyproject.toml"
        content = pyproject_path.read_text()
        
        checks = [
            ('skf = "speckit_flow:main"', "skf entry point"),
            ('speckit-flow = "speckit_flow:main"', "speckit-flow entry point"),
        ]
        
        all_found = True
        for check_str, description in checks:
            if check_str in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ❌ {description} not found")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"  ❌ Failed to read pyproject.toml: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("T008 Structure Validation (Pre-dependencies)")
    print("=" * 70)
    print()
    
    results = []
    results.append(test_package_structure())
    results.append(test_subpackage_imports())
    results.append(test_version_and_exports())
    results.append(test_entry_points_defined())
    
    print("\n" + "=" * 70)
    
    if all(results):
        print("✅ All structure checks passed!")
        print("ℹ  Full CLI testing will be possible after T009 (dependencies)")
        return 0
    else:
        print("❌ Some checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
