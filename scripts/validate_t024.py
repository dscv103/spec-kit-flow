#!/usr/bin/env python3
"""
Validation script for T024: Add skf dag --sessions N option

Acceptance Criteria:
1. `skf dag --sessions 5` assigns to 5 sessions
2. Session shown for each task in output
3. dag.yaml includes num_sessions field
"""

import subprocess
import sys
import tempfile
import yaml
from pathlib import Path

# Test colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result with color."""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {name}")
    if details:
        print(f"  {details}")


def run_command(cmd: list[str], cwd: Path = None) -> tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_sessions_option():
    """Test AC1: `skf dag --sessions 5` assigns to 5 sessions"""
    print(f"\n{BOLD}Test 1: --sessions option assigns tasks to N sessions{RESET}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Initialize git repo
        run_command(["git", "init"], cwd=repo_path)
        run_command(["git", "config", "user.email", "test@test.com"], cwd=repo_path)
        run_command(["git", "config", "user.name", "Test User"], cwd=repo_path)
        
        # Create test branch
        run_command(["git", "checkout", "-b", "001-test-feature"], cwd=repo_path)
        
        # Create specs directory and tasks.md
        specs_dir = repo_path / "specs" / "001-test-feature"
        specs_dir.mkdir(parents=True)
        
        # Create tasks.md with multiple parallelizable tasks
        tasks_content = """# Test Tasks

- [ ] [T001] [deps:] Setup project
- [ ] [T002] [P] [deps:T001] Feature A
- [ ] [T003] [P] [deps:T001] Feature B
- [ ] [T004] [P] [deps:T001] Feature C
- [ ] [T005] [P] [deps:T001] Feature D
- [ ] [T006] [P] [deps:T001] Feature E
- [ ] [T007] [deps:T002,T003,T004,T005,T006] Integration
"""
        (specs_dir / "tasks.md").write_text(tasks_content)
        
        # Commit so we have a proper git repo
        run_command(["git", "add", "."], cwd=repo_path)
        run_command(["git", "commit", "-m", "Initial"], cwd=repo_path)
        
        # Run skf dag --sessions 5
        exit_code, stdout, stderr = run_command(
            ["skf", "dag", "--sessions", "5"],
            cwd=repo_path
        )
        
        passed_command = exit_code == 0
        print_test(
            "Command executes successfully",
            passed_command,
            f"Exit code: {exit_code}"
        )
        
        if not passed_command:
            print(f"  STDOUT: {stdout}")
            print(f"  STDERR: {stderr}")
            return False
        
        # Check that dag.yaml was created
        dag_path = specs_dir / "dag.yaml"
        passed_file = dag_path.exists()
        print_test("dag.yaml file created", passed_file)
        
        if not passed_file:
            return False
        
        # Load and check dag.yaml
        with open(dag_path) as f:
            dag_data = yaml.safe_load(f)
        
        # Check num_sessions field
        passed_num_sessions = dag_data.get("num_sessions") == 5
        print_test(
            "dag.yaml includes num_sessions: 5",
            passed_num_sessions,
            f"Found: {dag_data.get('num_sessions')}"
        )
        
        # Check that parallel tasks are distributed across 5 sessions
        sessions_used = set()
        for phase in dag_data.get("phases", []):
            for task in phase.get("tasks", []):
                if task.get("session") is not None:
                    sessions_used.add(task["session"])
        
        # We should see sessions 0-4 used for the 5 parallel tasks
        passed_distribution = sessions_used >= {0, 1, 2, 3, 4}
        print_test(
            "Tasks distributed across 5 sessions",
            passed_distribution,
            f"Sessions used: {sorted(sessions_used)}"
        )
        
        return passed_command and passed_file and passed_num_sessions and passed_distribution


def test_visualization_shows_sessions():
    """Test AC2: Session shown for each task in output"""
    print(f"\n{BOLD}Test 2: Visualization shows session assignments{RESET}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Initialize git repo
        run_command(["git", "init"], cwd=repo_path)
        run_command(["git", "config", "user.email", "test@test.com"], cwd=repo_path)
        run_command(["git", "config", "user.name", "Test User"], cwd=repo_path)
        run_command(["git", "checkout", "-b", "001-test"], cwd=repo_path)
        
        # Create specs directory and tasks.md
        specs_dir = repo_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        
        tasks_content = """# Test Tasks
- [ ] [T001] [deps:] Setup
- [ ] [T002] [P] [deps:T001] Task A
- [ ] [T003] [P] [deps:T001] Task B
"""
        (specs_dir / "tasks.md").write_text(tasks_content)
        
        run_command(["git", "add", "."], cwd=repo_path)
        run_command(["git", "commit", "-m", "Initial"], cwd=repo_path)
        
        # Run with --visualize and --sessions
        exit_code, stdout, stderr = run_command(
            ["skf", "dag", "--sessions", "2", "--visualize"],
            cwd=repo_path
        )
        
        passed_command = exit_code == 0
        print_test("Command with --visualize succeeds", passed_command)
        
        if not passed_command:
            print(f"  STDOUT: {stdout}")
            print(f"  STDERR: {stderr}")
            return False
        
        # Check that output contains session information
        passed_session_0 = "[Session 0]" in stdout
        passed_session_1 = "[Session 1]" in stdout
        
        print_test(
            "Output contains [Session 0]",
            passed_session_0,
            "Found in visualization output" if passed_session_0 else "Not found"
        )
        
        print_test(
            "Output contains [Session 1]",
            passed_session_1,
            "Found in visualization output" if passed_session_1 else "Not found"
        )
        
        # Print relevant output for debugging
        if passed_session_0 or passed_session_1:
            print(f"\n  {YELLOW}Sample output:{RESET}")
            for line in stdout.split("\n"):
                if "Session" in line or "Phase" in line or line.strip().startswith("T"):
                    print(f"    {line}")
        
        return passed_command and passed_session_0 and passed_session_1


def test_default_behavior_unchanged():
    """Test that default behavior (no --sessions) still works"""
    print(f"\n{BOLD}Test 3: Default behavior unchanged{RESET}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Initialize git repo
        run_command(["git", "init"], cwd=repo_path)
        run_command(["git", "config", "user.email", "test@test.com"], cwd=repo_path)
        run_command(["git", "config", "user.name", "Test User"], cwd=repo_path)
        run_command(["git", "checkout", "-b", "001-test"], cwd=repo_path)
        
        # Create specs directory and tasks.md
        specs_dir = repo_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        
        tasks_content = """# Test Tasks
- [ ] [T001] [deps:] Setup
"""
        (specs_dir / "tasks.md").write_text(tasks_content)
        
        run_command(["git", "add", "."], cwd=repo_path)
        run_command(["git", "commit", "-m", "Initial"], cwd=repo_path)
        
        # Run without --sessions (should default to 3)
        exit_code, stdout, stderr = run_command(
            ["skf", "dag"],
            cwd=repo_path
        )
        
        passed_command = exit_code == 0
        print_test("Default command works", passed_command)
        
        if not passed_command:
            print(f"  STDOUT: {stdout}")
            print(f"  STDERR: {stderr}")
            return False
        
        # Check dag.yaml has default num_sessions
        dag_path = specs_dir / "dag.yaml"
        with open(dag_path) as f:
            dag_data = yaml.safe_load(f)
        
        passed_default = dag_data.get("num_sessions") == 3
        print_test(
            "Default num_sessions is 3",
            passed_default,
            f"Found: {dag_data.get('num_sessions')}"
        )
        
        return passed_command and passed_default


def main():
    """Run all validation tests."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}T024 Validation: Add skf dag --sessions N option{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    
    results = []
    
    # Run all tests
    results.append(("--sessions assigns to N sessions", test_sessions_option()))
    results.append(("Visualization shows sessions", test_visualization_shows_sessions()))
    results.append(("Default behavior unchanged", test_default_behavior_unchanged()))
    
    # Summary
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}Summary{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}✓{RESET}" if result else f"{RED}✗{RESET}"
        print(f"{status} {name}")
    
    print(f"\n{BOLD}Result: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}All acceptance criteria met!{RESET}")
        return 0
    else:
        print(f"{RED}Some tests failed.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
