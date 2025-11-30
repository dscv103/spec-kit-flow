---
name: User Experience Standards

description: CLI design standards, Rich formatting patterns, error presentation, progress indicators, and accessibility requirements for SpecKitFlow.

applyTo: "src/speckit_flow/**/*.py"
---

# User Experience Instructions

## Purpose

This document establishes user experience standards for SpecKitFlow CLI and IDE interactions. Every user-facing feature must provide a consistent, intuitive, and helpful experience.

## UX Principles

### Principle 1: Progressive Disclosure

Show essential information first, details on demand:

```python
# ❌ Overwhelming output
def dag_command():
    print(f"Parsed {len(tasks)} tasks from {tasks_path}")
    print(f"Task IDs: {', '.join(t.id for t in tasks)}")
    print(f"Dependencies: {json.dumps(deps, indent=2)}")
    print(f"Phases: {phases}")
    print(f"Sessions: {sessions}")
    # ... pages of output

# ✅ Progressive disclosure
def dag_command(verbose: bool = False):
    console.print(f"[green]✓[/green] Generated DAG: {len(phases)} phases, {len(tasks)} tasks")
    
    if verbose:
        # Show details only when requested
        for phase in phases:
            console.print(f"  Phase {phase.index}: {len(phase.tasks)} tasks")
```

### Principle 2: Fail Helpfully

When things go wrong, tell users what happened and what to do:

```python
# ❌ Unhelpful error
except FileNotFoundError:
    print("Error: File not found")
    sys.exit(1)

# ✅ Helpful error with guidance
except FileNotFoundError as e:
    console.print(f"[red]Error:[/red] Tasks file not found: {e.filename}")
    console.print()
    console.print("[dim]Expected location:[/dim]")
    console.print(f"  specs/{{branch}}/tasks.md")
    console.print()
    console.print("[dim]To create tasks, run:[/dim]")
    console.print("  specify plan  [dim]# Generate implementation plan[/dim]")
    console.print("  specify tasks [dim]# Generate tasks from plan[/dim]")
    raise typer.Exit(1)
```

### Principle 3: Confirm Destructive Actions

Always confirm before irreversible operations:

```python
# ✅ Confirm destructive action
@app.command()
def abort(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """Abort orchestration and cleanup all worktrees."""
    worktrees = list_worktrees()
    
    if not force:
        console.print(f"[yellow]Warning:[/yellow] This will delete {len(worktrees)} worktrees:")
        for wt in worktrees:
            console.print(f"  • {wt.path}")
        console.print()
        
        if not typer.confirm("Continue?"):
            raise typer.Abort()
    
    cleanup_worktrees()
    console.print("[green]✓[/green] Orchestration aborted, worktrees cleaned up")
```

### Principle 4: Show Progress for Long Operations

Users should know the system is working:

```python
# ✅ Progress indication
from rich.progress import Progress, SpinnerColumn, TextColumn

def create_worktrees(sessions: int):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Creating worktrees...", total=sessions)
        
        for i in range(sessions):
            progress.update(task, description=f"Creating session {i} worktree...")
            create_worktree(i)
            progress.advance(task)
    
    console.print(f"[green]✓[/green] Created {sessions} worktrees")
```

### Principle 5: Consistent Visual Language

Use consistent symbols and colors throughout:

| Symbol | Meaning | Color |
|--------|---------|-------|
| ✓ | Success/Complete | Green |
| ✗ | Error/Failed | Red |
| ⚠ | Warning | Yellow |
| → | Action/Next step | Cyan |
| • | List item | Default |
| ⋯ | In progress | Yellow |
| ○ | Pending/Not started | Dim |

```python
# Define consistent styles
STYLE_SUCCESS = "[green]✓[/green]"
STYLE_ERROR = "[red]✗[/red]"
STYLE_WARNING = "[yellow]⚠[/yellow]"
STYLE_ACTION = "[cyan]→[/cyan]"
STYLE_PENDING = "[dim]○[/dim]"
STYLE_IN_PROGRESS = "[yellow]⋯[/yellow]"

def print_task_status(task: TaskInfo):
    if task.status == "completed":
        console.print(f"{STYLE_SUCCESS} {task.id}: {task.name}")
    elif task.status == "in_progress":
        console.print(f"{STYLE_IN_PROGRESS} {task.id}: {task.name}")
    else:
        console.print(f"{STYLE_PENDING} {task.id}: {task.name}")
```

## CLI Design Standards

### Command Structure

Follow consistent patterns for all commands:

```
skf <command> [OPTIONS] [ARGUMENTS]
```

### Command Naming

| Pattern | Example | Description |
|---------|---------|-------------|
| Verb | `skf run` | Primary action |
| Noun | `skf dag` | View/generate artifact |
| Verb + Noun | `skf complete T001` | Action on specific item |

### Option Naming

