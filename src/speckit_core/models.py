"""
Pydantic data models for SpecKit.

This module defines all shared data models used across SpecKit tools,
including tasks, feature contexts, DAG nodes, and session states.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

__all__ = [
    "TaskInfo",
    "FeatureContext",
    "DAGNode",
    "SessionState",
    "TaskStatus",
    "SessionStatus",
]


# Enums for status fields
class TaskStatus(str, Enum):
    """Task execution status."""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class SessionStatus(str, Enum):
    """Session execution status."""
    idle = "idle"
    executing = "executing"
    waiting = "waiting"
    completed = "completed"
    failed = "failed"


class TaskInfo(BaseModel):
    """Task information parsed from tasks.md.
    
    Represents a single task with its metadata including dependencies,
    session assignment, and execution status.
    
    Attributes:
        id: Task identifier (e.g., "T001")
        name: Human-readable task name/description
        description: Optional detailed description
        dependencies: List of task IDs this task depends on
        session: Session ID assigned for execution (0-based, None if unassigned)
        parallelizable: Whether task can run in parallel with others
        story: Optional user story identifier (e.g., "US1")
        files: List of files this task modifies
        status: Current execution status
        completed: Whether checkbox is marked complete in tasks.md
        
    Example:
        >>> task = TaskInfo(
        ...     id="T001",
        ...     name="Setup database",
        ...     dependencies=[],
        ...     parallelizable=False
        ... )
        >>> assert task.session is None  # Not yet assigned
    """
    id: str = Field(..., pattern=r"^T\d{3}$", description="Task ID like T001")
    name: str = Field(..., min_length=1, description="Task name/description")
    description: Optional[str] = Field(default=None, description="Detailed task description")
    dependencies: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    session: Optional[int] = Field(default=None, ge=0, description="Assigned session ID")
    parallelizable: bool = Field(default=False, description="Can run in parallel")
    story: Optional[str] = Field(default=None, description="User story ID like US1")
    files: list[str] = Field(default_factory=list, description="Files modified by task")
    status: TaskStatus = Field(default=TaskStatus.pending, description="Execution status")
    completed: bool = Field(default=False, description="Whether marked complete in tasks.md")
    
    model_config = {"frozen": False}  # Allow mutations for session assignment


class FeatureContext(BaseModel):
    """Feature directory context with all standard file paths.
    
    This model holds the paths to all standard SpecKit files for a feature,
    making it easy to access spec.md, plan.md, tasks.md, and other artifacts.
    
    Attributes:
        repo_root: Root directory of the git repository
        branch: Current branch name
        feature_dir: Directory containing the feature spec
        spec_path: Path to spec.md
        plan_path: Path to plan.md
        tasks_path: Path to tasks.md
        research_path: Path to research.md (may not exist)
        data_model_path: Path to data-model.md (may not exist)
        quickstart_path: Path to quickstart.md (may not exist)
        contracts_dir: Path to contracts/ directory (may not exist)
    """
    repo_root: Path
    branch: str
    feature_dir: Path
    spec_path: Path
    plan_path: Path
    tasks_path: Path
    research_path: Optional[Path] = None
    data_model_path: Optional[Path] = None
    quickstart_path: Optional[Path] = None
    contracts_dir: Optional[Path] = None
    
    model_config = {"frozen": True}


class DAGNode(BaseModel):
    """DAG node for graph serialization to dag.yaml.
    
    Represents a task node in the DAG with all metadata needed for
    orchestration and visualization.
    
    Attributes:
        id: Task identifier
        name: Task name
        description: Task description
        files: List of files this task modifies
        dependencies: Task IDs this task depends on
        session: Assigned session ID
        parallelizable: Whether can run in parallel
        story: Optional user story identifier
        
    Example:
        >>> node = DAGNode(
        ...     id="T001",
        ...     name="Setup",
        ...     description="Initialize project",
        ...     files=["package.json"],
        ...     dependencies=[],
        ...     session=0,
        ...     parallelizable=False,
        ...     story=None
        ... )
    """
    id: str = Field(..., pattern=r"^T\d{3}$")
    name: str
    description: str
    files: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    session: int = Field(..., ge=0)
    parallelizable: bool
    story: Optional[str] = None
    
    model_config = {"frozen": True}


class SessionState(BaseModel):
    """Orchestration session state for flow-state.yaml.
    
    Tracks the state of a single session including its worktree,
    current task, and execution status.
    
    Attributes:
        session_id: Session identifier (0-based)
        worktree_path: Path to session's git worktree
        branch_name: Git branch name for this session
        current_task: Currently executing task ID (None if idle)
        completed_tasks: List of task IDs completed in this session
        status: Current session status
        
    Example:
        >>> session = SessionState(
        ...     session_id=0,
        ...     worktree_path=".worktrees-001/session-0",
        ...     branch_name="impl-001-session-0",
        ...     current_task="T002",
        ...     completed_tasks=["T001"],
        ...     status=SessionStatus.executing
        ... )
    """
    session_id: int = Field(..., ge=0)
    worktree_path: str = Field(..., description="Path to worktree directory")
    branch_name: str = Field(..., description="Git branch for this session")
    current_task: Optional[str] = Field(default=None, description="Current task ID")
    completed_tasks: list[str] = Field(default_factory=list, description="Completed task IDs")
    status: SessionStatus = Field(default=SessionStatus.idle)
    
    model_config = {"frozen": False}  # Allow status updates
