"""
SpecKitFlow - Parallel DAG-based orchestration for AI coding agents.

This package provides:
- DAG-based task dependency resolution
- Git worktree management for parallel sessions
- State management and checkpoint/recovery
- Agent adapters (starting with GitHub Copilot)
- CLI commands: skf, speckit-flow
"""

__version__ = "0.1.0"

import threading
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from speckit_core.config import SpecKitFlowConfig, load_config, save_config
from speckit_core.exceptions import ConfigurationError, FeatureNotFoundError, NotInGitRepoError
from speckit_core.models import SessionStatus, TaskStatus
from speckit_core.paths import get_current_branch, get_feature_paths, get_repo_root
from speckit_core.tasks import parse_tasks_file
from speckit_flow.agents.copilot import CopilotIDEAdapter
from speckit_flow.exceptions import CyclicDependencyError, StateNotFoundError
from speckit_flow.monitoring.dashboard import Dashboard
from speckit_flow.orchestration.completion import CompletionMonitor
from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.orchestration.session_coordinator import SessionCoordinator
from speckit_flow.state.manager import StateManager
from speckit_flow.worktree.merger import MergeOrchestrator

# Create Rich console for output
console = Console()

# Create Typer app for CLI
app = typer.Typer(
    name="skf",
    help="SpecKitFlow: Parallel DAG-based orchestration for AI coding agents",
    no_args_is_help=True,
)


def _visualize_dag(engine: DAGEngine) -> None:
    """Generate ASCII tree visualization of DAG phases and tasks.
    
    Creates a Rich Tree showing:
    - Phase hierarchy as parent nodes
    - Tasks within each phase as child nodes
    - Task dependencies inline (e.g., "T003 (deps: T001, T002)")
    - [P] marker for parallelizable tasks
    - Session assignment for each task (e.g., "[Session 0]")
    - Colors to distinguish phases from tasks
    
    Args:
        engine: DAGEngine with built graph and assigned sessions
    """
    # Create root tree
    tree = Tree("[bold]DAG Phases[/bold]")
    
    # Get phases
    phases = engine.get_phases()
    
    if not phases:
        console.print("[yellow]No phases to display[/yellow]")
        return
    
    # Add each phase and its tasks
    for phase_idx, phase_tasks in enumerate(phases):
        # Determine if phase is parallelizable
        parallelizable_count = sum(
            1 for tid in phase_tasks 
            if engine.get_task(tid).parallelizable
        )
        
        # Phase node styling
        if parallelizable_count > 0:
            phase_style = "cyan"
            phase_label = f"Phase {phase_idx} ({len(phase_tasks)} tasks, {parallelizable_count} parallel)"
        else:
            phase_style = "yellow"
            phase_label = f"Phase {phase_idx} ({len(phase_tasks)} tasks)"
        
        phase_node = tree.add(f"[{phase_style}]{phase_label}[/]")
        
        # Add tasks to phase
        for task_id in phase_tasks:
            task = engine.get_task(task_id)
            
            # Build task label
            task_parts = [task_id]
            
            # Add [P] marker if parallelizable
            if task.parallelizable:
                task_parts.append("[P]")
            
            # Add task name
            task_parts.append(task.name)
            
            # Add session assignment if set
            if task.session is not None:
                task_parts.append(f"[dim][Session {task.session}][/]")
            
            # Add dependencies inline if present
            if task.dependencies:
                deps_str = ", ".join(task.dependencies)
                task_parts.append(f"[dim](deps: {deps_str})[/]")
            
            task_label = " ".join(task_parts)
            phase_node.add(task_label)
    
    # Print the tree
    console.print()
    console.print(tree)
    console.print()


