#!/usr/bin/env python3
"""
Validation script for T009: Add speckit-flow dependencies

This script verifies that all required dependencies for speckit-flow
are installed and can be imported correctly.

Acceptance Criteria:
- AC1: `hatch env create` installs all dependencies
- AC2: All imports work: `import networkx`, `import watchfiles`, etc.
"""

import sys
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src" / "speckit_flow"))
sys.path.insert(0, str(repo_root / "src" / "speckit_core"))
sys.path.insert(0, str(repo_root / "src" / "specify_cli"))


def test_import(module_name: str, description: str) -> bool:
    """Test if a module can be imported."""
    try:
        __import__(module_name)
        print(f"✓ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"✗ {description}: {module_name}")
        print(f"  Error: {e}")
        return False


def main() -> int:
    """Run validation tests."""
    print("=" * 70)
    print("T009 Validation: speckit-flow Dependencies")
    print("=" * 70)
    print()

    all_passed = True

    # Test core dependencies
    print("Core dependencies (required by plan.md):")
    print("-" * 70)
    
    tests = [
        ("speckit_core", "speckit-core (local package)"),
        ("typer", "Typer (CLI framework)"),
        ("rich", "Rich (terminal formatting)"),
        ("networkx", "NetworkX (graph library)"),
        ("yaml", "PyYAML (YAML parsing)"),
        ("pydantic", "Pydantic (data validation)"),
        ("filelock", "filelock (file locking)"),
        ("watchfiles", "watchfiles (file watching)"),
    ]
    
    for module, description in tests:
        if not test_import(module, description):
            all_passed = False
    
    print()
    
    # Test that speckit_flow itself can be imported
    print("Package import tests:")
    print("-" * 70)
    
    package_tests = [
        ("speckit_flow", "speckit_flow package"),
        ("speckit_flow.agents", "speckit_flow.agents subpackage"),
        ("speckit_flow.monitoring", "speckit_flow.monitoring subpackage"),
        ("speckit_flow.orchestration", "speckit_flow.orchestration subpackage"),
        ("speckit_flow.state", "speckit_flow.state subpackage"),
        ("speckit_flow.worktree", "speckit_flow.worktree subpackage"),
    ]
    
    for module, description in package_tests:
        if not test_import(module, description):
            all_passed = False
    
    print()
    print("=" * 70)
    
    if all_passed:
        print("✓ All acceptance criteria passed!")
        print()
        print("AC1: ✓ All dependencies can be imported (implies hatch env create succeeded)")
        print("AC2: ✓ All imports work: networkx, watchfiles, typer, rich, etc.")
        return 0
    else:
        print("✗ Some tests failed. Check the output above.")
        print()
        print("To install dependencies, run:")
        print("  hatch env create")
        print("  hatch shell")
        return 1


if __name__ == "__main__":
    sys.exit(main())
