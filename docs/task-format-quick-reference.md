# Task Format Quick Reference for AI Agents

## Critical Format Requirements

When generating tasks.md files, **ALWAYS** use this exact format:

```markdown
- [ ] [T###] [P?] [US#?] [deps:T###,T###?] Description with file paths
```

## Components (in order)

1. **Checkbox**: `- [ ]` or `- [x]`
   - Space after dash
   - Space between brackets for unchecked
   - Single `x` for checked

2. **Task ID**: `[T###]` 
   - ⚠️ **MUST have brackets**
   - ⚠️ **MUST have exactly 3 digits**
   - Capital T
   - Leading zeros: T001, T023, T142

3. **[P] marker**: (optional)
   - Indicates parallelizable
   - Different files, no dependencies

4. **[US#] marker**: (optional)
   - User story reference
   - Format: [US1], [US2], etc.

5. **[deps:...] marker**: (optional)
   - Dependencies on other tasks
   - Format: [deps:T001,T002]
   - Empty for no deps: [deps:]

6. **Description**: 
   - Clear action statement
   - Include file paths
   - Example: `Create User model in src/models/user.py`

## Valid Examples ✅

```markdown
- [ ] [T001] Create project structure per implementation plan
- [ ] [T002] [P] Initialize database schema in src/db/schema.sql
- [ ] [T005] [P] [US1] Create User model in src/models/user.py
- [ ] [T010] [US1] [deps:T005] Implement UserService in src/services/user_service.py
- [x] [T001] [deps:] Setup project structure (completed task)
```

## Invalid Examples ❌

```markdown
❌ - [ ] T001 Create project            # Missing brackets around T001
❌ - [ ] [T1] Create project             # Only 1 digit (need 3)
❌ - [ ] [T0001] Create project          # 4 digits (need exactly 3)
❌ [T001] Create project                 # Missing checkbox
❌ T001 [P] Create project               # Missing both checkbox and brackets
❌ - [ ] [T001] Create project           # OK but missing file path in description
```

## Template Pattern

Use this pattern when generating tasks:

```markdown
## Phase 1: Setup

- [ ] [T001] Initialize project with [tech stack]
- [ ] [T002] [P] Configure development environment
- [ ] [T003] [P] Setup testing framework

## Phase 2: User Story 1 - [Title]

### Implementation

- [ ] [T004] [P] [US1] Create [Entity] model in src/models/[entity].py
- [ ] [T005] [US1] [deps:T004] Implement [Service] in src/services/[service].py
- [ ] [T006] [US1] [deps:T005] Add [Endpoint] in src/api/[endpoint].py
```

## Task ID Sequencing

- Start at T001
- Increment sequentially: T001, T002, T003...
- Use leading zeros: T001, T023, T142
- Order by execution sequence (consider dependencies)

## Dependencies Format

```markdown
- [ ] [T001] [deps:] No dependencies (empty deps)
- [ ] [T002] [deps:T001] Depends on T001
- [ ] [T005] [deps:T001,T003] Depends on T001 AND T003
```

## Common Mistakes to Avoid

1. **Forgetting brackets**: `T001` → Should be `[T001]`
2. **Wrong digit count**: `[T1]` or `[T0001]` → Should be `[T001]`
3. **Missing checkbox**: `[T001] Task` → Should be `- [ ] [T001] Task`
4. **Missing file paths**: Add specific file paths to descriptions
5. **Inconsistent format**: Pick one format and use consistently

## Validation Checklist

Before outputting tasks.md, verify:

- [ ] All task IDs use brackets: `[T###]`
- [ ] All task IDs have exactly 3 digits
- [ ] All lines start with checkbox: `- [ ]` or `- [x]`
- [ ] Sequential numbering (no gaps)
- [ ] File paths included in descriptions
- [ ] Dependencies reference valid task IDs
- [ ] [P] markers only on truly parallelizable tasks

## Parser Compatibility

The `skf dag` parser requires this exact format. Format errors will cause:
```
Warning: No tasks found in tasks.md
```

## Quick Test

After generating tasks.md, user can verify with:
```bash
skf dag --visualize
```

Should see:
```
✓ Parsed X tasks from tasks.md
```

If parser fails, check:
1. Brackets around all task IDs
2. Exactly 3 digits per ID
3. Checkbox at start of each line

## Reference Documents

- Full specification: `templates/tasks-template.md`
- Migration guide: `docs/task-format-migration.md`
- Command instructions: `templates/commands/tasks.md`
