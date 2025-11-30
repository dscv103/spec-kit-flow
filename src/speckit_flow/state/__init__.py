"""
State management for SpecKitFlow.

This subpackage contains:
- models: Pydantic models for orchestration state
- manager: YAML state persistence with atomic writes and file locking
- recovery: Checkpoint/restore functionality for crash recovery
"""

from speckit_flow.state.manager import StateManager
from speckit_flow.state.models import OrchestrationState, TaskStateInfo
from speckit_flow.state.recovery import RecoveryManager

__all__ = [
    "OrchestrationState",
    "TaskStateInfo",
    "StateManager",
    "RecoveryManager",
]
