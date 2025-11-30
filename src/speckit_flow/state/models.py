"""
State management models for SpecKitFlow orchestration.

This module defines the Pydantic models for orchestration state persistence,
including the main OrchestrationState model and supporting models for tasks
and sessions.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from speckit_core.models import SessionState, SessionStatus, TaskStatus

__all__ = [
    "TaskStateInfo",
    "OrchestrationState",
    "MergeStatus",
]


class MergeStatus(str):
    """Merge status values for orchestration state."""
    # Using string literals to match YAML schema
    # Values: null, "in_progress", "completed", "failed"
    pass


class TaskStateInfo(BaseModel):
    """Task state information for the tasks dictionary in flow-state.yaml.
    
    Tracks execution metadata for a single task including status,
    assigned session, and timestamps.
    
    Attributes:
        status: Current task status
        session: Session ID executing this task (None if unassigned)
        started_at: ISO 8601 timestamp when task started
        completed_at: ISO 8601 timestamp when task completed
        
    Example:
        >>> info = TaskStateInfo(
        ...     status=TaskStatus.completed,
        ...     session=0,
        ...     completed_at="2025-11-28T10:45:00Z"
        ... )
    """
    status: TaskStatus
    session: Optional[int] = Field(default=None, ge=0)
    started_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp")
    completed_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp")
    
    model_config = {"frozen": False}  # Allow status updates


class OrchestrationState(BaseModel):
    """Complete orchestration state for flow-state.yaml.
    
    This model represents the entire state of a SpecKitFlow orchestration,
    including all sessions, tasks, and execution metadata. It matches the
    flow-state.yaml schema defined in plan.md.
    
    Attributes:
        version: State schema version (e.g., "1.0")
        spec_id: Specification identifier (e.g., "001-feature-name")
        agent_type: AI agent type (e.g., "copilot")
        num_sessions: Number of parallel sessions
        base_branch: Base git branch for integration
        started_at: ISO 8601 timestamp when orchestration started
        updated_at: ISO 8601 timestamp of last state update
        current_phase: Currently executing phase name
        phases_completed: List of completed phase names
        sessions: List of session states
        tasks: Dictionary mapping task ID to task state info
        merge_status: Current merge status (null, in_progress, completed, failed)
        
    Example:
        >>> state = OrchestrationState(
        ...     version="1.0",
        ...     spec_id="001-test",
        ...     agent_type="copilot",
        ...     num_sessions=2,
        ...     base_branch="main",
        ...     started_at="2025-11-28T10:30:00Z",
        ...     updated_at="2025-11-28T10:30:00Z",
        ...     current_phase="phase-0",
        ...     phases_completed=[],
        ...     sessions=[],
        ...     tasks={}
        ... )
    """
    version: str = Field(default="1.0", description="State schema version")
    spec_id: str = Field(..., description="Specification identifier")
    agent_type: str = Field(..., description="AI agent type")
    num_sessions: int = Field(..., ge=1, description="Number of parallel sessions")
    base_branch: str = Field(..., description="Base git branch")
    started_at: str = Field(..., description="ISO 8601 timestamp")
    updated_at: str = Field(..., description="ISO 8601 timestamp")
    current_phase: str = Field(..., description="Current phase name")
    phases_completed: list[str] = Field(default_factory=list, description="Completed phases")
    sessions: list[SessionState] = Field(default_factory=list, description="Session states")
    tasks: dict[str, TaskStateInfo] = Field(default_factory=dict, description="Task states")
    merge_status: Optional[str] = Field(default=None, description="Merge status")
    
    model_config = {"frozen": False}  # Allow updates during orchestration
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format for state updates."""
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def mark_updated(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = self.get_current_timestamp()
