# Task Format Fix - Testing Checklist

This document provides test cases to verify that the task format fix is working correctly across different scenarios.

## Test Environment Setup

```bash
# Ensure you have both tools installed
uv tool install specify-cli --from git+https://github.com/dscv103/spec-kit-flow.git
uv tool install speckit-flow --from git+https://github.com/dscv103/spec-kit-flow.git

# Create test project
mkdir test-task-format
cd test-task-format
specify init . --ai copilot --force
```

## Test Case 1: New Project with /speckit.tasks

**Purpose**: Verify that newly generated tasks.md files work with skf dag

**Steps**:
1. Create a minimal spec and plan
2. Run `/speckit.tasks` to generate tasks.md
3. Verify format is correct
4. Run `skf dag --visualize`

**Expected Results**:
- [ ] tasks.md contains task IDs in brackets: `[T001]`, `[T002]`, etc.
- [ ] All task IDs have exactly 3 digits
- [ ] `skf dag --visualize` parses successfully
- [ ] No "Warning: No tasks found" error

**Test Script**:
```bash
# In your AI agent (e.g., Claude, Copilot):
# 1. Create spec and plan first
/speckit.specify Build a simple todo app with tasks and users
/speckit.plan Use Python FastAPI, SQLite database
/speckit.tasks

# 2. Verify format
grep -E "^\- \[ \] \[T[0-9]{3}\]" specs/*/tasks.md

# 3. Test parsing
skf dag --visualize
```

## Test Case 2: Migration from Old Format

**Purpose**: Verify that the migration script converts old format to new format

**Steps**:
1. Create a tasks.md with old format (T001 without brackets)
2. Run migration command
3. Verify conversion
4. Test with skf dag

**Test File** (`specs/001-test/tasks.md`):
```markdown
# Tasks

## Phase 1: Setup
- [ ] T001 Create project structure
- [ ] T002 [P] Initialize database
- [ ] T003 [P] [US1] Create User model in src/models/user.py

## Phase 2: Implementation
- [ ] T004 [US1] Implement UserService in src/services/user_service.py
```

**Migration Command**:
```bash
sed -i -E 's/^(- \[[x ]\] )T([0-9]{3})\b/\1[T\2]/' specs/001-test/tasks.md
```

**Verification**:
```bash
# Check format after migration
grep -E "^\- \[ \] \[T[0-9]{3}\]" specs/001-test/tasks.md

# Should show:
# - [ ] [T001] Create project structure
# - [ ] [T002] [P] Initialize database
# - [ ] [T003] [P] [US1] Create User model in src/models/user.py
# - [ ] [T004] [US1] Implement UserService in src/services/user_service.py
```

**Expected Results**:
- [ ] All T### converted to [T###]
- [ ] Other markers ([P], [US1]) preserved
- [ ] Descriptions unchanged
- [ ] `skf dag --visualize` works

## Test Case 3: Error Message Quality

**Purpose**: Verify that helpful error messages are shown for format issues

**Steps**:
1. Create tasks.md with intentional format errors
2. Run skf dag
3. Verify error message provides guidance

**Test Files**:

**Test 3a** - Missing brackets:
```markdown
- [ ] T001 Create project
```

**Test 3b** - Wrong digit count:
```markdown
- [ ] [T1] Create project
```

**Test 3c** - Missing checkbox:
```markdown
[T001] Create project
```

**Expected Results**:
- [ ] Error shows: "Task IDs must be in brackets: [T001] not T001"
- [ ] Error shows: "Task IDs must have exactly 3 digits"
- [ ] Error shows migration command: `sed -i -E ...`
- [ ] Error references migration guide: `docs/task-format-migration.md`

**Test Script**:
```bash
# Test 3a
echo "- [ ] T001 Create project" > specs/001-test/tasks.md
skf dag 2>&1 | grep "must be in brackets"

# Test 3b
echo "- [ ] [T1] Create project" > specs/001-test/tasks.md
skf dag 2>&1 | grep "exactly 3 digits"

# Test 3c
echo "[T001] Create project" > specs/001-test/tasks.md
skf dag 2>&1 | grep "checkbox"
```

## Test Case 4: Complex Task File

**Purpose**: Verify parser handles all supported markers correctly

**Test File** (`specs/001-complex/tasks.md`):
```markdown
# Tasks

## Phase 1: Setup
- [ ] [T001] [deps:] Initialize project structure
- [ ] [T002] [P] [deps:T001] Setup database
- [ ] [T003] [P] [deps:T001] Configure auth

## Phase 2: User Story 1
- [ ] [T004] [P] [US1] [deps:T002] Create User model in src/models/user.py
- [ ] [T005] [P] [US1] [deps:T002] Create Task model in src/models/task.py
- [ ] [T006] [US1] [deps:T004,T005] Implement UserService in src/services/user_service.py

## Phase 3: User Story 2
- [x] [T007] [P] [US2] [deps:T003] Add authentication endpoint
- [ ] [T008] [US2] [deps:T007] Add authorization middleware
```

