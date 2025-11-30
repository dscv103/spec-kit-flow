"""
Unit tests for DAG phase generation (T014).
"""

import pytest

from speckit_core.models import TaskInfo
from speckit_flow.orchestration.dag_engine import DAGEngine


class TestGetPhases:
    """Tests for DAGEngine.get_phases() method."""
    
    def test_empty_task_list_returns_empty_phases(self):
        """Empty task list returns empty phase list."""
        # Arrange
        tasks = []
        
        # Act
        engine = DAGEngine(tasks)
        phases = engine.get_phases()
        
        # Assert
        assert phases == []
        assert engine.phase_count == 0
    
    def test_single_task_with_no_deps_in_phase_0(self):
        """Single task with no dependencies appears in phase 0."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        phases = engine.get_phases()
        
        # Assert
        assert len(phases) == 1
        assert phases[0] == ["T001"]
    
    def test_tasks_with_no_deps_all_in_phase_0(self):
        """Multiple tasks with no dependencies all appear in phase 0."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Task A", dependencies=[]),
            TaskInfo(id="T002", name="Task B", dependencies=[]),
            TaskInfo(id="T003", name="Task C", dependencies=[]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        phases = engine.get_phases()
        
        # Assert
        assert len(phases) == 1
        assert set(phases[0]) == {"T001", "T002", "T003"}
    
    def test_linear_dependency_chain_creates_separate_phases(self):
        """Linear dependency chain creates one phase per task."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="Build", dependencies=["T001"]),
            TaskInfo(id="T003", name="Test", dependencies=["T002"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        phases = engine.get_phases()
        
        # Assert
        assert len(phases) == 3
        assert phases[0] == ["T001"]
        assert phases[1] == ["T002"]
        assert phases[2] == ["T003"]
    
    def test_parallel_branches_in_same_phase(self):
        """Parallel branches with same root appear in same phase."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="Feature A", dependencies=["T001"]),
            TaskInfo(id="T003", name="Feature B", dependencies=["T001"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        phases = engine.get_phases()
        
        # Assert
        assert len(phases) == 2
        assert phases[0] == ["T001"]
        assert set(phases[1]) == {"T002", "T003"}
    
    def test_diamond_dependency_structure(self):
        """Diamond dependency creates correct phases."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Root", dependencies=[]),
            TaskInfo(id="T002", name="Branch A", dependencies=["T001"]),
            TaskInfo(id="T003", name="Branch B", dependencies=["T001"]),
            TaskInfo(id="T004", name="Merge", dependencies=["T002", "T003"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        phases = engine.get_phases()
        
        # Assert
        assert len(phases) == 3
        assert phases[0] == ["T001"]
        assert set(phases[1]) == {"T002", "T003"}
        assert phases[2] == ["T004"]
    
    def test_complex_dag_with_multiple_levels(self):
        """Complex DAG with multiple dependency levels."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Init", dependencies=[]),
            TaskInfo(id="T002", name="Setup A", dependencies=[]),
            TaskInfo(id="T003", name="Build A", dependencies=["T001"]),
            TaskInfo(id="T004", name="Build B", dependencies=["T002"]),
            TaskInfo(id="T005", name="Test", dependencies=["T003", "T004"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        phases = engine.get_phases()
        
        # Assert
        assert len(phases) == 3
        assert set(phases[0]) == {"T001", "T002"}  # No dependencies
        assert set(phases[1]) == {"T003", "T004"}  # Depend on phase 0
        assert phases[2] == ["T005"]  # Depends on phase 1
    
    def test_tasks_sorted_within_phases(self):
        """Task IDs are sorted within each phase for determinism."""
        # Arrange
        tasks = [
            TaskInfo(id="T003", name="C", dependencies=[]),
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=[]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        phases = engine.get_phases()
        
        # Assert
        assert phases[0] == ["T001", "T002", "T003"]  # Sorted


class TestGetCriticalPath:
    """Tests for DAGEngine.get_critical_path() method."""
    
    def test_empty_task_list_returns_empty_path(self):
        """Empty task list returns empty critical path."""
        # Arrange
        tasks = []
        
        # Act
        engine = DAGEngine(tasks)
        path = engine.get_critical_path()
        
        # Assert
        assert path == []
    
    def test_single_task_is_critical_path(self):
        """Single task forms a critical path of length 1."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Only", dependencies=[]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        path = engine.get_critical_path()
        
        # Assert
        assert path == ["T001"]
    
    def test_linear_chain_is_full_critical_path(self):
        """Linear dependency chain is the critical path."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
            TaskInfo(id="T003", name="C", dependencies=["T002"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        path = engine.get_critical_path()
        
        # Assert
        assert path == ["T001", "T002", "T003"]
    
    def test_critical_path_chooses_longest_branch(self):
        """Critical path identifies the longest dependency chain."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Root", dependencies=[]),
            TaskInfo(id="T002", name="Short branch", dependencies=["T001"]),
            TaskInfo(id="T003", name="Long A", dependencies=["T001"]),
            TaskInfo(id="T004", name="Long B", dependencies=["T003"]),
            TaskInfo(id="T005", name="Long C", dependencies=["T004"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        path = engine.get_critical_path()
        
        # Assert
        # Longest path is T001 -> T003 -> T004 -> T005
        assert path == ["T001", "T003", "T004", "T005"]
    
    def test_diamond_critical_path(self):
        """Diamond structure has multiple equal-length paths."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Root", dependencies=[]),
            TaskInfo(id="T002", name="Branch A", dependencies=["T001"]),
            TaskInfo(id="T003", name="Branch B", dependencies=["T001"]),
            TaskInfo(id="T004", name="Merge", dependencies=["T002", "T003"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        path = engine.get_critical_path()
        
        # Assert
        # Either branch is valid, both have length 3
        assert len(path) == 3
        assert path[0] == "T001"
        assert path[2] == "T004"
        assert path[1] in ["T002", "T003"]
    
    def test_independent_tasks_picks_one(self):
        """Multiple independent tasks picks any one."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=[]),
            TaskInfo(id="T003", name="C", dependencies=[]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        path = engine.get_critical_path()
        
        # Assert
        assert len(path) == 1
        assert path[0] in ["T001", "T002", "T003"]


class TestPhaseCount:
    """Tests for DAGEngine.phase_count property."""
    
    def test_phase_count_matches_phases_length(self):
        """phase_count property matches length of get_phases()."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
            TaskInfo(id="T003", name="C", dependencies=["T001"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        
        # Assert
        assert engine.phase_count == len(engine.get_phases())
        assert engine.phase_count == 2
