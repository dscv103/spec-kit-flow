"""
Integration tests for specify-cli to verify T002 acceptance criteria.

These tests ensure that the existing specify CLI remains functional
after the Hatch workspace refactoring in T001.
"""
import subprocess
import sys
from pathlib import Path

import pytest


def test_specify_help_displays():
    """
    T002 AC1: `specify --help` displays help text.
    
    Verifies that the specify CLI entry point is accessible
    and displays help information correctly.
    """
    # Arrange: Get the repository root to set PYTHONPATH
    repo_root = Path(__file__).parent.parent.parent
    env = {
        **subprocess.os.environ.copy(),
        "PYTHONPATH": str(repo_root / "src" / "specify_cli")
    }
    
    # Act: Run specify --help
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "--help"],
        capture_output=True,
        text=True,
        env=env,
        cwd=repo_root,
    )
    
    # Assert: Command succeeds and displays expected content
    assert result.returncode == 0, f"specify --help failed with: {result.stderr}"
    assert "specify" in result.stdout.lower(), "Help text should mention 'specify'"
    assert "help" in result.stdout.lower(), "Help text should contain 'help'"
    
    # Verify key commands are listed
    assert "init" in result.stdout.lower(), "Help should list 'init' command"
    assert "check" in result.stdout.lower(), "Help should list 'check' command"


def test_specify_check_runs_without_import_errors():
    """
    T002 AC2: `specify check` runs without import errors.
    
    Verifies that the check command executes successfully and
    all imports resolve correctly.
    """
    # Arrange: Get the repository root to set PYTHONPATH
    repo_root = Path(__file__).parent.parent.parent
    env = {
        **subprocess.os.environ.copy(),
        "PYTHONPATH": str(repo_root / "src" / "specify_cli")
    }
    
    # Act: Run specify check
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "check"],
        capture_output=True,
        text=True,
        env=env,
        cwd=repo_root,
    )
    
    # Assert: No import errors in output
    assert "ImportError" not in result.stderr, f"Import error detected: {result.stderr}"
    assert "ModuleNotFoundError" not in result.stderr, f"Module not found: {result.stderr}"
    
    # The command may fail for missing tools (expected), but should not have import errors
    # We're just verifying the imports work, not that all tools are installed


def test_specify_import_works():
    """
    T002 AC3: Existing functionality unchanged - verify imports work.
    
    Tests that specify_cli can be imported directly in Python,
    which is how the entry point will use it.
    """
    # This test runs in the same Python process, so we need to ensure
    # the path is correct
    repo_root = Path(__file__).parent.parent.parent
    src_dir = repo_root / "src" / "specify_cli"
    
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    try:
        # Act: Import the module
        import specify_cli
        
        # Assert: Key components are accessible
        assert hasattr(specify_cli, "app"), "specify_cli should have 'app' (Typer app)"
        assert hasattr(specify_cli, "main"), "specify_cli should have 'main' function"
        assert callable(specify_cli.main), "main should be callable"
        
        # Verify the app is a Typer instance
        import typer
        assert isinstance(specify_cli.app, typer.Typer), "app should be a Typer instance"
        
    except ImportError as e:
        pytest.fail(f"Failed to import specify_cli: {e}")
    finally:
        # Cleanup: Remove from sys.path to avoid side effects
        if str(src_dir) in sys.path:
            sys.path.remove(str(src_dir))


def test_specify_version_command():
    """
    Additional verification: Test that version command works.
    
    This tests an additional command to ensure the CLI structure
    is intact and functional.
    """
    # Arrange
    repo_root = Path(__file__).parent.parent.parent
    env = {
        **subprocess.os.environ.copy(),
        "PYTHONPATH": str(repo_root / "src" / "specify_cli")
    }
    
    # Act: Run specify version
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "version"],
        capture_output=True,
        text=True,
        env=env,
        cwd=repo_root,
    )
    
    # Assert: Command succeeds
    assert result.returncode == 0, f"specify version failed with: {result.stderr}"
    # Version output should contain version information
    assert result.stdout.strip() != "", "Version command should produce output"
