"""
Unit tests for monitoring dashboard.

Tests the Dashboard class for real-time orchestration monitoring,
including rendering, state polling, and terminal degradation.
"""

import time
from datetime import datetime
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, patch

import pytest

from speckit_core.models import SessionState, SessionStatus, TaskStatus
from speckit_flow.exceptions import StateNotFoundError
from speckit_flow.monitoring.dashboard import Dashboard
from speckit_flow.state.manager import StateManager
from speckit_flow.state.models import OrchestrationState, TaskStateInfo


@pytest.fixture
def sample_state():
    """Create sample orchestration state for testing."""
    return OrchestrationState(
        version="1.0",
        spec_id="001-test",
        agent_type="copilot",
        num_sessions=2,
        base_branch="main",
        started_at="2025-11-28T10:30:00Z",
        updated_at="2025-11-28T10:45:00Z",
        current_phase="phase-1",
        phases_completed=["phase-0"],
        sessions=[
            SessionState(
                session_id=0,
                worktree_path=".worktrees-001/session-0-setup",
                branch_name="impl-001-session-0",
                current_task="T002",
                completed_tasks=["T001"],
                status=SessionStatus.executing,
            ),
            SessionState(
                session_id=1,
                worktree_path=".worktrees-001/session-1-feature",
                branch_name="impl-001-session-1",
                current_task="T003",
                completed_tasks=[],
                status=SessionStatus.executing,
            ),
        ],
        tasks={
            "T001": TaskStateInfo(
                status=TaskStatus.completed,
                session=0,
                started_at="2025-11-28T10:30:00Z",
                completed_at="2025-11-28T10:35:00Z",
            ),
            "T002": TaskStateInfo(
                status=TaskStatus.in_progress,
                session=0,
                started_at="2025-11-28T10:36:00Z",
            ),
            "T003": TaskStateInfo(
                status=TaskStatus.in_progress,
                session=1,
                started_at="2025-11-28T10:36:00Z",
            ),
            "T004": TaskStateInfo(
                status=TaskStatus.pending,
                session=None,
            ),
        },
    )


@pytest.fixture
def state_manager(tmp_path, sample_state):
    """Create StateManager with sample state."""
    manager = StateManager(tmp_path)
    manager.save(sample_state)
    return manager


class TestDashboardInitialization:
    """Tests for Dashboard initialization."""
    
    def test_creates_with_state_manager(self, state_manager):
        """Dashboard initializes with StateManager."""
        dashboard = Dashboard(state_manager)
        
        assert dashboard.state_manager == state_manager
        assert dashboard.refresh_rate == 0.5  # Default
        assert dashboard.console is not None
    
    def test_creates_with_custom_refresh_rate(self, state_manager):
        """Dashboard accepts custom refresh rate."""
        dashboard = Dashboard(state_manager, refresh_rate=1.0)
        
        assert dashboard.refresh_rate == 1.0
    
    def test_stop_flag_initially_false(self, state_manager):
        """Stop flag is initially False."""
        dashboard = Dashboard(state_manager)
        
        assert dashboard._stop is False


class TestSessionTableRendering:
    """Tests for session table rendering."""
    
    def test_renders_session_table(self, state_manager, sample_state):
        """Renders table with all sessions."""
        dashboard = Dashboard(state_manager)
        table = dashboard._render_session_table(sample_state)
        
        # Table should have correct structure
        assert table.title == "Sessions"
        assert len(table.columns) == 4  # ID, Status, Current Task, Worktree
        
        # Should have 2 rows (one per session)
        assert len(table.rows) == 2
    
    def test_session_status_colors(self, state_manager, sample_state):
        """Session status is styled with appropriate colors."""
        dashboard = Dashboard(state_manager)
        
        # Test various session statuses
        sample_state.sessions[0].status = SessionStatus.completed
        sample_state.sessions[1].status = SessionStatus.failed
        
        table = dashboard._render_session_table(sample_state)
        
        # Verify table renders without error (color codes present in markup)
        assert len(table.rows) == 2
    
    def test_handles_missing_worktree_path(self, state_manager, sample_state):
        """Handles sessions with no worktree path."""
        sample_state.sessions[0].worktree_path = None
        
        dashboard = Dashboard(state_manager)
        table = dashboard._render_session_table(sample_state)
        
        # Should show "—" for missing worktree
        assert len(table.rows) == 2
    
    def test_handles_empty_sessions(self, state_manager, sample_state):
        """Handles state with no sessions."""
        sample_state.sessions = []
        
        dashboard = Dashboard(state_manager)
        table = dashboard._render_session_table(sample_state)
        
        assert len(table.rows) == 0


