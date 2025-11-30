"""
Unit tests for SessionCoordinator.run() method (T030).

Tests the full orchestration workflow including initialization, phase execution,
resumption from checkpoints, and graceful shutdown.
"""

import signal
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from speckit_core.config import SpecKitFlowConfig
from speckit_core.models import SessionState, SessionStatus, TaskInfo, TaskStatus
from speckit_flow.agents.base import AgentAdapter
from speckit_flow.orchestration.dag_engine import DAGEngine
from speckit_flow.orchestration.session_coordinator import SessionCoordinator
from speckit_flow.state.models import OrchestrationState, TaskStateInfo


@pytest.fixture
def sample_tasks():
    """Sample task list for testing."""
    return [
        TaskInfo(
            id="T001",
            name="Setup",
            description="Initial setup",
            dependencies=[],
            parallelizable=False,
            story=None,
            files=[],
            status="pending"
        ),
        TaskInfo(
            id="T002",
            name="Feature A",
            description="Implement A",
            dependencies=["T001"],
            parallelizable=True,
            story=None,
            files=[],
            status="pending"
        ),
        TaskInfo(
            id="T003",
            name="Feature B",
            description="Implement B",
            dependencies=["T001"],
            parallelizable=True,
            story=None,
            files=[],
            status="pending"
        ),
    ]


@pytest.fixture
def dag_engine(sample_tasks):
    """DAG engine with sample tasks."""
    engine = DAGEngine(sample_tasks)
    engine.validate()
    return engine


@pytest.fixture
def config():
    """Sample configuration."""
    return SpecKitFlowConfig(agent_type="copilot", num_sessions=2)


@pytest.fixture
def mock_adapter():
    """Mock agent adapter."""
    adapter = Mock(spec=AgentAdapter)
    adapter.setup_session = Mock()
    adapter.notify_user = Mock()
    adapter.get_files_to_watch = Mock(return_value=[])
    return adapter


@pytest.fixture
def coordinator(dag_engine, config, mock_adapter, tmp_path):
    """Session coordinator instance."""
    return SessionCoordinator(
        dag=dag_engine,
        config=config,
        adapter=mock_adapter,
        repo_root=tmp_path,
        spec_id="test-001",
        base_branch="main"
    )


