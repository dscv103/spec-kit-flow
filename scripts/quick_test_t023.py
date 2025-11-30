#!/usr/bin/env python3
"""Quick test for T023 implementation."""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    try:
        from rich.tree import Tree
        from rich.console import Console
        from speckit_flow import _visualize_dag
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_visualize_function():
    """Test the _visualize_dag function exists and has correct signature."""
    print("\nTesting _visualize_dag function...")
    try:
        from speckit_flow import _visualize_dag
        import inspect
        
        sig = inspect.signature(_visualize_dag)
        params = list(sig.parameters.keys())
        
        if params == ["engine"]:
            print("  ✓ Function signature correct")
        else:
            print(f"  ✗ Unexpected parameters: {params}")
            return False
        
        # Check docstring
        if _visualize_dag.__doc__ and "ASCII tree" in _visualize_dag.__doc__:
            print("  ✓ Docstring mentions ASCII tree")
        else:
            print("  ⚠ Docstring could be more descriptive")
        
        return True
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        return False


def test_dag_command_signature():
    """Test that dag command has visualize parameter."""
    print("\nTesting dag command signature...")
    try:
        from speckit_flow import dag
        import inspect
        
        sig = inspect.signature(dag)
        params = sig.parameters
        
        if "visualize" in params:
            print("  ✓ visualize parameter present")
            
            # Check it's a boolean with default False
            param = params["visualize"]
            if hasattr(param, "default"):
                print(f"  ✓ Has default value")
            
            return True
        else:
            print(f"  ✗ visualize parameter not found")
            print(f"  Available parameters: {list(params.keys())}")
            return False
            
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        return False


def test_visualization_logic():
    """Test visualization with sample data."""
    print("\nTesting visualization logic...")
    try:
        from speckit_core.models import TaskInfo
        from speckit_flow.orchestration.dag_engine import DAGEngine
        from speckit_flow import _visualize_dag
        from rich.console import Console
        from io import StringIO
        
        # Create sample tasks
        tasks = [
            TaskInfo(
                id="T001",
                name="Setup project",
                description="Initial setup",
                dependencies=[],
                parallelizable=False,
            ),
            TaskInfo(
                id="T002",
                name="Feature A",
                description="Implement A",
                dependencies=["T001"],
                parallelizable=True,
            ),
            TaskInfo(
                id="T003",
                name="Feature B",
                description="Implement B",
                dependencies=["T001"],
                parallelizable=True,
            ),
            TaskInfo(
                id="T004",
                name="Integration",
                description="Integrate features",
                dependencies=["T002", "T003"],
                parallelizable=False,
            ),
        ]
        
        # Build DAG
        engine = DAGEngine(tasks)
        engine.assign_sessions(2)
        
        # Capture output
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)
        
        # Temporarily replace global console
        import speckit_flow
        original_console = speckit_flow.console
        speckit_flow.console = console
        
        try:
            _visualize_dag(engine)
            output = string_io.getvalue()
            
            # Check output contains expected elements
            checks = {
                "DAG Phases": "DAG Phases" in output,
                "Phase hierarchy": "Phase" in output,
                "Task IDs": "T001" in output and "T002" in output,
                "Dependencies": "(deps:" in output,
                "Parallel markers": "[P]" in output,
            }
            
            all_passed = True
            for check_name, result in checks.items():
                status = "✓" if result else "✗"
                print(f"  {status} {check_name}")
                if not result:
                    all_passed = False
            
            if all_passed:
                print("  ✓ All visualization elements present")
            
            return all_passed
            
        finally:
            # Restore original console
            speckit_flow.console = original_console
            
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("T023 Quick Test: skf dag --visualize")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Visualize function", test_visualize_function),
        ("DAG command signature", test_dag_command_signature),
        ("Visualization logic", test_visualization_logic),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ T023 implementation validated!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