class TestDAGTreeRendering:
    """Tests for DAG phase tree rendering."""
    
    def test_renders_dag_tree(self, state_manager, sample_state):
        """Renders tree with phase hierarchy."""
        dashboard = Dashboard(state_manager)
        tree = dashboard._render_dag_tree(sample_state)
        
        # Tree should have label
        assert tree.label is not None
        # Should have child nodes
        assert len(tree.children) > 0
    
    def test_shows_completed_phases(self, state_manager, sample_state):
        """Shows completed phases section."""
        dashboard = Dashboard(state_manager)
        tree = dashboard._render_dag_tree(sample_state)
        
        # Should have completed phases node
        assert len(tree.children) >= 1
    
    def test_shows_current_phase(self, state_manager, sample_state):
        """Shows current phase with in-progress tasks."""
        dashboard = Dashboard(state_manager)
        tree = dashboard._render_dag_tree(sample_state)
        
        # Should have current phase node
        assert sample_state.current_phase is not None
        assert len(tree.children) >= 2
    
    def test_shows_pending_tasks_count(self, state_manager, sample_state):
        """Shows count of pending tasks."""
        dashboard = Dashboard(state_manager)
        tree = dashboard._render_dag_tree(sample_state)
        
        # Should include pending count
        assert len(tree.children) >= 1
    
    def test_task_status_icons(self, state_manager, sample_state):
        """Tasks have appropriate status icons."""
        # Add tasks with various statuses
        sample_state.tasks["T005"] = TaskStateInfo(
            status=TaskStatus.failed,
            session=0,
        )
        
        dashboard = Dashboard(state_manager)
        tree = dashboard._render_dag_tree(sample_state)
        
        # Tree renders successfully with all status types
        assert tree is not None


class TestProgressBarRendering:
    """Tests for overall progress bar."""
    
    def test_renders_progress_bar(self, state_manager, sample_state):
        """Renders progress bar with correct counts."""
        dashboard = Dashboard(state_manager)
        progress = dashboard._render_progress_bar(sample_state)
        
        # Should have one task tracking overall progress
        assert len(progress.tasks) == 1
        
        task = list(progress.tasks)[0]
        assert progress.tasks[task].total == 4  # 4 total tasks
        assert progress.tasks[task].completed == 1  # 1 completed
    
    def test_progress_percentage(self, state_manager, sample_state):
        """Progress percentage is calculated correctly."""
        dashboard = Dashboard(state_manager)
        progress = dashboard._render_progress_bar(sample_state)
        
        task = list(progress.tasks)[0]
        # 1 of 4 tasks complete = 25%
        assert progress.tasks[task].percentage == 25.0
    
    def test_handles_no_tasks(self, state_manager, sample_state):
        """Handles state with no tasks."""
        sample_state.tasks = {}
        
        dashboard = Dashboard(state_manager)
        progress = dashboard._render_progress_bar(sample_state)
        
        task = list(progress.tasks)[0]
        assert progress.tasks[task].total == 0


class TestCompleteDashboardRendering:
    """Tests for full dashboard layout."""
    
    def test_renders_complete_dashboard(self, state_manager, sample_state):
        """Renders complete dashboard with all sections."""
        dashboard = Dashboard(state_manager)
        layout = dashboard._render_dashboard(sample_state)
        
        # Should return a renderable Group
        assert layout is not None
    
    def test_includes_title_panel(self, state_manager, sample_state):
        """Dashboard includes title panel with metadata."""
        dashboard = Dashboard(state_manager)
        layout = dashboard._render_dashboard(sample_state)
        
        # Render should succeed
        assert layout is not None


