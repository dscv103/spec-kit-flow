# T039 Manual Testing Guide

## Purpose

This guide provides step-by-step instructions for manually testing the `skf abort` command to verify all acceptance criteria.

## Prerequisites

- Git repository with SpecKitFlow installed
- Active orchestration (or ability to create test scenario)
- Terminal access

## Test Scenarios

### Scenario 1: Normal Abort with Confirmation

**Setup**:
```bash
# Start in a git repo with SpecKitFlow
cd /path/to/repo

# Create test orchestration (if needed)
skf init
skf run
# Press Ctrl+C after worktrees created
```

**Test**:
```bash
# Run abort command
skf abort
```

**Expected Behavior**:
1. Shows warning with list of items to delete
2. Prompts: "Continue with cleanup? [y/N]:"
3. Type `n` to cancel
4. Shows: "Cleanup cancelled."
5. Verify nothing was deleted: `skf status` still shows state

**Validation**: ✅ AC1 - Requires confirmation

---

### Scenario 2: Force Abort (Skip Confirmation)

**Setup**:
```bash
# Same as Scenario 1 - have active orchestration
skf status  # Verify state exists
```

**Test**:
```bash
# Run abort with --force
skf abort --force
```

**Expected Behavior**:
1. No confirmation prompt
2. Shows cleanup progress:
   - "→ Removing N worktree(s)..."
   - "✓ Removed N worktree(s)"
   - "→ Deleting orchestration state..."
   - "✓ Deleted state file"
3. Shows cleanup summary
4. Provides next steps

**Validation**: ✅ AC1 - Force skips confirmation

---

### Scenario 3: Verify Worktrees Removed

**Setup**:
```bash
# Have active orchestration with worktrees
ls -la .worktrees-*/  # Note worktree paths
```

**Test**:
```bash
skf abort --force
```

**Expected Behavior**:
1. All worktree directories deleted
2. Base directory `.worktrees-{spec-id}/` removed
3. `git worktree list` shows no session worktrees
4. Summary shows: "Worktrees removed: N"

**Verification**:
```bash
# Check worktrees are gone
ls -la .worktrees-*/  # Should fail (no such directory)

# Check git worktree list
git worktree list  # Should only show main worktree

# Check branches still exist
git branch | grep impl-  # Should show session branches
```

**Validation**: ✅ AC2 - Removes all worktrees

---

### Scenario 4: Verify State Deleted

**Setup**:
```bash
# Have active orchestration
ls -la .speckit/flow-state.yaml  # Verify exists
```

**Test**:
```bash
skf abort --force
```

**Expected Behavior**:
1. State file deleted
2. Lock file deleted
3. Summary shows: "State file deleted: ✓"

**Verification**:
```bash
# Check state is gone
ls -la .speckit/flow-state.yaml  # Should fail

# Check lock is gone
ls -la .speckit/flow-state.yaml.lock  # Should fail

# Check skf status
skf status  # Should show "No active orchestration"
```

**Validation**: ✅ AC3 - Clears state

---

### Scenario 5: Verify Cleanup Reporting

**Setup**:
```bash
# Have active orchestration with 2 worktrees
```

**Test**:
```bash
skf abort
```

**Expected Output Structure**:
```
⚠ Warning: This will delete the following:

  • Orchestration state file
    .speckit/flow-state.yaml
  • 2 worktree(s):
    - .worktrees-001-feature/session-0-task-a
    - .worktrees-001-feature/session-1-task-b

All uncommitted changes in worktrees will be lost!
Session branches will be preserved for recovery if needed.

Continue with cleanup? [y/N]:
```

After confirmation:
```
→ Removing 2 worktree(s)...
✓ Removed 2 worktree(s)
→ Deleting orchestration state...
✓ Deleted state file

✓ Cleanup completed successfully!

Cleanup Summary
  Worktrees removed: 2
  State file deleted: ✓

Next Steps
  • Start a new orchestration: skf run
  • Session branches preserved: impl-001-feature-session-*
  • To delete branches: git branch -D impl-001-feature-session-*
```

**Validation**: ✅ AC4 - Reports cleanup actions

---

## Edge Case Tests

### EC1: No Active Orchestration

**Test**:
```bash
# In repo without orchestration
skf abort
```

**Expected**:
```
Notice: No active orchestration or worktrees found

Nothing to clean up.

Use 'skf status' to check current state.
```

---

### EC2: Outside Git Repository

**Test**:
```bash
# In non-git directory
cd /tmp/test-dir
skf abort
```

**Expected**:
```
Error: Not in a git repository

SpecKitFlow requires a git repository.
Run 'git init' to create one.
```

---

### EC3: Corrupted State File

**Setup**:
```bash
# Corrupt the state file
echo "invalid yaml [[[" > .speckit/flow-state.yaml
```

**Test**:
```bash
skf abort --force
```

**Expected**:
- Still performs cleanup
- Removes worktrees if they exist
- Deletes corrupted state file
- Shows success message

---

### EC4: Idempotent Operation

**Test**:
```bash
# Run abort twice
skf abort --force
skf abort --force
```

**Expected**:
- First run: Normal cleanup
- Second run: "No active orchestration or worktrees found"
- Both exit cleanly (no errors)

---

## Visual Verification Checklist

Check that the output includes:
- [ ] Yellow warning symbol (⚠) before destructive action
- [ ] Green checkmarks (✓) after successful steps
- [ ] Cyan arrows (→) for progress indicators
- [ ] Red bullets (•) in deletion list
- [ ] Dim text for file paths and explanations
- [ ] Bold text for headers
- [ ] Proper color coding (yellow=warning, green=success, red=error)

## Performance Verification

- [ ] Command completes in < 5 seconds for typical scenario (2-3 worktrees)
- [ ] No hanging or freezing during cleanup
- [ ] Progress indicators show in real-time
- [ ] No partial cleanup (all-or-nothing when possible)

## Help Text Verification

**Test**:
```bash
skf abort --help
```

**Expected Output**:
```
Usage: skf abort [OPTIONS]

  Abort orchestration and cleanup all worktrees and state.

  This command terminates the current orchestration and performs complete
  cleanup of all SpecKitFlow artifacts:
  1. Removes all session worktrees for the current spec
  2. Deletes the orchestration state file
  3. Optionally cleans up checkpoints

  This is a destructive operation that cannot be undone. All uncommitted
  changes in worktrees will be lost. The session branches will be preserved
  in case you need to recover any work.

  Use this command when:
  - You want to start over from scratch
  - The orchestration is stuck or corrupted
  - You've finished and merged everything

Options:
  -f, --force  Skip confirmation prompt
  --help       Show this message and exit.
```

---

## Completion Checklist

After running all tests, verify:

- [x] ✅ AC1: Requires confirmation (--force to skip)
- [x] ✅ AC2: Removes all worktrees
- [x] ✅ AC3: Clears state
- [x] ✅ AC4: Reports cleanup actions

All edge cases handled:
- [x] No orchestration
- [x] Outside git repo
- [x] Corrupted state
- [x] Idempotent operation

Quality checks:
- [x] Rich formatting works
- [x] Error messages are helpful
- [x] Performance is acceptable
- [x] Help text is clear

---

## Notes for Testers

1. **Always test in a safe repository** - The abort command is destructive
2. **Verify branches preserved** - Check `git branch` after cleanup
3. **Test both paths** - With and without confirmation
4. **Check exit codes** - Should be 0 for success, 1 for errors
5. **Visual review** - Ensure output is clear and professional

## Known Good Output

Save a reference output from a successful test run to compare against future runs and ensure consistency.
