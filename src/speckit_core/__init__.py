"""
SpecKit Core - Shared library for SpecKit tools.

This package provides common utilities used by both specify-cli and speckit-flow:
- Path utilities for repository and feature directory handling
- Task parsing with DAG dependency markers
- Pydantic data models for tasks, features, and configuration
- YAML configuration loading and validation
"""

__version__ = "0.1.0"

# Module imports for convenience
from speckit_core import config, exceptions, models, paths, tasks

# Import commonly used models and enums
from speckit_core.models import (
    TaskInfo,
    FeatureContext,
    DAGNode,
    SessionState,
    TaskStatus,
    SessionStatus,
)
from speckit_core.config import (
    SpecKitFlowConfig,
    load_config,
    save_config,
)

__all__ = [
    "__version__",
    "config",
    "exceptions",
    "models",
    "paths",
    "tasks",
    # Models
    "TaskInfo",
    "FeatureContext",
    "DAGNode",
    "SessionState",
    "TaskStatus",
    "SessionStatus",
    # Config
    "SpecKitFlowConfig",
    "load_config",
    "save_config",
]