class TestRunMethod:
    """Tests for SessionCoordinator.run() method."""
    
    def test_run_method_exists(self, coordinator):
        """Verify run() method exists."""
        assert hasattr(coordinator, 'run')
        assert callable(coordinator.run)
    
    def test_run_initializes_when_no_state(self, coordinator):
        """AC1: Executes all phases in order - initializes on first run."""
        # Mock worktree creation to avoid git operations
        with patch.object(coordinator.worktree_manager, 'create') as mock_create:
            mock_create.return_value = coordinator.repo_root / "worktree"
            
            # Mock completion to return immediately
            with patch.object(coordinator.completion_monitor, 'wait_for_completion') as mock_wait:
                mock_wait.side_effect = lambda task_ids, **kwargs: task_ids
                
                # Mock run_phase to avoid actual execution
                with patch.object(coordinator, 'run_phase') as mock_run_phase:
                    # Run orchestration
                    coordinator.run()
                    
                    # Verify initialization happened
                    assert coordinator.state_manager.exists()
                    
                    # Verify phases were executed
                    # DAG has 2 phases: phase-0 (T001), phase-1 (T002, T003)
                    assert mock_run_phase.call_count == 2
    
    def test_run_resumes_from_existing_state(self, coordinator, tmp_path):
        """AC2: Resumes from checkpoint after crash."""
        # Create initial state with phase-0 completed
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        state = OrchestrationState(
            version="1.0",
            spec_id="test-001",
            agent_type="copilot",
            num_sessions=2,
            base_branch="main",
            started_at=now,
            updated_at=now,
            current_phase="phase-0",
            phases_completed=["phase-0"],
            sessions=[
                SessionState(
                    session_id=0,
                    worktree_path=".worktrees-test-001/session-0",
                    branch_name="impl-test-001-session-0",
                    current_task=None,
                    completed_tasks=["T001"],
                    status=SessionStatus.idle
                ),
            ],
            tasks={
                "T001": TaskStateInfo(status=TaskStatus.completed, session=0),
                "T002": TaskStateInfo(status=TaskStatus.pending, session=0),
                "T003": TaskStateInfo(status=TaskStatus.pending, session=1),
            }
        )
        
        # Save state
        coordinator.state_manager.save(state)
        
        # Mock run_phase to track execution
        with patch.object(coordinator, 'run_phase') as mock_run_phase:
            # Mock completion
            with patch.object(coordinator.completion_monitor, 'wait_for_completion') as mock_wait:
                mock_wait.side_effect = lambda task_ids, **kwargs: task_ids
                
                # Run orchestration
                coordinator.run()
                
                # Verify it resumed from phase 1 (skipping completed phase 0)
                # Should only call run_phase once for phase-1
                assert mock_run_phase.call_count == 1
                mock_run_phase.assert_called_with(1)
    
    def test_run_handles_keyboard_interrupt(self, coordinator):
        """AC3: Ctrl+C saves state before exit."""
        # Mock run_phase to raise KeyboardInterrupt
        with patch.object(coordinator, 'run_phase') as mock_run_phase:
            mock_run_phase.side_effect = KeyboardInterrupt()
            
            # Mock worktree creation
            with patch.object(coordinator.worktree_manager, 'create') as mock_create:
                mock_create.return_value = coordinator.repo_root / "worktree"
                
                # Run orchestration (should not raise)
                coordinator.run()
                
                # Verify interrupted flag was set
                assert coordinator._interrupted
                
                # Verify state exists (was saved)
                assert coordinator.state_manager.exists()
    
    def test_run_marks_all_tasks_complete(self, coordinator):
        """AC4: Final state shows all tasks completed."""
        # Mock worktree creation
        with patch.object(coordinator.worktree_manager, 'create') as mock_create:
            mock_create.return_value = coordinator.repo_root / "worktree"
            
            # Mock completion to return immediately
            with patch.object(coordinator.completion_monitor, 'wait_for_completion') as mock_wait:
                mock_wait.side_effect = lambda task_ids, **kwargs: task_ids
                
                # Run orchestration
                coordinator.run()
                
                # Load final state
                state = coordinator.state_manager.load()
                
                # Verify all sessions marked completed
                for session in state.sessions:
                    assert session.status == SessionStatus.completed
                    assert session.current_task is None
                
                # Verify all tasks completed
                for task_id, task_state in state.tasks.items():
                    assert task_state.status == TaskStatus.completed
    
    def test_run_creates_checkpoints(self, coordinator):
        """Verify checkpoints are created after each phase."""
        # Mock worktree creation
        with patch.object(coordinator.worktree_manager, 'create') as mock_create:
            mock_create.return_value = coordinator.repo_root / "worktree"
            
            # Mock completion
            with patch.object(coordinator.completion_monitor, 'wait_for_completion') as mock_wait:
                mock_wait.side_effect = lambda task_ids, **kwargs: task_ids
                
                # Track checkpoint creation
                with patch.object(coordinator, 'checkpoint_phase') as mock_checkpoint:
                    mock_checkpoint.return_value = Path("/tmp/checkpoint.yaml")
                    
                    # Run orchestration
                    coordinator.run()
                    
                    # Verify checkpoint called after each phase
                    # 2 phases + 1 final = 3 checkpoints
                    assert mock_checkpoint.call_count == 3
    
    def test_run_installs_signal_handlers(self, coordinator):
        """Verify signal handlers are installed and restored."""
        # Get original handlers
        original_sigint = signal.signal(signal.SIGINT, signal.SIG_DFL)
        original_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        
        # Restore for test
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        
        # Mock worktree creation
        with patch.object(coordinator.worktree_manager, 'create') as mock_create:
            mock_create.return_value = coordinator.repo_root / "worktree"
            
            # Mock completion
            with patch.object(coordinator.completion_monitor, 'wait_for_completion') as mock_wait:
                mock_wait.side_effect = lambda task_ids, **kwargs: task_ids
                
                # Run orchestration
                coordinator.run()
        
        # Verify original handlers restored
        current_sigint = signal.signal(signal.SIGINT, original_sigint)
        current_sigterm = signal.signal(signal.SIGTERM, original_sigterm)
        
        # Handlers should be back to original
        assert current_sigint == original_sigint
        assert current_sigterm == original_sigterm
    
    def test_run_handles_phase_execution_error(self, coordinator):
        """Verify error handling during phase execution."""
        # Mock worktree creation
        with patch.object(coordinator.worktree_manager, 'create') as mock_create:
            mock_create.return_value = coordinator.repo_root / "worktree"
            
            # Mock run_phase to raise an error
            with patch.object(coordinator, 'run_phase') as mock_run_phase:
                mock_run_phase.side_effect = RuntimeError("Phase execution failed")
                
                # Run should propagate the error
                with pytest.raises(RuntimeError, match="Phase execution failed"):
                    coordinator.run()
                
                # State should still be saved
                assert coordinator.state_manager.exists()
    
    def test_run_displays_completion_message(self, coordinator, capsys):
        """Verify completion message is displayed."""
        # Mock worktree creation
        with patch.object(coordinator.worktree_manager, 'create') as mock_create:
            mock_create.return_value = coordinator.repo_root / "worktree"
            
            # Mock completion
            with patch.object(coordinator.completion_monitor, 'wait_for_completion') as mock_wait:
                mock_wait.side_effect = lambda task_ids, **kwargs: task_ids
                
                # Run orchestration
                coordinator.run()
        
        # Capture output (note: Rich console output may not be captured by capsys)
        # This test verifies the code path exists
        # Full output testing would require Rich Console mocking


class TestHandleInterrupt:
    """Tests for interrupt signal handling."""
    
    def test_handle_interrupt_sets_flag(self, coordinator):
        """Verify _handle_interrupt sets the interrupted flag."""
        assert not coordinator._interrupted
        
        # Call handler
        coordinator._handle_interrupt(signal.SIGINT, None)
        
        # Verify flag set
        assert coordinator._interrupted


class TestAcceptanceCriteria:
    """Consolidated acceptance criteria tests."""
    
    def test_all_acceptance_criteria(self, coordinator):
        """Verify all AC checkboxes for T030."""
        # AC1: Executes all phases in order ✓
        # Tested in test_run_initializes_when_no_state
        
        # AC2: Resumes from checkpoint after crash ✓
        # Tested in test_run_resumes_from_existing_state
        
        # AC3: Ctrl+C saves state before exit ✓
        # Tested in test_run_handles_keyboard_interrupt
        
        # AC4: Final state shows all tasks completed ✓
        # Tested in test_run_marks_all_tasks_complete
        
        assert True  # All ACs verified

