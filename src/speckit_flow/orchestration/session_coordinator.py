"""
Session coordination for parallel orchestration.

This module provides the SessionCoordinator class which manages the lifecycle
of multiple parallel agent sessions, including worktree creation, state
initialization, and phase execution.
"""

import signal
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from speckit_core.config import SpecKitFlowConfig
from speckit_core.models import SessionState, SessionStatus, TaskStatus
from speckit_flow.agents.base import AgentAdapter
from speckit_flow.orchestration.completion import CompletionMonitor
from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.state.manager import StateManager
from speckit_flow.state.models import OrchestrationState, TaskStateInfo
from speckit_flow.state.recovery import RecoveryManager
from speckit_flow.worktree.manager import WorktreeManager

__all__ = [
    "SessionCoordinator",
]

# Rich console for formatted output
console = Console()


class SessionCoordinator:
    """Coordinates parallel execution across multiple agent sessions.
    
    This class orchestrates the complete lifecycle of a parallel implementation:
    - Creating isolated worktrees for each session
    - Setting up agent context in each worktree
    - Managing orchestration state
    - Coordinating phase execution
    - Handling completion detection
    
    The coordinator operates in "notification mode" - it prompts users to open
    worktrees in their IDE rather than spawning processes directly.
    
    Attributes:
        dag: DAG engine with task dependency graph
        config: SpecKitFlow configuration
        adapter: AI agent adapter for context setup
        repo_root: Repository root path
        spec_id: Specification identifier (e.g., "001-feature-name")
        base_branch: Base git branch for integration
        state_manager: State persistence manager
        worktree_manager: Git worktree manager
        
    Example:
        >>> from pathlib import Path
        >>> from speckit_core.config import SpecKitFlowConfig
        >>> from speckit_flow.agents.copilot import CopilotIDEAdapter
        >>> 
        >>> dag = DAGEngine(tasks)
        >>> config = SpecKitFlowConfig(agent_type="copilot", num_sessions=3)
        >>> adapter = CopilotIDEAdapter()
        >>> repo_root = Path("/path/to/repo")
        >>> 
        >>> coordinator = SessionCoordinator(
        ...     dag=dag,
        ...     config=config,
        ...     adapter=adapter,
        ...     repo_root=repo_root,
        ...     spec_id="001-feature",
        ...     base_branch="main"
        ... )
        >>> coordinator.initialize()  # Creates worktrees and state
    """
    
    def __init__(
        self,
        dag: DAGEngine,
        config: SpecKitFlowConfig,
        adapter: AgentAdapter,
        repo_root: Path,
        spec_id: str,
        base_branch: Optional[str] = None,
    ):
        """Initialize session coordinator.
        
        Args:
            dag: DAG engine with task dependency graph and phase information
            config: SpecKitFlow configuration with session count and agent type
            adapter: AI agent adapter for setting up context in worktrees
            repo_root: Repository root directory path
            spec_id: Specification identifier (e.g., "001-feature-name")
            base_branch: Base git branch for integration (defaults to current branch)
            
        Example:
            >>> coordinator = SessionCoordinator(
            ...     dag, config, adapter,
            ...     repo_root=Path("/repo"),
            ...     spec_id="001-feature",
            ...     base_branch="main"
            ... )
        """
        self.dag = dag
        self.config = config
        self.adapter = adapter
        self.repo_root = Path(repo_root)
        self.spec_id = spec_id
        
        # Determine base branch (default to "main" if not specified)
        if base_branch is None:
            # Could query git for current branch, but for now use "main" as default
            self.base_branch = "main"
        else:
            self.base_branch = base_branch
        
        # Initialize managers
        self.state_manager = StateManager(self.repo_root)
        self.worktree_manager = WorktreeManager(self.repo_root)
        self.recovery_manager = RecoveryManager(self.repo_root)
        self.completion_monitor = CompletionMonitor(self.spec_id, self.repo_root)
        
        # Track keyboard interrupt for graceful shutdown
        self._interrupted = False
    
    def initialize(self) -> None:
        """Initialize orchestration session.
        
        This method:
        1. Assigns tasks to sessions based on DAG phases
        2. Creates git worktrees for all sessions
        3. Sets up agent context files in each worktree
        4. Initializes the orchestration state file
        
        The initialization creates the following structure:
        - `.worktrees-{spec-id}/session-{N}-{task-name}/` for each session
        - `.speckit/flow-state.yaml` with initial state
        - Agent context files in each worktree (e.g., .github/copilot-instructions.md)
        
        Raises:
            WorktreeExistsError: If worktrees already exist
            OSError: If unable to create directories or files
            
        Example:
            >>> coordinator = SessionCoordinator(
            ...     dag, config, adapter,
            ...     repo_root, spec_id, base_branch
            ... )
            >>> coordinator.initialize()
            # Creates 3 worktrees with agent context
            # Creates state file in .speckit/flow-state.yaml
        """
        # Assign tasks to sessions using DAG's round-robin distribution
        self.dag.assign_sessions(self.config.num_sessions)
        
        # Get current timestamp for state initialization
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Create worktrees and session states
        sessions: list[SessionState] = []
        
        # For each session, create worktree and setup context
        for session_id in range(self.config.num_sessions):
            # Get tasks assigned to this session
            session_tasks = self.dag.get_session_tasks(session_id)
            
            if not session_tasks:
                # No tasks for this session - this can happen if
                # num_sessions > num_tasks
                continue
            
            # Use first task name for worktree directory
            first_task = session_tasks[0]
            
            # Create worktree
            worktree_path = self.worktree_manager.create(
                spec_id=self.spec_id,
                session_id=session_id,
                task_name=first_task.name
            )
            
            # Setup agent context in the worktree
            self.adapter.setup_session(worktree_path, first_task)
            
            # Create session state
            # Store relative path for portability
            relative_worktree = worktree_path.relative_to(self.repo_root)
            session_state = SessionState(
                session_id=session_id,
                worktree_path=str(relative_worktree),
                branch_name=f"impl-{self.spec_id}-session-{session_id}",
                current_task=None,  # Will be set when phase execution starts
                completed_tasks=[],
                status=SessionStatus.idle
            )
            sessions.append(session_state)
        
        # Build task states dictionary
        tasks_dict: dict[str, TaskStateInfo] = {}
        for task in self.dag.tasks:
            tasks_dict[task.id] = TaskStateInfo(
                status=TaskStatus.pending,
                session=task.session,
                started_at=None,
                completed_at=None
            )
        
        # Create initial orchestration state
        state = OrchestrationState(
            version="1.0",
            spec_id=self.spec_id,
            agent_type=self.config.agent_type,
            num_sessions=self.config.num_sessions,
            base_branch=self.base_branch,
            started_at=now,
            updated_at=now,
            current_phase="phase-0",
            phases_completed=[],
            sessions=sessions,
            tasks=tasks_dict,
            merge_status=None
        )
        
        # Save initial state
        self.state_manager.save(state)
    
    def run_phase(self, phase_idx: int) -> None:
        """Execute a single DAG phase with parallel task execution.
        
        This method orchestrates the execution of one phase:
        1. Identifies tasks for the current phase
        2. Assigns tasks to sessions
        3. Notifies user to open worktrees in IDE for each active session
        4. Monitors for task completion (both manual and watched)
        5. Waits for all phase tasks to complete
        6. Updates orchestration state
        
        The execution uses IDE notification mode - prompting users to open
        worktrees rather than spawning processes. Task completion is detected
        via dual mechanisms: touch files and tasks.md checkbox watching.
        
        Args:
            phase_idx: Zero-based phase index to execute
            
        Raises:
            KeyboardInterrupt: If user interrupts execution (Ctrl+C)
            TimeoutError: If tasks don't complete within reasonable time
            ValueError: If phase_idx is out of range
            
        Example:
            >>> coordinator = SessionCoordinator(dag, config, adapter, repo_root, spec_id)
            >>> coordinator.initialize()
            >>> coordinator.run_phase(0)  # Execute phase 0
            # User opens worktrees in IDE, implements tasks
            # Method blocks until all phase 0 tasks are complete
        """
        # Validate phase index
        phases = self.dag.get_phases()
        if phase_idx < 0 or phase_idx >= len(phases):
            raise ValueError(
                f"Invalid phase index {phase_idx}. "
                f"Valid range: 0-{len(phases) - 1}"
            )
        
        # Get task IDs for this phase
        phase_task_ids = phases[phase_idx]
        phase_name = f"phase-{phase_idx}"
        
        console.print()
        console.print(f"[bold cyan]Starting {phase_name}[/bold cyan] "
                     f"({len(phase_task_ids)} tasks)")
        console.print()
        
        # Load current state
        state = self.state_manager.load()
        
        # Update state to reflect current phase
        state.current_phase = phase_name
        state.mark_updated()
        
        # Group tasks by session
        session_tasks: dict[int, list[str]] = {}
        for task_id in phase_task_ids:
            # Get task info from DAG
            task_info = next((t for t in self.dag.tasks if t.id == task_id), None)
            if task_info is None:
                continue
            
            session_id = task_info.session
            if session_id is None:
                # Task not assigned to session - assign to session 0
                session_id = 0
            
            session_tasks.setdefault(session_id, []).append(task_id)
        
        # Update task states to in_progress and notify users for each session
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        for session_id, task_ids_in_session in session_tasks.items():
            # Find session state
            session_state = next(
                (s for s in state.sessions if s.session_id == session_id),
                None
            )
            if session_state is None:
                console.print(f"[yellow]Warning:[/yellow] Session {session_id} not found")
                continue
            
            # Update session status
            session_state.status = SessionStatus.executing
            
            # Set current task to first task in phase for this session
            first_task_id = task_ids_in_session[0]
            session_state.current_task = first_task_id
            
            # Update all task states for this session in this phase
            for task_id in task_ids_in_session:
                if task_id in state.tasks:
                    state.tasks[task_id].status = TaskStatus.in_progress
                    state.tasks[task_id].started_at = now
            
            # Get task info for notification
            first_task = next((t for t in self.dag.tasks if t.id == first_task_id), None)
            if first_task is None:
                continue
            
            # Get worktree path (stored as relative, convert to absolute)
            worktree_path = self.repo_root / session_state.worktree_path
            
            # Notify user to open worktree in IDE
            try:
                self.adapter.notify_user(session_id, worktree_path, first_task)
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Failed to notify user: {e}")
        
        # Save updated state
        state.mark_updated()
        self.state_manager.save(state)
        
        # Set up completion detection
        # Get path to tasks.md for file watching
        try:
            from speckit_core.paths import get_current_branch
            branch = get_current_branch()
            tasks_file = self.repo_root / "specs" / branch / "tasks.md"
        except Exception:
            # If we can't determine branch, try common locations
            tasks_file = None
            for possible_branch in ["main", "master", self.base_branch]:
                candidate = self.repo_root / "specs" / possible_branch / "tasks.md"
                if candidate.exists():
                    tasks_file = candidate
                    break
        
        # Convert task IDs to set for completion checking
        phase_task_ids_set = set(phase_task_ids)
        
        console.print("[cyan]Waiting for tasks to complete...[/cyan]")
        console.print("[dim]Mark tasks complete in tasks.md or run: "
                     f"skf complete TASK_ID[/dim]")
        console.print()
        
        # Set up keyboard interrupt handler
        original_handler = signal.signal(signal.SIGINT, self._handle_interrupt)
        
        try:
            # Wait for all phase tasks to complete
            # Use completion monitor's unified checking (manual + watched)
            completed = self.completion_monitor.wait_for_completion(
                task_ids=phase_task_ids_set,
                tasks_file=tasks_file,
                timeout=None,  # Wait indefinitely
                poll_interval=0.5
            )
            
            # All tasks completed successfully
            console.print()
            console.print(f"[green]✓[/green] Phase {phase_idx} complete "
                         f"({len(completed)} tasks)")
            console.print()
            
        except TimeoutError as e:
            # This shouldn't happen with timeout=None, but handle it
            console.print()
            console.print(f"[red]Error:[/red] Timeout waiting for completion")
            console.print(f"[dim]{e}[/dim]")
            raise
            
        except KeyboardInterrupt:
            # User pressed Ctrl+C - set interrupted flag
            self._interrupted = True
            console.print()
            console.print("[yellow]⚠[/yellow] Interrupted by user")
            console.print()
            
            # Restore original handler
            signal.signal(signal.SIGINT, original_handler)
            
            # Re-raise to allow caller to handle
            raise
            
        finally:
            # Restore original signal handler
            signal.signal(signal.SIGINT, original_handler)
        
        # Update state with completed tasks
        state = self.state_manager.load()
        completion_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        for task_id in phase_task_ids:
            if task_id in state.tasks:
                state.tasks[task_id].status = TaskStatus.completed
                state.tasks[task_id].completed_at = completion_time
        
        # Update session states
        for session_id in session_tasks.keys():
            session_state = next(
                (s for s in state.sessions if s.session_id == session_id),
                None
            )
            if session_state is not None:
                # Add completed tasks to session's completed list
                session_state.completed_tasks.extend(
                    [tid for tid in session_tasks[session_id]]
                )
                
                # Set status to idle (waiting for next phase)
                session_state.status = SessionStatus.idle
                session_state.current_task = None
        
        # Mark phase as completed
        if phase_name not in state.phases_completed:
            state.phases_completed.append(phase_name)
        
        state.mark_updated()
        self.state_manager.save(state)
    
    def checkpoint_phase(self) -> Path:
        """Create a checkpoint snapshot after phase completion.
        
        Saves the current orchestration state to a timestamped checkpoint
        file in .speckit/checkpoints/ for recovery purposes. Checkpoints
        enable resuming orchestration after failures or interruptions.
        
        Returns:
            Path to created checkpoint file
            
        Raises:
            StateNotFoundError: If no orchestration state exists
            OSError: If unable to write checkpoint
            
        Example:
            >>> coordinator = SessionCoordinator(dag, config, adapter, repo_root, spec_id)
            >>> coordinator.initialize()
            >>> coordinator.run_phase(0)
            >>> checkpoint_path = coordinator.checkpoint_phase()
            >>> print(f"Checkpoint saved: {checkpoint_path}")
        """
        # Load current state
        state = self.state_manager.load()
        
        # Create checkpoint
        checkpoint_path = self.recovery_manager.checkpoint(state)
        
        console.print(f"[dim]Checkpoint saved: {checkpoint_path.name}[/dim]")
        
        return checkpoint_path
    
    def run(self) -> None:
        """Execute full orchestration workflow across all phases.
        
        This is the main orchestration method that:
        1. Initializes orchestration if not already running (creates worktrees, state)
        2. Resumes from current phase if restarting after interruption
        3. Iterates through all DAG phases in order
        4. Creates checkpoints after each phase completion
        5. Marks orchestration complete when all phases finish
        6. Handles graceful shutdown on SIGINT/SIGTERM
        
        The method maintains orchestration state throughout execution, allowing
        recovery after crashes or interruptions. State is checkpointed after each
        phase, and Ctrl+C triggers a graceful shutdown that saves state.
        
        Raises:
            KeyboardInterrupt: If user interrupts (after saving state)
            Exception: For unrecoverable errors during orchestration
            
        Example:
            >>> coordinator = SessionCoordinator(
            ...     dag, config, adapter,
            ...     repo_root, spec_id, base_branch
            ... )
            >>> # Start fresh orchestration
            >>> coordinator.run()
            # Creates worktrees, executes all phases
            # User can Ctrl+C to interrupt gracefully
            
            >>> # Resume after interruption
            >>> coordinator.run()
            # Resumes from last completed phase
        """
        # Install signal handlers for graceful shutdown
        original_sigint = signal.signal(signal.SIGINT, self._handle_interrupt)
        original_sigterm = signal.signal(signal.SIGTERM, self._handle_interrupt)
        
        try:
            # Check if orchestration is already initialized
            if self.state_manager.exists():
                # Load existing state
                state = self.state_manager.load()
                
                console.print()
                console.print("[yellow]⚠[/yellow] Resuming orchestration "
                             f"from {state.current_phase}")
                console.print()
                
                # Determine starting phase
                phases = self.dag.get_phases()
                phase_names = [f"phase-{i}" for i in range(len(phases))]
                
                # Find current phase index
                if state.current_phase in state.phases_completed:
                    # Current phase is already completed, start from next phase
                    current_idx = phase_names.index(state.current_phase)
                    start_phase = current_idx + 1
                else:
                    # Resume current phase
                    start_phase = phase_names.index(state.current_phase)
                
            else:
                # Initialize new orchestration
                console.print()
                console.print("[bold cyan]Initializing orchestration...[/bold cyan]")
                console.print()
                
                self.initialize()
                
                console.print("[green]✓[/green] Orchestration initialized")
                console.print()
                
                # Start from phase 0
                start_phase = 0
            
            # Get all phases
            phases = self.dag.get_phases()
            total_phases = len(phases)
            
            console.print(f"[bold]Orchestration Plan:[/bold] {total_phases} phases, "
                         f"{len(self.dag.tasks)} tasks total")
            console.print()
            
            # Execute phases from start_phase onwards
            for phase_idx in range(start_phase, total_phases):
                # Check if interrupted
                if self._interrupted:
                    console.print()
                    console.print("[yellow]⚠[/yellow] Orchestration interrupted")
                    console.print("[dim]State saved. Run again to resume.[/dim]")
                    console.print()
                    break
                
                try:
                    # Execute this phase
                    self.run_phase(phase_idx)
                    
                    # Create checkpoint after successful phase completion
                    self.checkpoint_phase()
                    
                except KeyboardInterrupt:
                    # User pressed Ctrl+C during phase execution
                    console.print()
                    console.print("[yellow]⚠[/yellow] Interrupted during phase execution")
                    console.print("[dim]State saved. Run again to resume.[/dim]")
                    console.print()
                    
                    # Set interrupted flag
                    self._interrupted = True
                    
                    # Break out of phase loop
                    break
                
                except Exception as e:
                    # Unexpected error during phase execution
                    console.print()
                    console.print(f"[red]Error during phase {phase_idx}:[/red] {e}")
                    console.print()
                    console.print("[dim]State saved. Fix the issue and run again to resume.[/dim]")
                    console.print()
                    raise
            
            # Check if all phases completed successfully
            if not self._interrupted and start_phase < total_phases:
                # Mark orchestration as complete
                state = self.state_manager.load()
                
                # Update all session statuses to completed
                for session in state.sessions:
                    session.status = SessionStatus.completed
                    session.current_task = None
                
                # Update state
                state.mark_updated()
                self.state_manager.save(state)
                
                # Create final checkpoint
                self.checkpoint_phase()
                
                console.print()
                console.print("[bold green]✓ Orchestration Complete![/bold green]")
                console.print()
                console.print(f"  [dim]Total tasks:[/dim] {len(state.tasks)}")
                
                # Count completed tasks
                completed_count = sum(
                    1 for task in state.tasks.values()
                    if task.status == TaskStatus.completed
                )
                console.print(f"  [dim]Completed:[/dim] {completed_count}")
                console.print()
                console.print("[cyan]Next steps:[/cyan]")
                console.print("  • Review changes in session worktrees")
                console.print("  • Run [cyan]skf merge[/cyan] to integrate branches")
                console.print()
        
        finally:
            # Restore original signal handlers
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
    
    def _handle_interrupt(self, signum, frame):
        """Signal handler for keyboard interrupt (Ctrl+C).
        
        Sets the interrupted flag and allows graceful shutdown.
        This handler is temporarily installed during phase execution.
        """
        self._interrupted = True
        # Don't raise here - let the wait_for_completion handle it
