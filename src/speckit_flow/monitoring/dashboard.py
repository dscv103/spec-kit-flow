"""
Real-time dashboard for monitoring orchestration progress.

This module provides a Rich Live display that shows session status,
DAG phase progress, and overall orchestration state in real-time.
"""

import time
from pathlib import Path
from typing import Optional

from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, ProgressColumn, Task, TextColumn
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from speckit_core.models import SessionStatus, TaskStatus
from speckit_flow.state.manager import StateManager
from speckit_flow.state.models import OrchestrationState

__all__ = ["Dashboard"]


class Dashboard:
    """Real-time terminal dashboard for orchestration monitoring.
    
    Displays a live-updating view of:
    - Session status table (ID, worktree, task, status)
    - DAG phase tree with completion indicators
    - Overall progress bar
    - Next-action prompts with copy-pasteable paths and commands
    
    The dashboard polls the state file at regular intervals and updates
    the display when changes are detected. Next-action prompts guide users
    on what to do next based on the current orchestration state.
    
    Attributes:
        state_manager: StateManager for loading current state
        refresh_rate: Update frequency in seconds
        console: Rich Console for rendering
        
    Example:
        >>> dashboard = Dashboard(StateManager(repo_root))
        >>> dashboard.run(duration=60)  # Run for 60 seconds
    """
    
    def __init__(self, state_manager: StateManager, refresh_rate: float = 0.5):
        """Initialize dashboard.
        
        Args:
            state_manager: StateManager for loading orchestration state
            refresh_rate: How often to poll state file (seconds)
        """
        self.state_manager = state_manager
        self.refresh_rate = refresh_rate
        self.console = Console()
        self._stop = False
    
    def stop(self) -> None:
        """Signal dashboard to stop updating."""
        self._stop = True
    
    def _render_session_table(self, state: OrchestrationState) -> Table:
        """Render session status table.
        
        Args:
            state: Current orchestration state
            
        Returns:
            Rich Table with session information
        """
        table = Table(
            title="Sessions",
            show_header=True,
            header_style="bold cyan",
            box=None,
        )
        
        table.add_column("ID", style="bold", width=4)
        table.add_column("Status", width=12)
        table.add_column("Current Task", width=15)
        table.add_column("Worktree", style="dim")
        
        for session in state.sessions:
            # Status styling
            status_map = {
                SessionStatus.idle: ("idle", "dim"),
                SessionStatus.executing: ("executing", "yellow"),
                SessionStatus.waiting: ("waiting", "blue"),
                SessionStatus.completed: ("completed", "green"),
                SessionStatus.failed: ("failed", "red"),
            }
            status_text, status_style = status_map.get(
                session.status,
                (str(session.status), "")
            )
            
            # Format status with color
            if status_style:
                status_display = f"[{status_style}]{status_text}[/]"
            else:
                status_display = status_text
            
            # Current task
            current_task = session.current_task or "—"
            
            # Worktree path - show relative or basename for readability
            if session.worktree_path:
                worktree_path = Path(session.worktree_path)
                try:
                    # Try relative to state manager's repo root
                    worktree_display = str(worktree_path.relative_to(self.state_manager.repo_root))
                except ValueError:
                    # Fall back to basename
                    worktree_display = worktree_path.name
            else:
                worktree_display = "—"
            
            table.add_row(
                str(session.session_id),
                status_display,
                current_task,
                worktree_display,
            )
        
        return table
    
    def _render_dag_tree(self, state: OrchestrationState) -> Tree:
        """Render DAG phase tree with completion indicators.
        
        Shows hierarchical view of phases and tasks with status icons:
        - ✓ (green): completed
        - ⋯ (yellow): in progress
        - ○ (dim): pending
        
        Args:
            state: Current orchestration state
            
        Returns:
            Rich Tree with phase hierarchy
        """
        tree = Tree("[bold]DAG Progress[/bold]")
        
        # Get task statuses for quick lookup
        task_statuses = {
            task_id: info.status
            for task_id, info in state.tasks.items()
        }
        
        # Group tasks by phase from state
        # We need to reconstruct phases from task dependencies
        # For simplicity, we'll show completed/active/pending sections
        phases_completed = state.phases_completed
        current_phase = state.current_phase
        
        # Add completed phases
        if phases_completed:
            completed_node = tree.add("[green]Completed Phases[/green]")
            for phase_name in phases_completed:
                completed_node.add(f"[green]✓[/green] {phase_name}")
        
        # Add current phase
        if current_phase:
            current_node = tree.add(f"[yellow]Current Phase: {current_phase}[/yellow]")
            
            # Show tasks in current phase (in progress or pending)
            current_phase_tasks = [
                (task_id, info)
                for task_id, info in state.tasks.items()
                if info.status in (TaskStatus.in_progress, TaskStatus.pending)
            ]
            
            for task_id, info in sorted(current_phase_tasks):
                # Status icon
                if info.status == TaskStatus.completed:
                    icon = "[green]✓[/green]"
                elif info.status == TaskStatus.in_progress:
                    icon = "[yellow]⋯[/yellow]"
                elif info.status == TaskStatus.failed:
                    icon = "[red]✗[/red]"
                else:
                    icon = "[dim]○[/dim]"
                
                # Session info
                session_text = f" [dim](session {info.session})[/dim]" if info.session is not None else ""
                
                current_node.add(f"{icon} {task_id}{session_text}")
        
        # Show summary of pending tasks
        pending_count = sum(
            1 for info in state.tasks.values()
            if info.status == TaskStatus.pending
        )
        if pending_count > 0:
            tree.add(f"[dim]Pending: {pending_count} tasks[/dim]")
        
        return tree
    
    def _render_progress_bar(self, state: OrchestrationState) -> Progress:
        """Render overall progress bar.
        
        Shows percentage of tasks completed out of total.
        
        Args:
            state: Current orchestration state
            
        Returns:
            Rich Progress with overall completion
        """
        total_tasks = len(state.tasks)
        completed_tasks = sum(
            1 for info in state.tasks.values()
            if info.status == TaskStatus.completed
        )
        
        progress = Progress(
            TextColumn("[bold]Overall Progress"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total} tasks)"),
        )
        
        progress.add_task(
            "tasks",
            total=total_tasks,
            completed=completed_tasks,
        )
        
        return progress
    
    def _render_next_actions(self, state: OrchestrationState) -> Panel:
        """Render next-action prompts panel.
        
        Shows actionable next steps based on current orchestration state:
        - Open session worktrees in VS Code
        - Wait for specific tasks to complete
        - Run merge command when all complete
        
        Args:
            state: Current orchestration state
            
        Returns:
            Rich Panel with actionable prompts
        """
        # Determine what actions are needed
        actions = []
        
        # Check if all tasks are complete
        all_complete = all(
            info.status == TaskStatus.completed
            for info in state.tasks.values()
        )
        
        if all_complete:
            # All tasks done - prompt for merge
            actions.append(
                "[green]✓[/green] All tasks complete!\n\n"
                "[bold]Next step:[/bold] Integrate changes\n"
                "  [cyan]skf merge[/cyan]"
            )
        else:
            # Find sessions that are executing
            executing_sessions = [
                s for s in state.sessions
                if s.status == SessionStatus.executing
            ]
            
            # Find sessions that need to start
            idle_sessions = [
                s for s in state.sessions
                if s.status == SessionStatus.idle and s.current_task
            ]
            
            # Find waiting tasks
            waiting_tasks = [
                task_id for task_id, info in state.tasks.items()
                if info.status == TaskStatus.in_progress
            ]
            
            # Add prompts for idle sessions
            if idle_sessions:
                for session in idle_sessions[:3]:  # Show max 3 to avoid clutter
                    worktree_path = Path(session.worktree_path) if session.worktree_path else None
                    if worktree_path:
                        # Show relative path if possible
                        try:
                            display_path = worktree_path.relative_to(self.state_manager.repo_root)
                        except (ValueError, AttributeError):
                            display_path = worktree_path
                        
                        actions.append(
                            f"[yellow]⋯[/yellow] [bold]Session {session.session_id}:[/bold] {session.current_task}\n"
                            f"  Open in VS Code:\n"
                            f"  [green]{worktree_path.absolute() if worktree_path else ''}[/green]\n"
                            f"  Run: [cyan]/speckit.implement[/cyan]"
                        )
                
                if len(idle_sessions) > 3:
                    actions.append(
                        f"[dim]... and {len(idle_sessions) - 3} more sessions ready to start[/dim]"
                    )
            
            # Add prompt for waiting tasks
            if waiting_tasks and not idle_sessions:
                if len(waiting_tasks) <= 3:
                    tasks_str = ", ".join(waiting_tasks)
                    actions.append(
                        f"[blue]⏳[/blue] Waiting for tasks to complete:\n"
                        f"  {tasks_str}"
                    )
                else:
                    actions.append(
                        f"[blue]⏳[/blue] Waiting for {len(waiting_tasks)} tasks to complete"
                    )
            
            # Add executing session info
            if executing_sessions and not idle_sessions:
                actions.append(
                    f"[dim]Currently executing:[/dim]\n"
                    + "\n".join(
                        f"  Session {s.session_id}: {s.current_task}"
                        for s in executing_sessions[:3]
                    )
                )
        
        # Combine actions or show default message
        if actions:
            content = "\n\n".join(actions)
        else:
            content = "[dim]No pending actions. Monitoring orchestration...[/dim]"
        
        return Panel(
            content,
            title="[bold cyan]Next Actions[/bold cyan]",
            border_style="cyan",
        )
    
    def _render_dashboard(self, state: OrchestrationState) -> RenderableType:
        """Render complete dashboard layout.
        
        Args:
            state: Current orchestration state
            
        Returns:
            Renderable dashboard layout
        """
        # Title panel
        title = Panel(
            f"[bold]SpecKitFlow Orchestration[/bold]\n"
            f"Spec: {state.spec_id} | Agent: {state.agent_type} | Sessions: {state.num_sessions}",
            border_style="cyan",
        )
        
        # Session table
        session_table = self._render_session_table(state)
        
        # DAG tree
        dag_tree = self._render_dag_tree(state)
        
        # Progress bar
        progress = self._render_progress_bar(state)
        
        # Next actions panel
        next_actions = self._render_next_actions(state)
        
        # Combine into layout
        # Use Group to stack renderables vertically
        layout = Group(
            title,
            Text(),  # Blank line
            session_table,
            Text(),  # Blank line
            dag_tree,
            Text(),  # Blank line
            progress,
            Text(),  # Blank line
            next_actions,
        )
        
        return layout
    
    def run(self, duration: Optional[float] = None) -> None:
        """Run dashboard with live updates.
        
        Polls state file at regular intervals and updates display.
        Runs until duration expires, state shows completion, or stop() called.
        
        Args:
            duration: Optional time limit in seconds (None = run indefinitely)
            
        Example:
            >>> dashboard = Dashboard(state_manager)
            >>> dashboard.run(duration=60)  # Run for 1 minute
        """
        start_time = time.time()
        
        with Live(
            self._get_display(),
            console=self.console,
            refresh_per_second=1 / self.refresh_rate,
            screen=False,  # Don't take over full screen
        ) as live:
            while not self._stop:
                # Check duration limit
                if duration is not None and (time.time() - start_time) >= duration:
                    break
                
                # Update display
                try:
                    live.update(self._get_display())
                except Exception as e:
                    # If we can't load state, show error and retry
                    live.update(
                        Panel(
                            f"[red]Error loading state:[/red] {e}",
                            border_style="red",
                        )
                    )
                
                # Check if orchestration is complete
                try:
                    state = self.state_manager.load()
                    if self._is_complete(state):
                        break
                except Exception:
                    pass
                
                time.sleep(self.refresh_rate)
    
    def _get_display(self) -> RenderableType:
        """Get current dashboard display.
        
        Returns:
            Renderable dashboard or error message
        """
        try:
            state = self.state_manager.load()
            return self._render_dashboard(state)
        except Exception as e:
            return Panel(
                f"[yellow]Waiting for orchestration to start...[/yellow]\n\n"
                f"[dim]State file: {self.state_manager.state_path}[/dim]",
                border_style="yellow",
            )
    
    def _is_complete(self, state: OrchestrationState) -> bool:
        """Check if orchestration is complete.
        
        Args:
            state: Current orchestration state
            
        Returns:
            True if all tasks completed or orchestration failed
        """
        # Check if all tasks are complete or failed
        all_done = all(
            info.status in (TaskStatus.completed, TaskStatus.failed)
            for info in state.tasks.values()
        )
        
        # Check if all sessions are complete or failed
        sessions_done = all(
            session.status in (SessionStatus.completed, SessionStatus.failed)
            for session in state.sessions
        )
        
        return all_done and sessions_done
    
    def render_once(self) -> None:
        """Render dashboard once without live updates.
        
        Useful for single-shot status display or testing.
        """
        try:
            state = self.state_manager.load()
            self.console.print(self._render_dashboard(state))
        except Exception as e:
            self.console.print(
                Panel(
                    f"[red]Error:[/red] {e}",
                    border_style="red",
                )
            )