class TestDashboardRunning:
    """Tests for dashboard run loop."""
    
    def test_stops_after_duration(self, state_manager):
        """Dashboard stops after specified duration."""
        dashboard = Dashboard(state_manager, refresh_rate=0.1)
        
        start = time.time()
        dashboard.run(duration=0.3)
        elapsed = time.time() - start
        
        # Should stop around 0.3 seconds
        assert 0.2 <= elapsed <= 0.5
    
    def test_stops_on_stop_signal(self, state_manager):
        """Dashboard stops when stop() is called."""
        dashboard = Dashboard(state_manager, refresh_rate=0.1)
        
        # Run in background thread
        def run_dashboard():
            dashboard.run()
        
        thread = Thread(target=run_dashboard, daemon=True)
        thread.start()
        
        # Let it run a bit
        time.sleep(0.2)
        
        # Signal stop
        dashboard.stop()
        
        # Wait for thread to finish
        thread.join(timeout=1.0)
        
        assert not thread.is_alive()
    
    def test_stops_on_completion(self, state_manager, sample_state):
        """Dashboard stops when orchestration completes."""
        # Mark all tasks and sessions complete
        for task_info in sample_state.tasks.values():
            task_info.status = TaskStatus.completed
        for session in sample_state.sessions:
            session.status = SessionStatus.completed
        
        state_manager.save(sample_state)
        
        dashboard = Dashboard(state_manager, refresh_rate=0.1)
        
        start = time.time()
        dashboard.run()
        elapsed = time.time() - start
        
        # Should stop quickly (within a few refresh cycles)
        assert elapsed < 1.0
    
    def test_handles_missing_state_file(self, tmp_path):
        """Dashboard handles missing state file gracefully."""
        manager = StateManager(tmp_path)
        # Don't create state file
        
        dashboard = Dashboard(manager, refresh_rate=0.1)
        
        # Should not crash
        dashboard.run(duration=0.2)


class TestRenderOnce:
    """Tests for single-shot rendering."""
    
    def test_renders_without_live_display(self, state_manager, sample_state):
        """Renders dashboard once without Live display."""
        dashboard = Dashboard(state_manager)
        
        # Should not raise
        with patch.object(dashboard.console, "print"):
            dashboard.render_once()
    
    def test_handles_missing_state(self, tmp_path):
        """Renders error message when state missing."""
        manager = StateManager(tmp_path)
        dashboard = Dashboard(manager)
        
        # Should show error panel
        with patch.object(dashboard.console, "print") as mock_print:
            dashboard.render_once()
            mock_print.assert_called_once()


class TestCompletionDetection:
    """Tests for completion detection logic."""
    
    def test_detects_all_tasks_complete(self, state_manager, sample_state):
        """Detects when all tasks are complete."""
        # Mark all complete
        for task_info in sample_state.tasks.values():
            task_info.status = TaskStatus.completed
        for session in sample_state.sessions:
            session.status = SessionStatus.completed
        
        dashboard = Dashboard(state_manager)
        
        assert dashboard._is_complete(sample_state) is True
    
    def test_detects_incomplete_tasks(self, state_manager, sample_state):
        """Detects when tasks are still in progress."""
        dashboard = Dashboard(state_manager)
        
        # Sample state has in_progress tasks
        assert dashboard._is_complete(sample_state) is False
    
    def test_detects_failed_completion(self, state_manager, sample_state):
        """Detects completion even with failed tasks."""
        # Mark some failed
        sample_state.tasks["T002"].status = TaskStatus.failed
        sample_state.tasks["T003"].status = TaskStatus.completed
        sample_state.tasks["T004"].status = TaskStatus.completed
        
        for session in sample_state.sessions:
            session.status = SessionStatus.completed
        
        dashboard = Dashboard(state_manager)
        
        # All tasks done (either completed or failed) = complete
        assert dashboard._is_complete(sample_state) is True


