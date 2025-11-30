# T006 Implementation Summary

## Task: Implement tasks.py

**Status**: ✅ Complete

### Implementation Overview

Created `src/speckit_core/tasks.py` with comprehensive task parsing functionality supporting both standard and extended task formats with DAG markers.

### Key Features

1. **Dual Format Support**
   - Standard: `- [ ] [T001] [P] [US1] Description`
   - Extended: `- [ ] [T001] [P] [US1] [deps:T000,T001] Description`

2. **Marker Parsing**
   - Task ID: `[T###]` (required)
   - Parallelizable: `[P]` (optional)
   - User Story: `[US#]` (optional)
   - Dependencies: `[deps:T001,T002]` (optional)
   - Checkbox: `[ ]` or `[x]` (required)

3. **File Path Extraction**
   - Extracts file paths in backticks from descriptions
   - Example: `` `src/models/User.ts` ``

4. **Backward Compatibility**
   - Tasks without `[deps:]` marker work correctly
   - Handles both old and new formats seamlessly

### Files Created/Modified

- `src/speckit_core/tasks.py` - Main implementation
- `tests/unit/speckit_core/test_tasks.py` - Comprehensive test suite
- `scripts/validate_t006.py` - Validation script

### Acceptance Criteria Status

- [x] **AC1**: Parses standard format: `- [ ] [T001] [P] [US1] Description`
- [x] **AC2**: Parses extended format: `- [ ] [T001] [P] [US1] [deps:T000] Description`
- [x] **AC3**: Handles completed tasks: `- [x] [T001] ...`
- [x] **AC4**: Handles tasks without optional markers
- [x] **AC5**: Returns empty list for invalid/empty files
- [x] **AC6**: Extracts file paths from description if present

### Implementation Details

#### parse_task_line(line: str) -> Optional[TaskInfo]

Parses a single task line using regex patterns:

```python
TASK_LINE_PATTERN = re.compile(
    r"^-\s+\[([x\sX])\]\s+"  # Checkbox
    r"\[([T]\d{3})\]\s+"      # Task ID
    r"(?:\[P\]\s+)?"          # Optional [P]
    r"(?:\[US\d+\]\s+)?"      # Optional [US#]
    r"(?:\[deps:([^\]]*)\]\s+)?"  # Optional [deps:...]
    r"(.+)$",                 # Description
    re.IGNORECASE
)
```

**Features**:
- Case-insensitive parsing
- Whitespace tolerance
- Bold text removal from descriptions
- File path extraction using backtick pattern

#### parse_tasks_file(path: Path) -> list[TaskInfo]

Parses entire tasks.md file:

- Single-read for performance
- UTF-8 encoding support
- Line-by-line parsing
- Preserves task order from file

**Error Handling**:
- Raises `FileNotFoundError` for missing files
- Returns empty list for files with no tasks
- Graceful handling of invalid lines (skips them)

### Testing

Created comprehensive test suite with 30+ test cases covering:

- All marker combinations
- Edge cases (Unicode, long lines, special chars)
- Backward compatibility
- File I/O operations
- Real-world task parsing

**Run tests**:
```bash
python scripts/validate_t006.py  # Quick validation
pytest tests/unit/speckit_core/test_tasks.py -v  # Full test suite
```

### Code Quality

- ✅ Full type hints on all functions
- ✅ Comprehensive docstrings with examples
- ✅ Follows code-quality.instructions.md
- ✅ Follows testing.instructions.md (AAA pattern)
- ✅ Efficient regex-based parsing
- ✅ Single-pass file reading

### Performance Characteristics

- **parse_task_line**: O(1) - regex match + extraction
- **parse_tasks_file**: O(n) - single file read, line-by-line parse
- **Memory**: Minimal - only stores TaskInfo objects, not full content

### Dependencies

Task T006 depends on:
- T003 ✅ (speckit_core package structure)
- T005 ✅ (TaskInfo model)

### Next Steps

With T006 complete, the following tasks are now unblocked:
- **T007**: Implement config.py (depends on T003, T005)
- **T013**: Implement DAG engine core (depends on T006, T010)
- **T022**: Implement skf dag command (depends on T004, T006, T016)

### Usage Example

```python
from pathlib import Path
from speckit_core.tasks import parse_task_line, parse_tasks_file

# Parse a single line
line = "- [ ] [T001] [P] [deps:] **Setup project**"
task = parse_task_line(line)
print(f"Task {task.id}: {task.name}")
print(f"Dependencies: {task.dependencies}")
print(f"Parallelizable: {task.parallelizable}")

# Parse entire file
tasks = parse_tasks_file(Path("specs/my-feature/tasks.md"))
print(f"Found {len(tasks)} tasks")

for task in tasks:
    if task.completed:
        print(f"✓ {task.id}: {task.name}")
    else:
        print(f"○ {task.id}: {task.name}")
```

### Validation

Run the validation script to verify all acceptance criteria:

```bash
chmod +x scripts/validate_t006.py
python scripts/validate_t006.py
```

Expected output:
```
✓ AC1: Standard format parsing works
✓ AC2: Extended format with dependencies works
✓ AC3: Completed task parsing works
✓ AC4: Tasks without optional markers work
✓ AC5: Empty file returns empty list
✓ AC6: File path extraction works
✓ Real file test: Parsed 43 tasks from tasks.md

============================================================
✅ ALL ACCEPTANCE CRITERIA PASSED
============================================================
```

---

**Task T006 is complete and ready for review.**
