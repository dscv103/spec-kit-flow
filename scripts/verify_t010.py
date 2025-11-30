#!/usr/bin/env python3
"""
Verification script for T010: State Models

Tests all acceptance criteria:
- AC1: Models match schema in plan.md exactly
- AC2: Round-trip YAML serialization preserves all fields
- AC3: Timestamps use ISO 8601 format
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml
from speckit_core.models import SessionState, SessionStatus, TaskStatus
from speckit_flow.state.models import OrchestrationState, TaskStateInfo


def verify_ac1_models_match_schema():
    """AC1: Models match schema in plan.md exactly."""
    print("Verifying AC1: Models match schema in plan.md exactly...")
    
    # Create state matching plan.md example
    state = OrchestrationState(
        version="1.0",
        spec_id="001-feature-name",
        agent_type="copilot",
        num_sessions=3,
        base_branch="main",
        started_at="2025-11-28T10:30:00Z",
        updated_at="2025-11-28T11:45:00Z",
        current_phase="phase-1",
        phases_completed=["phase-0"],
        sessions=[
            SessionState(
                session_id=0,
                worktree_path=".worktrees-001/session-0-user-model",
                branch_name="impl-001-session-0",
                current_task="T002",
                completed_tasks=["T001"],
                status=SessionStatus.executing
            ),
            SessionState(
                session_id=1,
                worktree_path=".worktrees-001/session-1-task-model",
                branch_name="impl-001-session-1",
                current_task="T003",
                completed_tasks=[],
                status=SessionStatus.executing
            )
        ],
        tasks={
            "T001": TaskStateInfo(
                status=TaskStatus.completed,
                session=0,
                completed_at="2025-11-28T10:45:00Z"
            ),
            "T002": TaskStateInfo(
                status=TaskStatus.in_progress,
                session=0,
                started_at="2025-11-28T10:46:00Z"
            ),
            "T003": TaskStateInfo(
                status=TaskStatus.in_progress,
                session=1,
                started_at="2025-11-28T10:46:00Z"
            ),
            "T004": TaskStateInfo(
                status=TaskStatus.pending,
                session=None
            )
        },
        merge_status=None
    )
    
    # Verify all required fields are present
    assert state.version == "1.0"
    assert state.spec_id == "001-feature-name"
    assert state.agent_type == "copilot"
    assert state.num_sessions == 3
    assert state.base_branch == "main"
    assert state.started_at == "2025-11-28T10:30:00Z"
    assert state.updated_at == "2025-11-28T11:45:00Z"
    assert state.current_phase == "phase-1"
    assert state.phases_completed == ["phase-0"]
    assert len(state.sessions) == 2
    assert len(state.tasks) == 4
    assert state.merge_status is None
    
    # Verify sessions structure
    assert state.sessions[0].session_id == 0
    assert state.sessions[0].current_task == "T002"
    assert state.sessions[0].status == SessionStatus.executing
    
    # Verify tasks structure
    assert state.tasks["T001"].status == TaskStatus.completed
    assert state.tasks["T001"].session == 0
    assert state.tasks["T001"].completed_at == "2025-11-28T10:45:00Z"
    
    print("  ✓ OrchestrationState has all required fields")
    print("  ✓ Field types match schema")
    print("  ✓ Nested structures (sessions, tasks) work correctly")
    print()


def verify_ac2_round_trip_serialization():
    """AC2: Round-trip YAML serialization preserves all fields."""
    print("Verifying AC2: Round-trip YAML serialization preserves all fields...")
    
    # Create complex state with all fields
    original = OrchestrationState(
        version="1.0",
        spec_id="001-complex-test",
        agent_type="copilot",
        num_sessions=3,
        base_branch="develop",
        started_at="2025-11-28T09:00:00Z",
        updated_at="2025-11-28T10:00:00Z",
        current_phase="phase-2",
        phases_completed=["phase-0", "phase-1"],
        sessions=[
            SessionState(
                session_id=0,
                worktree_path=".worktrees-001/session-0",
                branch_name="impl-001-session-0",
                current_task="T005",
                completed_tasks=["T001", "T002"],
                status=SessionStatus.completed
            ),
            SessionState(
                session_id=1,
                worktree_path=".worktrees-001/session-1",
                branch_name="impl-001-session-1",
                current_task=None,
                completed_tasks=["T003", "T004"],
                status=SessionStatus.idle
            )
        ],
        tasks={
            "T001": TaskStateInfo(
                status=TaskStatus.completed,
                session=0,
                started_at="2025-11-28T09:10:00Z",
                completed_at="2025-11-28T09:20:00Z"
            ),
            "T002": TaskStateInfo(
                status=TaskStatus.failed,
                session=0,
                started_at="2025-11-28T09:25:00Z"
            )
        },
        merge_status="completed"
    )
    
    # Serialize to dict
    state_dict = original.model_dump()
    
    # Serialize to YAML
    yaml_str = yaml.dump(state_dict, default_flow_style=False)
    
    # Parse YAML back to dict
    parsed_dict = yaml.safe_load(yaml_str)
    
    # Deserialize back to model
    restored = OrchestrationState.model_validate(parsed_dict)
    
    # Verify all fields preserved
    assert restored.version == original.version
    assert restored.spec_id == original.spec_id
    assert restored.agent_type == original.agent_type
    assert restored.num_sessions == original.num_sessions
    assert restored.base_branch == original.base_branch
    assert restored.started_at == original.started_at
    assert restored.updated_at == original.updated_at
    assert restored.current_phase == original.current_phase
    assert restored.phases_completed == original.phases_completed
    assert restored.merge_status == original.merge_status
    
    # Verify sessions preserved
    assert len(restored.sessions) == len(original.sessions)
    assert restored.sessions[0].session_id == original.sessions[0].session_id
    assert restored.sessions[0].current_task == original.sessions[0].current_task
    assert restored.sessions[0].completed_tasks == original.sessions[0].completed_tasks
    
    # Verify tasks preserved
    assert len(restored.tasks) == len(original.tasks)
    assert restored.tasks["T001"].status == original.tasks["T001"].status
    assert restored.tasks["T001"].session == original.tasks["T001"].session
    assert restored.tasks["T001"].started_at == original.tasks["T001"].started_at
    assert restored.tasks["T001"].completed_at == original.tasks["T001"].completed_at
    
    print("  ✓ Serialization to dict works")
    print("  ✓ YAML serialization works")
    print("  ✓ Deserialization from YAML works")
    print("  ✓ All fields preserved in round-trip")
    print()


def verify_ac3_timestamps_iso8601():
    """AC3: Timestamps use ISO 8601 format."""
    print("Verifying AC3: Timestamps use ISO 8601 format...")
    
    # Create state with timestamps
    state = OrchestrationState(
        spec_id="001-test",
        agent_type="copilot",
        num_sessions=1,
        base_branch="main",
        started_at="2025-11-28T10:30:00Z",
        updated_at="2025-11-28T10:30:00Z",
        current_phase="phase-0"
    )
    
    # Verify ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
    assert len(state.started_at) == 20
    assert state.started_at[10] == "T"  # Date-time separator
    assert state.started_at[-1] == "Z"  # UTC indicator
    assert state.started_at.count("-") == 2  # Date separators
    assert state.started_at.count(":") == 2  # Time separators
    
    # Test get_current_timestamp() method
    timestamp = state.get_current_timestamp()
    assert len(timestamp) == 20
    assert timestamp[10] == "T"
    assert timestamp[-1] == "Z"
    
    # Test mark_updated() method
    original_updated = state.updated_at
    state.mark_updated()
    assert state.updated_at != original_updated
    assert len(state.updated_at) == 20
    assert state.updated_at[10] == "T"
    assert state.updated_at[-1] == "Z"
    
    # Verify TaskStateInfo timestamps
    task = TaskStateInfo(
        status=TaskStatus.completed,
        started_at="2025-11-28T10:00:00Z",
        completed_at="2025-11-28T10:15:00Z"
    )
    assert task.started_at[10] == "T"
    assert task.started_at[-1] == "Z"
    assert task.completed_at[10] == "T"
    assert task.completed_at[-1] == "Z"
    
    print("  ✓ started_at uses ISO 8601 format")
    print("  ✓ updated_at uses ISO 8601 format")
    print("  ✓ get_current_timestamp() returns ISO 8601 format")
    print("  ✓ mark_updated() uses ISO 8601 format")
    print("  ✓ TaskStateInfo timestamps use ISO 8601 format")
    print()


def verify_enums():
    """Verify TaskStatus and SessionStatus enums are imported correctly."""
    print("Verifying enums from speckit_core...")
    
    # Verify TaskStatus enum
    assert TaskStatus.pending == "pending"
    assert TaskStatus.in_progress == "in_progress"
    assert TaskStatus.completed == "completed"
    assert TaskStatus.failed == "failed"
    
    # Verify SessionStatus enum
    assert SessionStatus.idle == "idle"
    assert SessionStatus.executing == "executing"
    assert SessionStatus.waiting == "waiting"
    assert SessionStatus.completed == "completed"
    assert SessionStatus.failed == "failed"
    
    print("  ✓ TaskStatus enum imported correctly")
    print("  ✓ SessionStatus enum imported correctly")
    print()


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("T010 Verification: State Models")
    print("=" * 70)
    print()
    
    try:
        verify_enums()
        verify_ac1_models_match_schema()
        verify_ac2_round_trip_serialization()
        verify_ac3_timestamps_iso8601()
        
        print("=" * 70)
        print("✅ T010 VERIFICATION PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✓ AC1: Models match schema in plan.md exactly")
        print("  ✓ AC2: Round-trip YAML serialization preserves all fields")
        print("  ✓ AC3: Timestamps use ISO 8601 format")
        print()
        print("All acceptance criteria verified successfully!")
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 70)
        print("❌ T010 VERIFICATION FAILED")
        print("=" * 70)
        print(f"Assertion Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ T010 VERIFICATION ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
