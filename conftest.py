# conftest.py
import pytest
from unittest.mock import Mock, MagicMock
from terminal_formatter import MockTerminalFormatter as MockTF

@pytest.fixture
def mock_terminal_formatter():
    return MockTF
