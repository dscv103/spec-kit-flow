"""
Unit tests for speckit_core.tasks module.

Tests task line parsing with all supported formats including
DAG markers, dependencies, and backward compatibility.
"""

import tempfile
from pathlib import Path

import pytest

from speckit_core.exceptions import TaskParseError
from speckit_core.models import TaskInfo
from speckit_core.tasks import parse_task_line, parse_tasks_file


class TestParseTaskLine:
    """Unit tests for parse_task_line function."""
    
    def test_parses_minimal_task(self):
        """Parses task with only required elements."""
        line = "- [ ] [T001] Simple task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"
        assert task.name == "Simple task"
        assert task.completed is False
        assert task.parallelizable is False
        assert task.story is None
        assert task.dependencies == []
    
    def test_parses_standard_format(self):
        """Parses standard format: - [ ] [T001] [P] [US1] Description"""
        line = "- [ ] [T001] [P] [US1] Implement User model"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"
        assert task.name == "Implement User model"
        assert task.parallelizable is True
        assert task.story == "US1"
        assert task.dependencies == []
        assert task.completed is False
    
    def test_parses_extended_format_with_deps(self):
        """Parses extended format: - [ ] [T001] [P] [US1] [deps:T000] Description"""
        line = "- [ ] [T002] [P] [US1] [deps:T001] Add User validation"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T002"
        assert task.name == "Add User validation"
        assert task.parallelizable is True
        assert task.story == "US1"
        assert task.dependencies == ["T001"]
    
    def test_parses_multiple_dependencies(self):
        """Parses task with multiple dependencies."""
        line = "- [ ] [T003] [deps:T001,T002] Integration task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T003"
        assert task.dependencies == ["T001", "T002"]
    
    def test_parses_empty_deps_marker(self):
        """Parses [deps:] as no dependencies (not None)."""
        line = "- [ ] [T001] [deps:] Initial task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.dependencies == []
    
    def test_handles_completed_task(self):
        """Correctly identifies completed tasks with [x]."""
        line = "- [x] [T001] Completed task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"
        assert task.completed is True
    
    def test_handles_completed_task_uppercase_x(self):
        """Handles uppercase X in checkbox."""
        line = "- [X] [T001] Completed task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.completed is True
    
    def test_parses_task_without_parallelizable_marker(self):
        """Handles tasks without [P] marker."""
        line = "- [ ] [T001] [US1] Sequential task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.parallelizable is False
        assert task.story == "US1"
    
    def test_parses_task_without_story_marker(self):
        """Handles tasks without [US#] marker."""
        line = "- [ ] [T001] [P] Task without story"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.parallelizable is True
        assert task.story is None
    
    def test_parses_task_with_bold_name(self):
        """Parses tasks with **bold** name format."""
        line = "- [ ] [T001] [P] **Implement feature**"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.name == "Implement feature"
    
    def test_extracts_file_paths_from_description(self):
        """Extracts file paths in backticks from description."""
        line = "- [ ] [T001] Implement `src/models/User.ts` and `src/models/Task.ts`"
        task = parse_task_line(line)
        
        assert task is not None
        assert "src/models/User.ts" in task.files
        assert "src/models/Task.ts" in task.files
    
    def test_returns_none_for_non_task_line(self):
        """Returns None for lines that aren't tasks."""
        assert parse_task_line("## Section Header") is None
        assert parse_task_line("Regular paragraph text") is None
        assert parse_task_line("- Regular bullet point") is None
        assert parse_task_line("") is None
        assert parse_task_line("   ") is None
    
    def test_handles_whitespace_variations(self):
        """Handles various whitespace patterns."""
        line = "  - [ ]  [T001]   [P]  Task with extra spaces  "
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"
        assert task.parallelizable is True
    
    def test_handles_dependency_whitespace(self):
        """Handles whitespace in dependency list."""
        line = "- [ ] [T003] [deps: T001 , T002 ] Task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.dependencies == ["T001", "T002"]
    
    def test_handles_case_variations(self):
        """Handles case variations in markers."""
        line = "- [ ] [t001] [p] [us1] Task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"  # Normalized to uppercase
        assert task.parallelizable is True
        assert task.story == "US1"
    
    def test_real_world_task_from_tasks_md(self):
        """Parses actual task line from tasks.md."""
        line = "- [x] [T001] [deps:] **Update pyproject.toml for Hatch workspaces**"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"
        assert task.name == "Update pyproject.toml for Hatch workspaces"
        assert task.completed is True
        assert task.dependencies == []


