"""
Git worktree management for SpecKitFlow.

This subpackage contains:
- manager: Git worktree CRUD operations
- merger: Branch integration and conflict resolution
"""

from speckit_flow.worktree.manager import WorktreeManager, WorktreeInfo
from speckit_flow.worktree.merger import MergeOrchestrator, MergeAnalysis, SessionChanges

__all__ = [
    "WorktreeManager",
    "WorktreeInfo",
    "MergeOrchestrator",
    "MergeAnalysis",
    "SessionChanges",
]
