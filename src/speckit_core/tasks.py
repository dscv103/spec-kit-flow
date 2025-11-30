"""
Task parsing utilities for tasks.md files.

This module provides functions for parsing task lines with DAG markers
including task IDs, dependencies, parallelizable flags, and story mappings.
"""

import re
from pathlib import Path
from typing import Optional

from speckit_core.exceptions import TaskParseError
from speckit_core.models import TaskInfo

__all__ = [
    "parse_task_line",
    "parse_tasks_file",
]

# Regex patterns for task line parsing
TASK_LINE_PATTERN = re.compile(
    r"^-\s+\[([x\sX])\]\s+"  # Checkbox: - [ ] or - [x]
    r"\[([T]\d{3})\]\s+"      # Task ID: [T001]
    r"(?:\[P\]\s+)?"          # Optional: [P]
    r"(?:\[US\d+\]\s+)?"      # Optional: [US1]
    r"(?:\[deps:([^\]]*)\]\s+)?"  # Optional: [deps:T001,T002]
    r"(.+)$",                 # Description (rest of line)
    re.IGNORECASE
)

# Alternative pattern for tasks without extended markers (backward compatibility)
SIMPLE_TASK_PATTERN = re.compile(
    r"^-\s+\[([x\sX])\]\s+"  # Checkbox
    r"\[([T]\d{3})\]\s+"      # Task ID
    r"(?:\[P\]\s+)?"          # Optional [P]
    r"(?:\[US\d+\]\s+)?"      # Optional [US#]
    r"\*\*(.+?)\*\*",         # Bold task name
    re.IGNORECASE
)

# Pattern to extract [P] marker
PARALLEL_PATTERN = re.compile(r"\[P\]", re.IGNORECASE)

# Pattern to extract [US#] marker
STORY_PATTERN = re.compile(r"\[US(\d+)\]", re.IGNORECASE)

# Pattern to extract file paths from description (e.g., src/models/User.ts)
FILE_PATH_PATTERN = re.compile(r"`([^`]+\.[a-zA-Z]{1,5})`")


def parse_task_line(line: str) -> Optional[TaskInfo]:
    """Parse a single task line from tasks.md.
    
    Supports multiple formats:
    - Standard: `- [ ] [T001] [P] [US1] Description`
    - Extended: `- [ ] [T001] [P] [US1] [deps:T000] Description`
    - Completed: `- [x] [T001] Description`
    - Bold format: `- [ ] [T001] [P] **Task Name**`
    
    Args:
        line: Task line to parse.
        
    Returns:
        TaskInfo object if line is a valid task, None otherwise.
        
    Example:
        >>> task = parse_task_line("- [ ] [T001] [P] [US1] [deps:] Setup project")
        >>> assert task.id == "T001"
        >>> assert task.parallelizable is True
        >>> assert task.story == "US1"
        >>> assert task.dependencies == []
    """
    if not line.strip():
        return None
    
    # Try to match the extended format first
    match = TASK_LINE_PATTERN.match(line.strip())
    
    if not match:
        # Not a task line
        return None
    
    checkbox, task_id, deps_str, description = match.groups()
    
    # Determine if task is completed
    completed = checkbox.lower() == "x"
    
    # Check for [P] marker
    parallelizable = bool(PARALLEL_PATTERN.search(line))
    
    # Extract story ID if present
    story_match = STORY_PATTERN.search(line)
    story = f"US{story_match.group(1)}" if story_match else None
    
    # Parse dependencies
    dependencies = []
    if deps_str is not None:
        # Split by comma and strip whitespace
        deps_str = deps_str.strip()
        if deps_str:  # Only if not empty (handles [deps:] case)
            dependencies = [d.strip() for d in deps_str.split(",") if d.strip()]
    
    # Extract task name from description (remove ** markers if present)
    name = description.strip()
    # Remove bold markers
    name = re.sub(r"\*\*(.+?)\*\*", r"\1", name)
    # Clean up extra whitespace
    name = " ".join(name.split())
    
    # Extract file paths from description (in backticks)
    files = FILE_PATH_PATTERN.findall(description)
    
    # Create TaskInfo object
    try:
        return TaskInfo(
            id=task_id.upper(),
            name=name,
            description=description.strip(),
            dependencies=dependencies,
            parallelizable=parallelizable,
            story=story,
            files=files,
            completed=completed,
        )
    except Exception as e:
        # If TaskInfo validation fails, return None
        # This handles edge cases with invalid data
        return None


def parse_tasks_file(path: Path) -> list[TaskInfo]:
    """Parse all tasks from a tasks.md file.
    
    Reads the entire file and extracts all valid task lines,
    returning a list of TaskInfo objects.
    
    Args:
        path: Path to tasks.md file.
        
    Returns:
        List of TaskInfo objects. Returns empty list if no tasks found.
        
    Raises:
        FileNotFoundError: If tasks file doesn't exist.
        
    Example:
        >>> tasks = parse_tasks_file(Path("tasks.md"))
        >>> assert all(task.id.startswith("T") for task in tasks)
    """
    if not path.exists():
        raise FileNotFoundError(f"Tasks file not found: {path}")
    
    # Read entire file at once for performance
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise TaskParseError(f"Failed to read tasks file: {path}\n{e}")
    
    # Parse each line
    tasks = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        task = parse_task_line(line)
        if task is not None:
            tasks.append(task)
    
    return tasks