class TestNarrowTerminalDegradation:
    """Tests for narrow terminal handling."""
    
    def test_renders_in_narrow_terminal(self, state_manager, sample_state):
        """Dashboard renders gracefully in narrow terminals."""
        # Simulate narrow console
        with patch.object(Dashboard, '__init__', lambda self, sm, rr=0.5: (
            setattr(self, 'state_manager', sm),
            setattr(self, 'refresh_rate', rr),
            setattr(self, 'console', Mock(width=60)),
            setattr(self, '_stop', False),
        )):
            dashboard = Dashboard(state_manager)
            layout = dashboard._render_dashboard(sample_state)
            
            # Should render without error
            assert layout is not None


class TestStatePolling:
    """Tests for state file polling behavior."""
    
    def test_polls_at_refresh_rate(self, state_manager, sample_state):
        """Dashboard polls state file at specified rate."""
        dashboard = Dashboard(state_manager, refresh_rate=0.1)
        
        poll_count = 0
        original_load = state_manager.load
        
        def counting_load():
            nonlocal poll_count
            poll_count += 1
            return original_load()
        
        with patch.object(state_manager, 'load', side_effect=counting_load):
            dashboard.run(duration=0.3)
        
        # Should poll approximately 3 times in 0.3 seconds with 0.1s refresh
        assert 2 <= poll_count <= 5
    
    def test_continues_on_load_error(self, state_manager):
        """Dashboard continues running if state load fails temporarily."""
        dashboard = Dashboard(state_manager, refresh_rate=0.1)
        
        call_count = 0
        
        def failing_load():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise StateNotFoundError("Temporary error")
            return state_manager.load()
        
        with patch.object(state_manager, 'load', side_effect=failing_load):
            # Should not crash despite initial errors
            dashboard.run(duration=0.3)


