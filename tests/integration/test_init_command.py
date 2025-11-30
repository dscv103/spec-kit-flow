"""
Integration tests for 'skf init' command.

Tests the initialization workflow including:
- Configuration file creation
- Repository validation
- Specs directory validation
- Default values
- Option overrides
"""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from speckit_flow import app

runner = CliRunner()


class TestInitCommand:
    """Integration tests for skf init command."""
    
    def test_init_creates_config_with_defaults(self, temp_repo):
        """skf init creates config file with default values."""
        # Arrange: Create specs directory
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act: Run init command
        result = runner.invoke(app, ["init"], cwd=str(temp_repo))
        
        # Assert: Command succeeds
        assert result.exit_code == 0
        assert "✓" in result.stdout
        assert "initialized successfully" in result.stdout
        
        # Assert: Config file created
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        assert config_path.exists()
        
        # Assert: Config has default values
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["agent_type"] == "copilot"
        assert config_data["num_sessions"] == 3
    
    def test_init_with_custom_sessions(self, temp_repo):
        """skf init --sessions N creates config with specified session count."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(app, ["init", "--sessions", "5"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["num_sessions"] == 5
        assert "Sessions: 5" in result.stdout
    
    def test_init_with_custom_agent(self, temp_repo):
        """skf init --agent TYPE creates config with specified agent."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(app, ["init", "--agent", "goose"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["agent_type"] == "goose"
        assert "Agent:    goose" in result.stdout
    
    def test_init_with_all_options(self, temp_repo):
        """skf init with both --sessions and --agent."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(
            app,
            ["init", "--sessions", "7", "--agent", "opencode"],
            cwd=str(temp_repo)
        )
        
        # Assert
        assert result.exit_code == 0
        
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["num_sessions"] == 7
        assert config_data["agent_type"] == "opencode"
    
    def test_init_errors_if_not_in_git_repo(self, temp_dir):
        """skf init fails with clear error when not in git repo."""
        # Arrange: temp_dir is NOT a git repo (use temp_dir, not temp_repo)
        specs_dir = temp_dir / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(app, ["init"], cwd=str(temp_dir))
        
        # Assert
        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "Not in a git repository" in result.stdout
        assert "git init" in result.stdout
    
    def test_init_errors_if_no_specs_directory(self, temp_repo):
        """skf init fails when specs/ directory doesn't exist."""
        # Arrange: temp_repo exists but has NO specs/ directory
        
        # Act
        result = runner.invoke(app, ["init"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "specs/ directory not found" in result.stdout
    
    def test_init_prompts_on_existing_config(self, temp_repo):
        """skf init prompts for confirmation when config already exists."""
        # Arrange: Create specs and existing config
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        config_dir = temp_repo / ".speckit"
        config_dir.mkdir()
        config_path = config_dir / "speckit-flow.yaml"
        config_path.write_text("agent_type: copilot\nnum_sessions: 3\n")
        
        # Act: Run init with "no" response
        result = runner.invoke(app, ["init"], input="n\n", cwd=str(temp_repo))
        
        # Assert: Command exits without overwriting
        assert result.exit_code == 0
        assert "Warning:" in result.stdout
        assert "Configuration already exists" in result.stdout
        assert "Configuration unchanged" in result.stdout
        
        # Config should remain unchanged
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["num_sessions"] == 3
    
    def test_init_overwrites_with_confirmation(self, temp_repo):
        """skf init overwrites existing config when user confirms."""
        # Arrange: Create specs and existing config with different values
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        config_dir = temp_repo / ".speckit"
        config_dir.mkdir()
        config_path = config_dir / "speckit-flow.yaml"
        config_path.write_text("agent_type: copilot\nnum_sessions: 3\n")
        
        # Act: Run init with "yes" response and new sessions value
        result = runner.invoke(
            app,
            ["init", "--sessions", "5"],
            input="y\n",
            cwd=str(temp_repo)
        )
        
        # Assert: Command succeeds and overwrites
        assert result.exit_code == 0
        assert "initialized successfully" in result.stdout
        
        # Config should be updated
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["num_sessions"] == 5
    
    def test_init_creates_speckit_directory(self, temp_repo):
        """skf init creates .speckit/ directory if it doesn't exist."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        speckit_dir = temp_repo / ".speckit"
        assert not speckit_dir.exists()
        
        # Act
        result = runner.invoke(app, ["init"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        assert speckit_dir.exists()
        assert speckit_dir.is_dir()
    
    def test_init_shows_next_steps(self, temp_repo):
        """skf init displays helpful next steps."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(app, ["init"], cwd=str(temp_repo))
        
        # Assert: Next steps are shown
        assert result.exit_code == 0
        assert "Next steps" in result.stdout
        assert "skf dag" in result.stdout
        assert "skf run" in result.stdout
    
    def test_init_validates_session_bounds(self, temp_repo):
        """skf init validates num_sessions is within bounds (1-10)."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act: Try sessions < 1
        result = runner.invoke(app, ["init", "--sessions", "0"], cwd=str(temp_repo))
        
        # Assert: Should fail validation
        assert result.exit_code != 0
        
        # Act: Try sessions > 10
        result = runner.invoke(app, ["init", "--sessions", "11"], cwd=str(temp_repo))
        
        # Assert: Should fail validation
        assert result.exit_code != 0
    
    def test_init_min_session_count(self, temp_repo):
        """skf init accepts minimum session count of 1."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(app, ["init", "--sessions", "1"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["num_sessions"] == 1
    
    def test_init_max_session_count(self, temp_repo):
        """skf init accepts maximum session count of 10."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(app, ["init", "--sessions", "10"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["num_sessions"] == 10


class TestInitCommandEdgeCases:
    """Edge case tests for skf init command."""
    
    def test_init_with_empty_specs_directory(self, temp_repo):
        """skf init succeeds even if specs/ directory is empty."""
        # Arrange: Create empty specs directory
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(app, ["init"], cwd=str(temp_repo))
        
        # Assert: Should succeed (features can be added later)
        assert result.exit_code == 0
        
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        assert config_path.exists()
    
    def test_init_config_file_is_valid_yaml(self, temp_repo):
        """Generated config file is valid YAML."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(app, ["init"], cwd=str(temp_repo))
        
        # Assert
        assert result.exit_code == 0
        
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        # Should not raise exception
        config_data = yaml.safe_load(config_path.read_text())
        assert isinstance(config_data, dict)
        assert "agent_type" in config_data
        assert "num_sessions" in config_data
    
    def test_init_with_special_agent_name(self, temp_repo):
        """skf init accepts agent names with special characters."""
        # Arrange
        specs_dir = temp_repo / "specs"
        specs_dir.mkdir()
        
        # Act
        result = runner.invoke(
            app,
            ["init", "--agent", "my-custom-agent_v2"],
            cwd=str(temp_repo)
        )
        
        # Assert
        assert result.exit_code == 0
        
        config_path = temp_repo / ".speckit" / "speckit-flow.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["agent_type"] == "my-custom-agent_v2"
