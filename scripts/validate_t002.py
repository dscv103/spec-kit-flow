#!/usr/bin/env python3
"""
T002 Validation Script

This script verifies that all acceptance criteria for T002 are met.
Run this to confirm the specify CLI still works after T001 refactoring.
"""
import subprocess
import sys
from pathlib import Path


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def run_check(description: str, command: list[str], check_func=None) -> bool:
    """Run a check and report results."""
    print(f"🔍 {description}")
    print(f"   Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        
        # Apply custom check function if provided
        if check_func:
            success = check_func(result)
        else:
            success = result.returncode == 0
        
        if success:
            print("   ✅ PASSED\n")
            return True
        else:
            print("   ❌ FAILED")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}\n")
            return False
            
    except Exception as e:
        print(f"   ❌ FAILED: {e}\n")
        return False


def main():
    """Run all T002 validation checks."""
    print_section("T002: Verify existing specify-cli still works")
    
    repo_root = Path(__file__).parent.parent
    
    results = []
    
    # AC1: specify --help displays help text
    print_section("AC1: verify --help displays help text")
    
    def check_help(result):
        if result.returncode != 0:
            return False
        output = result.stdout.lower()
        return "specify" in output and "help" in output and "init" in output
    
    results.append(run_check(
        "Run specify --help",
        [sys.executable, "-m", "specify_cli", "--help"],
        check_help
    ))
    
    # AC2: specify check runs without import errors
    print_section("AC2: specify check runs without import errors")
    
    def check_no_import_errors(result):
        stderr = result.stderr
        return "ImportError" not in stderr and "ModuleNotFoundError" not in stderr
    
    results.append(run_check(
        "Run specify check (verify no import errors)",
        [sys.executable, "-m", "specify_cli", "check"],
        check_no_import_errors
    ))
    
    # AC3: Existing functionality unchanged - test imports
    print_section("AC3: Existing functionality unchanged")
    
    def check_import(result):
        return result.returncode == 0 and "SUCCESS" in result.stdout
    
    # Create a small test script
    test_script = repo_root / "test_import_temp.py"
    test_script.write_text("""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src" / "specify_cli"))
import specify_cli
assert hasattr(specify_cli, 'app')
assert hasattr(specify_cli, 'main')
print("SUCCESS: All imports work correctly")
""")
    
    try:
        results.append(run_check(
            "Import specify_cli module",
            [sys.executable, str(test_script)],
            check_import
        ))
    finally:
        test_script.unlink(missing_ok=True)
    
    # Additional verification: version command
    print_section("Additional Verification: version command")
    
    results.append(run_check(
        "Run specify version",
        [sys.executable, "-m", "specify_cli", "version"],
        lambda r: r.returncode == 0
    ))
    
    # Summary
    print_section("Summary")
    
    passed = sum(results)
    total = len(results)
    
    print(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All acceptance criteria met! T002 is COMPLETE.\n")
        return 0
    else:
        print(f"\n❌ {total - passed} check(s) failed. T002 needs attention.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
