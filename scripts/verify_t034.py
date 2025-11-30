#!/usr/bin/env python3
"""
Quick verification script for T034: skf init command.

This script demonstrates the init command functionality.
Run from the repository root.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd: list[str], cwd: Path = None, input_text: str = None) -> tuple[int, str]:
    """Run a command and return exit code and output."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        input=input_text,
    )
    return result.returncode, result.stdout + result.stderr


def main():
    print("=" * 70)
    print("T034 Verification: skf init command")
    print("=" * 70)
    print()
    
    # Create temp directory and initialize git repo
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        print(f"✓ Created temporary directory: {temp_path}")
        
        # Initialize git repo
        run_command(["git", "init"], cwd=temp_path)
        run_command(["git", "config", "user.email", "test@test.com"], cwd=temp_path)
        run_command(["git", "config", "user.name", "Test User"], cwd=temp_path)
        print("✓ Initialized git repository")
        print()
        
        # Test 1: Error when no specs/ directory
        print("Test 1: Verify error when specs/ directory is missing")
        print("-" * 70)
        exit_code, output = run_command(["python", "-m", "speckit_flow", "init"], cwd=temp_path)
        
        if exit_code != 0 and "specs/ directory not found" in output:
            print("✓ PASS: Correctly errors when specs/ is missing")
            print(f"  Error message shown: {output[:100]}...")
        else:
            print("✗ FAIL: Did not error correctly")
            print(f"  Exit code: {exit_code}")
            print(f"  Output: {output}")
            return 1
        print()
        
        # Create specs directory
        (temp_path / "specs").mkdir()
        print("✓ Created specs/ directory")
        print()
        
        # Test 2: Create config with defaults
        print("Test 2: Create config with default values")
        print("-" * 70)
        exit_code, output = run_command(["python", "-m", "speckit_flow", "init"], cwd=temp_path)
        
        if exit_code == 0 and "initialized successfully" in output:
            print("✓ PASS: Config created successfully")
            print(f"  Output preview: {output[:200]}...")
            
            # Check config file
            config_path = temp_path / ".speckit" / "speckit-flow.yaml"
            if config_path.exists():
                content = config_path.read_text()
                print(f"✓ Config file created at: {config_path}")
                print(f"  Content:\n{content}")
                
                if "agent_type: copilot" in content and "num_sessions: 3" in content:
                    print("✓ PASS: Config has correct default values")
                else:
                    print("✗ FAIL: Config values incorrect")
                    return 1
            else:
                print("✗ FAIL: Config file not created")
                return 1
        else:
            print("✗ FAIL: Command did not succeed")
            print(f"  Exit code: {exit_code}")
            print(f"  Output: {output}")
            return 1
        print()
        
        # Test 3: Overwrite existing config
        print("Test 3: Overwrite existing config with custom values")
        print("-" * 70)
        exit_code, output = run_command(
            ["python", "-m", "speckit_flow", "init", "--sessions", "5", "--agent", "goose"],
            cwd=temp_path,
            input_text="y\n"  # Confirm overwrite
        )
        
        if exit_code == 0:
            print("✓ PASS: Config updated successfully")
            
            # Check updated values
            config_path = temp_path / ".speckit" / "speckit-flow.yaml"
            content = config_path.read_text()
            print(f"  Updated content:\n{content}")
            
            if "agent_type: goose" in content and "num_sessions: 5" in content:
                print("✓ PASS: Config updated with custom values")
            else:
                print("✗ FAIL: Config not updated correctly")
                return 1
        else:
            print("✗ FAIL: Update command did not succeed")
            print(f"  Exit code: {exit_code}")
            print(f"  Output: {output}")
            return 1
        print()
    
    print("=" * 70)
    print("All verification tests passed! ✓")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
