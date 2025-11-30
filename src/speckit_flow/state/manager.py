"""
State management with atomic writes and file locking.

This module provides the StateManager class for persisting and loading
orchestration state with safeguards against corruption and concurrent access.
"""

import os
import tempfile
from pathlib import Path

import yaml
from filelock import FileLock

from speckit_flow.exceptions import StateNotFoundError
from speckit_flow.state.models import OrchestrationState

__all__ = [
    "StateManager",
]


class StateManager:
    """Manages orchestration state persistence with atomic writes and locking.
    
    This class handles loading, saving, and deleting the orchestration state
    file (.speckit/flow-state.yaml) with safeguards:
    - Atomic writes using temp file + rename to prevent corruption
    - File locking to prevent concurrent write conflicts
    - Automatic directory creation
    
    Attributes:
        repo_root: Path to repository root
        state_path: Path to flow-state.yaml
        lock_path: Path to lock file
        
    Example:
        >>> manager = StateManager(Path("/repo"))
        >>> state = OrchestrationState(...)
        >>> manager.save(state)
        >>> loaded = manager.load()
        >>> assert loaded == state
    """
    
    def __init__(self, repo_root: Path):
        """Initialize state manager.
        
        Args:
            repo_root: Path to repository root directory
        """
        self.repo_root = Path(repo_root)
        self.speckit_dir = self.repo_root / ".speckit"
        self.state_path = self.speckit_dir / "flow-state.yaml"
        self.lock_path = Path(str(self.state_path) + ".lock")
    
    def exists(self) -> bool:
        """Check if state file exists.
        
        Returns:
            True if flow-state.yaml exists, False otherwise
        """
        return self.state_path.exists()
    
    def load(self) -> OrchestrationState:
        """Load orchestration state from disk.
        
        Uses file locking to ensure safe concurrent reads.
        
        Returns:
            Loaded OrchestrationState
            
        Raises:
            StateNotFoundError: If state file does not exist
            yaml.YAMLError: If state file is invalid YAML
            pydantic.ValidationError: If state doesn't match schema
        """
        if not self.exists():
            raise StateNotFoundError(
                f"Orchestration state not found: {self.state_path}\n"
                "Start a new orchestration with: skf run"
            )
        
        lock = FileLock(str(self.lock_path), timeout=10)
        with lock:
            content = self.state_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            return OrchestrationState.model_validate(data)
    
    def save(self, state: OrchestrationState) -> None:
        """Save orchestration state to disk atomically.
        
        Uses atomic write pattern (temp file + rename) to prevent corruption
        if process crashes during write. Uses file locking to prevent
        concurrent write conflicts.
        
        Args:
            state: OrchestrationState to save
            
        Raises:
            OSError: If unable to write to disk
        """
        # Ensure .speckit directory exists
        self.speckit_dir.mkdir(parents=True, exist_ok=True)
        
        # Update timestamp before saving
        state.mark_updated()
        
        # Serialize to YAML
        content = yaml.dump(
            state.model_dump(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        
        lock = FileLock(str(self.lock_path), timeout=10)
        with lock:
            # Write to temp file in same directory (for same filesystem)
            fd, temp_path_str = tempfile.mkstemp(
                dir=self.speckit_dir,
                prefix=".flow-state-",
                suffix=".yaml.tmp",
            )
            temp_path = Path(temp_path_str)
            
            try:
                # Write content
                os.write(fd, content.encode("utf-8"))
                # Ensure data is written to disk
                os.fsync(fd)
                os.close(fd)
                
                # Atomic rename (POSIX guarantees atomicity)
                os.replace(temp_path, self.state_path)
                
            except Exception:
                # Clean up temp file on failure
                os.close(fd)
                if temp_path.exists():
                    temp_path.unlink()
                raise
    
    def delete(self) -> None:
        """Delete state file and lock file.
        
        Safe to call even if files don't exist.
        """
        lock = FileLock(str(self.lock_path), timeout=10)
        with lock:
            if self.state_path.exists():
                self.state_path.unlink()
            
        # Clean up lock file after releasing lock
        if self.lock_path.exists():
            self.lock_path.unlink()
