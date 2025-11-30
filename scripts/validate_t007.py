#!/usr/bin/env python3
"""
Validation script for T007: Implement config.py

This script validates all acceptance criteria for T007.
"""

import sys
import tempfile
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.config import SpecKitFlowConfig, load_config, save_config
from speckit_core.exceptions import ConfigurationError


def check(condition: bool, message: str) -> bool:
    """Check a condition and print result."""
    symbol = "✓" if condition else "✗"
    print(f"  {symbol} {message}")
    return condition


def main():
    """Run all validation checks."""
    print("Validating T007 Acceptance Criteria\n")
    print("=" * 60)
    
    all_passed = True
    
    # AC 1: Loads valid YAML config files
    print("\n[AC 1] Loads valid YAML config files")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            speckit_dir = tmp_path / ".speckit"
            speckit_dir.mkdir()
            config_file = speckit_dir / "speckit-flow.yaml"
            
            # Test with valid config
            config_file.write_text("agent_type: goose\nnum_sessions: 5\n")
            config = load_config(tmp_path)
            
            passed = check(config.agent_type == "goose", "Loaded agent_type correctly")
            all_passed &= passed
            passed = check(config.num_sessions == 5, "Loaded num_sessions correctly")
            all_passed &= passed
    except Exception as e:
        check(False, f"Failed to load valid config: {e}")
        all_passed = False
    
    # AC 2: Raises clear error for invalid/missing config
    print("\n[AC 2] Raises clear error for invalid/missing config")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Test missing config
            try:
                load_config(tmp_path)
                check(False, "Should raise FileNotFoundError for missing config")
                all_passed = False
            except FileNotFoundError as e:
                passed = check(
                    "Configuration file not found" in str(e),
                    "FileNotFoundError has helpful message"
                )
                all_passed &= passed
                passed = check("skf init" in str(e), "Error suggests 'skf init'")
                all_passed &= passed
            
            # Test invalid YAML
            speckit_dir = tmp_path / ".speckit"
            speckit_dir.mkdir()
            config_file = speckit_dir / "speckit-flow.yaml"
            config_file.write_text("agent_type: [invalid\n")
            
            try:
                load_config(tmp_path)
                check(False, "Should raise ConfigurationError for invalid YAML")
                all_passed = False
            except ConfigurationError as e:
                passed = check(
                    "Failed to parse YAML" in str(e),
                    "ConfigurationError for invalid YAML"
                )
                all_passed &= passed
            
            # Test invalid values
            config_file.write_text("agent_type: copilot\nnum_sessions: 100\n")
            try:
                load_config(tmp_path)
                check(False, "Should raise ConfigurationError for invalid values")
                all_passed = False
            except ConfigurationError as e:
                passed = check(
                    "Invalid configuration" in str(e),
                    "ConfigurationError for invalid values"
                )
                all_passed &= passed
    except Exception as e:
        check(False, f"Unexpected error in validation: {e}")
        all_passed = False
    
    # AC 3: Saves config with proper YAML formatting
    print("\n[AC 3] Saves config with proper YAML formatting")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config = SpecKitFlowConfig(agent_type="opencode", num_sessions=4)
            
            save_config(config, tmp_path)
            
            config_file = tmp_path / ".speckit" / "speckit-flow.yaml"
            passed = check(config_file.exists(), "Config file created")
            all_passed &= passed
            
            # Verify YAML content
            content = config_file.read_text()
            data = yaml.safe_load(content)
            
            passed = check(data["agent_type"] == "opencode", "agent_type saved correctly")
            all_passed &= passed
            passed = check(data["num_sessions"] == 4, "num_sessions saved correctly")
            all_passed &= passed
            
            # Check formatting (not flow style)
            passed = check("{" not in content, "Uses block style (not flow style)")
            all_passed &= passed
            passed = check(content.count("\n") > 1, "Multi-line formatting")
            all_passed &= passed
    except Exception as e:
        check(False, f"Failed to save config: {e}")
        all_passed = False
    
    # AC 4: Default values applied when fields missing
    print("\n[AC 4] Default values applied when fields missing")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            speckit_dir = tmp_path / ".speckit"
            speckit_dir.mkdir()
            config_file = speckit_dir / "speckit-flow.yaml"
            
            # Test with only agent_type
            config_file.write_text("agent_type: custom\n")
            config = load_config(tmp_path)
            
            passed = check(config.agent_type == "custom", "Custom agent_type loaded")
            all_passed &= passed
            passed = check(config.num_sessions == 3, "Default num_sessions applied")
            all_passed &= passed
            
            # Test with empty file
            config_file.write_text("")
            config = load_config(tmp_path)
            
            passed = check(config.agent_type == "copilot", "Default agent_type applied")
            all_passed &= passed
            passed = check(config.num_sessions == 3, "Default num_sessions applied")
            all_passed &= passed
            
            # Test model defaults
            config = SpecKitFlowConfig()
            passed = check(config.agent_type == "copilot", "Model default agent_type")
            all_passed &= passed
            passed = check(config.num_sessions == 3, "Model default num_sessions")
            all_passed &= passed
    except Exception as e:
        check(False, f"Failed default value test: {e}")
        all_passed = False
    
    # Additional validation: Round-trip
    print("\n[Additional] Round-trip save/load")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            original = SpecKitFlowConfig(agent_type="test", num_sessions=7)
            
            save_config(original, tmp_path)
            loaded = load_config(tmp_path)
            
            passed = check(
                loaded.agent_type == original.agent_type,
                "agent_type preserved in round-trip"
            )
            all_passed &= passed
            passed = check(
                loaded.num_sessions == original.num_sessions,
                "num_sessions preserved in round-trip"
            )
            all_passed &= passed
    except Exception as e:
        check(False, f"Round-trip failed: {e}")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All acceptance criteria PASSED")
        return 0
    else:
        print("✗ Some acceptance criteria FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
