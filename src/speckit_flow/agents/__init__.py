"""
Agent adapters for SpecKitFlow.

This subpackage contains:
- base: Abstract AgentAdapter interface
- copilot: GitHub Copilot IDE notification adapter

Additional adapters can be added for other AI coding assistants.
"""

from .base import AgentAdapter
from .copilot import CopilotIDEAdapter

__all__ = [
    "AgentAdapter",
    "CopilotIDEAdapter",
]
