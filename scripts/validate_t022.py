#!/usr/bin/env python3
"""
Validation script for T022: skf dag command.

Tests:
1. Command generates dag.yaml in correct location
2. Prints human-readable summary to stdout
3. Exits with error code 1 if no tasks.md found
4. Exits with error code 1 if cyclic dependencies detected
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def run_command(cmd: list[str], cwd: Path = None) -> tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def setup_test_repo(repo_path: Path) -> None:
    """Initialize a git repo with spec structure."""
    # Initialize git
    run_command(["git", "init"], cwd=repo_path)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=repo_path)
    run_command(["git", "config", "user.name", "Test User"], cwd=repo_path)
    
    # Create initial commit
    readme = repo_path / "README.md"
    readme.write_text("# Test Repo\n")
    run_command(["git", "add", "."], cwd=repo_path)
    run_command(["git", "commit", "-m", "Initial commit"], cwd=repo_path)


def test_dag_command_success():
    """Test that skf dag generates dag.yaml successfully."""
    print("\n=== Test 1: Successful DAG generation ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        setup_test_repo(repo_path)
        
        # Create feature directory with tasks.md
        feature_dir = repo_path / "specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)
        
        tasks_content = """# Tasks

- [ ] [T001] [deps:] **Setup project**
- [ ] [T002] [P] [deps:T001] **Implement feature A**
- [ ] [T003] [P] [deps:T001] **Implement feature B**
- [ ] [T004] [deps:T002,T003] **Integration test**
"""
        (feature_dir / "tasks.md").write_text(tasks_content)
        
        # Create feature branch
        run_command(["git", "checkout", "-b", "001-test-feature"], cwd=repo_path)
        
        # Run skf dag
        returncode, stdout, stderr = run_command(
            ["python", "-m", "speckit_flow", "dag"],
            cwd=repo_path
        )
        
        print(f"Exit code: {returncode}")
        print(f"Stdout:\n{stdout}")
        if stderr:
            print(f"Stderr:\n{stderr}")
        
        # Verify exit code
        assert returncode == 0, f"Expected exit code 0, got {returncode}"
        
        # Verify dag.yaml exists
        dag_path = feature_dir / "dag.yaml"
        assert dag_path.exists(), f"dag.yaml not found at {dag_path}"
        
        # Verify dag.yaml content
        dag_data = yaml.safe_load(dag_path.read_text())
        assert dag_data["version"] == "1.0"
        assert dag_data["spec_id"] == "001-test-feature"
        assert dag_data["num_sessions"] == 3
        assert "phases" in dag_data
        assert len(dag_data["phases"]) > 0
        
        # Verify summary in output
        assert "DAG generated successfully" in stdout
        assert "Tasks:" in stdout
        assert "Phases:" in stdout
        assert "Sessions:" in stdout
        
        print("✓ Test 1 passed: DAG generated successfully")


def test_dag_command_no_tasks_file():
    """Test that skf dag exits with code 1 when tasks.md is missing."""
    print("\n=== Test 2: No tasks.md file ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        setup_test_repo(repo_path)
        
        # Create feature directory WITHOUT tasks.md
        feature_dir = repo_path / "specs" / "002-no-tasks"
        feature_dir.mkdir(parents=True)
        
        # Create feature branch
        run_command(["git", "checkout", "-b", "002-no-tasks"], cwd=repo_path)
        
        # Run skf dag
        returncode, stdout, stderr = run_command(
            ["python", "-m", "speckit_flow", "dag"],
            cwd=repo_path
        )
        
        print(f"Exit code: {returncode}")
        print(f"Stdout:\n{stdout}")
        
        # Verify exit code is 1
        assert returncode == 1, f"Expected exit code 1, got {returncode}"
        
        # Verify error message
        assert "Error:" in stdout or "Error:" in stderr
        assert "not found" in stdout.lower() or "not found" in stderr.lower()
        
        print("✓ Test 2 passed: Exits with code 1 for missing tasks.md")


def test_dag_command_cyclic_dependency():
    """Test that skf dag exits with code 1 for circular dependencies."""
    print("\n=== Test 3: Circular dependency detection ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        setup_test_repo(repo_path)
        
        # Create feature directory with cyclic tasks
        feature_dir = repo_path / "specs" / "003-cyclic"
        feature_dir.mkdir(parents=True)
        
        # Create tasks with circular dependency: T001 -> T002 -> T003 -> T001
        tasks_content = """# Tasks

- [ ] [T001] [deps:T003] **Task A**
- [ ] [T002] [deps:T001] **Task B**
- [ ] [T003] [deps:T002] **Task C**
"""
        (feature_dir / "tasks.md").write_text(tasks_content)
        
        # Create feature branch
        run_command(["git", "checkout", "-b", "003-cyclic"], cwd=repo_path)
        
        # Run skf dag
        returncode, stdout, stderr = run_command(
            ["python", "-m", "speckit_flow", "dag"],
            cwd=repo_path
        )
        
        print(f"Exit code: {returncode}")
        print(f"Stdout:\n{stdout}")
        
        # Verify exit code is 1
        assert returncode == 1, f"Expected exit code 1, got {returncode}"
        
        # Verify error message mentions circular dependency
        output = stdout + stderr
        assert "circular" in output.lower() or "cycle" in output.lower(), \
            "Error message should mention circular dependency"
        
        print("✓ Test 3 passed: Detects circular dependencies")


def test_dag_command_custom_sessions():
    """Test that --sessions option works."""
    print("\n=== Test 4: Custom session count ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        setup_test_repo(repo_path)
        
        # Create feature directory with tasks
        feature_dir = repo_path / "specs" / "004-sessions"
        feature_dir.mkdir(parents=True)
        
        tasks_content = """# Tasks

- [ ] [T001] [deps:] **Setup**
- [ ] [T002] [P] [deps:T001] **Feature A**
- [ ] [T003] [P] [deps:T001] **Feature B**
"""
        (feature_dir / "tasks.md").write_text(tasks_content)
        
        # Create feature branch
        run_command(["git", "checkout", "-b", "004-sessions"], cwd=repo_path)
        
        # Run skf dag with custom session count
        returncode, stdout, stderr = run_command(
            ["python", "-m", "speckit_flow", "dag", "--sessions", "5"],
            cwd=repo_path
        )
        
        print(f"Exit code: {returncode}")
        print(f"Stdout:\n{stdout}")
        
        # Verify exit code
        assert returncode == 0, f"Expected exit code 0, got {returncode}"
        
        # Verify dag.yaml has correct session count
        dag_path = feature_dir / "dag.yaml"
        dag_data = yaml.safe_load(dag_path.read_text())
        assert dag_data["num_sessions"] == 5, \
            f"Expected 5 sessions, got {dag_data['num_sessions']}"
        
        # Verify summary shows 5 sessions
        assert "Sessions: 5" in stdout
        
        print("✓ Test 4 passed: Custom session count works")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("T022 Validation: skf dag command")
    print("=" * 60)
    
    try:
        test_dag_command_success()
        test_dag_command_no_tasks_file()
        test_dag_command_cyclic_dependency()
        test_dag_command_custom_sessions()
        
        print("\n" + "=" * 60)
        print("✓ All T022 acceptance criteria validated successfully!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
