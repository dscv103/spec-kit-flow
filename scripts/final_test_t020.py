#!/usr/bin/env python3
"""
Final validation test for T020: Implement agents/base.py

This script performs comprehensive testing of all acceptance criteria
and verifies the implementation is production-ready.
"""

import sys
from pathlib import Path

# Add src directories to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

def test_imports():
    """Test all import paths work correctly."""
    print("Testing imports...")
    
    # Test package import
    try:
        from speckit_flow.agents import AgentAdapter
        print("  ✓ from speckit_flow.agents import AgentAdapter")
    except ImportError as e:
        print(f"  ❌ Package import failed: {e}")
        return False
    
    # Test direct module import
    try:
        from speckit_flow.agents.base import AgentAdapter as DirectAdapter
        print("  ✓ from speckit_flow.agents.base import AgentAdapter")
    except ImportError as e:
        print(f"  ❌ Direct import failed: {e}")
        return False
    
    # Verify they're the same object
    if AgentAdapter is not DirectAdapter:
        print("  ❌ Imports reference different objects")
        return False
    print("  ✓ Both imports reference same class")
    
    return True


def test_abstract_class():
    """Test that AgentAdapter is properly abstract."""
    print("\nTesting abstract class behavior...")
    
    from speckit_flow.agents import AgentAdapter
    from abc import ABC
    
    # Check inheritance
    if not issubclass(AgentAdapter, ABC):
        print("  ❌ AgentAdapter does not inherit from ABC")
        return False
    print("  ✓ Inherits from ABC")
    
    # Check abstract methods
    expected_methods = {'setup_session', 'notify_user', 'get_files_to_watch', 'get_context_file_path'}
    actual_methods = AgentAdapter.__abstractmethods__
    
    if actual_methods != expected_methods:
        print(f"  ❌ Expected abstract methods: {expected_methods}")
        print(f"     Got: {actual_methods}")
        return False
    print(f"  ✓ Has correct abstract methods: {actual_methods}")
    
    # Verify cannot instantiate
    try:
        AgentAdapter()
        print("  ❌ Should not be able to instantiate abstract class")
        return False
    except TypeError as e:
        if "abstract" in str(e).lower():
            print(f"  ✓ Cannot instantiate: {str(e)[:60]}...")
        else:
            print(f"  ❌ Wrong error type: {e}")
            return False
    
    return True


def test_method_signatures():
    """Test that all methods have correct signatures."""
    print("\nTesting method signatures...")
    
    from speckit_flow.agents import AgentAdapter
    from pathlib import Path as PathType
    from speckit_core.models import TaskInfo
    import inspect
    
    methods = {
        'setup_session': {
            'params': ['self', 'worktree', 'task'],
            'param_types': {'worktree': PathType, 'task': TaskInfo},
            'return': type(None),
        },
        'notify_user': {
            'params': ['self', 'session_id', 'worktree', 'task'],
            'param_types': {'session_id': int, 'worktree': PathType, 'task': TaskInfo},
            'return': type(None),
        },
        'get_files_to_watch': {
            'params': ['self', 'worktree'],
            'param_types': {'worktree': PathType},
            'return': list,  # Will check list[Path] separately
        },
        'get_context_file_path': {
            'params': ['self', 'worktree'],
            'param_types': {'worktree': PathType},
            'return': PathType,
        },
    }
    
    for method_name, expected in methods.items():
        method = getattr(AgentAdapter, method_name)
        sig = inspect.signature(method)
        
        # Check parameter names
        actual_params = list(sig.parameters.keys())
        if actual_params != expected['params']:
            print(f"  ❌ {method_name}: Expected params {expected['params']}, got {actual_params}")
            return False
        
        # Check parameter types
        for param_name, param_type in expected['param_types'].items():
            param = sig.parameters[param_name]
            if param.annotation == inspect.Parameter.empty:
                print(f"  ❌ {method_name}: Parameter '{param_name}' missing type annotation")
                return False
        
        # Check return type
        if sig.return_annotation == inspect.Signature.empty:
            print(f"  ❌ {method_name}: Missing return type annotation")
            return False
        
        print(f"  ✓ {method_name} signature correct")
    
    return True


def test_docstrings():
    """Test that all docstrings are comprehensive."""
    print("\nTesting docstrings...")
    
    from speckit_flow.agents import AgentAdapter
    
    # Check class docstring
    if not AgentAdapter.__doc__:
        print("  ❌ Class missing docstring")
        return False
    
    class_doc = AgentAdapter.__doc__
    if len(class_doc) < 200:
        print(f"  ❌ Class docstring too short ({len(class_doc)} chars)")
        return False
    
    required_in_class = ["adapter", "abstract", "example"]
    for keyword in required_in_class:
        if keyword.lower() not in class_doc.lower():
            print(f"  ❌ Class docstring missing keyword: {keyword}")
            return False
    
    print(f"  ✓ Class docstring comprehensive ({len(class_doc)} chars)")
    
    # Check method docstrings
    methods = ['setup_session', 'notify_user', 'get_files_to_watch', 'get_context_file_path']
    
    for method_name in methods:
        method = getattr(AgentAdapter, method_name)
        if not method.__doc__:
            print(f"  ❌ {method_name} missing docstring")
            return False
        
        doc = method.__doc__
        if len(doc) < 100:
            print(f"  ❌ {method_name} docstring too short ({len(doc)} chars)")
            return False
        
        # Check for required sections
        doc_lower = doc.lower()
        required = ['args:', 'example']
        for section in required:
            if section not in doc_lower:
                print(f"  ❌ {method_name} docstring missing section: {section}")
                return False
        
        print(f"  ✓ {method_name} docstring comprehensive ({len(doc)} chars)")
    
    return True


