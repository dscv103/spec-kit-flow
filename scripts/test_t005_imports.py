#!/usr/bin/env python3
"""Quick import and basic usage test for models.py"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("Testing imports...")
from speckit_core import TaskInfo, FeatureContext, DAGNode, SessionState, TaskStatus, SessionStatus
print("✓ All imports successful")

print("\nTesting TaskInfo creation...")
task = TaskInfo(
    id="T001",
    name="Test task",
    dependencies=[],
    parallelizable=True
)
print(f"✓ Created TaskInfo: {task.id} - {task.name}")

print("\nTesting serialization (Pydantic v2)...")
data = task.model_dump()
print(f"✓ Serialized to dict: {data['id']}")

restored = TaskInfo.model_validate(data)
print(f"✓ Deserialized from dict: {restored.id}")

print("\nTesting FeatureContext...")
ctx = FeatureContext(
    repo_root=Path("/repo"),
    branch="test",
    feature_dir=Path("/repo/specs/test"),
    spec_path=Path("/repo/specs/test/spec.md"),
    plan_path=Path("/repo/specs/test/plan.md"),
    tasks_path=Path("/repo/specs/test/tasks.md"),
)
print(f"✓ Created FeatureContext for branch: {ctx.branch}")

print("\nTesting DAGNode...")
node = DAGNode(
    id="T001",
    name="Setup",
    description="Initialize",
    dependencies=[],
    session=0,
    parallelizable=False,
)
print(f"✓ Created DAGNode: {node.id}")

print("\nTesting SessionState...")
session = SessionState(
    session_id=0,
    worktree_path=".worktrees-001/session-0",
    branch_name="impl-001-session-0",
)
print(f"✓ Created SessionState: {session.session_id}")

print("\nTesting enums...")
assert TaskStatus.pending.value == "pending"
assert SessionStatus.executing.value == "executing"
print("✓ Enums work correctly")

print("\n" + "="*50)
print("✅ ALL BASIC TESTS PASSED")
print("="*50)