class TestNextActionsPanel:
    """Tests for next-action prompts panel."""
    
    def test_renders_next_actions_for_idle_sessions(self, state_manager):
        """Next actions panel shows prompt to open idle session worktrees."""
        state = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:30:00Z",
            current_phase="phase-0",
            phases_completed=[],
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=str(state_manager.repo_root / ".worktrees-001/session-0"),
                    branch_name="impl-001-session-0",
                    current_task="T001",
                    completed_tasks=[],
                    status=SessionStatus.idle,
                ),
            ],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.pending, session=0),
            },
        )
        
        dashboard = Dashboard(state_manager)
        panel = dashboard._render_next_actions(state)
        
        # Should contain session info
        assert "Session 0" in str(panel)
        assert "T001" in str(panel)
        assert "/speckit.implement" in str(panel)
        # Should show absolute path
        assert str(state_manager.repo_root) in str(panel)
    
    def test_renders_next_actions_for_all_complete(self, state_manager):
        """Next actions panel prompts for merge when all tasks complete."""
        state = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-1",
            phases_completed=["phase-0"],
            sessions=[
                SessionState(
                    session_id=0,
                    status=SessionStatus.completed,
                ),
                SessionState(
                    session_id=1,
                    status=SessionStatus.completed,
                ),
            ],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T002": TaskStateInfo(status=TaskStatus.completed, session=1),
            },
        )
        
        dashboard = Dashboard(state_manager)
        panel = dashboard._render_next_actions(state)
        
        # Should prompt for merge
        assert "All tasks complete" in str(panel)
        assert "skf merge" in str(panel)
    
    def test_renders_next_actions_for_waiting_tasks(self, state_manager):
        """Next actions panel shows waiting message for in-progress tasks."""
        state = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:35:00Z",
            current_phase="phase-0",
            phases_completed=[],
            sessions=[
                SessionState(
                    session_id=0,
                    status=SessionStatus.executing,
                    current_task="T001",
                ),
            ],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.in_progress, session=0),
                "T002": TaskStateInfo(status=TaskStatus.pending, session=None),
            },
        )
        
        dashboard = Dashboard(state_manager)
        panel = dashboard._render_next_actions(state)
        
        # Should show waiting message
        assert "Waiting for" in str(panel) or "Currently executing" in str(panel)
        assert "T001" in str(panel)
    
    def test_renders_multiple_idle_sessions(self, state_manager):
        """Next actions panel shows multiple idle sessions."""
        sessions = [
            SessionState(
                session_id=i,
                worktree_path=str(state_manager.repo_root / f".worktrees-001/session-{i}"),
                branch_name=f"impl-001-session-{i}",
                current_task=f"T{i+1:03d}",
                completed_tasks=[],
                status=SessionStatus.idle,
            )
            for i in range(5)
        ]
        
        state = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=5,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:30:00Z",
            current_phase="phase-0",
            phases_completed=[],
            sessions=sessions,
            tasks={
                f"T{i+1:03d}": TaskStateInfo(status=TaskStatus.pending, session=i)
                for i in range(5)
            },
        )
        
        dashboard = Dashboard(state_manager)
        panel = dashboard._render_next_actions(state)
        
        panel_str = str(panel)
        
        # Should show first 3 sessions
        assert "Session 0" in panel_str
        assert "Session 1" in panel_str
        assert "Session 2" in panel_str
        
        # Should indicate more sessions available
        assert "2 more sessions" in panel_str
    
    def test_renders_no_actions_message(self, state_manager):
        """Next actions panel shows default message when no actions needed."""
        state = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:30:00Z",
            current_phase="phase-0",
            phases_completed=[],
            sessions=[
                SessionState(
                    session_id=0,
                    status=SessionStatus.waiting,
                ),
            ],
            tasks={},
        )
        
        dashboard = Dashboard(state_manager)
        panel = dashboard._render_next_actions(state)
        
        # Should show monitoring message
        assert "No pending actions" in str(panel) or "Monitoring" in str(panel)
    
    def test_next_actions_paths_are_copy_pasteable(self, state_manager):
        """Next actions panel paths are absolute and copy-pasteable."""
        worktree_path = state_manager.repo_root / ".worktrees-001/session-0"
        
        state = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:30:00Z",
            current_phase="phase-0",
            phases_completed=[],
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=str(worktree_path),
                    branch_name="impl-001-session-0",
                    current_task="T001",
                    status=SessionStatus.idle,
                ),
            ],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.pending, session=0),
            },
        )
        
        dashboard = Dashboard(state_manager)
        panel = dashboard._render_next_actions(state)
        
        panel_str = str(panel)
        
        # Should contain absolute path (starts with /)
        assert str(worktree_path.absolute()) in panel_str
    
    def test_next_actions_updates_with_state(self, state_manager):
        """Next actions panel content changes as state progresses."""
        # Initial state - idle session
        state_idle = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:30:00Z",
            current_phase="phase-0",
            phases_completed=[],
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path="/tmp/worktree",
                    current_task="T001",
                    status=SessionStatus.idle,
                ),
            ],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.pending, session=0),
            },
        )
        
        # Later state - all complete
        state_complete = OrchestrationState(
            version="1.0",
            spec_id="001-test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-28T10:30:00Z",
            updated_at="2025-11-28T10:45:00Z",
            current_phase="phase-0",
            phases_completed=["phase-0"],
            sessions=[
                SessionState(
                    session_id=0,
                    status=SessionStatus.completed,
                ),
            ],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
            },
        )
        
        dashboard = Dashboard(state_manager)
        
        # Render with idle state
        panel_idle = dashboard._render_next_actions(state_idle)
        assert "Session 0" in str(panel_idle)
        assert "/speckit.implement" in str(panel_idle)
        
        # Render with complete state
        panel_complete = dashboard._render_next_actions(state_complete)
        assert "All tasks complete" in str(panel_complete)
        assert "skf merge" in str(panel_complete)

