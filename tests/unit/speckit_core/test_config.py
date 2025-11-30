"""
Unit tests for speckit_core.config module.

Tests configuration loading, saving, validation, and error handling.
"""

import pytest
import yaml
from pathlib import Path

from speckit_core.config import SpecKitFlowConfig, load_config, save_config
from speckit_core.exceptions import ConfigurationError


class TestSpecKitFlowConfig:
    """Unit tests for SpecKitFlowConfig model."""
    
    def test_default_values(self):
        """Config has sensible defaults."""
        config = SpecKitFlowConfig()
        
        assert config.agent_type == "copilot"
        assert config.num_sessions == 3
    
    def test_custom_values(self):
        """Config accepts custom values."""
        config = SpecKitFlowConfig(agent_type="goose", num_sessions=5)
        
        assert config.agent_type == "goose"
        assert config.num_sessions == 5
    
    def test_num_sessions_minimum(self):
        """num_sessions must be at least 1."""
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            SpecKitFlowConfig(num_sessions=0)
        
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            SpecKitFlowConfig(num_sessions=-1)
    
    def test_num_sessions_maximum(self):
        """num_sessions must be at most 10."""
        with pytest.raises(ValueError, match="less than or equal to 10"):
            SpecKitFlowConfig(num_sessions=11)
        
        with pytest.raises(ValueError, match="less than or equal to 10"):
            SpecKitFlowConfig(num_sessions=100)
    
    def test_num_sessions_valid_range(self):
        """num_sessions accepts values 1-10."""
        for n in range(1, 11):
            config = SpecKitFlowConfig(num_sessions=n)
            assert config.num_sessions == n
    
    def test_agent_type_cannot_be_empty(self):
        """agent_type must not be empty."""
        with pytest.raises(ValueError, match="agent_type cannot be empty"):
            SpecKitFlowConfig(agent_type="")
        
        with pytest.raises(ValueError, match="agent_type cannot be empty"):
            SpecKitFlowConfig(agent_type="   ")
    
    def test_agent_type_trimmed(self):
        """agent_type is trimmed of whitespace."""
        config = SpecKitFlowConfig(agent_type="  copilot  ")
        assert config.agent_type == "copilot"
    
    def test_model_dump(self):
        """Config serializes to dict correctly."""
        config = SpecKitFlowConfig(agent_type="copilot", num_sessions=4)
        data = config.model_dump()
        
        assert data == {
            "agent_type": "copilot",
            "num_sessions": 4,
        }
    
    def test_model_validate(self):
        """Config validates from dict correctly."""
        data = {
            "agent_type": "goose",
            "num_sessions": 2,
        }
        config = SpecKitFlowConfig.model_validate(data)
        
        assert config.agent_type == "goose"
        assert config.num_sessions == 2


class TestLoadConfig:
    """Unit tests for load_config function."""
    
    def test_loads_valid_config(self, tmp_path):
        """Loads valid YAML config file."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text("agent_type: goose\nnum_sessions: 5\n")
        
        # Act
        config = load_config(tmp_path)
        
        # Assert
        assert config.agent_type == "goose"
        assert config.num_sessions == 5
    
    def test_applies_defaults_for_missing_fields(self, tmp_path):
        """Applies defaults when fields are missing."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text("agent_type: opencode\n")  # num_sessions missing
        
        # Act
        config = load_config(tmp_path)
        
        # Assert
        assert config.agent_type == "opencode"
        assert config.num_sessions == 3  # default
    
    def test_handles_empty_file(self, tmp_path):
        """Empty file uses all defaults."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text("")
        
        # Act
        config = load_config(tmp_path)
        
        # Assert
        assert config.agent_type == "copilot"
        assert config.num_sessions == 3
    
    def test_raises_file_not_found_error(self, tmp_path):
        """Raises FileNotFoundError if config doesn't exist."""
        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config(tmp_path)
        
        assert "Configuration file not found" in str(exc_info.value)
        assert "skf init" in str(exc_info.value)
    
    def test_raises_configuration_error_for_invalid_yaml(self, tmp_path):
        """Raises ConfigurationError for malformed YAML."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text("agent_type: [invalid\n")  # Invalid YAML
        
        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            load_config(tmp_path)
        
        assert "Failed to parse YAML" in str(exc_info.value)
    
    def test_raises_configuration_error_for_wrong_type(self, tmp_path):
        """Raises ConfigurationError if root is not a dict."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text("- item1\n- item2\n")  # List, not dict
        
        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            load_config(tmp_path)
        
        assert "Invalid configuration format" in str(exc_info.value)
        assert "Expected YAML mapping" in str(exc_info.value)
    
    def test_raises_configuration_error_for_invalid_values(self, tmp_path):
        """Raises ConfigurationError for invalid field values."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text("agent_type: copilot\nnum_sessions: 100\n")  # Too many
        
        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            load_config(tmp_path)
        
        assert "Invalid configuration" in str(exc_info.value)
    
    def test_handles_unicode_content(self, tmp_path):
        """Handles Unicode characters in config."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text("agent_type: 'copilot™'\nnum_sessions: 2\n")
        
        # Act
        config = load_config(tmp_path)
        
        # Assert
        assert config.agent_type == "copilot™"
        assert config.num_sessions == 2


