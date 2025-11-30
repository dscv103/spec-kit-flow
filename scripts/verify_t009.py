#!/usr/bin/env python3
"""
Verification script for T009: Add speckit-flow dependencies

This script verifies ALL acceptance criteria for T009:
- AC1: `hatch env create` installs all dependencies
- AC2: All imports work: `import networkx`, `import watchfiles`, etc.

Run this after: hatch env create && hatch run install-packages
"""

import sys
from pathlib import Path


def check_dependencies_in_pyproject() -> bool:
    """Verify dependencies are correctly specified in pyproject.toml."""
    print("=" * 70)
    print("Checking pyproject.toml dependencies configuration")
    print("=" * 70)
    
    pyproject_path = Path(__file__).parent.parent / "src" / "speckit_flow" / "pyproject.toml"
    content = pyproject_path.read_text()
    
    required_deps = [
        "speckit-core",
        "typer",
        "rich",
        "networkx",
        "pyyaml",
        "pydantic>=2.0",
        "filelock",
        "watchfiles",
    ]
    
    all_found = True
    for dep in required_deps:
        if dep in content:
            print(f"✓ Found: {dep}")
        else:
            print(f"✗ Missing: {dep}")
            all_found = False
    
    print()
    return all_found


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


def test_imports() -> bool:
    """Test that all required dependencies can be imported."""
    print("=" * 70)
    print("Testing dependency imports (AC2)")
    print("=" * 70)
    
    all_passed = True
    
    tests = [
        ("speckit_core", "speckit-core (local package)"),
        ("typer", "Typer (CLI framework)"),
        ("rich", "Rich (terminal formatting)"),
        ("networkx", "NetworkX (graph library)"),
        ("yaml", "PyYAML (YAML parsing) - import as 'yaml'"),
        ("pydantic", "Pydantic (data validation)"),
        ("filelock", "filelock (file locking)"),
        ("watchfiles", "watchfiles (file watching)"),
    ]
    
    for module, description in tests:
        if not test_import(module, description):
            all_passed = False
    
    print()
    return all_passed


def test_speckit_flow_imports() -> bool:
    """Test that speckit_flow package and subpackages import correctly."""
    print("=" * 70)
    print("Testing speckit_flow package imports")
    print("=" * 70)
    
    all_passed = True
    
    package_tests = [
        ("speckit_flow", "Main package"),
        ("speckit_flow.agents", "agents subpackage"),
        ("speckit_flow.monitoring", "monitoring subpackage"),
        ("speckit_flow.orchestration", "orchestration subpackage"),
        ("speckit_flow.state", "state subpackage"),
        ("speckit_flow.worktree", "worktree subpackage"),
    ]
    
    for module, description in package_tests:
        if not test_import(module, description):
            all_passed = False
    
    print()
    return all_passed


def verify_acceptance_criteria() -> tuple[bool, list[str]]:
    """Verify all acceptance criteria for T009."""
    print("\n" + "=" * 70)
    print("T009 ACCEPTANCE CRITERIA VERIFICATION")
    print("=" * 70)
    print()
    
    results = []
    all_passed = True
    
    # AC1: Dependencies configured
    print("AC1: `hatch env create` installs all dependencies")
    print("-" * 70)
    deps_configured = check_dependencies_in_pyproject()
    if deps_configured:
        print("✓ AC1 PASS: All dependencies correctly specified in pyproject.toml")
        results.append("✓ AC1: Dependencies configured in pyproject.toml")
    else:
        print("✗ AC1 FAIL: Missing dependencies in pyproject.toml")
        results.append("✗ AC1: Missing dependencies")
        all_passed = False
    print()
    
    # AC2: All imports work
    print("AC2: All imports work: `import networkx`, `import watchfiles`, etc.")
    print("-" * 70)
    imports_work = test_imports() and test_speckit_flow_imports()
    if imports_work:
        print("✓ AC2 PASS: All required imports successful")
        results.append("✓ AC2: All imports work (networkx, watchfiles, typer, rich, etc.)")
    else:
        print("✗ AC2 FAIL: Some imports failed")
        print()
        print("To fix, ensure you have run:")
        print("  hatch env create")
        print("  hatch run install-packages")
        results.append("✗ AC2: Import failures detected")
        all_passed = False
    print()
    
    return all_passed, results


def main() -> int:
    """Run all verification checks."""
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  T009 VERIFICATION: Add speckit-flow dependencies".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    all_passed, results = verify_acceptance_criteria()
    
    # Final summary
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    for result in results:
        print(result)
    print()
    
    if all_passed:
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 68 + "║")
        print("║" + "  ✓ ALL ACCEPTANCE CRITERIA PASSED".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("║" + "  T009 is COMPLETE and ready to be marked [x]".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("╚" + "=" * 68 + "╝")
        print()
        return 0
    else:
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 68 + "║")
        print("║" + "  ✗ SOME ACCEPTANCE CRITERIA FAILED".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("║" + "  Review failures above and fix before marking complete".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("╚" + "=" * 68 + "╝")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
