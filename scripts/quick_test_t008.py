#!/usr/bin/env python3
"""Quick import test for T008 validation."""

import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

print("Testing imports...")

try:
    # Test subpackage imports
    import speckit_flow.orchestration
    print("✓ speckit_flow.orchestration")
    
    import speckit_flow.agents
    print("✓ speckit_flow.agents")
    
    import speckit_flow.worktree
    print("✓ speckit_flow.worktree")
    
    import speckit_flow.monitoring
    print("✓ speckit_flow.monitoring")
    
    import speckit_flow.state
    print("✓ speckit_flow.state")
    
    # Test main package (will fail on typer import until T009)
    try:
        from speckit_flow import __version__
        print(f"✓ speckit_flow.__version__ = {__version__}")
    except ImportError as e:
        print(f"ℹ speckit_flow main import requires typer (T009): {e}")
    
    print("\n✅ All subpackages import successfully!")
    print("ℹ  Main package import requires T009 (typer dependency)")
    
except ImportError as e:
    print(f"\n❌ Import failed: {e}")
    sys.exit(1)
