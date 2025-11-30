#!/usr/bin/env python3
"""
Quick test for T007 config.py implementation.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.config import SpecKitFlowConfig, load_config, save_config
from speckit_core.exceptions import ConfigurationError

print("Testing T007 config.py implementation...\n")

# Test 1: Create config with defaults
print("1. Testing SpecKitFlowConfig with defaults...")
config = SpecKitFlowConfig()
assert config.agent_type == "copilot", "Default agent_type should be 'copilot'"
assert config.num_sessions == 3, "Default num_sessions should be 3"
print("   ✓ Defaults work correctly\n")

# Test 2: Create config with custom values
print("2. Testing SpecKitFlowConfig with custom values...")
config = SpecKitFlowConfig(agent_type="goose", num_sessions=5)
assert config.agent_type == "goose"
assert config.num_sessions == 5
print("   ✓ Custom values work correctly\n")

# Test 3: Validation
print("3. Testing validation...")
try:
    SpecKitFlowConfig(num_sessions=0)
    print("   ✗ Should have raised ValueError for num_sessions=0")
    sys.exit(1)
except ValueError:
    print("   ✓ Correctly rejects num_sessions=0")

try:
    SpecKitFlowConfig(num_sessions=11)
    print("   ✗ Should have raised ValueError for num_sessions=11")
    sys.exit(1)
except ValueError:
    print("   ✓ Correctly rejects num_sessions=11")

try:
    SpecKitFlowConfig(agent_type="")
    print("   ✗ Should have raised ValueError for empty agent_type")
    sys.exit(1)
except ValueError:
    print("   ✓ Correctly rejects empty agent_type\n")

# Test 4: Save and load
print("4. Testing save and load...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    
    # Save
    config = SpecKitFlowConfig(agent_type="opencode", num_sessions=7)
    save_config(config, tmp_path)
    
    config_file = tmp_path / ".speckit" / "speckit-flow.yaml"
    assert config_file.exists(), "Config file should exist after save"
    print("   ✓ Config saved successfully")
    
    # Load
    loaded = load_config(tmp_path)
    assert loaded.agent_type == "opencode"
    assert loaded.num_sessions == 7
    print("   ✓ Config loaded successfully")
    print("   ✓ Round-trip preserves data\n")

# Test 5: Error handling
print("5. Testing error handling...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    
    # Missing file
    try:
        load_config(tmp_path)
        print("   ✗ Should have raised FileNotFoundError")
        sys.exit(1)
    except FileNotFoundError as e:
        assert "Configuration file not found" in str(e)
        assert "skf init" in str(e)
        print("   ✓ FileNotFoundError with helpful message")
    
    # Invalid YAML
    speckit_dir = tmp_path / ".speckit"
    speckit_dir.mkdir()
    config_file = speckit_dir / "speckit-flow.yaml"
    config_file.write_text("[invalid yaml")
    
    try:
        load_config(tmp_path)
        print("   ✗ Should have raised ConfigurationError")
        sys.exit(1)
    except ConfigurationError as e:
        assert "Failed to parse YAML" in str(e)
        print("   ✓ ConfigurationError for invalid YAML")
    
    # Invalid values
    config_file.write_text("agent_type: test\nnum_sessions: 100\n")
    try:
        load_config(tmp_path)
        print("   ✗ Should have raised ConfigurationError")
        sys.exit(1)
    except ConfigurationError as e:
        assert "Invalid configuration" in str(e)
        print("   ✓ ConfigurationError for invalid values\n")

print("=" * 60)
print("✓ All tests passed! T007 implementation is working correctly.")
print("=" * 60)