```python
# Consistent option patterns
@app.command()
def dag(
    # Boolean flags: --flag / --no-flag
    visualize: bool = typer.Option(False, "--visualize", "-v", help="Show ASCII tree"),
    
    # Value options: --option VALUE
    sessions: int = typer.Option(3, "--sessions", "-s", help="Number of sessions"),
    
    # Output format options
    output: str = typer.Option("yaml", "--output", "-o", help="Output format: yaml, json"),
    
    # Common flags across commands
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output"),
):
```

### Help Text Standards

```python
@app.command()
def run(
    sessions: int = typer.Option(
        None,
        "--sessions", "-s",
        help="Number of parallel sessions [default: from config]",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Resume from last checkpoint instead of starting fresh",
    ),
):
    """
    Execute parallel orchestration across multiple agent sessions.
    
    This command:
    1. Creates git worktrees for each session
    2. Prompts you to open each worktree in VS Code
    3. Monitors task completion in each session
    4. Advances through DAG phases automatically
    
    Examples:
        skf run                  # Run with config defaults
        skf run --sessions 4     # Override session count
        skf run --resume         # Resume interrupted run
    """
```

## Output Formatting

### Standard Output Structure

```python
def print_dag_summary(dag: DAGEngine):
    """Print consistent DAG summary."""
    console.print()
    console.print("[bold]DAG Summary[/bold]")
    console.print()
    
    # Key metrics
    console.print(f"  Tasks:    {dag.task_count}")
    console.print(f"  Phases:   {dag.phase_count}")
    console.print(f"  Sessions: {dag.num_sessions}")
    console.print()
    
    # Status table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Phase", style="cyan")
    table.add_column("Tasks", justify="right")
    table.add_column("Parallel", justify="center")
    
    for phase in dag.phases:
        parallel = "✓" if phase.parallelizable else "–"
        table.add_row(phase.name, str(len(phase.tasks)), parallel)
    
    console.print(table)
    console.print()
```

### Table Formatting

Use Rich tables for structured data:

```python
from rich.table import Table

def print_session_status(sessions: list[SessionState]):
    table = Table(
        title="Session Status",
        show_header=True,
        header_style="bold cyan",
    )
    
    table.add_column("Session", style="bold", width=8)
    table.add_column("Status", width=12)
    table.add_column("Current Task", width=15)
    table.add_column("Worktree", style="dim")
    
    for session in sessions:
        status_style = {
            "idle": "dim",
            "executing": "yellow",
            "completed": "green",
            "failed": "red",
        }.get(session.status, "")
        
        table.add_row(
            str(session.session_id),
            f"[{status_style}]{session.status}[/]",
            session.current_task or "–",
            str(session.worktree_path),
        )
    
    console.print(table)
```

### Tree Formatting

Use Rich trees for hierarchical data:

```python
from rich.tree import Tree

def print_dag_tree(dag: DAGEngine):
    tree = Tree("[bold]DAG Phases[/bold]")
    
    for phase in dag.phases:
        phase_style = "cyan" if phase.parallelizable else "yellow"
        phase_node = tree.add(f"[{phase_style}]{phase.name}[/]")
        
        for task in phase.tasks:
            status_icon = {
                "completed": "[green]✓[/]",
                "in_progress": "[yellow]⋯[/]",
                "pending": "[dim]○[/]",
            }.get(task.status, "○")
            
            deps = f" [dim](deps: {', '.join(task.dependencies)})[/]" if task.dependencies else ""
            phase_node.add(f"{status_icon} {task.id}: {task.name}{deps}")
    
    console.print(tree)
```

## Interactive Elements

### Prompts

Use typer prompts with clear defaults:

```python
# Text prompt with default
name = typer.prompt("Feature name", default="new-feature")

# Confirmation prompt
if typer.confirm("Create worktrees?", default=True):
    create_worktrees()

# Choice prompt (using questionary for complex cases)
import questionary

agent = questionary.select(
    "Select AI agent:",
    choices=["copilot", "goose", "opencode"],
    default="copilot",
).ask()
```

### Progress Indicators

Use appropriate progress indicators:

```python
from rich.progress import Progress, BarColumn, TaskProgressColumn, TimeRemainingColumn

# Determinate progress (known total)
with Progress(
    "[progress.description]{task.description}",
    BarColumn(),
    TaskProgressColumn(),
    TimeRemainingColumn(),
) as progress:
    task = progress.add_task("Processing tasks...", total=len(tasks))
    for t in tasks:
        process(t)
        progress.advance(task)

# Indeterminate progress (unknown duration)
from rich.progress import SpinnerColumn

with Progress(
    SpinnerColumn(),
    "[progress.description]{task.description}",
    transient=True,
) as progress:
    progress.add_task("Waiting for agent completion...", total=None)
    wait_for_completion()
```

## IDE Notification Mode

### Session Prompts

When prompting user to open worktrees in IDE:

