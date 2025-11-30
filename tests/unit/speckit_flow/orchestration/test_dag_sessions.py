"""
Unit tests for DAG session assignment (T015).
"""

import pytest

from speckit_core.models import TaskInfo
from speckit_flow.orchestration.dag_engine import DAGEngine


class TestAssignSessions:
    """Tests for DAGEngine.assign_sessions() method."""
    
    def test_raises_error_for_invalid_num_sessions(self):
        """Raises ValueError if num_sessions < 1."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Task", dependencies=[])]
        engine = DAGEngine(tasks)
        
        # Act & Assert
        with pytest.raises(ValueError, match="num_sessions must be >= 1"):
            engine.assign_sessions(0)
        
        with pytest.raises(ValueError, match="num_sessions must be >= 1"):
            engine.assign_sessions(-1)
    
    def test_single_session_assigns_all_to_session_0(self):
        """All tasks assigned to session 0 when num_sessions=1."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
            TaskInfo(id="T003", name="C", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        engine.assign_sessions(1)
        
        # Assert
        assert engine.get_task("T001").session == 0
        assert engine.get_task("T002").session == 0
        assert engine.get_task("T003").session == 0
    
    def test_tasks_in_different_phases_can_be_in_different_sessions(self):
        """Tasks in different phases (sequential dependency) can be on different sessions."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[], parallelizable=False),
            TaskInfo(id="T002", name="Build", dependencies=["T001"], parallelizable=False),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        engine.assign_sessions(3)
        
        # Assert - Each task is in its own phase (single-task phases go to session 0)
        assert engine.get_task("T001").session == 0
        assert engine.get_task("T002").session == 0
    
    def test_single_task_in_phase_assigned_to_session_0(self):
        """Single task in a phase goes to session 0."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Only", dependencies=[]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        engine.assign_sessions(3)
        
        # Assert
        assert engine.get_task("T001").session == 0
    
    def test_tasks_in_same_phase_distributed_round_robin(self):
        """Tasks in same phase (no dependencies on each other) distributed round-robin."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Root", dependencies=[]),
            TaskInfo(id="T002", name="A", dependencies=["T001"]),
            TaskInfo(id="T003", name="B", dependencies=["T001"]),
            TaskInfo(id="T004", name="C", dependencies=["T001"]),
            TaskInfo(id="T005", name="D", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        engine.assign_sessions(2)
        
        # Assert
        # T001 is single task in phase 0
        assert engine.get_task("T001").session == 0
        
        # T002-T005 are in same phase (all depend on T001 only), distributed 0, 1, 0, 1
        # (sorted order: T002, T003, T004, T005)
        assert engine.get_task("T002").session == 0
        assert engine.get_task("T003").session == 1
        assert engine.get_task("T004").session == 0
        assert engine.get_task("T005").session == 1
    
    def test_even_distribution_across_sessions(self):
        """Tasks in same phase distributed evenly across available sessions."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="A", dependencies=["T001"]),
            TaskInfo(id="T003", name="B", dependencies=["T001"]),
            TaskInfo(id="T004", name="C", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        engine.assign_sessions(3)
        
        # Assert
        # T001 to session 0 (single task in phase)
        assert engine.get_task("T001").session == 0
        
        # T002, T003, T004 distributed to sessions 0, 1, 2
        assert engine.get_task("T002").session == 0
        assert engine.get_task("T003").session == 1
        assert engine.get_task("T004").session == 2
    
    def test_no_task_assigned_to_multiple_sessions(self):
        """Each task assigned to exactly one session."""
        # Arrange
        tasks = [
            TaskInfo(id=f"T{i:03d}", name=f"Task {i}", dependencies=[])
            for i in range(1, 11)
        ]
        engine = DAGEngine(tasks)
        
        # Act
        engine.assign_sessions(3)
        
        # Assert
        sessions = [engine.get_task(f"T{i:03d}").session for i in range(1, 11)]
        assert all(s is not None for s in sessions)
        assert len(sessions) == 10  # Each task has a session
    
    def test_tasks_in_same_phase_distributed_regardless_of_parallel_flag(self):
        """Tasks in same phase distributed across sessions (parallelizable flag is informational)."""
        # Arrange - All tasks depend on T001, so T002 and T003 are in same phase
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="Parallel", dependencies=["T001"], parallelizable=True),
            TaskInfo(id="T003", name="Sequential", dependencies=["T001"], parallelizable=False),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        engine.assign_sessions(3)
        
        # Assert
        # T001 in phase 0 (single task)
        assert engine.get_task("T001").session == 0
        # T002 and T003 in phase 1 (both depend only on T001), distributed across sessions
        assert engine.get_task("T002").session == 0
        assert engine.get_task("T003").session == 1


class TestGetSessionTasks:
    """Tests for DAGEngine.get_session_tasks() method."""
    
    def test_returns_empty_for_session_with_no_tasks(self):
        """Returns empty list for session with no assigned tasks."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Task", dependencies=[]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(3)
        
        # Act
        session_1_tasks = engine.get_session_tasks(1)
        session_2_tasks = engine.get_session_tasks(2)
        
        # Assert
        assert session_1_tasks == []
        assert session_2_tasks == []
    
    def test_returns_tasks_for_assigned_session(self):
        """Returns all tasks assigned to specified session."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Root", dependencies=[]),
            TaskInfo(id="T002", name="A", dependencies=["T001"]),
            TaskInfo(id="T003", name="B", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(2)
        
        # Act
        session_0_tasks = engine.get_session_tasks(0)
        session_1_tasks = engine.get_session_tasks(1)
        
        # Assert
        assert len(session_0_tasks) == 2  # T001 + T002
        assert len(session_1_tasks) == 1  # T003
        
        session_0_ids = [t.id for t in session_0_tasks]
        assert "T001" in session_0_ids
        assert "T002" in session_0_ids
        
        assert session_1_tasks[0].id == "T003"
    
    def test_tasks_ordered_by_dependencies(self):
        """Tasks returned in topological order (deps before dependents)."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Root", dependencies=[]),
            TaskInfo(id="T002", name="A", dependencies=["T001"]),
            TaskInfo(id="T003", name="B", dependencies=["T002"]),
        ]
        engine = DAGEngine(tasks)
        # Manually assign all to session 0
        for task in tasks:
            task.session = 0
        
        # Act
        session_tasks = engine.get_session_tasks(0)
        
        # Assert
        task_ids = [t.id for t in session_tasks]
        assert task_ids == ["T001", "T002", "T003"]
    
    def test_multiple_independent_tasks_in_session(self):
        """Multiple independent tasks in same session."""
        # Arrange - All tasks are in same phase (no dependencies)
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=[]),
            TaskInfo(id="T003", name="C", dependencies=[]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        session_tasks = engine.get_session_tasks(0)
        
        # Assert
        assert len(session_tasks) == 3
        task_ids = [t.id for t in session_tasks]
        assert set(task_ids) == {"T001", "T002", "T003"}
