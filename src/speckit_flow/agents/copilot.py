"""
GitHub Copilot IDE adapter for SpecKitFlow.

This module implements the GitHub Copilot integration for parallel orchestration,
operating in "IDE notification mode" where users are prompted to open worktrees
in VS Code rather than spawning CLI processes.
"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from speckit_core.models import TaskInfo
from speckit_core.paths import get_current_branch

from .base import AgentAdapter

__all__ = [
    "CopilotIDEAdapter",
]


class CopilotIDEAdapter(AgentAdapter):
    """GitHub Copilot IDE integration adapter.
    
    This adapter implements the IDE notification pattern for GitHub Copilot,
    creating context files in worktrees and prompting users to open them in
    VS Code with Copilot enabled.
    
    Key features:
    - Creates .github/copilot-instructions.md for task context
    - Uses Rich panels for clear, actionable user prompts
    - Watches tasks.md for completion detection
    - Works with VS Code's Copilot integration
    
    Note: This adapter does NOT use .github/agents/ directory. That location
    is reserved for *.agent.md files. Copilot uses copilot-instructions.md
    directly in .github/.
    
    Example:
        >>> adapter = CopilotIDEAdapter()
        >>> task = TaskInfo(id="T001", name="Setup database", dependencies=[])
        >>> worktree = Path("/repo/.worktrees-001/session-0")
        >>> adapter.setup_session(worktree, task)
        >>> adapter.notify_user(0, worktree, task)
        # Displays Rich panel prompting user to open worktree in VS Code
    """
    
    def __init__(self):
        """Initialize the Copilot adapter with Rich console."""
        self.console = Console()
    
    def setup_session(self, worktree: Path, task: TaskInfo) -> None:
        """Set up Copilot context file in worktree.
        
        Creates .github/copilot-instructions.md with task details that
        Copilot will use for context when generating code.
        
        Args:
            worktree: Path to the git worktree for this session
            task: TaskInfo object with task details
            
        Raises:
            OSError: If unable to create directory or file
            
        Example:
            >>> adapter = CopilotIDEAdapter()
            >>> task = TaskInfo(id="T001", name="Implement auth")
            >>> adapter.setup_session(Path("/repo/.worktrees/s0"), task)
            # Creates /repo/.worktrees/s0/.github/copilot-instructions.md
        """
        # Create .github directory (not .github/agents/)
        github_dir = worktree / ".github"
        github_dir.mkdir(parents=True, exist_ok=True)
        
        # Create copilot-instructions.md with task context
        context_file = github_dir / "copilot-instructions.md"
        
        # Build task context content
        context_content = self._build_context_content(task)
        
        # Write context file
        context_file.write_text(context_content, encoding="utf-8")
    
    def notify_user(self, session_id: int, worktree: Path, task: TaskInfo) -> None:
        """Display notification prompting user to open worktree in VS Code.
        
        Shows a Rich Panel with:
        - Session number and task details
        - Absolute worktree path (copy-pasteable)
        - Instructions for using Copilot
        - Command to run: /speckit.implement
        
        Args:
            session_id: Zero-based session identifier
            worktree: Absolute path to the worktree
            task: TaskInfo object with task details
            
        Example:
            >>> adapter = CopilotIDEAdapter()
            >>> adapter.notify_user(0, Path("/repo/.worktrees/s0"), task)
            # Prints formatted panel to terminal
        """
        # Build the panel content
        panel_content = f"""[bold]Session {session_id}[/bold]

Task: [cyan]{task.id}[/cyan] - {task.name}
"""
        
        # Add dependencies if any
        if task.dependencies:
            deps_str = ", ".join(task.dependencies)
            panel_content += f"\nDependencies: [dim]{deps_str}[/dim]"
        
        # Add files if any
        if task.files:
            files_str = ", ".join(task.files)
            panel_content += f"\nFiles: [dim]{files_str}[/dim]"
        
        panel_content += f"""

[bold]Instructions:[/bold]
1. Open this folder in VS Code:
   [green]{worktree.absolute()}[/green]