@app.command()
def dag(
    sessions: int = typer.Option(
        3,
        "--sessions", "-s",
        min=1,
        help="Number of parallel sessions for task assignment",
    ),
    visualize: bool = typer.Option(
        False,
        "--visualize", "-v",
        help="Display ASCII tree of phases and tasks",
    ),
) -> None:
    """Generate DAG from tasks.md and save to specs/{branch}/dag.yaml.
    
    This command:
    1. Locates the current feature's tasks.md file
    2. Parses tasks with their dependencies
    3. Builds a directed acyclic graph (DAG)
    4. Validates for circular dependencies
    5. Assigns tasks to sessions
    6. Saves the DAG to specs/{branch}/dag.yaml
    
    Examples:
        skf dag              # Use default 3 sessions
        skf dag --sessions 5 # Override to 5 sessions
    """
    try:
        # Get repository root and feature paths
        repo_root = get_repo_root()
        branch = get_current_branch()
        feature_context = get_feature_paths(repo_root, branch)
        
        # Check if tasks.md exists
        if not feature_context.tasks_path.exists():
            console.print(f"[red]Error:[/red] Tasks file not found: {feature_context.tasks_path}")
            console.print()
            console.print("[dim]Expected location:[/dim]")
            console.print(f"  specs/{{branch}}/tasks.md")
            console.print()
            console.print("[dim]To create tasks, run:[/dim]")
            console.print("  specify plan  [dim]# Generate implementation plan[/dim]")
            console.print("  specify tasks [dim]# Generate tasks from plan[/dim]")
            raise typer.Exit(1)
        
        # Parse tasks from file
        console.print(f"[cyan]→[/cyan] Parsing tasks from {feature_context.tasks_path.name}...")
        tasks = parse_tasks_file(feature_context.tasks_path)
        
        if not tasks:
            console.print("[yellow]Warning:[/yellow] No tasks found in tasks.md")
            console.print()
            console.print("[dim]The tasks file exists but contains no parseable tasks.[/dim]")
            console.print("[dim]Ensure tasks follow the format:[/dim]")
            console.print("  - [ ] [T001] [deps:] Task description")
            console.print()
            console.print("[yellow]Common issues:[/yellow]")
            console.print("  • Task IDs must be in brackets: [T001] not T001")
            console.print("  • Task IDs must have exactly 3 digits: [T001] not [T1]")
            console.print("  • Lines must start with checkbox: - [ ] or - [x]")
            console.print()
            console.print("[cyan]To fix existing tasks.md:[/cyan]")
            console.print("  sed -i -E 's/^(- \\[[x ]\\] )T([0-9]{3})\\b/\\1[T\\2]/' tasks.md")
            console.print()
            console.print("[cyan]Or regenerate with:[/cyan]")
            console.print("  /speckit.tasks [dim]# In your AI agent[/dim]")
            console.print()
            console.print("[dim]See docs/task-format-migration.md for detailed migration guide[/dim]")
            raise typer.Exit(1)
        
        # Build DAG
        console.print(f"[cyan]→[/cyan] Building dependency graph...")
        engine = DAGEngine(tasks)
        
        # Validate (will raise CyclicDependencyError if cycles exist)
        try:
            engine.validate()
        except CyclicDependencyError as e:
            console.print(f"[red]Error:[/red] Circular dependency detected")
            console.print()
            console.print("[red]Cycle:[/red]", " → ".join(e.cycle))
            console.print()
            console.print("[dim]Fix the dependency cycle in tasks.md and try again.[/dim]")
            raise typer.Exit(1)
        
        # Assign tasks to sessions
        console.print(f"[cyan]→[/cyan] Assigning tasks to {sessions} session(s)...")
        engine.assign_sessions(sessions)
        
        # Determine spec_id from feature directory name
        spec_id = feature_context.feature_dir.name
        
        # Save DAG to specs/{branch}/dag.yaml
        dag_path = feature_context.feature_dir / "dag.yaml"
        console.print(f"[cyan]→[/cyan] Saving DAG to {dag_path.relative_to(repo_root)}...")
        engine.save(dag_path, spec_id, sessions)
        
        # Print summary
        console.print()
        console.print("[green]✓[/green] DAG generated successfully")
        console.print()
        console.print("[bold]Summary[/bold]")
        console.print(f"  Tasks:    {engine.task_count}")
        console.print(f"  Phases:   {engine.phase_count}")
        console.print(f"  Sessions: {sessions}")
        console.print()
        
        # Show phase breakdown
        phases = engine.get_phases()
        for i, phase_tasks in enumerate(phases):
            parallel_count = sum(1 for tid in phase_tasks if engine.get_task(tid).parallelizable)
            console.print(f"  Phase {i}: {len(phase_tasks)} task(s)", end="")
            if parallel_count > 0:
                console.print(f" ({parallel_count} parallelizable)", style="dim")
            else:
                console.print()
        
        console.print()
        console.print(f"[dim]Output:[/dim] {dag_path.relative_to(repo_root)}")
        
        # Display visualization if requested
        if visualize:
            _visualize_dag(engine)
        
    except NotInGitRepoError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print()
        console.print("[dim]Run 'git init' to create a git repository.[/dim]")
        raise typer.Exit(1)
        
    except FeatureNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print()
        console.print("[dim]Create a feature branch or set SPECIFY_FEATURE environment variable.[/dim]")
        raise typer.Exit(1)
        
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        console.print()
        console.print("[dim]Please report this issue at:[/dim]")
        console.print("  https://github.com/dscv103/spec-kit-flow/issues")
        raise typer.Exit(1)


@app.command()
def init(
    sessions: int = typer.Option(
        3,
        "--sessions", "-s",
        min=1,
        max=10,
        help="Number of parallel sessions (1-10)",
    ),
    agent: str = typer.Option(
        "copilot",
        "--agent", "-a",
        help="AI agent to use (copilot, goose, opencode, etc.)",
    ),
) -> None:
    """Initialize SpecKitFlow configuration for this project.
    
    Creates .speckit/speckit-flow.yaml with orchestration settings.
    
    This command:
    1. Validates you're in a git repository
    2. Checks that a specs/ directory exists
    3. Creates .speckit/speckit-flow.yaml with your preferences
    
    Examples:
        skf init                    # Use defaults (copilot, 3 sessions)
        skf init --sessions 5       # Override session count
        skf init --agent goose      # Use different agent
    """
    try:
        # Validate we're in a git repository
        try:
            repo_root = get_repo_root()
        except NotInGitRepoError:
            console.print("[red]Error:[/red] Not in a git repository")
            console.print()
            console.print("[dim]SpecKitFlow requires a git repository.[/dim]")
            console.print("[dim]Run 'git init' to create one.[/dim]")
            raise typer.Exit(1)
        
        # Validate specs/ directory exists
        specs_dir = repo_root / "specs"
        if not specs_dir.exists() or not specs_dir.is_dir():
            console.print(f"[red]Error:[/red] specs/ directory not found")
            console.print()
            console.print(f"[dim]Expected location:[/dim] {specs_dir}")
            console.print()
            console.print("[dim]SpecKitFlow requires a spec-kit project structure.[/dim]")
            console.print("[dim]Create the specs/ directory or run this in a spec-kit project.[/dim]")
            raise typer.Exit(1)
        
        # Check if config already exists
        config_path = repo_root / ".speckit" / "speckit-flow.yaml"
        if config_path.exists():
            console.print("[yellow]Warning:[/yellow] Configuration already exists")
            console.print()
            console.print(f"[dim]Location:[/dim] {config_path.relative_to(repo_root)}")
            console.print()
            
            # Prompt to overwrite
            if not typer.confirm("Overwrite existing configuration?"):
                console.print()
                console.print("[dim]Configuration unchanged.[/dim]")
                raise typer.Exit(0)
            console.print()
        
        # Create configuration
        console.print("[cyan]→[/cyan] Creating SpecKitFlow configuration...")
        config = SpecKitFlowConfig(
            agent_type=agent,
            num_sessions=sessions,
        )
        save_config(config, repo_root)
        
        # Success message
        console.print()
        console.print("[green]✓[/green] SpecKitFlow initialized successfully")
        console.print()
        console.print("[bold]Configuration[/bold]")
        console.print(f"  Agent:    {config.agent_type}")
        console.print(f"  Sessions: {config.num_sessions}")
        console.print()
        console.print(f"[dim]Config file:[/dim] {config_path.relative_to(repo_root)}")
        console.print()
        console.print("[bold]Next steps[/bold]")
        console.print("  1. Ensure your tasks.md exists in a feature branch")
        console.print("  2. Run: [cyan]skf dag[/cyan] to generate dependency graph")
        console.print("  3. Run: [cyan]skf run[/cyan] to start parallel orchestration")
        console.print()
        
    except Exception as e:
        # Catch-all for unexpected errors
        if not isinstance(e, typer.Exit):
            console.print(f"[red]Unexpected error:[/red] {e}")
            console.print()
            console.print("[dim]Please report this issue at:[/dim]")
            console.print("  https://github.com/dscv103/spec-kit-flow/issues")
            raise typer.Exit(1)
        raise


