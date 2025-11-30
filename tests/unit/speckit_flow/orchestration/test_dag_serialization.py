"""
Unit tests for DAG serialization (T016).
"""

from pathlib import Path
import tempfile

import pytest
import yaml

from speckit_core.models import TaskInfo
from speckit_flow.orchestration.dag_engine import DAGEngine


class TestToYaml:
    """Tests for DAGEngine.to_yaml() method."""
    
    def test_generates_valid_yaml(self):
        """Generated YAML is valid and parseable."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        
        # Assert
        data = yaml.safe_load(yaml_str)
        assert isinstance(data, dict)
    
    def test_includes_version_field(self):
        """YAML includes version field."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        assert "version" in data
        assert data["version"] == "1.0"
    
    def test_includes_spec_id_field(self):
        """YAML includes spec_id field."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-feature-name", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        assert "spec_id" in data
        assert data["spec_id"] == "001-feature-name"
    
    def test_includes_generated_at_timestamp(self):
        """YAML includes generated_at with ISO 8601 timestamp."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        assert "generated_at" in data
        # Check ISO 8601 format (basic validation)
        timestamp = data["generated_at"]
        assert "T" in timestamp
        assert timestamp.endswith("Z")
    
    def test_includes_num_sessions_field(self):
        """YAML includes num_sessions field."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
        engine = DAGEngine(tasks)
        engine.assign_sessions(3)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 3)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        assert "num_sessions" in data
        assert data["num_sessions"] == 3
    
    def test_includes_phases_list(self):
        """YAML includes phases list."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="Build", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        assert "phases" in data
        assert isinstance(data["phases"], list)
        assert len(data["phases"]) == 2
    
    def test_phase_has_name_field(self):
        """Each phase has a name field."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="Build", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        phases = data["phases"]
        assert phases[0]["name"] == "phase-0"
        assert phases[1]["name"] == "phase-1"
    
    def test_phase_contains_tasks_list(self):
        """Each phase contains tasks list."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        phase = data["phases"][0]
        assert "tasks" in phase
        assert isinstance(phase["tasks"], list)
        assert len(phase["tasks"]) == 1
    
    def test_task_has_all_required_fields(self):
        """Each task has all required fields from schema."""
        # Arrange
        tasks = [
            TaskInfo(
                id="T001",
                name="Setup database",
                description="Initialize database schema",
                dependencies=[],
                parallelizable=False,
                story="US1",
                files=["db/schema.sql"],
            )
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        task = data["phases"][0]["tasks"][0]
        assert task["id"] == "T001"
        assert task["name"] == "Setup database"
        assert task["description"] == "Initialize database schema"
        assert task["files"] == ["db/schema.sql"]
        assert task["dependencies"] == []
        assert task["session"] == 0
        assert task["parallelizable"] is False
        assert task["story"] == "US1"
    
    def test_task_with_dependencies_serialized_correctly(self):
        """Task with dependencies serializes correctly."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        task_b = data["phases"][1]["tasks"][0]
        assert task_b["dependencies"] == ["T001"]
    
    def test_task_with_no_description_uses_name(self):
        """Task without description uses name as description."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[], description=None),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        # Act
        yaml_str = engine.to_yaml("001-test", 1)
        data = yaml.safe_load(yaml_str)
        
        # Assert
        task = data["phases"][0]["tasks"][0]
        assert task["description"] == "Setup"


class TestSave:
    """Tests for DAGEngine.save() method."""
    
    def test_creates_file_at_specified_path(self):
        """save() creates file at specified path."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dag.yaml"
            
            # Act
            engine.save(path, "001-test", 1)
            
            # Assert
            assert path.exists()
    
    def test_creates_parent_directories(self):
        """save() creates parent directories if missing."""
        # Arrange
        tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "specs" / "feature" / "dag.yaml"
            
            # Act
            engine.save(path, "001-test", 1)
            
            # Assert
            assert path.exists()
            assert path.parent.exists()
    
    def test_saved_file_contains_valid_yaml(self):
        """Saved file contains valid YAML matching schema."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="Build", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(2)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dag.yaml"
            
            # Act
            engine.save(path, "001-feature", 2)
            
            # Assert
            content = path.read_text()
            data = yaml.safe_load(content)
            assert data["version"] == "1.0"
            assert data["spec_id"] == "001-feature"
            assert data["num_sessions"] == 2
            assert len(data["phases"]) == 2


class TestLoad:
    """Tests for DAGEngine.load() method."""
    
    def test_raises_file_not_found_for_missing_file(self):
        """load() raises FileNotFoundError if path doesn't exist."""
        # Arrange
        path = Path("/nonexistent/dag.yaml")
        
        # Act & Assert
        with pytest.raises(FileNotFoundError, match="DAG file not found"):
            DAGEngine.load(path)
    
    def test_loads_tasks_from_valid_yaml(self):
        """load() reconstructs DAGEngine from valid YAML."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Setup", dependencies=[]),
            TaskInfo(id="T002", name="Build", dependencies=["T001"]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dag.yaml"
            engine.save(path, "001-test", 1)
            
            # Act
            loaded_engine = DAGEngine.load(path)
            
            # Assert
            assert loaded_engine.task_count == 2
            assert loaded_engine.get_task("T001").name == "Setup"
            assert loaded_engine.get_task("T002").name == "Build"
    
    def test_preserves_task_dependencies(self):
        """load() preserves task dependencies."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[]),
            TaskInfo(id="T002", name="B", dependencies=["T001"]),
            TaskInfo(id="T003", name="C", dependencies=["T001", "T002"]),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dag.yaml"
            engine.save(path, "001-test", 1)
            
            # Act
            loaded_engine = DAGEngine.load(path)
            
            # Assert
            assert loaded_engine.get_task("T001").dependencies == []
            assert loaded_engine.get_task("T002").dependencies == ["T001"]
            assert set(loaded_engine.get_task("T003").dependencies) == {"T001", "T002"}
    
    def test_preserves_session_assignments(self):
        """load() preserves session assignments."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="A", dependencies=[], parallelizable=True),
            TaskInfo(id="T002", name="B", dependencies=[], parallelizable=True),
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(2)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dag.yaml"
            engine.save(path, "001-test", 2)
            
            # Act
            loaded_engine = DAGEngine.load(path)
            
            # Assert
            assert loaded_engine.get_task("T001").session is not None
            assert loaded_engine.get_task("T002").session is not None
    
    def test_preserves_task_metadata(self):
        """load() preserves all task metadata."""
        # Arrange
        tasks = [
            TaskInfo(
                id="T001",
                name="Setup",
                description="Initialize project",
                dependencies=[],
                parallelizable=False,
                story="US1",
                files=["package.json"],
            )
        ]
        engine = DAGEngine(tasks)
        engine.assign_sessions(1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dag.yaml"
            engine.save(path, "001-test", 1)
            
            # Act
            loaded_engine = DAGEngine.load(path)
            
            # Assert
            task = loaded_engine.get_task("T001")
            assert task.name == "Setup"
            assert task.description == "Initialize project"
            assert task.parallelizable is False
            assert task.story == "US1"
            assert task.files == ["package.json"]
    
    def test_round_trip_preserves_all_data(self):
        """save() followed by load() preserves all data."""
        # Arrange
        tasks = [
            TaskInfo(id="T001", name="Root", dependencies=[]),
            TaskInfo(id="T002", name="A", dependencies=["T001"], parallelizable=True),
            TaskInfo(id="T003", name="B", dependencies=["T001"], parallelizable=True),
            TaskInfo(id="T004", name="Merge", dependencies=["T002", "T003"]),
        ]
        original_engine = DAGEngine(tasks)
        original_engine.assign_sessions(2)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dag.yaml"
            
            # Act
            original_engine.save(path, "001-test", 2)
            loaded_engine = DAGEngine.load(path)
            
            # Assert
            assert loaded_engine.task_count == original_engine.task_count
            assert loaded_engine.phase_count == original_engine.phase_count
            
            # Verify each task
            for task_id in ["T001", "T002", "T003", "T004"]:
                orig = original_engine.get_task(task_id)
                loaded = loaded_engine.get_task(task_id)
                assert loaded.id == orig.id
                assert loaded.name == orig.name
                assert loaded.dependencies == orig.dependencies
                assert loaded.session == orig.session
    
    def test_raises_value_error_for_invalid_yaml(self):
        """load() raises ValueError for invalid YAML structure."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.yaml"
            path.write_text("not a dict")
            
            # Act & Assert
            with pytest.raises(ValueError, match="Invalid DAG YAML"):
                DAGEngine.load(path)
    
    def test_raises_value_error_for_missing_phases(self):
        """load() raises ValueError if 'phases' field missing."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing_phases.yaml"
            path.write_text("version: '1.0'\nspec_id: '001-test'\n")
            
            # Act & Assert
            with pytest.raises(ValueError, match="missing 'phases' field"):
                DAGEngine.load(path)
