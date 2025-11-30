"""
Integration tests for skf run command with dashboard integration.

Tests the T042 implementation: dashboard running alongside orchestration.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from speckit_core.models import SessionStatus, TaskInfo, TaskStatus
from speckit_flow import app
from speckit_flow.monitoring.dashboard import Dashboard
from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.state.manager import StateManager
from speckit_flow.state.models import OrchestrationState, SessionState, TaskStateInfo


runner = CliRunner()


@pytest.fixture
def mock_repo_with_config(tmp_path):
    """Create a mock repository with config and tasks."""
    # Create git repo structure
    specs_dir = tmp_path / "specs" / "test-feature"
    specs_dir.mkdir(parents=True)
    
    # Create tasks.md
    tasks_content = """
# Tasks
- [ ] [T001] [deps:] Task 1
- [ ] [T002] [deps:T001] Task 2
"""
    (specs_dir / "tasks.md").write_text(tasks_content)
    
    # Create config
    config_dir = tmp_path / ".speckit"
    config_dir.mkdir()
    config_content = """
agent_type: copilot
num_sessions: 2
"""
    (config_dir / "speckit-flow.yaml").write_text(config_content)
    
    return tmp_path


class TestRunCommandDashboardIntegration:
    """Test dashboard integration with skf run command."""
    
    @patch("speckit_flow.get_repo_root")
    @patch("speckit_flow.get_feature_paths")
    @patch("speckit_flow.get_current_branch")
    @patch("speckit_flow.parse_tasks_file")
    @patch("speckit_flow.SessionCoordinator")
    @patch("speckit_flow.Dashboard")
    @patch("threading.Thread")
    def test_dashboard_enabled_by_default(
        self,
        mock_thread_class,
        mock_dashboard_class,
        mock_coordinator_class,
        mock_parse_tasks,
        mock_get_branch,
        mock_get_feature_paths,
        mock_get_repo_root,
        mock_repo_with_config,
    ):
        """Dashboard should be enabled by default in skf run."""
        # Arrange
        mock_get_repo_root.return_value = mock_repo_with_config
        mock_get_branch.return_value = "test-feature"
        
        # Mock feature context
        feature_context = Mock()
        feature_context.tasks_path = mock_repo_with_config / "specs" / "test-feature" / "tasks.md"
        feature_context.feature_dir = mock_repo_with_config / "specs" / "test-feature"
        mock_get_feature_paths.return_value = feature_context
        
        # Mock tasks
        tasks = [
            TaskInfo(id="T001", name="Task 1", dependencies=[]),
            TaskInfo(id="T002", name="Task 2", dependencies=["T001"]),
        ]
        mock_parse_tasks.return_value = tasks
        
        # Mock coordinator
        mock_coordinator = Mock()
        mock_coordinator.state_manager = Mock()
        mock_coordinator.state_manager.exists.return_value = False
        mock_coordinator_class.return_value = mock_coordinator
        
        # Mock dashboard
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard
        
        # Mock thread
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Act
        result = runner.invoke(app, ["run"])
        
        # Assert
        assert result.exit_code == 0
        
        # Dashboard should be created
        mock_dashboard_class.assert_called_once()
        call_kwargs = mock_dashboard_class.call_args.kwargs
        assert "state_manager" in call_kwargs
        assert call_kwargs["refresh_rate"] == 0.5
        
        # Thread should be started
        mock_thread_class.assert_called_once()
        assert mock_thread_class.call_args.kwargs["target"] == mock_dashboard.run
        assert mock_thread_class.call_args.kwargs["name"] == "dashboard"
        assert mock_thread_class.call_args.kwargs["daemon"] is True
        mock_thread.start.assert_called_once()
        
        # Dashboard should be stopped after orchestration
        mock_dashboard.stop.assert_called()
    
    @patch("speckit_flow.get_repo_root")
    @patch("speckit_flow.get_feature_paths")
    @patch("speckit_flow.get_current_branch")
    @patch("speckit_flow.parse_tasks_file")
    @patch("speckit_flow.SessionCoordinator")
    @patch("speckit_flow.Dashboard")
    @patch("threading.Thread")
    def test_dashboard_can_be_disabled(
        self,
        mock_thread_class,
        mock_dashboard_class,
        mock_coordinator_class,
        mock_parse_tasks,
        mock_get_branch,
        mock_get_feature_paths,
        mock_get_repo_root,
        mock_repo_with_config,
    ):
        """--no-dashboard flag should disable dashboard."""
        # Arrange
        mock_get_repo_root.return_value = mock_repo_with_config
        mock_get_branch.return_value = "test-feature"
        
        # Mock feature context
        feature_context = Mock()
        feature_context.tasks_path = mock_repo_with_config / "specs" / "test-feature" / "tasks.md"
        feature_context.feature_dir = mock_repo_with_config / "specs" / "test-feature"
        mock_get_feature_paths.return_value = feature_context
        
        # Mock tasks
        tasks = [
            TaskInfo(id="T001", name="Task 1", dependencies=[]),
        ]
        mock_parse_tasks.return_value = tasks
        
        # Mock coordinator
        mock_coordinator = Mock()
        mock_coordinator.state_manager = Mock()
        mock_coordinator.state_manager.exists.return_value = False
        mock_coordinator_class.return_value = mock_coordinator
        
        # Act
        result = runner.invoke(app, ["run", "--no-dashboard"])
        
        # Assert
        assert result.exit_code == 0
        
        # Dashboard should NOT be created
        mock_dashboard_class.assert_not_called()
        
        # Thread should NOT be started
        mock_thread_class.assert_not_called()
    
    @patch("speckit_flow.get_repo_root")
    @patch("speckit_flow.get_feature_paths")
    @patch("speckit_flow.get_current_branch")
    @patch("speckit_flow.parse_tasks_file")
    @patch("speckit_flow.SessionCoordinator")
    @patch("speckit_flow.Dashboard")
    @patch("threading.Thread")
    def test_dashboard_stops_on_keyboard_interrupt(
        self,
        mock_thread_class,
        mock_dashboard_class,
        mock_coordinator_class,
        mock_parse_tasks,
        mock_get_branch,
        mock_get_feature_paths,
        mock_get_repo_root,
        mock_repo_with_config,
    ):
        """Dashboard should stop cleanly when user interrupts orchestration."""
        # Arrange
        mock_get_repo_root.return_value = mock_repo_with_config
        mock_get_branch.return_value = "test-feature"
        
        # Mock feature context
        feature_context = Mock()
        feature_context.tasks_path = mock_repo_with_config / "specs" / "test-feature" / "tasks.md"
        feature_context.feature_dir = mock_repo_with_config / "specs" / "test-feature"
        mock_get_feature_paths.return_value = feature_context
        
        # Mock tasks
        tasks = [
            TaskInfo(id="T001", name="Task 1", dependencies=[]),
        ]
        mock_parse_tasks.return_value = tasks
        
        # Mock coordinator to raise KeyboardInterrupt
        mock_coordinator = Mock()
        mock_coordinator.state_manager = Mock()
        mock_coordinator.state_manager.exists.return_value = False
        mock_coordinator.run.side_effect = KeyboardInterrupt()
        mock_coordinator_class.return_value = mock_coordinator
        
        # Mock dashboard
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard
        
        # Mock thread
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Act
        result = runner.invoke(app, ["run"])
        
        # Assert
        assert result.exit_code == 0  # Graceful exit
        
        # Dashboard should be stopped (called at least once, possibly twice from finally block)
        assert mock_dashboard.stop.call_count >= 1
    
    @patch("speckit_flow.get_repo_root")
    @patch("speckit_flow.get_feature_paths")
    @patch("speckit_flow.get_current_branch")
    @patch("speckit_flow.parse_tasks_file")
    @patch("speckit_flow.SessionCoordinator")
    @patch("speckit_flow.Dashboard")
    @patch("threading.Thread")
    def test_dashboard_thread_joins_after_orchestration(
        self,
        mock_thread_class,
        mock_dashboard_class,
        mock_coordinator_class,
        mock_parse_tasks,
        mock_get_branch,
        mock_get_feature_paths,
        mock_get_repo_root,
        mock_repo_with_config,
    ):
        """Dashboard thread should be joined to ensure clean exit."""
        # Arrange
        mock_get_repo_root.return_value = mock_repo_with_config
        mock_get_branch.return_value = "test-feature"
        
        # Mock feature context
        feature_context = Mock()
        feature_context.tasks_path = mock_repo_with_config / "specs" / "test-feature" / "tasks.md"
        feature_context.feature_dir = mock_repo_with_config / "specs" / "test-feature"
        mock_get_feature_paths.return_value = feature_context
        
        # Mock tasks
        tasks = [
            TaskInfo(id="T001", name="Task 1", dependencies=[]),
        ]
        mock_parse_tasks.return_value = tasks
        
        # Mock coordinator
        mock_coordinator = Mock()
        mock_coordinator.state_manager = Mock()
        mock_coordinator.state_manager.exists.return_value = False
        mock_coordinator_class.return_value = mock_coordinator
        
        # Mock dashboard
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard
        
        # Mock thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        mock_thread_class.return_value = mock_thread
        
        # Act
        result = runner.invoke(app, ["run"])
        
        # Assert
        assert result.exit_code == 0
        
        # Thread should be joined with timeout to prevent hanging
        mock_thread.join.assert_called_once_with(timeout=1.0)


class TestDashboardThreadSafety:
    """Test thread safety and race conditions."""
    
    def test_dashboard_can_be_stopped_before_started(self):
        """Dashboard.stop() should be safe to call even if run() never started."""
        # Arrange
        state_manager = Mock()
        dashboard = Dashboard(state_manager, refresh_rate=0.5)
        
        # Act - stop before run
        dashboard.stop()
        
        # Assert - should not raise
        # This tests the safety of the implementation
    
    def test_dashboard_can_be_stopped_multiple_times(self):
        """Dashboard.stop() should be idempotent."""
        # Arrange
        state_manager = Mock()
        dashboard = Dashboard(state_manager, refresh_rate=0.5)
        
        # Act - stop multiple times
        dashboard.stop()
        dashboard.stop()
        dashboard.stop()
        
        # Assert - should not raise
        # This tests idempotency


@pytest.mark.slow
class TestDashboardIntegrationEndToEnd:
    """End-to-end integration tests with real Dashboard."""
    
    def test_dashboard_updates_with_state_changes(self, tmp_path):
        """Dashboard should reflect state changes in real-time."""
        # Arrange
        state_manager = StateManager(tmp_path)
        
        # Create initial state
        state = OrchestrationState(
            version="1.0",
            spec_id="test",
            agent_type="copilot",
            num_sessions=1,
            base_branch="main",
            started_at="2025-11-29T00:00:00Z",
            updated_at="2025-11-29T00:00:00Z",
            current_phase="phase-0",
            phases_completed=[],
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=".worktrees/session-0",
                    branch_name="impl-test-session-0",
                    current_task="T001",
                    completed_tasks=[],
                    status=SessionStatus.executing,
                )
            ],
            tasks={
                "T001": TaskStateInfo(
                    status=TaskStatus.in_progress,
                    session=0,
                    started_at="2025-11-29T00:00:00Z",
                )
            },
            merge_status=None,
        )
        state_manager.save(state)
        
        # Create dashboard
        dashboard = Dashboard(state_manager, refresh_rate=0.1)
        
        # Act - render once to verify it works with real state
        try:
            dashboard.render_once()
        except Exception as e:
            pytest.fail(f"Dashboard failed to render: {e}")
        
        # Update state
        state.tasks["T001"].status = TaskStatus.completed
        state_manager.save(state)
        
        # Render again with updated state
        try:
            dashboard.render_once()
        except Exception as e:
            pytest.fail(f"Dashboard failed to render updated state: {e}")


class TestAcceptanceCriteria:
    """Verify all acceptance criteria for T042."""
    
    @patch("speckit_flow.get_repo_root")
    @patch("speckit_flow.get_feature_paths")
    @patch("speckit_flow.get_current_branch")
    @patch("speckit_flow.parse_tasks_file")
    @patch("speckit_flow.SessionCoordinator")
    @patch("speckit_flow.Dashboard")
    @patch("threading.Thread")
    def test_ac1_dashboard_runs_alongside_orchestration(
        self,
        mock_thread_class,
        mock_dashboard_class,
        mock_coordinator_class,
        mock_parse_tasks,
        mock_get_branch,
        mock_get_feature_paths,
        mock_get_repo_root,
        tmp_path,
    ):
        """AC1: Dashboard runs alongside orchestration."""
        # Setup mocks
        mock_get_repo_root.return_value = tmp_path
        mock_get_branch.return_value = "test"
        
        feature_context = Mock()
        feature_context.tasks_path = tmp_path / "tasks.md"
        feature_context.tasks_path.write_text("- [ ] [T001] Task")
        feature_context.feature_dir = tmp_path
        mock_get_feature_paths.return_value = feature_context
        
        tasks = [TaskInfo(id="T001", name="Task", dependencies=[])]
        mock_parse_tasks.return_value = tasks
        
        mock_coordinator = Mock()
        mock_coordinator.state_manager.exists.return_value = False
        mock_coordinator_class.return_value = mock_coordinator
        
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Create config
        (tmp_path / ".speckit").mkdir()
        (tmp_path / ".speckit" / "speckit-flow.yaml").write_text("agent_type: copilot\nnum_sessions: 1")
        (tmp_path / "specs").mkdir()
        
        # Act
        result = runner.invoke(app, ["run"])
        
        # Assert - Dashboard created and thread started
        assert result.exit_code == 0
        mock_dashboard_class.assert_called_once()
        mock_thread.start.assert_called_once()
    
    @patch("speckit_flow.get_repo_root")
    @patch("speckit_flow.get_feature_paths")
    @patch("speckit_flow.get_current_branch")
    @patch("speckit_flow.parse_tasks_file")
    @patch("speckit_flow.SessionCoordinator")
    @patch("speckit_flow.Dashboard")
    def test_ac2_no_dashboard_disables_for_ci(
        self,
        mock_dashboard_class,
        mock_coordinator_class,
        mock_parse_tasks,
        mock_get_branch,
        mock_get_feature_paths,
        mock_get_repo_root,
        tmp_path,
    ):
        """AC2: --no-dashboard disables for CI/scripting."""
        # Setup mocks
        mock_get_repo_root.return_value = tmp_path
        mock_get_branch.return_value = "test"
        
        feature_context = Mock()
        feature_context.tasks_path = tmp_path / "tasks.md"
        feature_context.tasks_path.write_text("- [ ] [T001] Task")
        feature_context.feature_dir = tmp_path
        mock_get_feature_paths.return_value = feature_context
        
        tasks = [TaskInfo(id="T001", name="Task", dependencies=[])]
        mock_parse_tasks.return_value = tasks
        
        mock_coordinator = Mock()
        mock_coordinator.state_manager.exists.return_value = False
        mock_coordinator_class.return_value = mock_coordinator
        
        # Create config
        (tmp_path / ".speckit").mkdir()
        (tmp_path / ".speckit" / "speckit-flow.yaml").write_text("agent_type: copilot\nnum_sessions: 1")
        (tmp_path / "specs").mkdir()
        
        # Act
        result = runner.invoke(app, ["run", "--no-dashboard"])
        
        # Assert - Dashboard NOT created
        assert result.exit_code == 0
        mock_dashboard_class.assert_not_called()
    
    @patch("speckit_flow.get_repo_root")
    @patch("speckit_flow.get_feature_paths")
    @patch("speckit_flow.get_current_branch")
    @patch("speckit_flow.parse_tasks_file")
    @patch("speckit_flow.SessionCoordinator")
    @patch("speckit_flow.Dashboard")
    @patch("threading.Thread")
    def test_ac3_clean_exit_without_orphan_processes(
        self,
        mock_thread_class,
        mock_dashboard_class,
        mock_coordinator_class,
        mock_parse_tasks,
        mock_get_branch,
        mock_get_feature_paths,
        mock_get_repo_root,
        tmp_path,
    ):
        """AC3: Clean exit without orphan processes."""
        # Setup mocks
        mock_get_repo_root.return_value = tmp_path
        mock_get_branch.return_value = "test"
        
        feature_context = Mock()
        feature_context.tasks_path = tmp_path / "tasks.md"
        feature_context.tasks_path.write_text("- [ ] [T001] Task")
        feature_context.feature_dir = tmp_path
        mock_get_feature_paths.return_value = feature_context
        
        tasks = [TaskInfo(id="T001", name="Task", dependencies=[])]
        mock_parse_tasks.return_value = tasks
        
        mock_coordinator = Mock()
        mock_coordinator.state_manager.exists.return_value = False
        mock_coordinator_class.return_value = mock_coordinator
        
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard
        
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        mock_thread_class.return_value = mock_thread
        
        # Create config
        (tmp_path / ".speckit").mkdir()
        (tmp_path / ".speckit" / "speckit-flow.yaml").write_text("agent_type: copilot\nnum_sessions: 1")
        (tmp_path / "specs").mkdir()
        
        # Act
        result = runner.invoke(app, ["run"])
        
        # Assert - Dashboard stopped and thread joined
        assert result.exit_code == 0
        mock_dashboard.stop.assert_called()
        mock_thread.join.assert_called_with(timeout=1.0)