@app.command()
def run(
    sessions: int = typer.Option(
        None,
        "--sessions", "-s",
        min=1,
        max=10,
        help="Number of parallel sessions [default: from config]",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Resume from last checkpoint instead of starting fresh",
    ),
    dashboard: bool = typer.Option(
        True,
        "--dashboard/--no-dashboard",
        help="Show live dashboard during orchestration",
    ),
) -> None:
    """Execute parallel orchestration across multiple agent sessions.
    
    This command orchestrates the complete parallel implementation workflow:
    1. Loads configuration from .speckit/speckit-flow.yaml
    2. Parses tasks and builds DAG from tasks.md
    3. Creates git worktrees for each session (if not resuming)
    4. Prompts you to open each worktree in VS Code
    5. Monitors task completion across all sessions
    6. Advances through DAG phases automatically
    7. Creates checkpoints after each phase
    
    The orchestration uses IDE notification mode - you open worktrees in your
    IDE rather than the tool spawning processes. Task completion is detected
    via dual mechanisms: manual marking (skf complete) and tasks.md watching.
    
    State is persisted throughout execution, allowing graceful interruption
    (Ctrl+C) and resumption. Checkpoints are created after each phase.
    
    A live dashboard can optionally display real-time progress. Use
    --no-dashboard to disable for CI/scripting environments.
    
    Examples:
        skf run                      # Run with config defaults and dashboard
        skf run --sessions 4         # Override session count
        skf run --resume             # Resume interrupted orchestration
        skf run --no-dashboard       # Disable live dashboard (for CI)
    """
    try:
        # Get repository root
        try:
            repo_root = get_repo_root()
        except NotInGitRepoError:
            console.print("[red]Error:[/red] Not in a git repository")
            console.print()
            console.print("[dim]SpecKitFlow requires a git repository.[/dim]")
            console.print("[dim]Run 'git init' to create one.[/dim]")
            raise typer.Exit(1)
        
        # Load configuration
        try:
            config = load_config(repo_root)
        except ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print()
            console.print("[dim]Run 'skf init' to create configuration.[/dim]")
            raise typer.Exit(1)
        
        # Override session count if provided
        if sessions is not None:
            config.num_sessions = sessions
            console.print(f"[dim]Using {sessions} sessions (overriding config)[/dim]")
            console.print()
        
        # Get feature context
        try:
            branch = get_current_branch()
            feature_context = get_feature_paths(repo_root, branch)
        except FeatureNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print()
            console.print("[dim]Create a feature branch or set SPECIFY_FEATURE environment variable.[/dim]")
            raise typer.Exit(1)
        
        # Check if tasks.md exists
        if not feature_context.tasks_path.exists():
            console.print(f"[red]Error:[/red] Tasks file not found: {feature_context.tasks_path}")
            console.print()
            console.print("[dim]Expected location:[/dim]")
            console.print(f"  specs/{{branch}}/tasks.md")
            console.print()
            console.print("[dim]To create tasks, run:[/dim]")
            console.print("  specify plan  [dim]# Generate implementation plan[/dim]")
            console.print("  specify tasks [dim]# Generate tasks from plan[/dim]")
            raise typer.Exit(1)
        
        # Parse tasks
        console.print(f"[cyan]→[/cyan] Loading tasks from {feature_context.tasks_path.name}...")
        tasks = parse_tasks_file(feature_context.tasks_path)
        
        if not tasks:
            console.print("[yellow]Warning:[/yellow] No tasks found in tasks.md")
            console.print()
            console.print("[dim]The tasks file exists but contains no parseable tasks.[/dim]")
            console.print("[dim]Ensure tasks follow the format:[/dim]")
            console.print("  - [ ] [T001] [deps:] Task description")
            console.print()
            console.print("[yellow]Common issues:[/yellow]")
            console.print("  • Task IDs must be in brackets: [T001] not T001")
            console.print("  • Task IDs must have exactly 3 digits: [T001] not [T1]")
            console.print("  • Lines must start with checkbox: - [ ] or - [x]")
            console.print()
            console.print("[cyan]To fix existing tasks.md:[/cyan]")
            console.print("  sed -i -E 's/^(- \\[[x ]\\] )T([0-9]{3})\\b/\\1[T\\2]/' tasks.md")
            console.print()
            console.print("[cyan]Or regenerate with:[/cyan]")
            console.print("  /speckit.tasks [dim]# In your AI agent[/dim]")
            console.print()
            console.print("[dim]See docs/task-format-migration.md for detailed migration guide[/dim]")
            raise typer.Exit(1)
        
        # Build DAG
        console.print(f"[cyan]→[/cyan] Building dependency graph...")
        try:
            engine = DAGEngine(tasks)
            engine.validate()
        except CyclicDependencyError as e:
            console.print(f"[red]Error:[/red] Circular dependency detected")
            console.print()
            console.print("[red]Cycle:[/red]", " → ".join(e.cycle))
            console.print()
            console.print("[dim]Fix the dependency cycle in tasks.md and try again.[/dim]")
            raise typer.Exit(1)
        
        # Determine spec_id from feature directory name
        spec_id = feature_context.feature_dir.name
        
        # Get current branch as base branch
        try:
            base_branch = get_current_branch()
        except Exception:
            # Fallback to "main" if unable to determine
            base_branch = "main"
        
        # Create appropriate agent adapter
        # For now, only Copilot is implemented
        if config.agent_type == "copilot":
            adapter = CopilotIDEAdapter()
        else:
            console.print(f"[red]Error:[/red] Unsupported agent type: {config.agent_type}")
            console.print()
            console.print("[dim]Supported agents: copilot[/dim]")
            console.print("[dim]More agents coming soon![/dim]")
            raise typer.Exit(1)
        
        # Create session coordinator
        console.print(f"[cyan]→[/cyan] Setting up session coordinator...")
        coordinator = SessionCoordinator(
            dag=engine,
            config=config,
            adapter=adapter,
            repo_root=repo_root,
            spec_id=spec_id,
            base_branch=base_branch,
        )
        
        # Check if resume flag was set but no state exists
        if resume and not coordinator.state_manager.exists():
            console.print("[yellow]Warning:[/yellow] --resume flag set but no orchestration state found")
            console.print()
            console.print("[dim]Starting fresh orchestration...[/dim]")
            console.print()
        
        # Set up dashboard thread if enabled
        dashboard_thread = None
        dashboard_instance = None
        
        if dashboard:
            # Create dashboard instance
            dashboard_instance = Dashboard(
                state_manager=coordinator.state_manager,
                refresh_rate=0.5,  # Update twice per second
            )
            
            # Launch dashboard in background thread
            dashboard_thread = threading.Thread(
                target=dashboard_instance.run,
                name="dashboard",
                daemon=True,  # Allow main thread to exit
            )
            dashboard_thread.start()
            console.print("[dim]Dashboard started (live updates enabled)[/dim]")
            console.print()
        
        # Run full orchestration
        try:
            coordinator.run()
        except KeyboardInterrupt:
            # User interrupted - state was already saved by coordinator
            # Stop dashboard if running
            if dashboard_instance is not None:
                dashboard_instance.stop()
            
            console.print()
            console.print("[yellow]⚠[/yellow] Orchestration interrupted by user")
            console.print()
            console.print("[dim]State saved. Run 'skf run' again to resume.[/dim]")
            console.print()
            raise typer.Exit(0)
        finally:
            # Ensure dashboard stops cleanly
            if dashboard_instance is not None:
                dashboard_instance.stop()
            
            # Wait for dashboard thread to finish (with timeout)
            if dashboard_thread is not None and dashboard_thread.is_alive():
                dashboard_thread.join(timeout=1.0)
        
        # Success!
        console.print("[bold green]✓ Orchestration completed successfully![/bold green]")
        console.print()
        
    except typer.Exit:
        # Re-raise typer exits (these are intentional)
        raise
        
    except NotInGitRepoError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print()
        console.print("[dim]Run 'git init' to create a git repository.[/dim]")
        raise typer.Exit(1)
        
    except FeatureNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print()
        console.print("[dim]Create a feature branch or set SPECIFY_FEATURE environment variable.[/dim]")
        raise typer.Exit(1)
        
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        console.print()
        console.print("[dim]Please report this issue at:[/dim]")
        console.print("  https://github.com/dscv103/spec-kit-flow/issues")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Display current orchestration status.
    
    Shows detailed information about the active orchestration including:
    - Current phase and progress
    - Session states and assignments
    - Task completion status
    - Next actions to take
    
    If no orchestration is active, provides guidance on starting one.
    
    Examples:
        skf status          # Show current orchestration state
    """
    try:
        # Get repository root
        try:
            repo_root = get_repo_root()
        except NotInGitRepoError:
            console.print("[red]Error:[/red] Not in a git repository")
            console.print()
            console.print("[dim]SpecKitFlow requires a git repository.[/dim]")
            console.print("[dim]Run 'git init' to create one.[/dim]")
            raise typer.Exit(1)
        
        # Create state manager
        state_manager = StateManager(repo_root)
        
        # Check if state exists
        if not state_manager.exists():
            console.print("[yellow]Notice:[/yellow] No active orchestration found")
            console.print()
            console.print("[dim]Start a new orchestration with:[/dim]")
            console.print("  [cyan]skf run[/cyan]")
            console.print()
            console.print("[dim]Or initialize configuration first:[/dim]")
            console.print("  [cyan]skf init[/cyan]")
            raise typer.Exit(0)
        
        # Load state
        try:
            state = state_manager.load()
        except StateNotFoundError:
            console.print("[yellow]Notice:[/yellow] No active orchestration found")
            console.print()
            console.print("[dim]Start a new orchestration with:[/dim]")
            console.print("  [cyan]skf run[/cyan]")
            raise typer.Exit(0)
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to load orchestration state")
            console.print()
            console.print(f"[dim]Details:[/dim] {e}")
            console.print()
            console.print("[dim]The state file may be corrupted.[/dim]")
            console.print("[dim]Consider backing up and deleting:[/dim]")
            console.print(f"  {state_manager.state_path.relative_to(repo_root)}")
            raise typer.Exit(1)
        
        # Display header
        console.print()
        console.print("[bold]Orchestration Status[/bold]")
        console.print()
        
        # Display basic info
        console.print(f"[bold]Specification:[/bold] {state.spec_id}")
        console.print(f"[bold]Agent:[/bold] {state.agent_type}")
        console.print(f"[bold]Sessions:[/bold] {state.num_sessions}")
        console.print(f"[bold]Base Branch:[/bold] {state.base_branch}")
        console.print()
        
        # Display timestamps
        console.print(f"[dim]Started:[/dim] {state.started_at}")
        console.print(f"[dim]Updated:[/dim] {state.updated_at}")
        console.print()
        
        # Calculate task statistics
        total_tasks = len(state.tasks)
        completed_tasks = sum(1 for t in state.tasks.values() if t.status == TaskStatus.completed)
        in_progress_tasks = sum(1 for t in state.tasks.values() if t.status == TaskStatus.in_progress)
        failed_tasks = sum(1 for t in state.tasks.values() if t.status == TaskStatus.failed)
        pending_tasks = total_tasks - completed_tasks - in_progress_tasks - failed_tasks
        
        # Display progress
        console.print("[bold]Progress[/bold]")
        console.print(f"  Current Phase: [cyan]{state.current_phase}[/cyan]")
        console.print(f"  Phases Completed: {len(state.phases_completed)}")
        if state.phases_completed:
            console.print(f"    {', '.join(state.phases_completed)}")
        console.print()
        
        # Display task summary with color coding
        console.print("[bold]Tasks[/bold]")
        console.print(f"  Total: {total_tasks}")
        if completed_tasks > 0:
            console.print(f"  [green]✓[/green] Completed: {completed_tasks}")
        if in_progress_tasks > 0:
            console.print(f"  [yellow]⋯[/yellow] In Progress: {in_progress_tasks}")
        if failed_tasks > 0:
            console.print(f"  [red]✗[/red] Failed: {failed_tasks}")
        if pending_tasks > 0:
            console.print(f"  [dim]○[/dim] Pending: {pending_tasks}")
        console.print()
        
        # Display session table
        if state.sessions:
            console.print("[bold]Sessions[/bold]")
            console.print()
            
            session_table = Table(
                show_header=True,
                header_style="bold cyan",
                box=None,
            )
            
            session_table.add_column("ID", style="bold", width=4)
            session_table.add_column("Status", width=12)
            session_table.add_column("Current Task", width=12)
            session_table.add_column("Completed", justify="right", width=10)
            session_table.add_column("Worktree", style="dim")
            
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
                
                # Completed count
                completed_count = len(session.completed_tasks)
                
                # Worktree path (relative if possible)
                if session.worktree_path:
                    try:
                        worktree_display = str(Path(session.worktree_path).relative_to(repo_root))
                    except ValueError:
                        worktree_display = session.worktree_path
                else:
                    worktree_display = "—"
                
                session_table.add_row(
                    str(session.session_id),
                    status_display,
                    current_task,
                    str(completed_count),
                    worktree_display,
                )
            
            console.print(session_table)
            console.print()
        
        # Display detailed task list if there are in-progress or failed tasks
        active_tasks = [
            (task_id, task_info)
            for task_id, task_info in state.tasks.items()
            if task_info.status in (TaskStatus.in_progress, TaskStatus.failed)
        ]
        
        if active_tasks:
            console.print("[bold]Active Tasks[/bold]")
            for task_id, task_info in sorted(active_tasks):
                # Status icon and color
                if task_info.status == TaskStatus.in_progress:
                    icon = "[yellow]⋯[/yellow]"
                elif task_info.status == TaskStatus.failed:
                    icon = "[red]✗[/red]"
                else:
                    icon = "[dim]○[/dim]"
                
                # Session assignment
                session_info = f"[Session {task_info.session}]" if task_info.session is not None else "[Unassigned]"
                
                console.print(f"  {icon} {task_id} {session_info}")
            console.print()
        
        # Display merge status if set
        if state.merge_status:
            console.print("[bold]Merge Status[/bold]")
            merge_styles = {
                "in_progress": ("In Progress", "yellow"),
                "completed": ("Completed", "green"),
                "failed": ("Failed", "red"),
            }
            merge_text, merge_style = merge_styles.get(
                state.merge_status,
                (state.merge_status, "")
            )
            if merge_style:
                console.print(f"  [{merge_style}]{merge_text}[/]")
            else:
                console.print(f"  {merge_text}")
            console.print()
        
        # Display next actions
        console.print("[bold]Next Actions[/bold]")
        
        # Determine appropriate next action based on state
        if failed_tasks > 0:
            console.print("  [red]⚠[/red] Some tasks have failed. Review and fix issues.")
            console.print("  [dim]Check session worktrees for details.[/dim]")
        elif in_progress_tasks > 0:
            console.print("  [yellow]⋯[/yellow] Tasks in progress. Continue working on:")
            for session in state.sessions:
                if session.status == SessionStatus.executing and session.current_task:
                    console.print(f"    • Session {session.session_id}: {session.current_task}")
                    if session.worktree_path:
                        try:
                            rel_path = Path(session.worktree_path).relative_to(repo_root)
                            console.print(f"      [dim]Worktree:[/dim] {rel_path}")
                        except ValueError:
                            console.print(f"      [dim]Worktree:[/dim] {session.worktree_path}")
        elif pending_tasks > 0:
            console.print("  [cyan]→[/cyan] Continue orchestration:")
            console.print("    [cyan]skf run --resume[/cyan]")
        elif completed_tasks == total_tasks and not state.merge_status:
            console.print("  [green]✓[/green] All tasks completed! Ready to merge:")
            console.print("    [cyan]skf merge[/cyan]")
        elif state.merge_status == "completed":
            console.print("  [green]✓[/green] Orchestration and merge completed!")
            console.print("  [dim]Clean up with:[/dim]")
            console.print("    [cyan]skf abort[/cyan]  [dim]# Remove worktrees and state[/dim]")
        
        console.print()
        
    except typer.Exit:
        # Re-raise typer exits (these are intentional)
        raise
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        console.print()
        console.print("[dim]Please report this issue at:[/dim]")
        console.print("  https://github.com/dscv103/spec-kit-flow/issues")
        raise typer.Exit(1)


@app.command()
def complete(
    task_id: str = typer.Argument(
        ...,
        help="Task ID to mark as complete (e.g., T001)",
    ),
) -> None:
    """Mark a task as manually completed.
    
    Creates a completion marker file for the specified task, signaling
    that it has been completed. This is useful when:
    - The task was completed outside of normal tracking
    - You need to manually override completion status
    - Checkbox marking in tasks.md is not working
    
    The command validates that the task ID exists in the current DAG
    (if a DAG has been generated) and warns if the task is already
    marked complete.
    
    Completion markers are stored in `.speckit/completions/{task_id}.done`
    and are automatically detected by the orchestration system.
    
    Args:
        task_id: Task identifier (format: T###, e.g., T001, T042)
    
    Examples:
        skf complete T001        # Mark task T001 as complete
        skf complete T015        # Mark task T015 as complete
    """
    try:
        # Normalize task ID to uppercase
        task_id = task_id.upper()
        
        # Validate task ID format (T### pattern)
        import re
        if not re.match(r'^T\d{3}$', task_id):
            console.print(f"[red]Error:[/red] Invalid task ID format: {task_id}")
            console.print()
            console.print("[dim]Task IDs must follow the pattern T### (e.g., T001, T042)[/dim]")
            console.print()
            console.print("[bold]Examples:[/bold]")
            console.print("  [green]✓[/green] T001")
            console.print("  [green]✓[/green] T042")
            console.print("  [red]✗[/red] T1")
            console.print("  [red]✗[/red] T0001")
            console.print("  [red]✗[/red] task001")
            raise typer.Exit(1)
        
        # Get repository root
        try:
            repo_root = get_repo_root()
        except NotInGitRepoError:
            console.print("[red]Error:[/red] Not in a git repository")
            console.print()
            console.print("[dim]SpecKitFlow requires a git repository.[/dim]")
            console.print("[dim]Run 'git init' to create one.[/dim]")
            raise typer.Exit(1)
        
        # Try to load DAG to validate task exists
        try:
            branch = get_current_branch()
            feature_context = get_feature_paths(repo_root, branch)
            dag_path = feature_context.feature_dir / "dag.yaml"
            
            if dag_path.exists():
                # DAG exists - validate task ID
                # Parse DAG to get valid task IDs
                dag_data = yaml.safe_load(dag_path.read_text())
                valid_task_ids = set()
                
                if "phases" in dag_data:
                    for phase in dag_data["phases"]:
                        if "tasks" in phase:
                            for task in phase["tasks"]:
                                if "id" in task:
                                    valid_task_ids.add(task["id"])
                
                if valid_task_ids and task_id not in valid_task_ids:
                    console.print(f"[red]Error:[/red] Task ID '{task_id}' not found in DAG")
                    console.print()
                    console.print("[dim]Valid task IDs in current DAG:[/dim]")
                    for tid in sorted(valid_task_ids)[:10]:  # Show first 10
                        console.print(f"  • {tid}")
                    if len(valid_task_ids) > 10:
                        console.print(f"  [dim]... and {len(valid_task_ids) - 10} more[/dim]")
                    console.print()
                    console.print("[dim]Run 'skf dag' to regenerate the DAG from tasks.md[/dim]")
                    raise typer.Exit(1)
                
                # Get spec_id from DAG for CompletionMonitor
                spec_id = dag_data.get("spec_id", feature_context.feature_dir.name)
            else:
                # No DAG yet - use feature dir name as spec_id
                spec_id = feature_context.feature_dir.name
                console.print("[yellow]Notice:[/yellow] No DAG found, skipping task ID validation")
                console.print()
                console.print("[dim]Run 'skf dag' to generate DAG and enable validation[/dim]")
                console.print()
                
        except FeatureNotFoundError:
            # No feature context - just mark complete without validation
            console.print("[yellow]Notice:[/yellow] No feature context found, marking task without validation")
            console.print()
            spec_id = "default"
        
        # Create completion monitor
        monitor = CompletionMonitor(spec_id, repo_root)
        
        # Check if task is already complete
        if monitor.is_complete(task_id):
            console.print(f"[yellow]Warning:[/yellow] Task {task_id} is already marked complete")
            console.print()
            done_file = monitor.completions_dir / f"{task_id}.done"
            console.print(f"[dim]Completion marker:[/dim] {done_file.relative_to(repo_root)}")
            console.print()
            console.print("[dim]The task was already completed. No action taken.[/dim]")
            raise typer.Exit(0)
        
        # Mark task as complete
        console.print(f"[cyan]→[/cyan] Marking task {task_id} as complete...")
        monitor.mark_complete(task_id)
        
        # Success message
        console.print()
        console.print(f"[green]✓[/green] Task {task_id} marked as complete")
        console.print()
        
        done_file = monitor.completions_dir / f"{task_id}.done"
        console.print(f"[dim]Completion marker:[/dim] {done_file.relative_to(repo_root)}")
        console.print()
        
        # Provide next steps
        console.print("[bold]Next Steps[/bold]")
        console.print("  • The orchestration system will detect this completion automatically")
        console.print("  • Check status: [cyan]skf status[/cyan]")
        console.print("  • If running orchestration, it will proceed to dependent tasks")
        console.print()
        
    except typer.Exit:
        # Re-raise typer exits (these are intentional)
        raise
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        console.print()
        console.print("[dim]Please report this issue at:[/dim]")
        console.print("  https://github.com/dscv103/spec-kit-flow/issues")
        raise typer.Exit(1)


@app.command()
def merge(
    keep_worktrees: bool = typer.Option(
        False,
        "--keep-worktrees",
        help="Preserve worktrees after merge instead of cleaning up",
    ),
    test_cmd: str = typer.Option(
        None,
        "--test", "-t",
        help="Command to run for validation after merge (e.g., 'pytest', 'npm test')",
    ),
) -> None:
    """Merge session branches into a single integration branch.
    
    This command performs the final integration of parallel implementation:
    1. Analyzes changes across all session branches
    2. Detects potential merge conflicts before merging
    3. Prompts for confirmation if conflicts are detected
    4. Creates an integration branch (impl-{spec_id}-integrated)
    5. Sequentially merges session branches with --no-ff
    6. Optionally runs validation tests
    7. Cleans up worktrees (unless --keep-worktrees specified)
    
    The merge uses a sequential strategy, merging sessions in order (0, 1, 2...).
    If a conflict occurs, the merge is aborted and the repository is left in
    a clean state with detailed conflict information.
    
    Args:
        keep_worktrees: Preserve session worktrees after merge for inspection
        test_cmd: Optional command to run for validation (e.g., "pytest tests/")
        
    Examples:
        skf merge                           # Merge and cleanup
        skf merge --keep-worktrees          # Merge but keep worktrees
        skf merge --test "pytest tests/"    # Merge with validation
    """
    try:
        # Get repository root
        try:
            repo_root = get_repo_root()
        except NotInGitRepoError:
            console.print("[red]Error:[/red] Not in a git repository")
            console.print()
            console.print("[dim]SpecKitFlow requires a git repository.[/dim]")
            console.print("[dim]Run 'git init' to create one.[/dim]")
            raise typer.Exit(1)
        
        # Get feature context to determine spec_id
        try:
            branch = get_current_branch()
            feature_context = get_feature_paths(repo_root, branch)
            spec_id = feature_context.feature_dir.name
        except FeatureNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print()
            console.print("[dim]Create a feature branch or set SPECIFY_FEATURE environment variable.[/dim]")
            raise typer.Exit(1)
        
        # Create merge orchestrator
        console.print(f"[cyan]→[/cyan] Initializing merge for spec: {spec_id}...")
        orchestrator = MergeOrchestrator(spec_id, repo_root)
        
        # Step 1: Analyze changes
        console.print(f"[cyan]→[/cyan] Analyzing changes across session branches...")
        try:
            analysis = orchestrator.analyze()
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        
        # Display analysis results
        console.print()
        console.print("[bold]Merge Analysis[/bold]")
        console.print()
        console.print(f"  Base branch: [cyan]{analysis.base_branch}[/cyan]")
        console.print(f"  Sessions found: {len(analysis.session_changes)}")
        console.print(f"  Total files changed: {analysis.total_files_changed}")
        console.print()
        
        # Display per-session changes
        for session in analysis.session_changes:
            console.print(f"  [bold]Session {session.session_id}[/bold] ({session.branch_name}):")
            if session.added_files:
                console.print(f"    [green]+[/green] Added: {len(session.added_files)} file(s)")
            if session.modified_files:
                console.print(f"    [yellow]M[/yellow] Modified: {len(session.modified_files)} file(s)")
            if session.deleted_files:
                console.print(f"    [red]-[/red] Deleted: {len(session.deleted_files)} file(s)")
            if not session.all_changed_files:
                console.print("    [dim]No changes[/dim]")
        console.print()
        
        # Check for overlapping changes (potential conflicts)
        if not analysis.safe_to_merge:
            console.print("[yellow]⚠ Warning:[/yellow] Potential merge conflicts detected")
            console.print()
            console.print("[bold]Overlapping Files[/bold]")
            console.print("[dim]The following files were modified by multiple sessions:[/dim]")
            console.print()
            
            for filepath, session_ids in sorted(analysis.overlapping_files.items()):
                sessions_str = ", ".join(f"Session {sid}" for sid in sorted(session_ids))
                console.print(f"  [yellow]•[/yellow] {filepath}")
                console.print(f"    [dim]Modified by: {sessions_str}[/dim]")
            console.print()
            
            # Prompt for confirmation
            console.print("[yellow]These conflicts may require manual resolution.[/yellow]")
            if not typer.confirm("Continue with merge?", default=True):
                console.print()
                console.print("[dim]Merge cancelled.[/dim]")
                raise typer.Exit(0)
            console.print()
        else:
            console.print("[green]✓[/green] No overlapping changes detected - merge should be clean")
            console.print()
        
        # Step 2: Execute merge
        console.print(f"[cyan]→[/cyan] Merging session branches...")
        try:
            result = orchestrator.merge_sequential()
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        
        if not result.success:
            # Merge failed due to conflict
            console.print()
            console.print(f"[red]✗ Merge failed:[/red] Conflict in session {result.conflict_session}")
            console.print()
            console.print("[bold]Conflicting Files[/bold]")
            for filepath in result.conflicting_files:
                console.print(f"  [red]•[/red] {filepath}")
            console.print()
            console.print(f"[dim]Error:[/dim] {result.error_message}")
            console.print()
            console.print("[bold]Next Steps[/bold]")
            console.print("  1. Review the conflict in the affected files")
            console.print("  2. Consider manual merge of the conflicting sessions")
            console.print("  3. Or adjust task assignments to avoid file overlap")
            console.print()
            console.print("[dim]The repository has been left in a clean state.[/dim]")
            raise typer.Exit(1)
        
        # Merge succeeded!
        console.print()
        console.print(f"[green]✓[/green] Successfully merged {len(result.merged_sessions)} session(s)")
        console.print(f"[green]✓[/green] Integration branch created: [cyan]{result.integration_branch}[/cyan]")
        console.print()
        
        # Step 3: Run validation if requested
        if test_cmd:
            console.print(f"[cyan]→[/cyan] Running validation: {test_cmd}...")
            console.print()
            
            validation_success, validation_output = orchestrator.validate(test_cmd)
            
            if validation_success:
                console.print("[green]✓[/green] Validation passed")
                console.print()
                if validation_output.strip():
                    console.print("[dim]Test output:[/dim]")
                    # Show first 20 lines of output
                    output_lines = validation_output.splitlines()
                    for line in output_lines[:20]:
                        console.print(f"  {line}")
                    if len(output_lines) > 20:
                        console.print(f"  [dim]... ({len(output_lines) - 20} more lines)[/dim]")
                    console.print()
            else:
                console.print("[red]✗[/red] Validation failed")
                console.print()
                console.print("[dim]Test output:[/dim]")
                # Show all output for failures
                for line in validation_output.splitlines():
                    console.print(f"  {line}")
                console.print()
                console.print("[yellow]Warning:[/yellow] Tests failed but merge completed.")
                console.print("[dim]Fix the issues in the integration branch before finalizing.[/dim]")
                console.print()
        
        # Step 4: Finalize (cleanup worktrees and show summary)
        console.print(f"[cyan]→[/cyan] Finalizing merge...")
        summary = orchestrator.finalize(keep_worktrees=keep_worktrees)
        
        console.print()
        console.print("[bold green]✓ Merge completed successfully![/bold green]")
        console.print()
        
        # Display summary
        console.print("[bold]Merge Summary[/bold]")
        console.print(f"  Integration branch: [cyan]{summary['integration_branch']}[/cyan]")
        console.print(f"  Files changed: {summary['files_changed']}")
        console.print(f"  Lines added: [green]+{summary['lines_added']}[/green]")
        console.print(f"  Lines deleted: [red]-{summary['lines_deleted']}[/red]")
        
        if keep_worktrees:
            console.print(f"  Worktrees: [yellow]Preserved for inspection[/yellow]")
        else:
            console.print(f"  Worktrees removed: {summary['worktrees_removed']}")
        console.print()
        
        # Display next steps
        console.print("[bold]Next Steps[/bold]")
        console.print(f"  1. Review the integration branch: [cyan]git checkout {summary['integration_branch']}[/cyan]")
        console.print(f"  2. Test thoroughly before merging to {analysis.base_branch}")
        console.print(f"  3. When ready: [cyan]git checkout {analysis.base_branch} && git merge {summary['integration_branch']}[/cyan]")
        
        if keep_worktrees:
            console.print()
            console.print("[dim]To clean up worktrees later, run:[/dim]")
            console.print("  [cyan]skf abort[/cyan]")
        
        console.print()
        
    except typer.Exit:
        # Re-raise typer exits (these are intentional)
        raise
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        console.print()
        console.print("[dim]Please report this issue at:[/dim]")
        console.print("  https://github.com/dscv103/spec-kit-flow/issues")
        raise typer.Exit(1)


@app.command()
def abort(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Abort orchestration and cleanup all worktrees and state.
    
    This command terminates the current orchestration and performs complete
    cleanup of all SpecKitFlow artifacts:
    1. Removes all session worktrees for the current spec
    2. Deletes the orchestration state file
    3. Optionally cleans up checkpoints
    
    This is a destructive operation that cannot be undone. All uncommitted
    changes in worktrees will be lost. The session branches will be preserved
    in case you need to recover any work.
    
    Use this command when:
    - You want to start over from scratch
    - The orchestration is stuck or corrupted
    - You've finished and merged everything
    
    Args:
        force: Skip confirmation prompt and proceed immediately
        
    Examples:
        skf abort           # Prompts for confirmation
        skf abort --force   # No confirmation, immediate cleanup
    """
    try:
        # Get repository root
        try:
            repo_root = get_repo_root()
        except NotInGitRepoError:
            console.print("[red]Error:[/red] Not in a git repository")
            console.print()
            console.print("[dim]SpecKitFlow requires a git repository.[/dim]")
            console.print("[dim]Run 'git init' to create one.[/dim]")
            raise typer.Exit(1)
        
        # Create state manager to check for active orchestration
        state_manager = StateManager(repo_root)
        
        # Track what needs to be cleaned up
        has_state = state_manager.exists()
        spec_id = None
        worktrees_to_remove = []
        
        # Try to load state to get spec_id
        if has_state:
            try:
                state = state_manager.load()
                spec_id = state.spec_id
            except Exception:
                # State exists but can't be loaded - we'll still clean it up
                # Try to infer spec_id from feature context
                try:
                    branch = get_current_branch()
                    feature_context = get_feature_paths(repo_root, branch)
                    spec_id = feature_context.feature_dir.name
                except Exception:
                    # Can't determine spec_id - will clean up state but not worktrees
                    pass
        else:
            # No state file - try to infer spec_id from feature context
            try:
                branch = get_current_branch()
                feature_context = get_feature_paths(repo_root, branch)
                spec_id = feature_context.feature_dir.name
            except Exception:
                # No feature context either
                pass
        
        # Get worktrees to remove if we have a spec_id
        if spec_id:
            from speckit_flow.worktree.manager import WorktreeManager
            
            manager = WorktreeManager(repo_root)
            worktrees_to_remove = manager.get_spec_worktrees(spec_id)
        
        # Check if there's anything to clean up
        if not has_state and not worktrees_to_remove:
            console.print("[yellow]Notice:[/yellow] No active orchestration or worktrees found")
            console.print()
            console.print("[dim]Nothing to clean up.[/dim]")
            console.print()
            console.print("[dim]Use 'skf status' to check current state.[/dim]")
            raise typer.Exit(0)
        
        # Display what will be removed
        console.print()
        console.print("[bold yellow]⚠ Warning: This will delete the following:[/bold yellow]")
        console.print()
        
        if has_state:
            console.print("  [red]•[/red] Orchestration state file")
            console.print(f"    [dim]{state_manager.state_path.relative_to(repo_root)}[/dim]")
        
        if worktrees_to_remove:
            console.print(f"  [red]•[/red] {len(worktrees_to_remove)} worktree(s):")
            for worktree in worktrees_to_remove:
                try:
                    rel_path = worktree.path.relative_to(repo_root)
                    console.print(f"    [dim]- {rel_path}[/dim]")
                except ValueError:
                    console.print(f"    [dim]- {worktree.path}[/dim]")
        
        console.print()
        console.print("[yellow]All uncommitted changes in worktrees will be lost![/yellow]")
        console.print("[dim]Session branches will be preserved for recovery if needed.[/dim]")
        console.print()
        
        # Prompt for confirmation unless --force is set
        if not force:
            if not typer.confirm("Continue with cleanup?", default=False):
                console.print()
                console.print("[dim]Cleanup cancelled.[/dim]")
                raise typer.Exit(0)
            console.print()
        
        # Perform cleanup
        cleanup_summary = {
            "worktrees_removed": 0,
            "state_deleted": False,
            "checkpoints_found": 0,
        }
        
        # Step 1: Remove worktrees
        if worktrees_to_remove:
            from speckit_flow.worktree.manager import WorktreeManager
            
            console.print(f"[cyan]→[/cyan] Removing {len(worktrees_to_remove)} worktree(s)...")
            
            manager = WorktreeManager(repo_root)
            cleanup_summary["worktrees_removed"] = manager.cleanup_spec(spec_id)
            
            console.print(f"[green]✓[/green] Removed {cleanup_summary['worktrees_removed']} worktree(s)")
        
        # Step 2: Delete state file
        if has_state:
            console.print(f"[cyan]→[/cyan] Deleting orchestration state...")
            state_manager.delete()
            cleanup_summary["state_deleted"] = True
            console.print(f"[green]✓[/green] Deleted state file")
        
        # Step 3: Check for checkpoints (informational only)
        checkpoints_dir = repo_root / ".speckit" / "checkpoints"
        if checkpoints_dir.exists():
            checkpoint_files = list(checkpoints_dir.glob("*.yaml"))
            cleanup_summary["checkpoints_found"] = len(checkpoint_files)
        
        # Display summary
        console.print()
        console.print("[bold green]✓ Cleanup completed successfully![/bold green]")
        console.print()
        
        console.print("[bold]Cleanup Summary[/bold]")
        if cleanup_summary["worktrees_removed"] > 0:
            console.print(f"  Worktrees removed: {cleanup_summary['worktrees_removed']}")
        if cleanup_summary["state_deleted"]:
            console.print("  State file deleted: [green]✓[/green]")
        if cleanup_summary["checkpoints_found"] > 0:
            console.print(f"  Checkpoints found: {cleanup_summary['checkpoints_found']}")
            console.print(f"    [dim]Location:[/dim] {checkpoints_dir.relative_to(repo_root)}")
            console.print("    [dim]To remove checkpoints, delete the directory manually[/dim]")
        console.print()
        
        # Display next steps
        console.print("[bold]Next Steps[/bold]")
        console.print("  • Start a new orchestration: [cyan]skf run[/cyan]")
        
        if spec_id:
            console.print(f"  • Session branches preserved: [cyan]impl-{spec_id}-session-*[/cyan]")
            console.print("  • To delete branches: [cyan]git branch -D impl-{spec_id}-session-*[/cyan]")
        
        console.print()
        
    except typer.Exit:
        # Re-raise typer exits (these are intentional)
        raise
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        console.print()
        console.print("[dim]Please report this issue at:[/dim]")
        console.print("  https://github.com/dscv103/spec-kit-flow/issues")
        raise typer.Exit(1)


def main() -> None:
    """Entry point for skf and speckit-flow commands."""
    app()


__all__ = [
    "__version__",
    "app",
    "main",
]
