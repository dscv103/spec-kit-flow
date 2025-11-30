# Task Format Migration Guide

## Overview

This guide helps you migrate existing `tasks.md` files to be compatible with the `skf dag` parser.

## The Issue

The `skf dag` parser requires task IDs to be enclosed in brackets with exactly 3 digits: `[T###]`

**Parser expects:**
```markdown
- [ ] [T001] [deps:] Setup project structure
- [ ] [T002] [P] [deps:T001] Implement feature
```

**Old format (incompatible):**
```markdown
- [ ] T001 Setup project structure
- [ ] T002 [P] Implement feature
```

## Quick Fix: Automated Migration

Use this sed command to fix task IDs in your tasks.md:

```bash
# Backup first
cp specs/your-feature/tasks.md specs/your-feature/tasks.md.backup

# Fix task IDs (add brackets)
sed -i -E 's/^(- \[[x ]\] )T([0-9]{3})\b/\1[T\2]/' specs/your-feature/tasks.md
```

**What this does:**
- Finds lines starting with `- [ ]` or `- [x]` followed by `T###`
- Wraps the task ID in brackets: `T001` → `[T001]`
- Preserves all other content (descriptions, markers, etc.)

## Manual Migration

If you prefer manual editing, follow this pattern:

### Before:
```markdown
- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Python project with FastAPI dependencies
- [ ] T003 [P] Configure linting and formatting tools
- [ ] T010 [P] [US1] Contract test for user endpoint
```

### After:
```markdown
- [ ] [T001] Create project structure per implementation plan
- [ ] [T002] Initialize Python project with FastAPI dependencies
- [ ] [T003] [P] Configure linting and formatting tools
- [ ] [T010] [P] [US1] Contract test for user endpoint
```

**Changes:**
- `T001` → `[T001]`
- `T002` → `[T002]`
- `T003 [P]` → `[T003] [P]`
- `T010 [P] [US1]` → `[T010] [P] [US1]`

## Verification

After migration, verify the format is correct:

```bash
# Test the parser
skf dag --visualize
```

If successful, you should see:
```
✓ Parsed X tasks from tasks.md
```

If you still see `Warning: No tasks found`, check:
1. Task IDs have brackets: `[T###]`
2. Task IDs have exactly 3 digits: `[T001]` not `[T1]`
3. Lines start with markdown checkbox: `- [ ]`

## Using `/speckit.tasks` (Recommended)

The easiest approach is to regenerate tasks using the updated template:

```bash
# In your AI agent (Claude, Copilot, etc.)
/speckit.tasks
```

This will generate tasks.md with the correct format automatically.

## Format Specification

### Required Format

```
- [ ] [T###] [P?] [US#?] [deps:T###,T###?] Description with file paths
```

**Components:**
- `- [ ]` or `- [x]` - Markdown checkbox (required)
- `[T###]` - Task ID with brackets and 3 digits (required)
- `[P]` - Parallelizable marker (optional)
- `[US#]` - User story reference (optional)
- `[deps:...]` - Dependencies on other tasks (optional)
- Description with file paths

### Valid Examples

```markdown
- [ ] [T001] Setup project structure
- [ ] [T002] [P] Initialize database
- [ ] [T005] [P] [US1] Create User model in src/models/user.py
- [ ] [T010] [US1] [deps:T005] Implement UserService in src/services/user_service.py
- [x] [T001] [deps:] Setup project structure (completed)
```

### Invalid Examples

```markdown
- [ ] T001 Setup project structure          # Missing brackets
- [ ] [T1] Setup project structure          # Only 1 digit
- [ ] [T0001] Setup project structure       # 4 digits
- [T001] Setup project structure            # Missing checkbox
- T001 [P] Setup project structure          # Missing checkbox and brackets
```

## Troubleshooting

### Error: "No tasks found in tasks.md"

**Cause**: Task format doesn't match parser expectations.

**Solution**:
1. Verify brackets around task IDs: `[T###]`
2. Ensure exactly 3 digits: `[T001]` not `[T1]`
3. Check checkbox format: `- [ ]` with space between brackets

### Error: "Invalid task ID format"

**Cause**: Task IDs not following `T###` pattern.

**Solution**:
- Use capital T: `[T001]` not `[t001]`
- Use exactly 3 digits: `[T001]` not `[T1]` or `[T0001]`
- No extra characters: `[T001]` not `[T001A]`

### Error: "Unexpected error: 1"

**Cause**: Python exception in parser (often format-related).

**Solution**:
1. Check for special characters in task descriptions
2. Ensure UTF-8 encoding of tasks.md
3. Verify no corrupted lines

## Getting Help

If migration issues persist:

1. **Check the examples** in [templates/tasks-template.md](../templates/tasks-template.md)
2. **Run parser in debug mode**: `skf dag --debug` (if available)
3. **Open an issue**: https://github.com/dscv103/spec-kit-flow/issues

Include:
- Your tasks.md content (or a sample)
- Error message from `skf dag`
- Output of `skf --version`
