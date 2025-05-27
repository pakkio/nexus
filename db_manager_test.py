# tests/test_db_manager.py
import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
from db_manager import DbManager, MockConnection, MockCursor

class TestDbManager:
    @pytest.fixture
    def mock_terminal_formatter(self):
        class MockTF:
            RED = YELLOW = GREEN = RESET = BOLD = DIM = ""
            MAGENTA = CYAN = BRIGHT_CYAN = BG_BLUE = ""
            BRIGHT_WHITE = BG_GREEN = BLACK = ""
            @staticmethod
            def format_terminal_text(text, width=80): return text
        return MockTF

    @pytest.fixture
    def temp_mockup_dir(self):
        # Create a temporary directory for testing
        temp_dir = tempfile.mkdtemp()

        # Create subdirectories for testing
        os.makedirs(os.path.join(temp_dir, "PlayerState"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "PlayerProfiles"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "PlayerInventory"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "NPCs"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "Storyboards"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "ConversationHistory"), exist_ok=True)

        yield temp_dir

        # Clean up after tests
        shutil.rmtree(temp_dir)

    def test_initialize_db_manager_mockup(self, temp_mockup_dir):
        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        # Check that it's using the right directory
        assert db.mockup_dir == temp_mockup_dir
        assert db.use_mockup is True

    def test_connect_mockup(self, temp_mockup_dir):
        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        # Test connect method creates a MockConnection
        connection = db.connect()
        assert isinstance(connection, MockConnection)
        assert connection.mockup_dir == temp_mockup_dir

    def test_get_storyboard_empty(self, temp_mockup_dir):
        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        # Test getting storyboard when none exists
        story = db.get_storyboard()
        assert story["name"] == "Default Story"
        assert "[No storyboard data found or loaded]" in story["description"]

    def test_get_storyboard_with_data(self, temp_mockup_dir):
        # Create a test storyboard file
        storyboard_data = {
            "name": "Test Storyboard",
            "description": "This is a test storyboard."
        }
        storyboard_dir = os.path.join(temp_mockup_dir, "Storyboards")
        with open(os.path.join(storyboard_dir, "1.json"), "w") as f:
            json.dump(storyboard_data, f)

        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        # Test getting storyboard
        story = db.get_storyboard()
        assert story["name"] == "Test Storyboard"
        assert story["description"] == "This is a test storyboard."

    def test_get_npc(self, temp_mockup_dir):
        # Create a test NPC file
        npc_data = {
            "name": "Test NPC",
            "area": "Test Area",
            "role": "Test Role",
            "code": "test_npc"
        }
        npc_dir = os.path.join(temp_mockup_dir, "NPCs")
        with open(os.path.join(npc_dir, "test_npc.json"), "w") as f:
            json.dump(npc_data, f)

        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        # Test getting NPC
        npc = db.get_npc("Test Area", "Test NPC")
        assert npc["name"] == "Test NPC"
        assert npc["area"] == "Test Area"
        assert npc["role"] == "Test Role"
        assert npc["code"] == "test_npc"

        # Test getting non-existent NPC
        npc = db.get_npc("Test Area", "Non-existent NPC")
        assert npc is None

    def test_list_npcs_by_area(self, temp_mockup_dir):
        # Create test NPC files
        npc_dir = os.path.join(temp_mockup_dir, "NPCs")

        npc1 = {
            "name": "NPC 1",
            "area": "Area 1",
            "role": "Role 1",
            "code": "npc1"
        }
        with open(os.path.join(npc_dir, "npc1.json"), "w") as f:
            json.dump(npc1, f)

        npc2 = {
            "name": "NPC 2",
            "area": "Area 2",
            "role": "Role 2",
            "code": "npc2"
        }
        with open(os.path.join(npc_dir, "npc2.json"), "w") as f:
            json.dump(npc2, f)

        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        # Test listing NPCs
        npcs = db.list_npcs_by_area()

        # Verify NPCs are listed
        assert len(npcs) == 2
        # Verify they are sorted by area
        assert npcs[0]["name"] == "NPC 1"
        assert npcs[0]["area"] == "Area 1"
        assert npcs[1]["name"] == "NPC 2"
        assert npcs[1]["area"] == "Area 2"

    def test_player_state_crud(self, temp_mockup_dir):
        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        player_id = "test_player"

        # Test loading default state
        state = db.load_player_state(player_id)
        assert state["credits"] == 220  # Default value
        assert state["current_area"] is None

        # Test saving and loading state
        state["current_area"] = "Test Area"
        state["credits"] = 500
        db.save_player_state(player_id, state)

        loaded_state = db.load_player_state(player_id)
        assert loaded_state["current_area"] == "Test Area"
        assert loaded_state["credits"] == 500

        # Test getting player credits
        assert db.get_player_credits(player_id) == 500

        # Test updating player credits
        game_state = {"player_credits_cache": 500, "TerminalFormatter": Mock()}
        result = db.update_player_credits(player_id, 100, game_state)
        assert result is True
        assert game_state["player_credits_cache"] == 600
        assert db.get_player_credits(player_id) == 600

    def test_player_profile_crud(self, temp_mockup_dir):
        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        player_id = "test_player"

        # Test loading default profile
        profile = db.load_player_profile(player_id)
        assert "core_traits" in profile
        assert "decision_patterns" in profile
        assert profile["core_traits"]["curiosity"] == 5  # Default value

        # Test saving and loading profile with modifications
        profile["core_traits"]["curiosity"] = 8
        profile["key_experiences_tags"].append("test_experience")
        db.save_player_profile(player_id, profile)

        loaded_profile = db.load_player_profile(player_id)
        assert loaded_profile["core_traits"]["curiosity"] == 8
        assert "test_experience" in loaded_profile["key_experiences_tags"]

    def test_inventory_management(self, temp_mockup_dir):
        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        player_id = "test_player"

        # Test loading empty inventory
        inventory = db.load_inventory(player_id)
        assert inventory == []

        # Test adding item to inventory
        game_state = {"player_inventory": [], "TerminalFormatter": Mock()}
        result = db.add_item_to_inventory(player_id, "Test Item", game_state)
        assert result is True
        assert game_state["player_inventory"] == ["test item"]  # Note: lowercase after cleaning

        # Test loading inventory with item
        inventory = db.load_inventory(player_id)
        assert "test item" in inventory

        # Test removing item from inventory
        result = db.remove_item_from_inventory(player_id, "Test Item", game_state)
        assert result is True
        assert game_state["player_inventory"] == []

        # Test removing non-existent item
        result = db.remove_item_from_inventory(player_id, "Non-existent Item", game_state)
        assert result is False

    def test_conversation_management(self, temp_mockup_dir):
        # Initialize DbManager in mockup mode
        db = DbManager(use_mockup=True, mockup_dir=temp_mockup_dir)

        player_id = "test_player"
        npc_code = "test_npc"

        # Create test directory for conversations
        player_conv_dir = os.path.join(temp_mockup_dir, "ConversationHistory", player_id)
        os.makedirs(player_conv_dir, exist_ok=True)

        # Test loading empty conversation
        conversation = db.load_conversation(player_id, npc_code)
        assert conversation == []

        # Test saving and loading conversation
        test_conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        db.save_conversation(player_id, npc_code, test_conversation)

        loaded_conversation = db.load_conversation(player_id, npc_code)
        assert len(loaded_conversation) == 2
        assert loaded_conversation[0]["role"] == "user"
        assert loaded_conversation[0]["content"] == "Hello"
        assert loaded_conversation[1]["role"] == "assistant"
        assert loaded_conversation[1]["content"] == "Hi there"

    def test_mock_connection(self, temp_mockup_dir):
        # Test MockConnection methods
        conn = MockConnection(temp_mockup_dir)

        # Test is_connected
        assert conn.is_connected() is True

        # Test cursor creation
        cursor = conn.cursor()
        assert isinstance(cursor, MockCursor)

        # Test close
        conn.close()
        assert conn.is_connected() is False

        # Test other methods for coverage
        conn.commit()
        conn.rollback()
        conn.start_transaction()

    def test_mock_cursor(self, temp_mockup_dir):
        # Test MockCursor methods
        cursor = MockCursor(temp_mockup_dir)

        # Test execute
        cursor.execute("SELECT * FROM test")

        # Test executemany
        cursor.executemany("INSERT INTO test VALUES (%s)", [("value1",), ("value2",)])

        # Test fetchone and fetchall
        assert cursor.fetchone() is None
        assert cursor.fetchall() == []

        # Test properties
        assert cursor.rowcount == 0
        assert cursor.description is None

        # Test close
        cursor.close()
