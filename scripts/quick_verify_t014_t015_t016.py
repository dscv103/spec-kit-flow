#!/usr/bin/env python3
"""
Quick verification script for T014, T015, T016.
Tests key functionality without full test suite.
"""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

def test_imports():
    """Verify all imports work."""
    print("Testing imports...")
    try:
        from speckit_flow.orchestration.dag_engine import DAGEngine, DAGOutput, DAGPhase
        from speckit_core.models import TaskInfo
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic DAG functionality."""
    print("Testing basic functionality...")
    try:
        from speckit_flow.orchestration.dag_engine import DAGEngine
        from speckit_core.models import TaskInfo
        
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="Build", dependencies=["T001"]),
        ]
        
        engine = DAGEngine(tasks)
        engine.validate()
        
        phases = engine.get_phases()
        assert len(phases) == 2, "Should have 2 phases"
        
        critical = engine.get_critical_path()
        assert len(critical) == 2, "Critical path should have 2 tasks"
        
        engine.assign_sessions(2)
        assert engine.get_task("T001").session is not None, "Task should have session"
        
        print("  ✓ Basic functionality works")
        return True
    except Exception as e:
        print(f"  ✗ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_serialization():
    """Test YAML serialization."""
    print("Testing serialization...")
    try:
        from speckit_flow.orchestration.dag_engine import DAGEngine
        from speckit_core.models import TaskInfo
        import yaml
        
        tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        assert "version" in data, "Should have version"
        assert "spec_id" in data, "Should have spec_id"
        assert "phases" in data, "Should have phases"
        
        print("  ✓ Serialization works")
        return True
    except Exception as e:
        print(f"  ✗ Serialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Quick Verification: T014, T015, T016")
    print("=" * 60)
    print()
    
    tests = [
        test_imports,
        test_basic_functionality,
        test_serialization,
    ]
    
    results = [test() for test in tests]
    
    print()
    print("=" * 60)
    if all(results):
        print("✅ All quick verification tests passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
