"""
Unit tests for dag_engine.py.

Tests the DAGEngine class for building, validating, and analyzing
task dependency graphs.
"""

import pytest

from speckit_core.models import TaskInfo, TaskStatus
from speckit_flow.exceptions import CyclicDependencyError
from speckit_flow.orchestration.dag_engine import DAGEngine


class TestDAGEngineInit:
    """Test DAGEngine initialization."""
    
    def test_init_with_empty_tasks(self):
        """DAGEngine initializes with empty task list."""
        # Arrange & Act
        engine = DAGEngine([])
        
        # Assert
        assert engine.tasks == []
        assert engine.task_count == 0
    
    def test_init_with_tasks(self):
        """DAGEngine initializes with task list."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Task 1", dependencies=[]),
            TaskInfo(id="T002", name="Task 2", dependencies=["T001"]),
        ]
        
        # Act
        engine = DAGEngine(tasks)
        
        # Assert
        assert engine.tasks == tasks
        assert engine.task_count == 2


class TestDAGEngineBuildGraph:
    """Test graph building functionality."""
    
    def test_build_graph_empty_tasks(self):
        """Builds empty graph for empty task list."""
        # Arrange
        engine = DAGEngine([])
        
        # Act
        graph = engine.build_graph()
        
        # Assert
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
    
    def test_build_graph_single_task(self):
        """Builds graph with single task node."""
        # Arrange
        task = TaskInfo(id="T001", name="Single task", dependencies=[])
        engine = DAGEngine([task])
        
        # Act
        graph = engine.build_graph()
        
        # Assert
        assert len(graph.nodes) == 1
        assert "T001" in graph.nodes
        assert graph.nodes["T001"]["task"] == task
        assert len(graph.edges) == 0
    
    def test_build_graph_with_dependencies(self):
        """Builds graph with dependency edges."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Task 1", dependencies=[]),
            TaskInfo(id="T002", name="Task 2", dependencies=["T001"]),
            TaskInfo(id="T003", name="Task 3", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        graph = engine.build_graph()
        
        # Assert
        assert len(graph.nodes) == 3
        assert graph.has_edge("T001", "T002")
        assert graph.has_edge("T001", "T003")
        assert not graph.has_edge("T002", "T003")  # No edge between siblings
    
    def test_build_graph_multiple_dependencies(self):
        """Builds graph with tasks having multiple dependencies."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Task 1", dependencies=[]),
            TaskInfo(id="T002", name="Task 2", dependencies=[]),
            TaskInfo(id="T003", name="Task 3", dependencies=["T001", "T002"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        graph = engine.build_graph()
        
        # Assert
        assert len(graph.nodes) == 3
        assert graph.has_edge("T001", "T003")
        assert graph.has_edge("T002", "T003")
        assert not graph.has_edge("T001", "T002")
    
    def test_build_graph_complex_chain(self):
        """Builds graph with complex dependency chain."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Root", dependencies=[]),
            TaskInfo(id="T002", name="Level 1a", dependencies=["T001"]),
            TaskInfo(id="T003", name="Level 1b", dependencies=["T001"]),
            TaskInfo(id="T004", name="Level 2", dependencies=["T002", "T003"]),
            TaskInfo(id="T005", name="Level 3", dependencies=["T004"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        graph = engine.build_graph()
        
        # Assert
        assert len(graph.nodes) == 5
        assert len(graph.edges) == 5
        # Verify correct edges exist
        assert graph.has_edge("T001", "T002")
        assert graph.has_edge("T001", "T003")
        assert graph.has_edge("T002", "T004")
        assert graph.has_edge("T003", "T004")
        assert graph.has_edge("T004", "T005")
    
    def test_build_graph_stores_full_task_data(self):
        """Graph nodes contain full TaskInfo data."""
        # Arrange
        task = TaskInfo(
            id="T001",
            name="Full task",
            description="Detailed description",
            dependencies=[],
            parallelizable=True,
            story="US1",
            files=["file1.py", "file2.py"],
            status=TaskStatus.pending,
        )
        engine = DAGEngine([task])
        
        # Act
        graph = engine.build_graph()
        
        # Assert
        stored_task = graph.nodes["T001"]["task"]
        assert stored_task == task
        assert stored_task.name == "Full task"
        assert stored_task.description == "Detailed description"
        assert stored_task.parallelizable is True
        assert stored_task.story == "US1"
        assert stored_task.files == ["file1.py", "file2.py"]
    
    def test_build_graph_caches_result(self):
        """build_graph() caches result and returns same instance."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Task", dependencies=[])]
        engine = DAGEngine(tasks)
        
        # Act
        graph1 = engine.build_graph()
        graph2 = engine.build_graph()
        
        # Assert
        assert graph1 is graph2  # Same object instance


class TestDAGEngineCycleDetection:
    """Test circular dependency detection."""
    
    def test_direct_cycle_two_tasks(self):
        """Detects direct cycle between two tasks."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=["T002"]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act & Assert
        with pytest.raises(CyclicDependencyError) as exc_info:
            engine.build_graph()
        
        assert "T001" in exc_info.value.cycle
        assert "T002" in exc_info.value.cycle
        assert "Circular dependency detected" in str(exc_info.value)
    
    def test_indirect_cycle_three_tasks(self):
        """Detects indirect cycle through multiple tasks."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=["T003"]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
            TaskInfo(id="T003", name="C", dependencies=["T002"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act & Assert
        with pytest.raises(CyclicDependencyError) as exc_info:
            engine.build_graph()
        
        cycle = exc_info.value.cycle
        assert len(cycle) >= 3  # Cycle includes at least T001, T002, T003
        assert "T001" in cycle
        assert "T002" in cycle
        assert "T003" in cycle
    
    def test_self_dependency(self):
        """Detects self-dependency cycle."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Self-loop", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act & Assert
        with pytest.raises(CyclicDependencyError) as exc_info:
            engine.build_graph()
        
        assert "T001" in exc_info.value.cycle
    
    def test_cycle_with_valid_tasks(self):
        """Detects cycle even when some tasks are valid."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Valid 1", dependencies=[]),
            TaskInfo(id="T002", name="Valid 2", dependencies=["T001"]),
            TaskInfo(id="T003", name="Cycle A", dependencies=["T004"]),
            TaskInfo(id="T004", name="Cycle B", dependencies=["T003"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act & Assert
        with pytest.raises(CyclicDependencyError) as exc_info:
            engine.build_graph()
        
        cycle = exc_info.value.cycle
        assert "T003" in cycle
        assert "T004" in cycle


class TestDAGEngineValidate:
    """Test graph validation."""
    
    def test_validate_empty_graph(self):
        """Validates empty graph as valid DAG."""
        # Arrange
        engine = DAGEngine([])
        
        # Act
        result = engine.validate()
        
        # Assert
        assert result is True
    
    def test_validate_valid_dag(self):
        """Validates correct DAG structure."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
            TaskInfo(id="T003", name="C", dependencies=["T001"]),
            TaskInfo(id="T004", name="D", dependencies=["T002", "T003"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        result = engine.validate()
        
        # Assert
        assert result is True
    
    def test_validate_raises_on_cycle(self):
        """validate() raises CyclicDependencyError for cycles."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=["T002"]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act & Assert
        with pytest.raises(CyclicDependencyError):
            engine.validate()
    
    def test_validate_builds_graph_if_needed(self):
        """validate() builds graph if not already built."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="A", dependencies=[])]
        engine = DAGEngine(tasks)
        assert engine._graph is None
        
        # Act
        engine.validate()
        
        # Assert
        assert engine._graph is not None


class TestDAGEngineHelpers:
    """Test helper methods."""
    
    def test_graph_property(self):
        """graph property builds and returns graph."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="A", dependencies=[])]
        engine = DAGEngine(tasks)
        
        # Act
        graph = engine.graph
        
        # Assert
        assert graph is not None
        assert "T001" in graph.nodes
    
    def test_get_task(self):
        """get_task() returns correct TaskInfo."""
        # Arrange
        task1 = TaskInfo(id="T001", name="Task 1", dependencies=[])
        task2 = TaskInfo(id="T002", name="Task 2", dependencies=["T001"])
        engine = DAGEngine([task1, task2])
        
        # Act
        retrieved = engine.get_task("T002")
        
        # Assert
        assert retrieved == task2
        assert retrieved.name == "Task 2"
    
    def test_get_task_missing(self):
        """get_task() raises KeyError for missing task."""
        # Arrange
        engine = DAGEngine([TaskInfo(id="T001", name="A", dependencies=[])])
        
        # Act & Assert
        with pytest.raises(KeyError):
            engine.get_task("T999")
    
    def test_task_count(self):
        """task_count returns correct number of tasks."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=[]),
            TaskInfo(id="T003", name="C", dependencies=[]),
        ]
        engine = DAGEngine(tasks)
        
        # Act & Assert
        assert engine.task_count == 3


class TestDAGEngineEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_missing_dependency_task(self):
        """Handles task referencing non-existent dependency."""
        # Arrange - T002 depends on T999 which doesn't exist
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=["T999"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act - Should build graph but have disconnected dependency node
        graph = engine.build_graph()
        
        # Assert - Graph contains edge but T999 has no task data
        assert graph.has_edge("T999", "T002")
        assert "T999" in graph.nodes
        # T999 node exists but has no task attribute (or has None)
    
    def test_disconnected_components(self):
        """Handles graph with disconnected components."""
        # Arrange - Two separate task chains with no connection
        tasks = [
            TaskInfo(id="T001", name="Chain A-1", dependencies=[]),
            TaskInfo(id="T002", name="Chain A-2", dependencies=["T001"]),
            TaskInfo(id="T003", name="Chain B-1", dependencies=[]),
            TaskInfo(id="T004", name="Chain B-2", dependencies=["T003"]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        graph = engine.build_graph()
        
        # Assert
        assert len(graph.nodes) == 4
        assert graph.has_edge("T001", "T002")
        assert graph.has_edge("T003", "T004")
        assert not graph.has_edge("T001", "T003")
        assert not graph.has_edge("T002", "T004")
        # Validate as valid DAG (disconnected is ok)
        assert engine.validate() is True
    
    def test_all_tasks_independent(self):
        """Handles tasks with no dependencies (all parallel)."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=[]),
            TaskInfo(id="T003", name="C", dependencies=[]),
        ]
        engine = DAGEngine(tasks)
        
        # Act
        graph = engine.build_graph()
        
        # Assert
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 0  # No dependencies = no edges
        assert engine.validate() is True
