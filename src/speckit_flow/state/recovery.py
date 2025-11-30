"""
Checkpoint and recovery functionality for orchestration state.

This module provides checkpoint creation, listing, restoration, and cleanup
for orchestration state snapshots.
"""

from datetime import datetime
from pathlib import Path

import yaml

from speckit_flow.state.models import OrchestrationState

__all__ = [
    "RecoveryManager",
]


class RecoveryManager:
    """Manages state checkpoints for recovery after failures.
    
    Creates timestamped snapshots of orchestration state in
    .speckit/checkpoints/ directory for recovery purposes.
    
    Attributes:
        repo_root: Path to repository root
        checkpoints_dir: Path to checkpoints directory
        
    Example:
        >>> manager = RecoveryManager(Path("/repo"))
        >>> checkpoint_path = manager.checkpoint(state)
        >>> restored = manager.restore_from_checkpoint(checkpoint_path)
    """
    
    def __init__(self, repo_root: Path):
        """Initialize recovery manager.
        
        Args:
            repo_root: Path to repository root directory
        """
        self.repo_root = Path(repo_root)
        self.speckit_dir = self.repo_root / ".speckit"
        self.checkpoints_dir = self.speckit_dir / "checkpoints"
    
    def checkpoint(self, state: OrchestrationState) -> Path:
        """Create a checkpoint snapshot of current state.
        
        Saves state to a timestamped file in .speckit/checkpoints/
        using ISO 8601 format: YYYY-MM-DDTHH-MM-SSZ.yaml
        
        Args:
            state: OrchestrationState to checkpoint
            
        Returns:
            Path to created checkpoint file
            
        Raises:
            OSError: If unable to write checkpoint
        """
        # Ensure checkpoints directory exists
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp filename
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        checkpoint_path = self.checkpoints_dir / f"{timestamp}.yaml"
        
        # Serialize state
        content = yaml.dump(
            state.model_dump(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        
        # Write checkpoint
        checkpoint_path.write_text(content, encoding="utf-8")
        
        return checkpoint_path
    
    def list_checkpoints(self) -> list[Path]:
        """List all checkpoint files sorted by timestamp (newest first).
        
        Returns:
            List of checkpoint file paths sorted by modification time
        """
        if not self.checkpoints_dir.exists():
            return []
        
        # Get all .yaml files
        checkpoints = list(self.checkpoints_dir.glob("*.yaml"))
        
        # Sort by modification time (newest first)
        checkpoints.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return checkpoints
    
    def get_latest_checkpoint(self) -> Path | None:
        """Get the most recent checkpoint file.
        
        Returns:
            Path to latest checkpoint, or None if no checkpoints exist
        """
        checkpoints = self.list_checkpoints()
        return checkpoints[0] if checkpoints else None
    
    def restore_from_checkpoint(self, path: Path) -> OrchestrationState:
        """Restore orchestration state from a checkpoint file.
        
        Args:
            path: Path to checkpoint file
            
        Returns:
            Restored OrchestrationState
            
        Raises:
            FileNotFoundError: If checkpoint file doesn't exist
            yaml.YAMLError: If checkpoint file is invalid YAML
            pydantic.ValidationError: If checkpoint doesn't match schema
        """
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        return OrchestrationState.model_validate(data)
    
    def cleanup_old_checkpoints(self, keep: int = 10) -> int:
        """Remove old checkpoint files, keeping only the N most recent.
        
        Args:
            keep: Number of recent checkpoints to preserve (default: 10)
            
        Returns:
            Number of checkpoints deleted
        """
        if not self.checkpoints_dir.exists():
            return 0
        
        checkpoints = self.list_checkpoints()
        
        # Delete all except the N most recent
        to_delete = checkpoints[keep:]
        for checkpoint in to_delete:
            checkpoint.unlink()
        
        return len(to_delete)
