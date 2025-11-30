---
name: Verify Task Completion
description: Verify that a completed task meets all acceptance criteria.
agent: SpecKitFlow Implementation Agent
---

# Verify Task Completion

@speckit-flow Please verify task completion.

## Task to Verify

{{input}}

## Verification Steps

1. **Read** the task definition from `specs/speckit-flow/tasks.md`
2. **Check** each acceptance criterion (AC) checkbox
3. **Test** the implementation meets each criterion
4. **Report** verification results:
   - ✓ Criteria that pass
   - ✗ Criteria that fail (with explanation)
   - Recommendations for any fixes needed

If all criteria pass, confirm the task can be marked complete.
