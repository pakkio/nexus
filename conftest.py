# conftest.py
import pytest
from unittest.mock import Mock, MagicMock

@pytest.fixture
def mock_terminal_formatter():
    class MockTF:
        RED = YELLOW = GREEN = RESET = BOLD = DIM = ""
        MAGENTA = CYAN = BRIGHT_CYAN = BG_BLUE = ""
        BRIGHT_WHITE = BG_GREEN = BLACK = ""
        BRIGHT_MAGENTA = BRIGHT_GREEN = BRIGHT_YELLOW = ITALIC = ""

        @staticmethod
        def supports_ansi():
            return True

        @staticmethod
        def format_terminal_text(text, width=80):
            return text

        @staticmethod
        def get_terminal_width():
            return 80
    return MockTF
