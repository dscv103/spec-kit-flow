#!/usr/bin/env python3
"""
Quick import verification for T007.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("Verifying T007 imports...\n")

# Test 1: Import from config module
print("1. Importing from speckit_core.config...")
try:
    from speckit_core.config import SpecKitFlowConfig, load_config, save_config
    print("   ✓ Direct imports work\n")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Import from speckit_core package
print("2. Importing from speckit_core package...")
try:
    from speckit_core import SpecKitFlowConfig, load_config, save_config
    print("   ✓ Package-level imports work\n")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 3: Check __all__ exports
print("3. Checking __all__ exports...")
import speckit_core.config
expected_exports = ["SpecKitFlowConfig", "load_config", "save_config"]
actual_exports = speckit_core.config.__all__

for export in expected_exports:
    if export not in actual_exports:
        print(f"   ✗ Missing export: {export}")
        sys.exit(1)

print(f"   ✓ All exports present: {actual_exports}\n")

# Test 4: Verify model can be instantiated
print("4. Instantiating SpecKitFlowConfig...")
try:
    config = SpecKitFlowConfig()
    print(f"   ✓ Default config: agent_type={config.agent_type}, num_sessions={config.num_sessions}\n")
except Exception as e:
    print(f"   ✗ Instantiation failed: {e}")
    sys.exit(1)

# Test 5: Check exception imports
print("5. Checking exception imports...")
try:
    from speckit_core.exceptions import ConfigurationError
    print("   ✓ ConfigurationError imported\n")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

print("=" * 60)
print("✓ All imports verified successfully!")
print("=" * 60)
