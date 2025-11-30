"""
Abstract base class for AI agent adapters.

This module defines the AgentAdapter interface that all agent implementations
must follow. Each adapter is responsible for:
- Setting up agent context in worktrees
- Notifying users when action is required
- Providing file watch paths for completion detection
- Managing agent-specific configuration
"""

from abc import ABC, abstractmethod
from pathlib import Path

from speckit_core.models import TaskInfo

__all__ = [
    "AgentAdapter",
]


class AgentAdapter(ABC):
    """Abstract base class for AI agent session adapters.
    
    This interface defines the contract for integrating different AI coding
    assistants (GitHub Copilot, Goose, OpenCode, etc.) with SpecKitFlow's
    parallel orchestration system.
    
    Each adapter implementation handles:
    - Creating agent-specific context files in worktrees
    - Prompting users to open worktrees in their IDE/tool
    - Specifying which files to watch for completion detection
    - Managing agent-specific configuration paths
    
    Adapters operate in "notification mode" - they prompt the user to take
    action rather than spawning processes directly. This allows developers
    to work in their preferred environment.
    
    Example:
        >>> class MyAgentAdapter(AgentAdapter):
        ...     def setup_session(self, worktree: Path, task: TaskInfo) -> None:
        ...         # Create agent context file
        ...         context_file = worktree / ".myagent" / "context.md"
        ...         context_file.parent.mkdir(parents=True, exist_ok=True)
        ...         context_file.write_text(f"Task: {task.name}")
        ...
        ...     def notify_user(self, session_id: int, worktree: Path, task: TaskInfo) -> None:
        ...         print(f"Open {worktree} and run /myagent.implement")
        ...
        ...     def get_files_to_watch(self, worktree: Path) -> list[Path]:
        ...         return [worktree / "tasks.md"]
        ...
        ...     def get_context_file_path(self, worktree: Path) -> Path:
        ...         return worktree / ".myagent" / "context.md"
    """
    
    @abstractmethod
    def setup_session(self, worktree: Path, task: TaskInfo) -> None:
        """Set up agent context for a session in the worktree.
        
        This method is called once when a worktree is created for a session.
        It should create any agent-specific files or directories needed for
        the agent to understand the task context.
        
        Common implementations:
        - Create agent instructions/context file (e.g., .github/copilot-instructions.md)
        - Write task details, files to modify, acceptance criteria
        - Set up any agent-specific configuration
        
        Note: GitHub Copilot uses .github/copilot-instructions.md
              Generic *.agent.md files go in .github/agents/
        
        Args:
            worktree: Path to the git worktree for this session
            task: TaskInfo object containing task details to inject into context
            
        Raises:
            OSError: If unable to create directories or files
            
        Example:
            >>> adapter = CopilotAdapter()
            >>> task = TaskInfo(id="T001", name="Setup database")
            >>> adapter.setup_session(Path("/repo/.worktrees/session-0"), task)
            # Creates /repo/.worktrees/session-0/.github/copilot-instructions.md
        """
        raise NotImplementedError("Subclasses must implement setup_session()")
    
    @abstractmethod
    def notify_user(self, session_id: int, worktree: Path, task: TaskInfo) -> None:
        """Notify user that a session is ready and requires action.
        
        This method displays instructions to the user about how to start working
        on the task in this session. It should:
        - Show the session number and task details
        - Display the worktree path (absolute, copy-pasteable)
        - Provide clear instructions on what to do next
        - Include any agent-specific commands to run
        
        The output should use Rich formatting for clear, visually distinct prompts.
        
        Args:
            session_id: Zero-based session identifier (0, 1, 2, ...)
            worktree: Absolute path to the worktree to open
            task: TaskInfo object with task details to display
            
        Example:
            >>> adapter.notify_user(0, Path("/repo/.worktrees/session-0"), task)
            # Prints Rich Panel:
            # ╭─────────────────────────────────────╮
            # │ Session 0: Setup database           │
            # │                                     │
            # │ Open: /repo/.worktrees/session-0    │
            # │ Run: /copilot.implement             │
            # ╰─────────────────────────────────────╯
        """
        raise NotImplementedError("Subclasses must implement notify_user()")
    
    @abstractmethod
    def get_files_to_watch(self, worktree: Path) -> list[Path]:
        """Return list of files to watch for completion detection.
        
        These files are monitored for changes during task execution. When a
        watched file changes, the completion detection system checks if the
        task has been marked complete.
        
        Most adapters watch the tasks.md file for checkbox changes:
        `- [ ] [T001] ...` → `- [x] [T001] ...`
        
        Args:
            worktree: Path to the worktree being monitored
            
        Returns:
            List of absolute paths to files that indicate task completion
            when modified. Typically includes the tasks.md file in the
            worktree's specs directory.
            
        Example:
            >>> paths = adapter.get_files_to_watch(Path("/repo/.worktrees/session-0"))
            >>> print(paths)
            [Path("/repo/.worktrees/session-0/specs/feature/tasks.md")]
        """
        raise NotImplementedError("Subclasses must implement get_files_to_watch()")
    
    @abstractmethod
    def get_context_file_path(self, worktree: Path) -> Path:
        """Return path to the agent context file in the worktree.
        
        This is the primary file where task context is written for the agent
        to read. The path depends on the agent's conventions:
        - GitHub Copilot: .github/copilot-instructions.md
        - Generic agents: .github/agents/*.agent.md
        - Goose: .goose/instructions.md
        - OpenCode: .opencode/context.md
        
        Args:
            worktree: Path to the worktree
            
        Returns:
            Absolute path to the agent's context file within the worktree
            
        Example:
            >>> path = adapter.get_context_file_path(Path("/repo/.worktrees/session-0"))
            >>> print(path)
            Path("/repo/.worktrees/session-0/.github/copilot-instructions.md")
        """
        raise NotImplementedError("Subclasses must implement get_context_file_path()")
