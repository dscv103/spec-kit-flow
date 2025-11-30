#!/usr/bin/env python3
"""
T007 Acceptance Criteria Verification

This script systematically verifies all 4 acceptance criteria for T007.
"""

import sys
import tempfile
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_core.config import SpecKitFlowConfig, load_config, save_config
from speckit_core.exceptions import ConfigurationError


def verify_ac1() -> bool:
    """AC1: Loads valid YAML config files"""
    print("\n" + "="*60)
    print("AC1: Loads valid YAML config files")
    print("="*60)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            speckit_dir = tmp_path / ".speckit"
            speckit_dir.mkdir()
            config_file = speckit_dir / "speckit-flow.yaml"
            
            # Test 1: Load config with custom values
            config_file.write_text("agent_type: goose\nnum_sessions: 5\n")
            config = load_config(tmp_path)
            
            assert config.agent_type == "goose", "Failed: agent_type not loaded correctly"
            assert config.num_sessions == 5, "Failed: num_sessions not loaded correctly"
            print("✓ Loads custom values correctly")
            
            # Test 2: Load config with only agent_type
            config_file.write_text("agent_type: opencode\n")
            config = load_config(tmp_path)
            
            assert config.agent_type == "opencode", "Failed: custom agent_type not loaded"
            assert config.num_sessions == 3, "Failed: default not applied for missing field"
            print("✓ Applies defaults for missing fields")
            
            # Test 3: Load empty config
            config_file.write_text("")
            config = load_config(tmp_path)
            
            assert config.agent_type == "copilot", "Failed: default agent_type not applied"
            assert config.num_sessions == 3, "Failed: default num_sessions not applied"
            print("✓ Handles empty files (uses all defaults)")
            
            print("\n✅ AC1 PASSED: Loads valid YAML config files")
            return True
            
    except Exception as e:
        print(f"\n❌ AC1 FAILED: {e}")
        return False