class TestSaveConfig:
    """Unit tests for save_config function."""
    
    def test_saves_config_to_file(self, tmp_path):
        """Saves config to correct location with valid YAML."""
        # Arrange
        config = SpecKitFlowConfig(agent_type="goose", num_sessions=4)
        
        # Act
        save_config(config, tmp_path)
        
        # Assert
        config_file = tmp_path / ".speckit" / "speckit-flow.yaml"
        assert config_file.exists()
        
        # Verify content
        content = config_file.read_text()
        data = yaml.safe_load(content)
        assert data == {
            "agent_type": "goose",
            "num_sessions": 4,
        }
    
    def test_creates_speckit_directory(self, tmp_path):
        """Creates .speckit directory if it doesn't exist."""
        # Arrange
        config = SpecKitFlowConfig()
        speckit_dir = tmp_path / ".speckit"
        assert not speckit_dir.exists()
        
        # Act
        save_config(config, tmp_path)
        
        # Assert
        assert speckit_dir.exists()
        assert speckit_dir.is_dir()
    
    def test_overwrites_existing_config(self, tmp_path):
        """Overwrites existing config file."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text("old_content: true\n")
        
        config = SpecKitFlowConfig(agent_type="copilot", num_sessions=2)
        
        # Act
        save_config(config, tmp_path)
        
        # Assert
        content = config_file.read_text()
        data = yaml.safe_load(content)
        assert "old_content" not in data
        assert data["agent_type"] == "copilot"
        assert data["num_sessions"] == 2
    
    def test_yaml_formatting(self, tmp_path):
        """YAML is properly formatted."""
        # Arrange
        config = SpecKitFlowConfig(agent_type="opencode", num_sessions=1)
        
        # Act
        save_config(config, tmp_path)
        
        # Assert
        config_file = tmp_path / ".speckit" / "speckit-flow.yaml"
        content = config_file.read_text()
        
        # Check it's valid YAML
        data = yaml.safe_load(content)
        assert data is not None
        
        # Check it's not flow style (compact)
        assert "{" not in content  # Flow style would use braces
        assert content.count("\n") > 1  # Multiple lines
    
    def test_handles_unicode(self, tmp_path):
        """Handles Unicode characters correctly."""
        # Arrange
        config = SpecKitFlowConfig(agent_type="copilot™", num_sessions=3)
        
        # Act
        save_config(config, tmp_path)
        
        # Assert
        config_file = tmp_path / ".speckit" / "speckit-flow.yaml"
        content = config_file.read_text(encoding="utf-8")
        assert "copilot™" in content


class TestConfigRoundTrip:
    """Integration tests for save/load round-trip."""
    
    def test_round_trip_preserves_data(self, tmp_path):
        """Save and load preserves all config data."""
        # Arrange
        original = SpecKitFlowConfig(agent_type="goose", num_sessions=7)
        
        # Act
        save_config(original, tmp_path)
        loaded = load_config(tmp_path)
        
        # Assert
        assert loaded.agent_type == original.agent_type
        assert loaded.num_sessions == original.num_sessions
    
    def test_round_trip_with_defaults(self, tmp_path):
        """Round trip works with default values."""
        # Arrange
        original = SpecKitFlowConfig()
        
        # Act
        save_config(original, tmp_path)
        loaded = load_config(tmp_path)
        
        # Assert
        assert loaded.agent_type == "copilot"
        assert loaded.num_sessions == 3
    
    def test_multiple_save_load_cycles(self, tmp_path):
        """Multiple save/load cycles work correctly."""
        configs = [
            SpecKitFlowConfig(agent_type="copilot", num_sessions=2),
            SpecKitFlowConfig(agent_type="goose", num_sessions=5),
            SpecKitFlowConfig(agent_type="opencode", num_sessions=8),
        ]
        
        for config in configs:
            save_config(config, tmp_path)
            loaded = load_config(tmp_path)
            assert loaded.agent_type == config.agent_type
            assert loaded.num_sessions == config.num_sessions


class TestEdgeCases:
    """Edge case tests for config module."""
    
    def test_config_with_boundary_values(self, tmp_path):
        """Config with min and max values works."""
        # Minimum
        config_min = SpecKitFlowConfig(agent_type="a", num_sessions=1)
        save_config(config_min, tmp_path)
        loaded_min = load_config(tmp_path)
        assert loaded_min.agent_type == "a"
        assert loaded_min.num_sessions == 1
        
        # Maximum
        config_max = SpecKitFlowConfig(agent_type="z" * 100, num_sessions=10)
        save_config(config_max, tmp_path)
        loaded_max = load_config(tmp_path)
        assert loaded_max.agent_type == "z" * 100
        assert loaded_max.num_sessions == 10
    
    def test_config_file_with_extra_fields(self, tmp_path):
        """Extra fields in config file are ignored."""
        # Arrange
        speckit_dir = tmp_path / ".speckit"
        speckit_dir.mkdir()
        config_file = speckit_dir / "speckit-flow.yaml"
        config_file.write_text(
            "agent_type: copilot\n"
            "num_sessions: 3\n"
            "extra_field: should_be_ignored\n"
        )
        
        # Act
        config = load_config(tmp_path)
        
        # Assert
        assert config.agent_type == "copilot"
        assert config.num_sessions == 3
        assert not hasattr(config, "extra_field")