```python
def notify_session_ready(session: SessionState, task: TaskInfo):
    """Prompt user to open worktree in VS Code."""
    console.print()
    panel = Panel(
        f"""[bold]Session {session.session_id}[/bold]
        
Task: [cyan]{task.id}[/cyan] - {task.name}

[bold]Instructions:[/bold]
1. Open this folder in VS Code:
   [green]{session.worktree_path}[/green]

2. Run the Copilot command:
   [cyan]/speckit.implement[/cyan]

3. When complete, the task checkbox in tasks.md will be marked.
   Alternatively, run: [cyan]skf complete {task.id}[/cyan]""",
        title="[bold yellow]Action Required[/bold yellow]",
        border_style="yellow",
    )
    console.print(panel)
    console.print()
```

### Copy-Pasteable Paths

Always provide paths that can be copied directly:

```python
# ✅ Absolute path, easy to copy
console.print(f"[green]{worktree.absolute()}[/green]")

# ✅ With code block for terminal
console.print(f"  cd {worktree.absolute()}")

# ❌ Relative path that may not work from user's location
console.print(f".worktrees/session-0/")
```

## Error Presentation

### Error Hierarchy

```python
def handle_error(error: Exception):
    """Present errors with consistent formatting."""
    console.print()
    
    if isinstance(error, CyclicDependencyError):
        # User error - fixable
        console.print("[red]Error:[/red] Circular dependency detected")
        console.print()
        console.print("Cycle:", " → ".join(error.cycle))
        console.print()
        console.print("[dim]Fix the dependency cycle in tasks.md and try again.[/dim]")
        
    elif isinstance(error, StateNotFoundError):
        # Expected state - helpful guidance
        console.print("[yellow]Notice:[/yellow] No active orchestration found")
        console.print()
        console.print("[dim]Start a new orchestration with:[/dim]")
        console.print("  skf run")
        
    elif isinstance(error, subprocess.CalledProcessError):
        # System error - technical details
        console.print("[red]Error:[/red] Git command failed")
        console.print()
        console.print(f"[dim]Command:[/dim] {' '.join(error.cmd)}")
        console.print(f"[dim]Exit code:[/dim] {error.returncode}")
        if error.stderr:
            console.print(f"[dim]Output:[/dim] {error.stderr.decode()}")
            
    else:
        # Unexpected error - ask for report
        console.print("[red]Unexpected error:[/red]", str(error))
        console.print()
        console.print("[dim]Please report this issue at:[/dim]")
        console.print("  https://github.com/owner/speckit-flow/issues")
    
    console.print()
```

### Validation Errors

```python
def validate_config(config: dict) -> list[str]:
    """Validate config and return list of errors."""
    errors = []
    
    if config.get("num_sessions", 0) < 1:
        errors.append("num_sessions must be at least 1")
    
    if config.get("agent_type") not in ("copilot", "goose", "opencode"):
        errors.append(f"Invalid agent_type: {config.get('agent_type')}")
    
    return errors

def print_validation_errors(errors: list[str]):
    console.print("[red]Configuration errors:[/red]")
    console.print()
    for error in errors:
        console.print(f"  [red]•[/red] {error}")
    console.print()
    console.print("[dim]Fix these issues in .speckit/speckit-flow.yaml[/dim]")
```

## Accessibility

### Color-Blind Friendly

Don't rely on color alone to convey meaning:

```python
# ❌ Color only
console.print(f"[green]{task.name}[/green]")  # Complete
console.print(f"[red]{task.name}[/red]")      # Failed

# ✅ Color + symbol
console.print(f"[green]✓[/green] {task.name}")  # Complete
console.print(f"[red]✗[/red] {task.name}")      # Failed
```

### Screen Reader Friendly

Avoid purely visual elements in critical output:

```python
# ❌ Visual-only progress
console.print("Processing: ████████░░░░ 66%")

# ✅ Semantic progress
console.print("Processing: 66% (8 of 12 tasks complete)")
```

### Terminal Width

Handle narrow terminals gracefully:

```python
from rich.console import Console

console = Console()

def print_worktree_info(path: Path):
    if console.width < 80:
        # Narrow terminal: vertical layout
        console.print(f"Path:")
        console.print(f"  {path}")
    else:
        # Wide terminal: horizontal layout
        console.print(f"Path: {path}")
```

## Consistency Checklist

Before completing any user-facing feature:

- [ ] Uses consistent status symbols (✓, ✗, ⚠, ⋯, ○)
- [ ] Uses consistent colors (green=success, red=error, yellow=warning, cyan=info)
- [ ] Provides helpful error messages with next steps
- [ ] Confirms destructive actions
- [ ] Shows progress for operations > 1 second
- [ ] Paths are absolute and copy-pasteable
- [ ] Help text includes examples
- [ ] Works in narrow terminals (< 80 columns)
- [ ] Meaning is conveyed without color (symbols/text)