**Expected Results**:
- [ ] Parses all 8 tasks
- [ ] Recognizes 3 phases
- [ ] Identifies parallel tasks: T002, T003, T004, T005, T007
- [ ] Recognizes completed task: T007
- [ ] Maps dependencies correctly
- [ ] Maps user stories correctly: US1 (T004-T006), US2 (T007-T008)

**Test Script**:
```bash
skf dag --visualize

# Should show DAG structure with:
# - 3 phases
# - Dependencies as edges
# - [P] markers visible
# - Completed task marked differently
```

## Test Case 5: SpecKitFlow Full Workflow

**Purpose**: End-to-end test from generation to orchestration

**Steps**:
1. Generate tasks with `/speckit.tasks`
2. Initialize SpecKitFlow
3. Generate DAG
4. Run init (dry run)

**Expected Results**:
- [ ] No format errors at any step
- [ ] DAG visualization shows correct structure
- [ ] Session assignment works
- [ ] No parser errors

**Test Script**:
```bash
# 1. Generate tasks (in AI agent)
/speckit.tasks

# 2. Initialize SpecKitFlow
skf init --sessions 3 --agent copilot

# 3. Generate and visualize DAG
skf dag --visualize

# 4. Check status (before run)
skf status

# Should see:
# ✓ No format errors
# ✓ Tasks parsed successfully
# ✓ DAG structure displayed
# ✓ Sessions configured
```

## Test Case 6: Template Consistency

**Purpose**: Verify all examples in templates use correct format

**Steps**:
1. Check templates/tasks-template.md
2. Check templates/commands/tasks.md
3. Verify all examples use [T###] format

**Expected Results**:
- [ ] All task IDs in brackets: `[T###]`
- [ ] No examples with old format: `T###`
- [ ] Format specification is clear
- [ ] Examples match specification

**Test Script**:
```bash
# Check for old format (should find NONE)
grep -n "^\- \[ \] T[0-9]" templates/tasks-template.md
grep -n "^\- \[ \] T[0-9]" templates/commands/tasks.md

# Check for new format (should find ALL)
grep -n "^\- \[ \] \[T[0-9]" templates/tasks-template.md
```

## Test Case 7: Documentation Accuracy

**Purpose**: Verify documentation reflects correct format

**Steps**:
1. Check README.md format examples
2. Check migration guide
3. Check quick reference

**Expected Results**:
- [ ] README shows bracketed format: `[T###]`
- [ ] Migration guide explains format correctly
- [ ] Quick reference card matches parser requirements
- [ ] All examples consistent

**Test Script**:
```bash
# Check README
grep -A 5 "Task Format Extensions" README.md | grep "\[T"

# Check migration guide exists
test -f docs/task-format-migration.md && echo "✓ Migration guide exists"

# Check quick reference exists
test -f docs/task-format-quick-reference.md && echo "✓ Quick reference exists"
```

## Regression Tests

After any future changes, re-run all tests to ensure:
- [ ] Parser still accepts bracketed format: `[T###]`
- [ ] Error messages still helpful
- [ ] Migration script still works
- [ ] Templates still generate correct format
- [ ] Documentation still accurate

## Test Results Template

Record test results here:

```
Date: ____________________
Tester: __________________
Version: _________________

Test Case 1 (New Project):         [ ] PASS [ ] FAIL
Test Case 2 (Migration):           [ ] PASS [ ] FAIL
Test Case 3 (Error Messages):      [ ] PASS [ ] FAIL
Test Case 4 (Complex File):        [ ] PASS [ ] FAIL
Test Case 5 (Full Workflow):       [ ] PASS [ ] FAIL
Test Case 6 (Template Consistency): [ ] PASS [ ] FAIL
Test Case 7 (Documentation):       [ ] PASS [ ] FAIL

Notes:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

## Troubleshooting

If tests fail:

1. **Parser errors**: Check regex in `src/speckit_core/tasks.py`
2. **Template issues**: Verify all examples in templates use `[T###]`
3. **Migration fails**: Test sed command on sample file
4. **Error messages unclear**: Update messages in `src/speckit_flow/__init__.py`
5. **Documentation mismatch**: Update affected docs

## Success Criteria

All tests pass when:
- ✅ New projects generate correct format automatically
- ✅ Old format can be migrated successfully
- ✅ Error messages guide users to fix issues
- ✅ Complex files parse correctly
- ✅ Full workflow completes without format errors
- ✅ Templates and docs are consistent
- ✅ No regressions in functionality
