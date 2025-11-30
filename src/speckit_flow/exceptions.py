"""
Custom exceptions for SpecKitFlow.

This module defines all custom exceptions used by speckit_flow components.
"""

__all__ = [
    "SpecKitFlowError",
    "CyclicDependencyError",
    "StateNotFoundError",
    "WorktreeExistsError",
]


class SpecKitFlowError(Exception):
    """Base exception for all SpecKitFlow errors."""
    pass


class CyclicDependencyError(SpecKitFlowError):
    """Task dependency graph contains cycles.
    
    Attributes:
        cycle: List of task IDs forming the cycle
    """
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' → '.join(cycle)}")


class StateNotFoundError(SpecKitFlowError):
    """Orchestration state file not found."""
    pass


class WorktreeExistsError(SpecKitFlowError):
    """Git worktree already exists at the specified location."""
    pass
