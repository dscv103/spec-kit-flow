"""
DAG engine for task dependency resolution.

This module provides the DAGEngine class which constructs and validates
directed acyclic graphs from task lists, enabling parallel orchestration
through dependency analysis.
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, Field

from speckit_core.models import DAGNode, TaskInfo
from speckit_flow.exceptions import CyclicDependencyError

if TYPE_CHECKING:
    import networkx as nx

__all__ = ["DAGEngine", "DAGOutput", "DAGPhase"]


class DAGPhase(BaseModel):
    """A phase in the DAG containing parallel tasks.
    
    Attributes:
        name: Phase name (e.g., "phase-0")
        tasks: List of task nodes in this phase
    """
    name: str
    tasks: list[DAGNode]
    
    model_config = {"frozen": True}


class DAGOutput(BaseModel):
    """Complete DAG output matching dag.yaml schema.
    
    This model represents the full DAG structure that gets serialized
    to specs/{branch}/dag.yaml.
    
    Attributes:
        version: Schema version (e.g., "1.0")
        spec_id: Specification identifier
        generated_at: ISO 8601 timestamp of generation
        num_sessions: Number of parallel sessions
        phases: List of execution phases
        
    Example:
        >>> output = DAGOutput(
        ...     version="1.0",
        ...     spec_id="001-test",
        ...     generated_at="2025-11-28T10:30:00Z",
        ...     num_sessions=2,
        ...     phases=[]
        ... )
    """
    version: str = Field(default="1.0")
    spec_id: str
    generated_at: str
    num_sessions: int = Field(ge=1)
    phases: list[DAGPhase]
    
    model_config = {"frozen": True}


class DAGEngine:
    """Directed Acyclic Graph engine for task dependency resolution.
    
    This engine builds a dependency graph from tasks, validates it for
    cycles, and provides methods to extract parallel execution phases.
    
    The graph uses task IDs as nodes and stores full TaskInfo objects
    as node attributes for downstream processing.
    
    Attributes:
        tasks: List of TaskInfo objects to build graph from
        graph: The underlying networkx DiGraph (built lazily)
        
    Example:
        >>> tasks = [
        ...     TaskInfo(id="T001", name="Setup", dependencies=[]),
        ...     TaskInfo(id="T002", name="Build", dependencies=["T001"]),
        ... ]
        >>> engine = DAGEngine(tasks)
        >>> engine.validate()  # Raises CyclicDependencyError if cycles exist
        True
        >>> graph = engine.build_graph()
        >>> assert graph.has_edge("T001", "T002")
    """
    
    def __init__(self, tasks: list[TaskInfo]):
        """Initialize DAG engine with task list.
        
        Args:
            tasks: List of TaskInfo objects to build graph from
        """
        self.tasks = tasks
        self._graph: "nx.DiGraph | None" = None
        self._task_map: dict[str, TaskInfo] = {t.id: t for t in tasks}
    
    def build_graph(self) -> "nx.DiGraph":
        """Build directed graph from task list.
        
        Creates a networkx DiGraph where:
        - Nodes are task IDs (strings like "T001")
        - Node attributes contain the full TaskInfo object
        - Edges represent dependencies (from dependency to dependent)
        
        The graph is built incrementally, checking for cycles after each
        edge addition to provide early cycle detection with meaningful
        error messages.
        
        Returns:
            NetworkX DiGraph with task IDs as nodes
            
        Raises:
            CyclicDependencyError: If a cycle is detected during construction
            
        Example:
            >>> tasks = [TaskInfo(id="T001", name="A", dependencies=[])]
            >>> engine = DAGEngine(tasks)
            >>> graph = engine.build_graph()
            >>> assert "T001" in graph.nodes
            >>> assert graph.nodes["T001"]["task"].name == "A"
        """
        # Lazy import for performance
        import networkx as nx
        
        if self._graph is not None:
            return self._graph
        
        graph = nx.DiGraph()
        
        # First pass: Add all nodes with their task data
        for task in self.tasks:
            graph.add_node(task.id, task=task)
        
        # Second pass: Add dependency edges with cycle checking
        for task in self.tasks:
            for dep_id in task.dependencies:
                # Add edge from dependency to dependent
                # (dep_id must complete before task.id can start)
                graph.add_edge(dep_id, task.id)
                
                # Check for cycles immediately after adding edge
                if not nx.is_directed_acyclic_graph(graph):
                    # Find the cycle for error reporting
                    try:
                        cycle_edges = nx.find_cycle(graph, orientation="original")
                        # Extract node sequence from cycle edges
                        cycle = [edge[0] for edge in cycle_edges]
                        # Close the cycle for display
                        cycle.append(cycle[0])
                        raise CyclicDependencyError(cycle=cycle)
                    except nx.NetworkXNoCycle:
                        # Should not happen, but handle gracefully
                        raise CyclicDependencyError(cycle=[dep_id, task.id])
        
        self._graph = graph
        return graph
    
    def validate(self) -> bool:
        """Validate that the task graph is a valid DAG.
        
        Checks that the dependency graph is acyclic using networkx's
        is_directed_acyclic_graph function. This method builds the graph
        if not already built.
        
        Returns:
            True if the graph is a valid DAG
            
        Raises:
            CyclicDependencyError: If circular dependencies are detected
            
        Example:
            >>> tasks = [TaskInfo(id="T001", name="A", dependencies=[])]
            >>> engine = DAGEngine(tasks)
            >>> assert engine.validate() is True
            
            >>> bad_tasks = [
            ...     TaskInfo(id="T001", name="A", dependencies=["T002"]),
            ...     TaskInfo(id="T002", name="B", dependencies=["T001"]),
            ... ]
            >>> bad_engine = DAGEngine(bad_tasks)
            >>> bad_engine.validate()  # Raises CyclicDependencyError
        """
        # build_graph() will raise CyclicDependencyError if cycle detected
        graph = self.build_graph()
        
        # Double-check (should always be True if build_graph succeeded)
        import networkx as nx
        if not nx.is_directed_acyclic_graph(graph):
            # This should not happen, but provide fallback
            try:
                cycle_edges = nx.find_cycle(graph, orientation="original")
                cycle = [edge[0] for edge in cycle_edges]
                cycle.append(cycle[0])
                raise CyclicDependencyError(cycle=cycle)
            except nx.NetworkXNoCycle:
                pass
        
        return True
    
    @property
    def graph(self) -> "nx.DiGraph":
        """Get the built graph, building it if necessary.
        
        Returns:
            The networkx DiGraph
        """
        if self._graph is None:
            self.build_graph()
        return self._graph
    
    def get_task(self, task_id: str) -> TaskInfo:
        """Get TaskInfo by ID.
        
        Args:
            task_id: Task identifier like "T001"
            
        Returns:
            TaskInfo object
            
        Raises:
            KeyError: If task_id not found
        """
        return self._task_map[task_id]
    
    @property
    def task_count(self) -> int:
        """Get total number of tasks."""
        return len(self.tasks)
    
    def get_phases(self) -> list[list[str]]:
        """Extract parallel execution phases using topological generations.
        
        Uses networkx's topological_generations to group tasks into phases
        where all tasks in a phase can execute in parallel (no dependencies
        between them). Each phase contains tasks that depend only on tasks
        from previous phases.
        
        Phase 0 contains tasks with no dependencies.
        Phase N contains tasks whose dependencies are all in phases 0..N-1.
        
        Returns:
            List of phases, where each phase is a list of task IDs that
            can execute in parallel
            
        Example:
            >>> tasks = [
            ...     TaskInfo(id="T001", name="Setup", dependencies=[]),
            ...     TaskInfo(id="T002", name="Build", dependencies=["T001"]),
            ...     TaskInfo(id="T003", name="Test", dependencies=["T001"]),
            ... ]
            >>> engine = DAGEngine(tasks)
            >>> phases = engine.get_phases()
            >>> assert phases[0] == ["T001"]
            >>> assert set(phases[1]) == {"T002", "T003"}
        """
        import networkx as nx
        
        graph = self.build_graph()
        
        # Handle empty graph
        if graph.number_of_nodes() == 0:
            return []
        
        # Use topological_generations to get parallel phases
        # Each generation is a set of nodes with no inter-dependencies
        phases: list[list[str]] = []
        for generation in nx.topological_generations(graph):
            # Sort task IDs within each phase for deterministic output
            phase = sorted(list(generation))
            phases.append(phase)
        
        return phases
    
    def get_critical_path(self) -> list[str]:
        """Calculate the critical path (longest dependency chain).
        
        The critical path represents the longest sequence of dependent tasks
        from any starting task to any ending task. This identifies the
        bottleneck tasks that determine minimum execution time.
        
        Uses networkx's dag_longest_path which finds the longest path in
        a DAG by treating all edges as having weight 1.
        
        Returns:
            List of task IDs forming the critical path, ordered from
            first task to last
            
        Example:
            >>> tasks = [
            ...     TaskInfo(id="T001", name="A", dependencies=[]),
            ...     TaskInfo(id="T002", name="B", dependencies=["T001"]),
            ...     TaskInfo(id="T003", name="C", dependencies=["T002"]),
            ...     TaskInfo(id="T004", name="D", dependencies=["T001"]),
            ... ]
            >>> engine = DAGEngine(tasks)
            >>> path = engine.get_critical_path()
            >>> assert path == ["T001", "T002", "T003"]  # Longest chain
        """
        import networkx as nx
        
        graph = self.build_graph()
        
        # Handle empty graph
        if graph.number_of_nodes() == 0:
            return []
        
        # Find longest path (critical path)
        try:
            critical_path = nx.dag_longest_path(graph)
            return list(critical_path)
        except nx.NetworkXError:
            # Handle edge case of disconnected graph
            # Return longest path among all components
            longest = []
            for component in nx.weakly_connected_components(graph):
                subgraph = graph.subgraph(component)
                try:
                    path = nx.dag_longest_path(subgraph)
                    if len(path) > len(longest):
                        longest = list(path)
                except nx.NetworkXError:
                    continue
            return longest
    
    @property
    def phase_count(self) -> int:
        """Get total number of phases."""
        return len(self.get_phases())
    
    def assign_sessions(self, num_sessions: int) -> None:
        """Assign tasks to sessions using round-robin distribution within phases.
        
        Distributes tasks across sessions to balance load while respecting
        dependencies. Tasks in the same phase are assigned round-robin to
        available sessions. Sequential (non-parallel) tasks are assigned to
        session 0 by convention.
        
        This method mutates the TaskInfo objects in-place, setting their
        session attribute.
        
        Args:
            num_sessions: Number of available sessions (must be >= 1)
            
        Raises:
            ValueError: If num_sessions < 1
            
        Example:
            >>> tasks = [
            ...     TaskInfo(id="T001", name="Setup", dependencies=[]),
            ...     TaskInfo(id="T002", name="A", dependencies=["T001"], parallelizable=True),
            ...     TaskInfo(id="T003", name="B", dependencies=["T001"], parallelizable=True),
            ... ]
            >>> engine = DAGEngine(tasks)
            >>> engine.assign_sessions(2)
            >>> assert engine.get_task("T001").session == 0  # Sequential
            >>> assert engine.get_task("T002").session == 0  # First parallel
            >>> assert engine.get_task("T003").session == 1  # Second parallel
        """
        if num_sessions < 1:
            raise ValueError(f"num_sessions must be >= 1, got {num_sessions}")
        
        phases = self.get_phases()
        
        for phase in phases:
            # Check if all tasks in phase are parallelizable
            phase_tasks = [self.get_task(tid) for tid in phase]
            all_parallel = all(t.parallelizable for t in phase_tasks)
            
            if not all_parallel or len(phase) == 1:
                # Sequential phase or single task: assign all to session 0
                for task in phase_tasks:
                    task.session = 0
            else:
                # Parallel phase: round-robin assignment
                for idx, task in enumerate(phase_tasks):
                    task.session = idx % num_sessions
    
    def get_session_tasks(self, session_id: int) -> list[TaskInfo]:
        """Get all tasks assigned to a specific session.
        
        Returns tasks in topological order (dependencies before dependents).
        
        Args:
            session_id: Session identifier (0-based)
            
        Returns:
            List of TaskInfo objects assigned to this session,
            ordered by dependencies
            
        Example:
            >>> tasks = [
            ...     TaskInfo(id="T001", name="A", dependencies=[]),
            ...     TaskInfo(id="T002", name="B", dependencies=["T001"]),
            ... ]
            >>> engine = DAGEngine(tasks)
            >>> engine.assign_sessions(2)
            >>> engine.get_task("T001").session = 0
            >>> engine.get_task("T002").session = 1
            >>> session_0 = engine.get_session_tasks(0)
            >>> assert len(session_0) == 1
            >>> assert session_0[0].id == "T001"
        """
        import networkx as nx
        
        graph = self.build_graph()
        
        # Get tasks for this session in topological order
        session_tasks = []
        for task_id in nx.topological_sort(graph):
            task = self.get_task(task_id)
            if task.session == session_id:
                session_tasks.append(task)
        
        return session_tasks
    
    def to_yaml(self, spec_id: str, num_sessions: int) -> str:
        """Serialize DAG to YAML string matching dag.yaml schema.
        
        Generates YAML output that matches the schema defined in plan.md,
        including metadata, phases, and task details.
        
        Args:
            spec_id: Specification identifier (e.g., "001-feature-name")
            num_sessions: Number of sessions tasks are assigned to
            
        Returns:
            YAML string representation of the DAG
            
        Example:
            >>> tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
            >>> engine = DAGEngine(tasks)
            >>> engine.assign_sessions(1)
            >>> yaml_str = engine.to_yaml("001-test", 1)
            >>> assert "version: '1.0'" in yaml_str
            >>> assert "spec_id: 001-test" in yaml_str
        """
        # Generate timestamp
        generated_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Build phases with tasks
        phases_list: list[DAGPhase] = []
        for phase_idx, phase_task_ids in enumerate(self.get_phases()):
            phase_tasks = []
            for task_id in phase_task_ids:
                task = self.get_task(task_id)
                # Create DAGNode from TaskInfo
                node = DAGNode(
                    id=task.id,
                    name=task.name,
                    description=task.description or task.name,
                    files=task.files,
                    dependencies=task.dependencies,
                    session=task.session if task.session is not None else 0,
                    parallelizable=task.parallelizable,
                    story=task.story,
                )
                phase_tasks.append(node)
            
            phase = DAGPhase(
                name=f"phase-{phase_idx}",
                tasks=phase_tasks
            )
            phases_list.append(phase)
        
        # Create output model
        output = DAGOutput(
            version="1.0",
            spec_id=spec_id,
            generated_at=generated_at,
            num_sessions=num_sessions,
            phases=phases_list,
        )
        
        # Serialize to YAML
        data = output.model_dump()
        return yaml.dump(data, sort_keys=False, default_flow_style=False)
    
    def save(self, path: Path, spec_id: str, num_sessions: int) -> None:
        """Save DAG to YAML file.
        
        Writes the DAG in YAML format to the specified path, creating
        parent directories if needed.
        
        Args:
            path: Path to write dag.yaml file
            spec_id: Specification identifier
            num_sessions: Number of sessions
            
        Example:
            >>> from pathlib import Path
            >>> tasks = [TaskInfo(id="T001", name="Setup", dependencies=[])]
            >>> engine = DAGEngine(tasks)
            >>> engine.assign_sessions(1)
            >>> engine.save(Path("dag.yaml"), "001-test", 1)
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate YAML
        yaml_content = self.to_yaml(spec_id, num_sessions)
        
        # Write to file
        path.write_text(yaml_content, encoding="utf-8")
    
    @classmethod
    def load(cls, path: Path) -> "DAGEngine":
        """Load DAG from YAML file.
        
        Reads a dag.yaml file and reconstructs the DAGEngine with all
        tasks and their assignments.
        
        Args:
            path: Path to dag.yaml file
            
        Returns:
            DAGEngine instance with tasks loaded from file
            
        Raises:
            FileNotFoundError: If path does not exist
            ValueError: If YAML is invalid or missing required fields
            
        Example:
            >>> from pathlib import Path
            >>> # Assuming dag.yaml exists
            >>> engine = DAGEngine.load(Path("dag.yaml"))
            >>> assert engine.task_count > 0
        """
        if not path.exists():
            raise FileNotFoundError(f"DAG file not found: {path}")
        
        # Load YAML
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        
        if not isinstance(data, dict):
            raise ValueError(f"Invalid DAG YAML: expected dict, got {type(data)}")
        
        # Validate required fields
        if "phases" not in data:
            raise ValueError("Invalid DAG YAML: missing 'phases' field")
        
        # Extract tasks from phases
        tasks: list[TaskInfo] = []
        for phase_data in data["phases"]:
            if not isinstance(phase_data, dict) or "tasks" not in phase_data:
                continue
            
            for task_data in phase_data["tasks"]:
                if not isinstance(task_data, dict):
                    continue
                
                # Reconstruct TaskInfo from DAGNode data
                task = TaskInfo(
                    id=task_data.get("id", ""),
                    name=task_data.get("name", ""),
                    description=task_data.get("description"),
                    dependencies=task_data.get("dependencies", []),
                    session=task_data.get("session"),
                    parallelizable=task_data.get("parallelizable", False),
                    story=task_data.get("story"),
                    files=task_data.get("files", []),
                )
                tasks.append(task)
        
        # Create DAGEngine with loaded tasks
        return cls(tasks)
