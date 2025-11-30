"""
Orchestration components for SpecKitFlow.

This subpackage contains:
- dag_engine: DAG construction and analysis
- scheduler: Task-to-session assignment
- session_coordinator: Multi-session lifecycle management
- completion: Completion detection mechanisms
"""

from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.orchestration.completion import CompletionMonitor, watch_tasks_file
from speckit_flow.orchestration.session_coordinator import SessionCoordinator

__all__ = [
    "DAGEngine",
    "CompletionMonitor",
    "watch_tasks_file",
    "SessionCoordinator",
]