2. Run the Copilot command:
   [cyan]/speckit.implement[/cyan]

3. When complete, the task checkbox in tasks.md will be marked.
   Alternatively, run: [cyan]skf complete {task.id}[/cyan]"""
        
        # Display panel
        self.console.print()
        panel = Panel(
            panel_content,
            title="[bold yellow]Action Required[/bold yellow]",
            border_style="yellow",
        )
        self.console.print(panel)
        self.console.print()
    
    def get_files_to_watch(self, worktree: Path) -> list[Path]:
        """Return tasks.md path for completion detection.
        
        Copilot adapter watches the tasks.md file in the worktree's specs
        directory for checkbox changes indicating task completion.
        
        Args:
            worktree: Path to the worktree being monitored
            
        Returns:
            List containing the tasks.md path in the worktree
            
        Example:
            >>> adapter = CopilotIDEAdapter()
            >>> paths = adapter.get_files_to_watch(Path("/repo/.worktrees/s0"))
            >>> assert len(paths) == 1
            >>> assert paths[0].name == "tasks.md"
        """
        # Get the current branch to determine specs path
        try:
            branch = get_current_branch()
        except Exception:
            # Fallback to main if unable to detect branch
            branch = "main"
        
        # Return tasks.md in the worktree's specs directory
        tasks_path = worktree / "specs" / branch / "tasks.md"
        return [tasks_path]
    
    def get_context_file_path(self, worktree: Path) -> Path:
        """Return path to copilot-instructions.md in worktree.
        
        Args:
            worktree: Path to the worktree
            
        Returns:
            Path to .github/copilot-instructions.md
            
        Example:
            >>> adapter = CopilotIDEAdapter()
            >>> path = adapter.get_context_file_path(Path("/repo/.worktrees/s0"))
            >>> assert path.name == "copilot-instructions.md"
            >>> assert path.parent.name == ".github"
        """
        return worktree / ".github" / "copilot-instructions.md"
    
    def _build_context_content(self, task: TaskInfo) -> str:
        """Build the content for copilot-instructions.md.
        
        Creates a structured context document that Copilot can use to
        understand the task requirements and implementation approach.
        
        Args:
            task: TaskInfo object with task details
            
        Returns:
            Formatted markdown content for the context file
        """
        content = f"""# Task: {task.id} - {task.name}

## Overview

You are working on implementing **{task.id}** as part of a parallel orchestration workflow.

## Task Details

- **Task ID**: {task.id}
- **Description**: {task.name}
- **Parallelizable**: {"Yes" if task.parallelizable else "No"}
"""
        
        if task.description:
            content += f"- **Details**: {task.description}\n"
        
        if task.dependencies:
            deps_str = ", ".join(task.dependencies)
            content += f"- **Dependencies**: {deps_str} (already completed)\n"
        
        if task.story:
            content += f"- **User Story**: {task.story}\n"
        
        if task.files:
            content += "\n## Files to Modify\n\n"
            for file in task.files:
                content += f"- `{file}`\n"
        
        content += """

## Implementation Guidelines

Follow these principles when implementing this task:

1. **Code Quality**: Write clean, well-documented code with type hints
2. **Testing**: Include unit tests following the AAA pattern
3. **Error Handling**: Use appropriate exceptions with helpful messages
4. **Pydantic v2**: Use `model_dump()` and `model_validate()` (not v1 syntax)
5. **File Operations**: Use `pathlib.Path` for all file paths
6. **State Management**: Use atomic writes (temp + rename) for persistence

## Completion

Mark the task complete by:
1. Checking the checkbox in tasks.md: `- [x] [""" + task.id + """]`
2. Or running: `skf complete """ + task.id + """`

## Need Help?

Reference the following documentation:
- `specs/speckit-flow/plan.md` - Architecture and schemas
- `specs/speckit-flow/tasks.md` - Full task list with acceptance criteria
- `.github/instructions/code-quality.instructions.md` - Code standards
- `.github/instructions/testing.instructions.md` - Testing patterns
"""
        
        return content

