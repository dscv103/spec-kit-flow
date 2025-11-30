"""
Test T003: speckit_core package skeleton structure.

Validates acceptance criteria:
- AC1: `from speckit_core import __version__` works
- AC2: Package structure matches plan.md specification
"""

import pytest


def test_import_version():
    """AC1: from speckit_core import __version__ works."""
    from speckit_core import __version__
    
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_module_imports():
    """AC2: All required modules can be imported."""
    # These imports should work without errors
    from speckit_core import config, exceptions, models, paths, tasks
    
    # Verify modules are accessible
    assert config is not None
    assert exceptions is not None
    assert models is not None
    assert paths is not None
    assert tasks is not None


def test_module_structure():
    """AC2: Package structure matches plan.md specification."""
    import speckit_core
    from pathlib import Path
    
    # Get package directory
    package_dir = Path(speckit_core.__file__).parent
    
    # Verify required files exist
    required_files = [
        "__init__.py",
        "paths.py",
        "tasks.py",
        "models.py",
        "config.py",
        "exceptions.py",
        "pyproject.toml",
    ]
    
    for filename in required_files:
        file_path = package_dir / filename
        assert file_path.exists(), f"Required file missing: {filename}"


def test_module_exports():
    """AC2: __all__ exports match expected public API."""
    import speckit_core
    
    expected_exports = {
        "__version__",
        "config",
        "exceptions",
        "models",
        "paths",
        "tasks",
    }
    
    actual_exports = set(speckit_core.__all__)
    assert actual_exports == expected_exports, (
        f"Exports mismatch. Expected: {expected_exports}, Got: {actual_exports}"
    )


def test_submodule_all_exports():
    """Verify each submodule has __all__ defined."""
    from speckit_core import config, exceptions, models, paths, tasks
    
    # Each module should have __all__ defined
    assert hasattr(paths, "__all__")
    assert hasattr(tasks, "__all__")
    assert hasattr(models, "__all__")
    assert hasattr(config, "__all__")
    assert hasattr(exceptions, "__all__")
    
    # Verify they're lists/tuples
    assert isinstance(paths.__all__, (list, tuple))
    assert isinstance(tasks.__all__, (list, tuple))
    assert isinstance(models.__all__, (list, tuple))
    assert isinstance(config.__all__, (list, tuple))
    assert isinstance(exceptions.__all__, (list, tuple))
