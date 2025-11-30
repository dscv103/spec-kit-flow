#!/usr/bin/env python3
"""
Quick test for T022: skf dag command.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from speckit_flow import app
from typer.testing import CliRunner

runner = CliRunner()


def test_basic_functionality():
    """Test basic command invocation."""
    print("Testing skf dag --help...")
    result = runner.invoke(app, ["dag", "--help"])
    print(f"Exit code: {result.exit_code}")
    print(f"Output:\n{result.stdout}")
    
    if result.exit_code == 0:
        print("✓ Help command works")
        return True
    else:
        print("✗ Help command failed")
        return False


def test_in_current_repo():
    """Test running in the current repo (should work)."""
    print("\nTesting skf dag in current repo...")
    
    # Change to repo root
    import os
    os.chdir(repo_root)
    
    result = runner.invoke(app, ["dag", "--sessions", "3"])
    print(f"Exit code: {result.exit_code}")
    print(f"Output:\n{result.stdout}")
    
    if result.exit_code == 0:
        print("✓ DAG generation works in current repo")
        
        # Check if dag.yaml was created
        dag_path = repo_root / "specs" / "speckit-flow" / "dag.yaml"
        if dag_path.exists():
            print(f"✓ dag.yaml created at {dag_path.relative_to(repo_root)}")
            
            # Show first few lines
            content = dag_path.read_text()
            lines = content.split('\n')[:10]
            print("\nFirst 10 lines of dag.yaml:")
            for line in lines:
                print(f"  {line}")
            
            return True
        else:
            print(f"✗ dag.yaml not found at expected location")
            return False
    else:
        print("✗ DAG generation failed")
        if "Error:" in result.stdout:
            print("Error message captured in output")
        return False


if __name__ == "__main__":
    success = True
    
    success = test_basic_functionality() and success
    success = test_in_current_repo() and success
    
    if success:
        print("\n✓ All quick tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
