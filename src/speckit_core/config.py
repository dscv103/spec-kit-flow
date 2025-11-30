"""
YAML configuration loading and validation.

This module provides functions for loading and saving SpecKitFlow
configuration files with Pydantic validation.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from .exceptions import ConfigurationError

__all__ = [
    "SpecKitFlowConfig",
    "load_config",
    "save_config",
]


class SpecKitFlowConfig(BaseModel):
    """SpecKitFlow project configuration.
    
    This model defines the configuration stored in .speckit/speckit-flow.yaml,
    which controls orchestration behavior including agent selection and
    number of parallel sessions.
    
    Attributes:
        agent_type: AI agent to use for orchestration (copilot, goose, opencode, etc.)
        num_sessions: Number of parallel sessions to run (1-10)
        
    Example:
        >>> config = SpecKitFlowConfig(agent_type="copilot", num_sessions=3)
        >>> assert config.agent_type == "copilot"
        >>> assert config.num_sessions == 3
    """
    agent_type: str = Field(
        default="copilot",
        description="AI agent to use: copilot, goose, opencode, etc."
    )
    num_sessions: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of parallel sessions (1-10)"
    )
    
    @field_validator("agent_type")
    @classmethod
    def validate_agent_type(cls, v: str) -> str:
        """Validate agent_type is non-empty."""
        if not v or not v.strip():
            raise ValueError("agent_type cannot be empty")
        return v.strip()
    
    model_config = {"frozen": False}


def load_config(repo_root: Path) -> SpecKitFlowConfig:
    """Load SpecKitFlow configuration from .speckit/speckit-flow.yaml.
    
    Loads and validates the project configuration file. If the file doesn't
    exist, raises FileNotFoundError. If the YAML is invalid or doesn't match
    the schema, raises ConfigurationError.
    
    Args:
        repo_root: Repository root directory.
        
    Returns:
        SpecKitFlowConfig object with validated configuration.
        
    Raises:
        FileNotFoundError: If config file doesn't exist.
        ConfigurationError: If config is invalid or malformed.
        
    Example:
        >>> repo = Path("/path/to/repo")
        >>> config = load_config(repo)
        >>> print(f"Using {config.agent_type} with {config.num_sessions} sessions")
    """
    config_path = repo_root / ".speckit" / "speckit-flow.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Run 'skf init' to create it."
        )
    
    try:
        content = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        
        if data is None:
            # Empty file - use defaults
            return SpecKitFlowConfig()
        
        if not isinstance(data, dict):
            raise ConfigurationError(
                f"Invalid configuration format in {config_path}\n"
                f"Expected YAML mapping, got {type(data).__name__}"
            )
        
        return SpecKitFlowConfig.model_validate(data)
        
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Failed to parse YAML in {config_path}: {e}"
        ) from e
    except ValueError as e:
        raise ConfigurationError(
            f"Invalid configuration in {config_path}: {e}"
        ) from e


def save_config(config: SpecKitFlowConfig, repo_root: Path) -> None:
    """Save SpecKitFlow configuration to .speckit/speckit-flow.yaml.
    
    Writes the configuration to the standard location with proper YAML
    formatting. Creates the .speckit directory if it doesn't exist.
    
    Args:
        config: SpecKitFlowConfig object to save.
        repo_root: Repository root directory.
        
    Raises:
        OSError: If file cannot be written (permissions, disk full, etc.)
        
    Example:
        >>> config = SpecKitFlowConfig(agent_type="copilot", num_sessions=5)
        >>> save_config(config, Path("/path/to/repo"))
    """
    speckit_dir = repo_root / ".speckit"
    config_path = speckit_dir / "speckit-flow.yaml"
    
    # Create .speckit directory if it doesn't exist
    speckit_dir.mkdir(parents=True, exist_ok=True)
    
    # Serialize to YAML with clean formatting
    data = config.model_dump()
    yaml_content = yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    
    # Write to file
    config_path.write_text(yaml_content, encoding="utf-8")
