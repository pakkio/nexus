# tests/test_main.py

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
import importlib

# Helper to import main.py dynamically
@pytest.fixture
def main_module():
    """Import the main module for testing."""
    # Store original sys.argv
    original_argv = sys.argv.copy()

    try:
        # Get the root directory of the project
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_path = os.path.join(root_dir, "main.py")

        if not os.path.exists(main_path):
            pytest.skip(f"main.py not found at {main_path}")

        # Add root dir to sys.path if not already there
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

        # Clear command line args for clean import
        sys.argv = ['main.py']

        # Use importlib to load the module
        spec = importlib.util.spec_from_file_location("main", main_path)
        main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main)

        yield main
    finally:
        # Restore original argv
        sys.argv = original_argv

@pytest.fixture
def mock_db_manager():
    """Mock the DbManager class."""
    with patch('main.DbManager') as MockDbManager:
        db_instance = MagicMock()
        MockDbManager.return_value = db_instance

        # Set up common mock behaviors
        db_instance.get_storyboard.return_value = {"description": "Test story"}

        yield MockDbManager, db_instance

@pytest.fixture
def mock_run_interaction_loop():
    """Mock the run_interaction_loop function."""
    with patch('main.run_interaction_loop') as mock_run:
        yield mock_run

def test_main_initialization(main_module, mock_db_manager, mock_run_interaction_loop):
    """Test initializing the main application with command line arguments."""
    MockDbManager, db_instance = mock_db_manager

    # Set up command line arguments
    test_args = [
        'main.py',
        '--mockup',
        '--mockup-dir', 'test_db',
        '--area', 'Test Area',
        '--npc', 'Test NPC',
        '--model', 'test-model',
        '--profile-analysis-model', 'profile-model',
        '--player', 'test_player'
    ]

    with patch('sys.argv', test_args):
        with patch('sys.exit'):  # Prevent actual exit
            # Call the main function
            main_module.main()

            # Verify DbManager was initialized correctly
            MockDbManager.assert_called_once_with(use_mockup=True, mockup_dir='test_db')

            # Verify run_interaction_loop was called with right parameters
            mock_run_interaction_loop.assert_called_once()
            args = mock_run_interaction_loop.call_args[1]
            assert args['db'] == db_instance
            assert args['initial_area'] == 'Test Area'
            assert args['initial_npc_name'] == 'Test NPC'
            assert args['model_name'] == 'test-model'
            assert args['profile_analysis_model_name'] == 'profile-model'
            assert args['player_id'] == 'test_player'

def test_main_with_no_area_but_npc(main_module, mock_db_manager, mock_run_interaction_loop):
    """Test that NPC is ignored if no area is specified."""
    MockDbManager, db_instance = mock_db_manager

    # Set up command line arguments with NPC but no area
    test_args = [
        'main.py',
        '--mockup',
        '--npc', 'Test NPC',  # NPC without area should be ignored
        '--model', 'test-model',
        '--player', 'test_player'
    ]

    with patch('sys.argv', test_args):
        with patch('sys.exit'):
            # Call the main function
            main_module.main()

            # Verify run_interaction_loop was called with NPC as None
            args = mock_run_interaction_loop.call_args[1]
            assert args['initial_area'] is None
            assert args['initial_npc_name'] is None

def test_main_with_db_connection_error(main_module, mock_db_manager, mock_run_interaction_loop):
    """Test handling of database connection errors."""
    MockDbManager, db_instance = mock_db_manager

    # Make connect throw an exception
    db_instance.connect.side_effect = Exception("Connection failed")

    # Set up minimal command line arguments
    test_args = ['main.py', '--mockup']

    with patch('sys.argv', test_args):
        with patch('sys.exit') as mock_exit:
            # Call the main function
            main_module.main()

            # Verify it continues despite connection warning
            mock_run_interaction_loop.assert_called_once()
            mock_exit.assert_not_called()

def test_main_with_critical_error(main_module, mock_db_manager):
    """Test handling of critical errors during execution."""
    MockDbManager, db_instance = mock_db_manager

    # Make run_interaction_loop throw an exception
    with patch('main.run_interaction_loop') as mock_run:
        mock_run.side_effect = Exception("Critical error")

        # Set up minimal command line arguments
        test_args = ['main.py', '--mockup']

        with patch('sys.argv', test_args):
            with patch('sys.exit') as mock_exit:
                # Call the main function
                main_module.main()

                # Verify it exits with error code 1
                mock_exit.assert_called_once_with(1)

def test_default_profile_model_fallback(main_module, mock_db_manager, mock_run_interaction_loop):
    """Test that profile analysis model falls back to dialogue model if not specified."""
    MockDbManager, db_instance = mock_db_manager

    # Set up command line arguments without profile model
    test_args = [
        'main.py',
        '--mockup',
        '--model', 'dialogue-model',  # Only specify dialogue model
        '--player', 'test_player'
    ]

    with patch('sys.argv', test_args):
        with patch('sys.exit'):
            # Call the main function
            main_module.main()

            # Verify profile_analysis_model_name defaults to model_name
            args = mock_run_interaction_loop.call_args[1]
            assert args['model_name'] == 'dialogue-model'
            assert args['profile_analysis_model_name'] == 'dialogue-model'