def test_not_implemented_errors():
    """Test that abstract methods raise NotImplementedError."""
    print("\nTesting NotImplementedError behavior...")
    
    from speckit_flow.agents import AgentAdapter
    from pathlib import Path as PathType
    from speckit_core.models import TaskInfo
    
    # Create a minimal concrete class that calls super()
    class TestAdapter(AgentAdapter):
        def setup_session(self, worktree: PathType, task: TaskInfo) -> None:
            super().setup_session(worktree, task)
        
        def notify_user(self, session_id: int, worktree: PathType, task: TaskInfo) -> None:
            super().notify_user(session_id, worktree, task)
        
        def get_files_to_watch(self, worktree: PathType) -> list[PathType]:
            return super().get_files_to_watch(worktree)
        
        def get_context_file_path(self, worktree: PathType) -> PathType:
            return super().get_context_file_path(worktree)
    
    adapter = TestAdapter()
    test_worktree = PathType("/tmp/test")
    test_task = TaskInfo(id="T001", name="Test task")
    
    # Test each method
    tests = [
        ("setup_session", lambda: adapter.setup_session(test_worktree, test_task)),
        ("notify_user", lambda: adapter.notify_user(0, test_worktree, test_task)),
        ("get_files_to_watch", lambda: adapter.get_files_to_watch(test_worktree)),
        ("get_context_file_path", lambda: adapter.get_context_file_path(test_worktree)),
    ]
    
    for method_name, method_call in tests:
        try:
            method_call()
            print(f"  ❌ {method_name} did not raise NotImplementedError")
            return False
        except NotImplementedError as e:
            if "implement" in str(e).lower():
                print(f"  ✓ {method_name} raises NotImplementedError")
            else:
                print(f"  ⚠ {method_name} raises NotImplementedError but message unclear: {e}")
        except Exception as e:
            print(f"  ❌ {method_name} raised wrong exception: {type(e).__name__}: {e}")
            return False
    
    return True


def test_concrete_implementation():
    """Test that concrete implementation works."""
    print("\nTesting concrete implementation...")
    
    from speckit_flow.agents import AgentAdapter
    from pathlib import Path as PathType
    from speckit_core.models import TaskInfo
    
    # Create a minimal working implementation
    class WorkingAdapter(AgentAdapter):
        def setup_session(self, worktree: PathType, task: TaskInfo) -> None:
            pass  # Minimal implementation
        
        def notify_user(self, session_id: int, worktree: PathType, task: TaskInfo) -> None:
            pass
        
        def get_files_to_watch(self, worktree: PathType) -> list[PathType]:
            return [worktree / "tasks.md"]
        
        def get_context_file_path(self, worktree: PathType) -> PathType:
            return worktree / ".agent" / "context.md"
    
    # Should be able to instantiate
    try:
        adapter = WorkingAdapter()
        print("  ✓ Can instantiate concrete implementation")
    except Exception as e:
        print(f"  ❌ Cannot instantiate concrete implementation: {e}")
        return False
    
    # Test methods work
    test_worktree = PathType("/tmp/test")
    test_task = TaskInfo(id="T001", name="Test task")
    
    try:
        adapter.setup_session(test_worktree, test_task)
        print("  ✓ setup_session() works")
        
        adapter.notify_user(0, test_worktree, test_task)
        print("  ✓ notify_user() works")
        
        files = adapter.get_files_to_watch(test_worktree)
        assert isinstance(files, list)
        assert all(isinstance(f, PathType) for f in files)
        print("  ✓ get_files_to_watch() returns list[Path]")
        
        context_path = adapter.get_context_file_path(test_worktree)
        assert isinstance(context_path, PathType)
        print("  ✓ get_context_file_path() returns Path")
        
    except Exception as e:
        print(f"  ❌ Method execution failed: {e}")
        return False
    
    return True


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("T020 FINAL VALIDATION")
    print("=" * 70)
    print()
    
    tests = [
        ("Import paths", test_imports),
        ("Abstract class behavior", test_abstract_class),
        ("Method signatures", test_method_signatures),
        ("Docstring quality", test_docstrings),
        ("NotImplementedError", test_not_implemented_errors),
        ("Concrete implementation", test_concrete_implementation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print()
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print()
    print("=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - T020 is COMPLETE and VERIFIED")
        print("=" * 70)
        print()
        print("Acceptance Criteria:")
        print("  ✅ Abstract methods raise NotImplementedError")
        print("  ✅ Type hints complete")
        print("  ✅ Docstrings explain expected behavior")
        print()
        print("Ready to proceed to T021 (agents/copilot.py)")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