def verify_ac2() -> bool:
    """AC2: Raises clear error for invalid/missing config"""
    print("\n" + "="*60)
    print("AC2: Raises clear error for invalid/missing config")
    print("="*60)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Test 1: Missing config file
            try:
                load_config(tmp_path)
                print("❌ Should have raised FileNotFoundError for missing config")
                return False
            except FileNotFoundError as e:
                error_msg = str(e)
                assert "Configuration file not found" in error_msg, "Missing helpful message"
                assert "skf init" in error_msg, "Missing suggestion to run 'skf init'"
                print("✓ FileNotFoundError with helpful message")
                print(f"  Message includes: 'Configuration file not found'")
                print(f"  Message suggests: 'skf init'")
            
            # Test 2: Invalid YAML syntax
            speckit_dir = tmp_path / ".speckit"
            speckit_dir.mkdir()
            config_file = speckit_dir / "speckit-flow.yaml"
            config_file.write_text("[invalid yaml syntax")
            
            try:
                load_config(tmp_path)
                print("❌ Should have raised ConfigurationError for invalid YAML")
                return False
            except ConfigurationError as e:
                assert "Failed to parse YAML" in str(e), "Missing YAML error message"
                print("✓ ConfigurationError for invalid YAML syntax")
                print(f"  Message: 'Failed to parse YAML'")
            
            # Test 3: Wrong root type (list instead of dict)
            config_file.write_text("- item1\n- item2\n")
            
            try:
                load_config(tmp_path)
                print("❌ Should have raised ConfigurationError for wrong type")
                return False
            except ConfigurationError as e:
                error_msg = str(e)
                assert "Invalid configuration format" in error_msg, "Missing format error"
                assert "Expected YAML mapping" in error_msg, "Missing type expectation"
                print("✓ ConfigurationError for wrong root type")
                print(f"  Message: 'Expected YAML mapping'")
            
            # Test 4: Invalid values (num_sessions out of range)
            config_file.write_text("agent_type: copilot\nnum_sessions: 100\n")
            
            try:
                load_config(tmp_path)
                print("❌ Should have raised ConfigurationError for invalid values")
                return False
            except ConfigurationError as e:
                assert "Invalid configuration" in str(e), "Missing validation error"
                print("✓ ConfigurationError for invalid field values")
                print(f"  Message: 'Invalid configuration'")
            
            # Test 5: Empty agent_type
            config_file.write_text("agent_type: ''\nnum_sessions: 3\n")
            
            try:
                load_config(tmp_path)
                print("❌ Should have raised ConfigurationError for empty agent_type")
                return False
            except ConfigurationError as e:
                assert "agent_type cannot be empty" in str(e), "Missing empty validation"
                print("✓ ConfigurationError for empty agent_type")
            
            print("\n✅ AC2 PASSED: Raises clear error for invalid/missing config")
            return True
            
    except Exception as e:
        print(f"\n❌ AC2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_ac3() -> bool:
    """AC3: Saves config with proper YAML formatting"""
    print("\n" + "="*60)
    print("AC3: Saves config with proper YAML formatting")
    print("="*60)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Test 1: Save config
            config = SpecKitFlowConfig(agent_type="opencode", num_sessions=7)
            save_config(config, tmp_path)
            
            config_file = tmp_path / ".speckit" / "speckit-flow.yaml"
            assert config_file.exists(), "Config file not created"
            print("✓ Creates config file at .speckit/speckit-flow.yaml")
            
            # Test 2: Verify .speckit directory created
            assert (tmp_path / ".speckit").is_dir(), ".speckit directory not created"
            print("✓ Creates .speckit directory if missing")
            
            # Test 3: Verify YAML content
            content = config_file.read_text()
            data = yaml.safe_load(content)
            
            assert data["agent_type"] == "opencode", "agent_type not saved correctly"
            assert data["num_sessions"] == 7, "num_sessions not saved correctly"
            print("✓ Saves correct values to YAML")
            
            # Test 4: Verify YAML formatting (block style, not flow style)
            assert "{" not in content, "Should use block style, not flow style"
            assert content.count("\n") > 1, "Should be multi-line format"
            print("✓ Uses block-style YAML formatting (not compact)")
            print(f"  Content preview:\n    {content.strip()[:60]}...")
            
            # Test 5: Unicode support
            config2 = SpecKitFlowConfig(agent_type="copilot™", num_sessions=2)
            save_config(config2, tmp_path)
            
            loaded = load_config(tmp_path)
            assert loaded.agent_type == "copilot™", "Unicode not preserved"
            print("✓ Handles Unicode characters correctly")
            
            print("\n✅ AC3 PASSED: Saves config with proper YAML formatting")
            return True
            
    except Exception as e:
        print(f"\n❌ AC3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_ac4() -> bool:
    """AC4: Default values applied when fields missing"""
    print("\n" + "="*60)
    print("AC4: Default values applied when fields missing")
    print("="*60)
    
    try:
        # Test 1: Model defaults
        config = SpecKitFlowConfig()
        assert config.agent_type == "copilot", "Default agent_type should be 'copilot'"
        assert config.num_sessions == 3, "Default num_sessions should be 3"
        print("✓ Model defaults: agent_type='copilot', num_sessions=3")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            speckit_dir = tmp_path / ".speckit"
            speckit_dir.mkdir()
            config_file = speckit_dir / "speckit-flow.yaml"
            
            # Test 2: Partial config (only agent_type)
            config_file.write_text("agent_type: custom\n")
            config = load_config(tmp_path)
            
            assert config.agent_type == "custom", "Custom agent_type not loaded"
            assert config.num_sessions == 3, "Default num_sessions not applied"
            print("✓ Applies default for missing num_sessions")
            
            # Test 3: Partial config (only num_sessions)
            config_file.write_text("num_sessions: 8\n")
            config = load_config(tmp_path)
            
            assert config.agent_type == "copilot", "Default agent_type not applied"
            assert config.num_sessions == 8, "Custom num_sessions not loaded"
            print("✓ Applies default for missing agent_type")
            
            # Test 4: Empty file (all defaults)
            config_file.write_text("")
            config = load_config(tmp_path)
            
            assert config.agent_type == "copilot", "Default agent_type not applied to empty file"
            assert config.num_sessions == 3, "Default num_sessions not applied to empty file"
            print("✓ Applies all defaults for empty file")
            
            # Test 5: Test boundary values with defaults
            config = SpecKitFlowConfig(num_sessions=1)  # min value
            assert config.num_sessions == 1, "Min value not accepted"
            assert config.agent_type == "copilot", "Default not applied with custom num_sessions"
            
            config = SpecKitFlowConfig(num_sessions=10)  # max value
            assert config.num_sessions == 10, "Max value not accepted"
            assert config.agent_type == "copilot", "Default not applied with custom num_sessions"
            print("✓ Defaults work with boundary values (1, 10)")
            
            print("\n✅ AC4 PASSED: Default values applied when fields missing")
            return True
            
    except Exception as e:
        print(f"\n❌ AC4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all acceptance criteria verifications"""
    print("\n" + "🔍 T007 ACCEPTANCE CRITERIA VERIFICATION")
    print("Task: Implement config.py")
    print("="*60)
    
    results = {
        "AC1: Loads valid YAML config files": verify_ac1(),
        "AC2: Raises clear error for invalid/missing config": verify_ac2(),
        "AC3: Saves config with proper YAML formatting": verify_ac3(),
        "AC4: Default values applied when fields missing": verify_ac4(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    for criterion, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {criterion}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL ACCEPTANCE CRITERIA VERIFIED")
        print("T007 is COMPLETE and ready for production")
        print("="*60)
        return 0
    else:
        failed_count = sum(1 for p in results.values() if not p)
        print(f"⚠️  {failed_count} ACCEPTANCE CRITERIA FAILED")
        print("T007 requires fixes before completion")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
