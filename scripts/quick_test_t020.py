#!/usr/bin/env python3
"""Quick test to verify T020 implementation can be imported."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    # Test basic import
    from speckit_flow.agents import AgentAdapter
    print("✓ Successfully imported AgentAdapter from speckit_flow.agents")
    
    # Test direct import
    from speckit_flow.agents.base import AgentAdapter as DirectAgentAdapter
    print("✓ Successfully imported AgentAdapter from speckit_flow.agents.base")
    
    # Verify they're the same
    assert AgentAdapter is DirectAgentAdapter
    print("✓ Both imports reference the same class")
    
    # Check it's abstract
    from abc import ABC
    assert issubclass(AgentAdapter, ABC)
    print("✓ AgentAdapter is an ABC subclass")
    
    # Check abstract methods exist
    abstract_methods = AgentAdapter.__abstractmethods__
    expected = {'setup_session', 'notify_user', 'get_files_to_watch', 'get_context_file_path'}
    assert abstract_methods == expected, f"Expected {expected}, got {abstract_methods}"
    print(f"✓ Has correct abstract methods: {abstract_methods}")
    
    # Check it can't be instantiated
    try:
        AgentAdapter()
        print("❌ FAIL: Should not be able to instantiate abstract class")
        sys.exit(1)
    except TypeError as e:
        print(f"✓ Cannot instantiate: {e}")
    
    print("\n✅ All basic checks passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