class TestParseTasksFile:
    """Unit tests for parse_tasks_file function."""
    
    def test_parses_file_with_multiple_tasks(self):
        """Parses file containing multiple tasks."""
        content = """# Tasks
        
- [ ] [T001] [deps:] First task
- [ ] [T002] [P] [deps:T001] Second task
- [ ] [T003] [P] [deps:T001] Third task

Some other text

- [ ] [T004] [deps:T002,T003] Fourth task
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            tasks = parse_tasks_file(temp_path)
            
            assert len(tasks) == 4
            assert tasks[0].id == "T001"
            assert tasks[1].id == "T002"
            assert tasks[2].id == "T003"
            assert tasks[3].id == "T004"
            assert tasks[3].dependencies == ["T002", "T003"]
        finally:
            temp_path.unlink()
    
    def test_returns_empty_list_for_file_with_no_tasks(self):
        """Returns empty list for file without tasks."""
        content = """# Document
        
This is just a regular markdown file.

## Section

- Regular bullet
- Another bullet
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            tasks = parse_tasks_file(temp_path)
            assert tasks == []
        finally:
            temp_path.unlink()
    
    def test_handles_empty_file(self):
        """Handles empty file gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            tasks = parse_tasks_file(temp_path)
            assert tasks == []
        finally:
            temp_path.unlink()
    
    def test_raises_for_missing_file(self):
        """Raises FileNotFoundError for missing file."""
        nonexistent = Path("/tmp/nonexistent-file-12345.md")
        
        with pytest.raises(FileNotFoundError) as exc_info:
            parse_tasks_file(nonexistent)
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_handles_unicode_content(self):
        """Handles Unicode characters in task descriptions."""
        content = "- [ ] [T001] Implement émojis 🚀 and special chars"
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            tasks = parse_tasks_file(temp_path)
            
            assert len(tasks) == 1
            assert tasks[0].name == "Implement émojis 🚀 and special chars"
        finally:
            temp_path.unlink()
    
    def test_handles_mixed_completed_and_pending(self):
        """Correctly identifies completed vs pending tasks."""
        content = """
- [x] [T001] Completed task
- [ ] [T002] Pending task
- [X] [T003] Also completed
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            tasks = parse_tasks_file(temp_path)
            
            assert len(tasks) == 3
            assert tasks[0].completed is True
            assert tasks[1].completed is False
            assert tasks[2].completed is True
        finally:
            temp_path.unlink()
    
    def test_preserves_task_order(self):
        """Preserves order of tasks from file."""
        content = """
- [ ] [T003] Third
- [ ] [T001] First  
- [ ] [T002] Second
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            tasks = parse_tasks_file(temp_path)
            
            # Order should match file order, not sorted by ID
            assert [t.id for t in tasks] == ["T003", "T001", "T002"]
        finally:
            temp_path.unlink()


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing task formats."""
    
    def test_parses_old_format_without_deps_marker(self):
        """Parses tasks that don't have [deps:...] marker."""
        line = "- [ ] [T001] [P] [US1] Old format task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"
        assert task.parallelizable is True
        assert task.story == "US1"
        # No deps marker means dependencies remains empty
        assert task.dependencies == []
    
    def test_parses_minimal_old_format(self):
        """Parses minimal old format (just checkbox and ID)."""
        line = "- [ ] [T001] Task description"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"
        assert task.name == "Task description"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_very_long_description(self):
        """Handles very long task descriptions."""
        long_desc = "A" * 10000
        line = f"- [ ] [T001] {long_desc}"
        task = parse_task_line(line)
        
        assert task is not None
        assert len(task.name) == 10000
    
    def test_task_with_special_characters(self):
        """Handles special characters in description."""
        line = "- [ ] [T001] Task with $pecial ch@rs & symbols!"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.name == "Task with $pecial ch@rs & symbols!"
    
    def test_multiple_file_extensions(self):
        """Extracts files with various extensions."""
        line = "- [ ] [T001] Files: `file.py`, `test.ts`, `data.json`, `doc.md`"
        task = parse_task_line(line)
        
        assert task is not None
        assert len(task.files) == 4
        assert "file.py" in task.files
        assert "test.ts" in task.files
    
    def test_task_id_with_leading_zeros(self):
        """Handles task IDs with leading zeros."""
        line = "- [ ] [T001] Task one"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T001"
    
    def test_high_task_numbers(self):
        """Handles high task numbers (T999)."""
        line = "- [ ] [T999] Last task"
        task = parse_task_line(line)
        
        assert task is not None
        assert task.id == "T999"
    
    def test_many_dependencies(self):
        """Handles tasks with many dependencies."""
        deps = ",".join([f"T{i:03d}" for i in range(1, 21)])
        line = f"- [ ] [T100] [deps:{deps}] Complex task"
        task = parse_task_line(line)
        
        assert task is not None
        assert len(task.dependencies) == 20
        assert "T001" in task.dependencies
        assert "T020" in task.dependencies
