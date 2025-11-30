#!/usr/bin/env python3
"""
Validation script for T020: Implement agents/base.py

Verifies all acceptance criteria:
- Abstract methods raise NotImplementedError
- Type hints complete
- Docstrings explain expected behavior
"""

import inspect
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speckit_flow.agents.base import AgentAdapter
from speckit_core.models import TaskInfo


def test_abstract_methods_raise_not_implemented():
    """AC: Abstract methods raise NotImplementedError."""
    print("Testing abstract methods raise NotImplementedError...")
    
    # Create a minimal concrete class that doesn't implement methods
    class MinimalAdapter(AgentAdapter):
        pass
    
    # Should not be able to instantiate without implementing abstract methods
    try:
        adapter = MinimalAdapter()
        print("  ❌ FAIL: Should not be able to instantiate without implementing abstract methods")
        return False
    except TypeError as e:
        if "abstract methods" in str(e):
            print(f"  ✓ Cannot instantiate without implementing abstract methods: {e}")
        else:
            print(f"  ❌ FAIL: Wrong error: {e}")
            return False
    
    # Create a concrete class that implements methods incorrectly (calls super)
    class TestAdapter(AgentAdapter):
        def setup_session(self, worktree: Path, task: TaskInfo) -> None:
            super().setup_session(worktree, task)
        
        def notify_user(self, session_id: int, worktree: Path, task: TaskInfo) -> None:
            super().notify_user(session_id, worktree, task)
        
        def get_files_to_watch(self, worktree: Path) -> list[Path]:
            return super().get_files_to_watch(worktree)
        
        def get_context_file_path(self, worktree: Path) -> Path:
            return super().get_context_file_path(worktree)
    
    adapter = TestAdapter()
    
    # Test each method raises NotImplementedError
    methods = [
        ("setup_session", lambda: adapter.setup_session(Path("/tmp"), TaskInfo(id="T001", name="test"))),
        ("notify_user", lambda: adapter.notify_user(0, Path("/tmp"), TaskInfo(id="T001", name="test"))),
        ("get_files_to_watch", lambda: adapter.get_files_to_watch(Path("/tmp"))),
        ("get_context_file_path", lambda: adapter.get_context_file_path(Path("/tmp"))),
    ]
    
    for method_name, method_call in methods:
        try:
            method_call()
            print(f"  ❌ FAIL: {method_name} did not raise NotImplementedError")
            return False
        except NotImplementedError:
            print(f"  ✓ {method_name} raises NotImplementedError")
        except Exception as e:
            print(f"  ❌ FAIL: {method_name} raised wrong exception: {e}")
            return False
    
    return True


def test_type_hints_complete():
    """AC: Type hints complete."""
    print("\nTesting type hints are complete...")
    
    methods = [
        "setup_session",
        "notify_user", 
        "get_files_to_watch",
        "get_context_file_path"
    ]
    
    for method_name in methods:
        method = getattr(AgentAdapter, method_name)
        sig = inspect.signature(method)
        
        # Check all parameters have annotations
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            if param.annotation == inspect.Parameter.empty:
                print(f"  ❌ FAIL: {method_name} parameter '{param_name}' missing type hint")
                return False
        
        # Check return type annotation exists
        if sig.return_annotation == inspect.Signature.empty:
            print(f"  ❌ FAIL: {method_name} missing return type annotation")
            return False
        
        print(f"  ✓ {method_name} has complete type hints")
    
    return True


def test_docstrings_explain_behavior():
    """AC: Docstrings explain expected behavior."""
    print("\nTesting docstrings explain expected behavior...")
    
    # Check class docstring
    if not AgentAdapter.__doc__ or len(AgentAdapter.__doc__.strip()) < 50:
        print("  ❌ FAIL: Class docstring missing or too short")
        return False
    print(f"  ✓ Class has comprehensive docstring ({len(AgentAdapter.__doc__)} chars)")
    
    # Check each method has a docstring
    methods = [
        "setup_session",
        "notify_user",
        "get_files_to_watch", 
        "get_context_file_path"
    ]
    
    for method_name in methods:
        method = getattr(AgentAdapter, method_name)
        if not method.__doc__ or len(method.__doc__.strip()) < 50:
            print(f"  ❌ FAIL: {method_name} docstring missing or too short")
            return False
        
        # Check docstring contains key sections
        doc = method.__doc__.lower()
        required_sections = ["args:", "example"]
        for section in required_sections:
            if section not in doc:
                print(f"  ❌ FAIL: {method_name} docstring missing '{section}' section")
                return False
        
        print(f"  ✓ {method_name} has comprehensive docstring")
    
    return True


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("T020 Acceptance Criteria Validation")
    print("=" * 60)
    
    tests = [
        ("Abstract methods raise NotImplementedError", test_abstract_methods_raise_not_implemented),
        ("Type hints complete", test_type_hints_complete),
        ("Docstrings explain expected behavior", test_docstrings_explain_behavior),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ All acceptance criteria verified!")
        return 0
    else:
        print("\n❌ Some acceptance criteria failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
