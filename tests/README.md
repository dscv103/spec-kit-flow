# SpecKitFlow Tests

This directory contains the test suite for SpecKitFlow, organized following the testing standards from `.github/instructions/testing.instructions.md`.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (fast, isolated)
│   ├── speckit_core/       # Tests for speckit_core package
│   └── speckit_flow/       # Tests for speckit_flow package
├── integration/            # Integration tests (component interactions)
│   └── test_specify_cli.py # T002 verification tests
└── e2e/                    # End-to-end tests (complete workflows)
```

## Running Tests

### All tests
```bash
pytest
```

### With coverage
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

### Specific test file
```bash
pytest tests/integration/test_specify_cli.py
```

### Specific test function
```bash
pytest tests/integration/test_specify_cli.py::test_specify_help_displays
```

### Skip slow tests
```bash
pytest -m "not slow"
```

### Using Hatch
```bash
hatch run test
hatch run test-cov
```

## Test Categories

### Unit Tests
- Test individual functions/classes in isolation
- Fast execution (< 1 second each)
- Use mocking for external dependencies
- Located in `tests/unit/`

### Integration Tests
- Test component interactions
- May use real file system, subprocess calls
- Located in `tests/integration/`

### End-to-End Tests
- Test complete user workflows
- Marked with `@pytest.mark.e2e`
- May be slow
- Located in `tests/e2e/`

## Task-Specific Tests

Each task from `specs/speckit-flow/tasks.md` should have corresponding tests that verify its acceptance criteria:

- **T002**: `tests/integration/test_specify_cli.py` - Verifies specify CLI still works
- More tests will be added as tasks are implemented

## Test Fixtures

Shared fixtures are defined in `conftest.py`. Common fixtures include:

- `temp_dir`: Temporary directory for test files
- `temp_repo`: Temporary git repository
- `temp_repo_with_spec`: Temporary repo with spec-kit structure
- `sample_tasks`: Sample TaskInfo list
- `sample_state`: Sample OrchestrationState

See `conftest.py` for complete fixture documentation.
