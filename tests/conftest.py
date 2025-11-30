"""
Pytest configuration for SpecKitFlow tests.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add src directories to Python path for tests
repo_root = Path(__file__).parent.parent
src_paths = [
    repo_root / "src" / "specify_cli",
    repo_root / "src" / "speckit_core", 
    repo_root / "src" / "speckit_flow",
]

for src_path in src_paths:
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


@pytest.fixture
def temp_dir():
    """Temporary directory that's cleaned up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_repo(temp_dir):
    """Temporary git repository."""
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir, check=True, capture_output=True
    )
    # Initial commit required for worktrees
    (temp_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir, check=True, capture_output=True
    )
    yield temp_dir
