# Path: db_manager.py
# Updated for Case-Insensitive Inventory & Credits System

from dotenv import load_dotenv
import mysql.connector
import os
import sys
import json
from typing import List, Dict, Optional, Any, Set, Tuple
from datetime import datetime
import traceback

try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    print("Warning (db_manager): terminal_formatter not found.")
    class TerminalFormatter:
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; BRIGHT_YELLOW=""; BRIGHT_GREEN = ""; BRIGHT_CYAN = "";
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))

class DbManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None, use_mockup: bool = False, mockup_dir: str = "database"):
        self.use_mockup = use_mockup
        self.mockup_dir = mockup_dir
        self.inventory_file_path_template = os.path.join(self.mockup_dir, "{player_id}_inventory.json")
        self.conversation_dir_template = os.path.join(self.mockup_dir, "ConversationHistory", "{player_id}")
        self.player_state_file_template = os.path.join(self.mockup_dir, "PlayerState", "{player_id}.json")
        self.player_profile_file_template = os.path.join(self.mockup_dir, "PlayerProfiles", "{player_id}.json")

        if config: self.db_config = config
        else:
            load_dotenv() # Ensure .env is loaded if not already
            self.db_config = {
                'host': os.environ.get('DB_HOST'), 'user': os.environ.get('DB_USER'),
                'password': os.environ.get('DB_PASSWORD'), 'database': os.environ.get('DB_NAME'),
                'port': int(os.environ.get('DB_PORT', 3306)),
                'connection_timeout': int(os.environ.get('DB_TIMEOUT', 10))
            }
        if self.use_mockup:
            os.makedirs(self.mockup_dir, exist_ok=True)
            for subdir_tmpl in [self.conversation_dir_template, self.player_state_file_template, self.player_profile_file_template]:
                # Ensure base directory of the template exists
                # e.g., for "ConversationHistory/{player_id}", ensure "ConversationHistory" exists
                # For "PlayerState/{player_id}.json", ensure "PlayerState" exists
                base_dir_path = os.path.dirname(subdir_tmpl.format(player_id="dummy").rstrip(os.sep))
                if base_dir_path: # Ensure it's not empty (e.g. if template is just "{player_id}_file.json")
                    os.makedirs(base_dir_path, exist_ok=True)
            for static_dir in ["NPCs", "Storyboards"]:
                os.makedirs(os.path.join(self.mockup_dir, static_dir), exist_ok=True)
            # print(f"DbManager: Mockup filesystem checked/initialized in '{self.mockup_dir}'")
        elif self.db_config and self.db_config.get('host'):
             pass # print(f"DbManager: Configured for Real Database.")
        # else:
             # print("DbManager: No DB host configured and not in mockup mode. DB operations might fail if attempted.")


    def connect(self) -> Any:
        if self.use_mockup: return MockConnection(self.mockup_dir)
        else:
            if not self.db_config or not all([self.db_config.get('host'), self.db_config.get('user'), self.db_config.get('database')]):
                # print(f"{TerminalFormatter.RED}DBManager: Database configuration incomplete. Cannot connect to real DB.{TerminalFormatter.RESET}")
                raise ValueError("Database configuration incomplete for real DB connection.")
            try:
                # Ensure mysql.connector is imported if not already
                if 'mysql.connector' not in sys.modules: import mysql.connector
                return mysql.connector.connect(**self.db_config)
            except mysql.connector.Error as err: # More specific error
                # print(f"{TerminalFormatter.RED}DBManager: Database connection error: {err}{TerminalFormatter.RESET}")
                raise # Re-raise the error to be caught by the caller
            except Exception as e: # Catch other potential errors
                # print(f"{TerminalFormatter.RED}DBManager: Unexpected error during DB connection: {e}{TerminalFormatter.RESET}")
                raise


    # --- NPC / Storyboard Methods ---
    def get_storyboard(self) -> Dict[str, Any]:
        default_story = {"name": "Default Story", "description": "[No storyboard data found or loaded]"}
        if self.use_mockup:
            s_dir = os.path.join(self.mockup_dir, "Storyboards")
            try:
                if os.path.exists(s_dir):
                    files = [f for f in os.listdir(s_dir) if f.endswith('.json')]
                    files.sort() # Pick consistently if multiple exist
                    if files:
                        with open(os.path.join(s_dir, files[0]), 'r', encoding='utf-8') as f:
                            return json.load(f)
            except Exception as e:
                # print(f"{TerminalFormatter.YELLOW}Warning: Could not load mockup storyboard: {e}{TerminalFormatter.RESET}")
                pass
            return default_story
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT name, description FROM Storyboards ORDER BY id LIMIT 1")
                story_data = cursor.fetchone()
                return story_data if story_data else default_story
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error loading storyboard: {e}{TerminalFormatter.RESET}")
                return default_story
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()


    def get_npc(self, area: str, name: str) -> Optional[Dict[str, Any]]:
        if self.use_mockup:
            npc_dir_path = os.path.join(self.mockup_dir, "NPCs")
            if os.path.exists(npc_dir_path):
                for filename in os.listdir(npc_dir_path):
                    # Match based on filename convention (e.g., area.name.json or just code.json)
                    # This is a bit loose; ideally, the filename is the NPC code.
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(npc_dir_path, filename), 'r', encoding='utf-8') as f:
                                npc_data = json.load(f)
                            # Check area and name case-insensitively
                            if npc_data.get('area','').strip().lower() == area.strip().lower() and \
                               npc_data.get('name','').strip().lower() == name.strip().lower():
                                if 'code' not in npc_data or not npc_data['code']: # Ensure code field from filename if missing
                                     npc_data['code'] = filename.replace('.json','')
                                return npc_data
                        except Exception: pass # Ignore malformed JSON files
            return None
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                # Using parameterized query for security
                query = "SELECT * FROM NPCs WHERE LOWER(area) = LOWER(%s) AND LOWER(name) = LOWER(%s) LIMIT 1"
                cursor.execute(query, (area.strip(), name.strip()))
                return cursor.fetchone()
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error getting NPC '{name}' in '{area}': {e}{TerminalFormatter.RESET}")
                return None
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def get_default_npc(self, area: str) -> Optional[Dict[str, Any]]:
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs"); npcs_in_area = []
            if os.path.exists(npc_dir):
                for filename in os.listdir(npc_dir):
                    if filename.endswith('.json'):
                        try:
                            with open(os.path.join(npc_dir, filename), 'r', encoding='utf-8') as f: npc = json.load(f)
                            if npc.get('area', '').strip().lower() == area.strip().lower():
                                if 'code' not in npc or not npc['code']: npc['code'] = filename.replace('.json', '')
                                npcs_in_area.append(npc)
                        except: pass
            if npcs_in_area: return sorted(npcs_in_area, key=lambda x: x.get('name', '').lower())[0] # Pick first alphabetically
            return None
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                query = "SELECT * FROM NPCs WHERE LOWER(area) = LOWER(%s) ORDER BY name LIMIT 1"
                cursor.execute(query, (area.strip(),))
                return cursor.fetchone()
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error getting default NPC in '{area}': {e}{TerminalFormatter.RESET}")
                return None
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()


    def list_npcs_by_area(self) -> List[Dict[str, str]]:
        npcs_list = []
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs")
            if os.path.exists(npc_dir):
                for filename in os.listdir(npc_dir):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(npc_dir, filename), 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                npcs_list.append({
                                    "code": data.get("code", filename.replace(".json","")),
                                    "name": data.get("name","Unknown NPC"),
                                    "area": data.get("area","Unknown Area"),
                                    "role": data.get("role","Unknown Role")
                                })
                        except Exception: pass
            return sorted(npcs_list, key=lambda x: (x.get('area','').lower(), x.get('name','').lower()))
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT code, name, area, role FROM NPCs ORDER BY area, name")
                return cursor.fetchall()
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error listing NPCs: {e}{TerminalFormatter.RESET}")
                return []
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()


    # --- Conversation History ---
    def save_conversation(self, player_id: str, npc_code: str, conversation_history: List[Dict[str, str]]) -> None:
        # conversation_history should NOT include system prompt if saving to DB
        # (as system prompt is dynamically generated on load)
        if not conversation_history or not player_id or not npc_code: return

        if self.use_mockup:
            p_dir = self.conversation_dir_template.format(player_id=player_id); os.makedirs(p_dir, exist_ok=True)
            file_path = os.path.join(p_dir, f"{npc_code}.json")
            try:
                with open(file_path, 'w', encoding='utf-8') as f: json.dump(conversation_history, f, indent=2, ensure_ascii=False)
            except Exception as e: print(f"Error saving mockup conversation {file_path}: {e}")
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                history_json = json.dumps(conversation_history)
                # Upsert logic: Insert or Update if exists
                sql = """
                    INSERT INTO ConversationHistory (player_id, npc_code, history, last_updated)
                    VALUES (%s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE history = VALUES(history), last_updated = NOW();
                """
                cursor.execute(sql, (player_id, npc_code, history_json))
                conn.commit()
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error saving conversation P:{player_id},NPC:{npc_code}: {e}{TerminalFormatter.RESET}")
                if conn: conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()


    def load_conversation(self, player_id: str, npc_code: str) -> List[Dict[str, str]]:
        if not player_id or not npc_code: return []
        if self.use_mockup:
            file_path = os.path.join(self.conversation_dir_template.format(player_id=player_id), f"{npc_code}.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
                except Exception: return [] # Return empty list on error (e.g. malformed JSON)
            return [] # File not found
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                cursor.execute("SELECT history FROM ConversationHistory WHERE player_id = %s AND npc_code = %s", (player_id, npc_code))
                result = cursor.fetchone()
                return json.loads(result[0]) if result and result[0] else []
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error loading conversation P:{player_id},NPC:{npc_code}: {e}{TerminalFormatter.RESET}")
                return []
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    # --- Inventory Management (Player Specific - UPDATED for Case-Insensitivity) ---
    def _clean_item_name(self, item_name: str) -> str:
        """Helper to standardize item names (lowercase, stripped)."""
        return str(item_name).strip().lower()

    def load_inventory(self, player_id: str) -> List[str]:
        """Loads player inventory. Items are assumed to be stored in lowercase."""
        if not player_id: return []
        inventory_list_cleaned: List[str] = []
        if self.use_mockup:
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            try:
                if not os.path.exists(inv_file):
                    with open(inv_file, 'w', encoding='utf-8') as f: json.dump([], f)
                    return []
                with open(inv_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Ensure it's a list and items are clean (should be if save_inventory is used)
                    if isinstance(loaded_data, list):
                        inventory_list_cleaned = sorted(list(set(self._clean_item_name(item) for item in loaded_data if item and str(item).strip())))
            except Exception as e:
                # print(f"{TerminalFormatter.YELLOW}Warning: Error loading mockup inventory {inv_file}: {e}. Returning empty list.{TerminalFormatter.RESET}")
                inventory_list_cleaned = []
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                cursor.execute("SELECT item_name FROM PlayerInventory WHERE player_id = %s ORDER BY item_name", (player_id,))
                # Assumes items in DB are already stored consistently (e.g., lowercase)
                inventory_list_cleaned = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error loading inventory for {player_id}: {e}{TerminalFormatter.RESET}")
                pass # inventory_list_cleaned remains empty
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        return inventory_list_cleaned # Already sorted and unique if from mockup save or DB query

    def save_inventory(self, player_id: str, inventory_list: List[str]) -> None:
        """Saves player inventory. Ensures items are unique, lowercase, and sorted."""
        if not player_id: return
        cleaned_inventory = sorted(list(set(self._clean_item_name(item) for item in inventory_list if item and str(item).strip())))

        if self.use_mockup:
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            os.makedirs(os.path.dirname(inv_file), exist_ok=True) # Ensure dir exists
            try:
                with open(inv_file, 'w', encoding='utf-8') as f: json.dump(cleaned_inventory, f, ensure_ascii=False, indent=2)
            except Exception as e: print(f"{TerminalFormatter.YELLOW}Warning: Error saving mockup inventory to {inv_file}: {e}{TerminalFormatter.RESET}")
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(); conn.start_transaction()
                cursor.execute("DELETE FROM PlayerInventory WHERE player_id = %s", (player_id,))
                if cleaned_inventory:
                    sql = "INSERT INTO PlayerInventory (player_id, item_name) VALUES (%s, %s)"
                    values = [(player_id, item) for item in cleaned_inventory]
                    cursor.executemany(sql, values)
                conn.commit()
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error saving inventory for {player_id}: {e}{TerminalFormatter.RESET}")
                if conn: conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def add_item_to_inventory(self, player_id: str, item_name: str, game_state: Optional[Dict[str, Any]] = None) -> bool:
        TF = TerminalFormatter; # Default TF
        if game_state and 'TerminalFormatter' in game_state: TF = game_state['TerminalFormatter']

        cleaned_item_name = self._clean_item_name(item_name)
        if not cleaned_item_name: print(f"{TF.RED}Error: Item name cannot be empty.{TF.RESET}"); return False
        if not player_id: print(f"{TF.RED}Error: Player ID required.{TF.RESET}"); return False

        current_inventory = self.load_inventory(player_id) # Loads cleaned items
        if cleaned_item_name not in current_inventory:
            current_inventory.append(cleaned_item_name)
            self.save_inventory(player_id, current_inventory)
            print(f"{TF.BRIGHT_GREEN}[Game System]: '{item_name.strip()}' added to your inventory! (as '{cleaned_item_name}'){TF.RESET}")
            if game_state and 'player_inventory' in game_state: # Update live game state if provided
                game_state['player_inventory'] = self.load_inventory(player_id) # Reload to ensure consistency
            return True
        else:
            # print(f"{TF.DIM}'{item_name.strip()}' (as '{cleaned_item_name}') is already in your inventory.{TF.RESET}")
            return False # Technically successful if already present, but return False for "no change made"

    def check_item_in_inventory(self, player_id: str, item_name: str) -> bool:
        cleaned_item_name = self._clean_item_name(item_name)
        if not cleaned_item_name or not player_id: return False
        inventory = self.load_inventory(player_id) # load_inventory returns cleaned list
        return cleaned_item_name in inventory

    def remove_item_from_inventory(self, player_id: str, item_name: str, game_state: Optional[Dict[str, Any]] = None) -> bool:
        TF = TerminalFormatter
        if game_state and 'TerminalFormatter' in game_state: TF = game_state['TerminalFormatter']

        cleaned_item_name = self._clean_item_name(item_name)
        if not cleaned_item_name: print(f"{TF.RED}Error: Item name for removal cannot be empty.{TF.RESET}"); return False
        if not player_id: print(f"{TF.RED}Error: Player ID required for item removal.{TF.RESET}"); return False

        current_inventory = self.load_inventory(player_id)
        if cleaned_item_name in current_inventory:
            current_inventory.remove(cleaned_item_name)
            self.save_inventory(player_id, current_inventory)
            # Message about removal is usually handled by the command processor.
            if game_state and 'player_inventory' in game_state: # Update live game state
                game_state['player_inventory'] = current_inventory # Use the modified list directly
            return True
        # print(f"{TF.YELLOW}Item '{item_name.strip()}' (as '{cleaned_item_name}') not found in inventory for removal.{TF.RESET}")
        return False # Item not found

    # --- Player State & Credits Management ---
    def load_player_state(self, player_id: str) -> Dict[str, Any]:
        """Loads player state, defaulting credits to 220 for new players."""
        default_credits = 220
        default_state = {'current_area': None, 'current_npc_code': None, 'plot_flags': {}, 'credits': default_credits}
        if not player_id: return default_state.copy() # Return a copy for safety

        loaded_state_data = None
        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f: loaded_raw = json.load(f)
                    # Validate and structure the loaded data
                    loaded_state_data = {
                        'current_area': loaded_raw.get('current_area'),
                        'current_npc_code': loaded_raw.get('current_npc_code'),
                        'plot_flags': loaded_raw.get('plot_flags', {}),
                        'credits': int(loaded_raw.get('credits', default_credits))
                    }
                except Exception as e:
                    # print(f"{TerminalFormatter.YELLOW}Warning: Error loading state file {state_file}: {e}. Using defaults.{TerminalFormatter.RESET}")
                    pass # loaded_state_data remains None
            if not loaded_state_data: # File not found or error, create and save default
                self.save_player_state(player_id, default_state)
                return default_state.copy()
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT current_area, current_npc_code, plot_flags, credits FROM PlayerState WHERE player_id = %s", (player_id,))
                result = cursor.fetchone()
                if result:
                    plot_flags_json = result.get('plot_flags', '{}')
                    loaded_state_data = {
                        'current_area': result.get('current_area'),
                        'current_npc_code': result.get('current_npc_code'),
                        'plot_flags': json.loads(plot_flags_json) if isinstance(plot_flags_json, str) else (plot_flags_json or {}),
                        'credits': int(result.get('credits', default_credits))
                    }
                else: # New player for DB
                    self.save_player_state(player_id, default_state) # Insert new row with defaults
                    return default_state.copy()
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error loading state for P:{player_id}: {e}{TerminalFormatter.RESET}")
                # Fallback to default if DB error, but don't save it over potentially good DB data
                return default_state.copy()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

        return loaded_state_data if loaded_state_data else default_state.copy()


    def save_player_state(self, player_id: str, state_data: Dict[str, Any]) -> None:
        if not player_id or not state_data: return

        # Extract relevant parts from the potentially larger game_session_state
        current_npc_val = state_data.get('current_npc')
        npc_code_to_save = current_npc_val.get('code') if isinstance(current_npc_val, dict) else state_data.get('current_npc_code')

        # Ensure credits are correctly sourced and an int
        credits_to_save = state_data.get('player_credits_cache', state_data.get('credits', 0))

        data_to_persist = {
            'current_area': state_data.get('current_area'),
            'current_npc_code': npc_code_to_save,
            'plot_flags': state_data.get('plot_flags', {}),
            'credits': int(credits_to_save)
        }
        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            try:
                with open(state_file, 'w', encoding='utf-8') as f: json.dump(data_to_persist, f, indent=2, ensure_ascii=False)
            except Exception as e: print(f"{TerminalFormatter.YELLOW}Warning: Error saving state to {state_file}: {e}{TerminalFormatter.RESET}")
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                sql = """
                    INSERT INTO PlayerState (player_id, current_area, current_npc_code, plot_flags, credits, last_seen)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                    current_area = VALUES(current_area), current_npc_code = VALUES(current_npc_code),
                    plot_flags = VALUES(plot_flags), credits = VALUES(credits), last_seen = NOW();
                """
                plot_flags_json = json.dumps(data_to_persist['plot_flags'])
                values = (player_id, data_to_persist['current_area'], data_to_persist['current_npc_code'], plot_flags_json, data_to_persist['credits'])
                cursor.execute(sql, values); conn.commit()
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error saving state for P:{player_id}: {e}{TerminalFormatter.RESET}")
                if conn: conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def get_player_credits(self, player_id: str) -> int:
        """Retrieves current credits for a player, defaults if new."""
        player_state = self.load_player_state(player_id) # load_player_state handles defaulting
        return player_state.get('credits', 220) # Ensure default here too, just in case

    def update_player_credits(self, player_id: str, amount_change: int, game_state_context: Dict[str, Any]) -> bool:
        """Updates player credits by amount_change. Returns True on success."""
        TF = game_state_context.get('TerminalFormatter', TerminalFormatter)
        current_credits = self.get_player_credits(player_id) # Get latest from storage
        new_credits = current_credits + amount_change

        if new_credits < 0:
            # Message handled by command_processor or caller based on this False return
            # print(f"{TF.RED}[Game System]: Insufficient credits. You only have {current_credits} Credits.{TF.RESET}")
            return False

        player_state = self.load_player_state(player_id) # Load full state to update
        player_state['credits'] = new_credits

        self.save_player_state(player_id, player_state) # Save the updated state

        # Update live game_session_state cache if provided
        if 'player_credits_cache' in game_state_context:
            game_state_context['player_credits_cache'] = new_credits

        # Caller (e.g. command_processor or main_core) handles printing messages about credits change
        return True

    # --- DB Schema (Simplified check) ---
    def ensure_db_schema(self):
        if self.use_mockup: return # No schema for mockup files
        # print(f"{TerminalFormatter.DIM}Checking database schema...{TerminalFormatter.RESET}")
        try:
            # Test connection first
            conn_test = self.connect()
            conn_test.close()

            # This is a very basic check. A real migration system is better.
            self._ensure_table_exists(
                table_name="PlayerState",
                create_sql="""
                    CREATE TABLE IF NOT EXISTS PlayerState (
                        player_id VARCHAR(255) NOT NULL PRIMARY KEY,
                        current_area VARCHAR(255) NULL,
                        current_npc_code VARCHAR(255) NULL,
                        plot_flags JSON NULL,
                        credits INT NOT NULL DEFAULT 220,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """,
                check_column='credits' # Check if 'credits' column exists
            )
            self._ensure_table_exists(
                table_name="PlayerInventory",
                create_sql="""
                    CREATE TABLE IF NOT EXISTS PlayerInventory (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        player_id VARCHAR(255) NOT NULL,
                        item_name VARCHAR(255) NOT NULL,
                        FOREIGN KEY (player_id) REFERENCES PlayerState(player_id) ON DELETE CASCADE,
                        UNIQUE KEY (player_id, item_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
            )
            self._ensure_table_exists(
                table_name="ConversationHistory",
                create_sql="""
                    CREATE TABLE IF NOT EXISTS ConversationHistory (
                        player_id VARCHAR(255) NOT NULL,
                        npc_code VARCHAR(255) NOT NULL,
                        history JSON NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (player_id, npc_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
            )
            # print(f"{TerminalFormatter.DIM}DB schema check complete.{TerminalFormatter.RESET}")
        except Exception as e:
            print(f"{TerminalFormatter.RED}Database schema check/ensure failed: {e}{TerminalFormatter.RESET}")
            print(f"{TerminalFormatter.YELLOW}Ensure DB is configured and accessible, or run in --mockup mode.{TerminalFormatter.RESET}")
            # Depending on severity, might want to sys.exit(1) if DB is critical and fails here.


    def _ensure_table_exists(self, table_name: str, create_sql: str, check_column: Optional[str] = None):
        if self.use_mockup: return
        if not self.db_config or not self.db_config.get('database'): return # Cannot check without DB name
        conn = None; cursor = None
        try:
            conn = self.connect(); cursor = conn.cursor();
            cursor.execute("SHOW TABLES LIKE %s;", (table_name,))
            if not cursor.fetchone(): # Table does not exist
                # print(f"{TerminalFormatter.DIM}Table '{table_name}' not found. Creating...{TerminalFormatter.RESET}")
                # Execute each statement in create_sql if it's multi-statement
                for statement in create_sql.split(';'):
                    if statement.strip(): cursor.execute(statement)
                conn.commit()
                # print(f"{TerminalFormatter.GREEN}Table '{table_name}' created.{TerminalFormatter.RESET}")
            elif check_column: # Table exists, check if specified column exists
                cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
                               (self.db_config['database'], table_name, check_column))
                if cursor.fetchone()[0] == 0:
                    # This is where a more robust migration would ALTER TABLE.
                    # For now, just a warning.
                    print(f"{TerminalFormatter.YELLOW}⚠️ Warning: Table '{table_name}' exists but crucial column '{check_column}' is MISSING.{TerminalFormatter.RESET}")
                    print(f"{TerminalFormatter.YELLOW}   Manual schema update might be needed if this is an existing database.{TerminalFormatter.RESET}")
        except Exception as e:
            # print(f"{TerminalFormatter.RED}DB error ensuring table '{table_name}': {e}{TerminalFormatter.RESET}")
            pass # Suppress error during auto-check, will fail later if critical
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()


class MockConnection:
    def __init__(self, mockup_dir): self.mockup_dir = mockup_dir; self._is_connected = True
    def cursor(self, dictionary=False): return MockCursor(self.mockup_dir, dictionary)
    def commit(self): pass
    def rollback(self): pass
    def close(self): self._is_connected = False
    def is_connected(self): return self._is_connected
    def start_transaction(self, **kwargs): pass # For compatibility if called

class MockCursor:
    def __init__(self, mockup_dir, dictionary=False):
        self.mockup_dir = mockup_dir
        self.dictionary = dictionary
        self.lastrowid = None # For INSERT operations
        self._results: List[Any] = [] # Store results of a "fetch"
        self._description: Optional[Tuple[Any, ...]] = None # Mimic cursor.description
    def execute(self, query, params=None, multi=False): self._results = [] # Reset results
    def executemany(self, query, params_list=None): self._results = [] # Reset results
    def fetchone(self): return self._results.pop(0) if self._results else None
    def fetchall(self): results = self._results; self._results = []; return results
    def close(self): pass
    @property
    def description(self): return self._description
    @property
    def rowcount(self): return 0 # Simplification

if __name__ == "__main__":
    # Basic tests for new/updated methods
    class TF: RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_YELLOW=""; BRIGHT_GREEN = ""; BRIGHT_CYAN = "";
    TerminalFormatter = TF # Assign to global for db_manager to pick up if imported directly

    print("--- DbManager Self-Tests ---")
    test_dir = "_db_manager_selftest"
    if os.path.exists(test_dir): import shutil; shutil.rmtree(test_dir) # Clean start
    os.makedirs(os.path.join(test_dir, "PlayerState"), exist_ok=True)
    os.makedirs(os.path.join(test_dir, "NPCs"), exist_ok=True)
    os.makedirs(os.path.join(test_dir, "Storyboards"), exist_ok=True)


    db = DbManager(use_mockup=True, mockup_dir=test_dir)
    p_id = "TestPlayer123"
    game_state_sim = {'TerminalFormatter': TF, 'player_credits_cache': 0, 'player_inventory': []}

    # Test Player State & Credits
    print(f"Initial credits for {p_id}: {db.get_player_credits(p_id)}")
    assert db.get_player_credits(p_id) == 220, "Default credits should be 220"

    db.update_player_credits(p_id, 50, game_state_sim)
    print(f"Credits after +50: {db.get_player_credits(p_id)}")
    assert db.get_player_credits(p_id) == 270
    assert game_state_sim['player_credits_cache'] == 270

    db.update_player_credits(p_id, -70, game_state_sim)
    print(f"Credits after -70: {db.get_player_credits(p_id)}")
    assert db.get_player_credits(p_id) == 200

    print(f"Trying to spend 300 (should fail): {db.update_player_credits(p_id, -300, game_state_sim)}")
    assert db.get_player_credits(p_id) == 200 # Should not change

    # Test Inventory
    print("Testing Inventory (case-insensitive):")
    db.add_item_to_inventory(p_id, "Test Item Alpha ", game_state_sim)
    db.add_item_to_inventory(p_id, "test item alpha", game_state_sim) # Should be treated as same
    db.add_item_to_inventory(p_id, "Beta Dust", game_state_sim)

    current_inv = db.load_inventory(p_id)
    print(f"Inventory: {current_inv}")
    assert len(current_inv) == 2, f"Expected 2 items, got {len(current_inv)}"
    assert "test item alpha" in current_inv
    assert "beta dust" in current_inv
    assert game_state_sim['player_inventory'] == current_inv

    assert db.check_item_in_inventory(p_id, " TeSt ItEm AlPhA  ") == True
    assert db.check_item_in_inventory(p_id, "gamma gunk") == False

    db.remove_item_from_inventory(p_id, "tEsT iTeM ALPHA", game_state_sim)
    current_inv_after_remove = db.load_inventory(p_id)
    print(f"Inventory after removing alpha: {current_inv_after_remove}")
    assert len(current_inv_after_remove) == 1
    assert "test item alpha" not in current_inv_after_remove
    assert "beta dust" in current_inv_after_remove
    assert game_state_sim['player_inventory'] == current_inv_after_remove

    # Clean up test directory
    if os.path.exists(test_dir): import shutil; shutil.rmtree(test_dir)
    print("--- DbManager Self-Tests Done ---")
