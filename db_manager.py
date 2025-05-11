# Path: db_manager.py
# Updated Version - Includes player_id, Player State, Inventory remove, AND Original Methods

from dotenv import load_dotenv
import mysql.connector # Import for real DB
import os
import sys 
import json
from typing import List, Dict, Optional, Any, Set, Tuple 
from datetime import datetime
import traceback

# --- Terminal Formatter (Assume available or provide basic fallback) ---
try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    print("Warning (db_manager): terminal_formatter not found. Using basic fallback.")
    class TerminalFormatter: # Basic Fallback
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; BRIGHT_YELLOW=""
        BRIGHT_GREEN = ""; # Added for consistency with inventory messages
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))

class DbManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None, use_mockup: bool = False, mockup_dir: str = "database"):
        """Initializes the DbManager."""
        self.use_mockup = use_mockup
        self.mockup_dir = mockup_dir
        self.inventory_file_path_template = os.path.join(self.mockup_dir, "{player_id}_inventory.json")
        self.conversation_dir_template = os.path.join(self.mockup_dir, "ConversationHistory", "{player_id}")
        self.player_state_file_template = os.path.join(self.mockup_dir, "PlayerState", "{player_id}.json")
        # NEW: Player Profile file template
        self.player_profile_file_template = os.path.join(self.mockup_dir, "PlayerProfiles", "{player_id}.json")


        if config:
            self.db_config = config
        else:
            self.db_config = { 
                'host': os.environ.get('DB_HOST'), 'user': os.environ.get('DB_USER'),
                'password': os.environ.get('DB_PASSWORD'), 'database': os.environ.get('DB_NAME'),
                'port': int(os.environ.get('DB_PORT', 3306)),
                'connection_timeout': int(os.environ.get('DB_TIMEOUT', 10))
            }
            if not self.use_mockup and not all([self.db_config['host'], self.db_config['user'], self.db_config['database']]):
                print("DbManager Warning: Real database mode selected, but DB config is missing.")

        if self.use_mockup:
            if not os.path.exists(self.mockup_dir):
                try: os.makedirs(self.mockup_dir)
                except OSError as e: print(f"⚠️ Error creating base mockup directory {self.mockup_dir}: {e}")
            
            # Directories for player-specific data that should persist across loads
            player_specific_subdirs_templates = [
                self.conversation_dir_template, 
                self.player_state_file_template,
                self.player_profile_file_template # NEW
            ]
            for subdir_tmpl in player_specific_subdirs_templates:
                # Create the base directory (e.g., "ConversationHistory", "PlayerState") if it doesn't exist
                # The player_id specific subfolder will be created when data for that player is first saved.
                base_player_data_dir = os.path.dirname(subdir_tmpl.split("{player_id}")[0]) # e.g. database/ConversationHistory
                if not os.path.exists(base_player_data_dir):
                    try: os.makedirs(base_player_data_dir)
                    except OSError as e: print(f"⚠️ Error creating player data subdirectory {base_player_data_dir}: {e}")

            # Directories for static world data (managed by load.py)
            static_data_dirs = ["NPCs", "Storyboards"]
            for table_dir_name in static_data_dirs:
                table_dir_path = os.path.join(self.mockup_dir, table_dir_name)
                if not os.path.exists(table_dir_path):
                    try: os.makedirs(table_dir_path)
                    except OSError as e: print(f"⚠️ Error creating static data subdirectory {table_dir_path}: {e}")
            
            print(f"DbManager: Mockup filesystem initialized in '{self.mockup_dir}'")

        elif self.db_config and self.db_config.get('host'):
            print(f"DbManager: Configured for Real Database ({self.db_config.get('host')}:{self.db_config.get('port')}/{self.db_config.get('database')})")


    def connect(self) -> Any:
        """Connects to the database or returns a mock connection."""
        if self.use_mockup:
            return MockConnection(self.mockup_dir) # MockConnection doesn't actually connect
        else:
            # ... (existing real DB connection logic) ...
            if not self.db_config or not all([self.db_config['host'], self.db_config['user'], self.db_config['database']]):
                raise ValueError("Database configuration is incomplete.")
            try:
                if 'mysql' not in sys.modules: import mysql.connector
                return mysql.connector.connect(**self.db_config)
            except mysql.connector.Error as err: print(f"Database connection error: {err}"); raise
            except ImportError: print("ERROR: mysql.connector not installed."); raise

    # --- NPC / Storyboard Methods (Largely Unchanged) ---
    def get_storyboard(self) -> Dict[str, Any]:
        # ... (existing implementation) ...
        if self.use_mockup:
            storyboard_dir = os.path.join(self.mockup_dir, "Storyboards")
            try:
                storyboard_files = [f for f in os.listdir(storyboard_dir) if f.endswith('.json')]
                if storyboard_files:
                    storyboard_files.sort() 
                    file_path = os.path.join(storyboard_dir, storyboard_files[0])
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
                    except Exception as e: print(f"⚠️ Error reading/parsing storyboard {file_path}: {e}"); return {"description": "[Error - storyboard read error]"}
            except Exception as e: print(f"⚠️ Error accessing storyboard directory {storyboard_dir}: {e}")
            return {"description": "[No storyboard found or error occurred]"}
        else: # DB
            conn = None; cursor = None; row = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM Storyboards LIMIT 1"); row = cursor.fetchone()
            except Exception as e: print(f"⚠️ DB error fetching storyboard: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return row if row else {"description": "[No storyboard found in DB]"}


    def get_npc(self, area: str, name: str) -> Optional[Dict[str, Any]]:
        # ... (existing implementation) ...
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs")
            try:
                for filename in os.listdir(npc_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(npc_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f: npc = json.load(f)
                            if npc.get('area', '').lower() == area.lower() and npc.get('name', '').lower() == name.lower():
                                if 'code' not in npc: npc['code'] = filename.replace('.json', '') # Add code if missing
                                return npc
                        except Exception as e: print(f"⚠️ Error reading/parsing NPC file {file_path}: {e}")
            except Exception as e: print(f"⚠️ Error accessing NPC directory {npc_dir}: {e}")
            return None
        else: # DB
            conn = None; cursor = None; npc_data = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM NPCs WHERE LOWER(area) = LOWER(%s) AND LOWER(name) = LOWER(%s)", (area, name))
                npc_data = cursor.fetchone()
            except Exception as e: print(f"⚠️ DB error fetching NPC {name} in {area}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return npc_data

    def get_default_npc(self, area: str) -> Optional[Dict[str, Any]]:
        # ... (existing implementation, ensure it adds 'code' for mockup like get_npc) ...
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs")
            npcs_in_area = []
            try:
                for filename in os.listdir(npc_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(npc_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f: npc = json.load(f)
                            if npc.get('area', '').lower() == area.lower():
                                if 'code' not in npc: npc['code'] = filename.replace('.json', '')
                                npcs_in_area.append(npc)
                        except: pass 
            except: pass
            if npcs_in_area: return sorted(npcs_in_area, key=lambda x: x.get('name', '').lower())[0]
            return None
        else: # DB
            conn = None; cursor = None; npc_data = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM NPCs WHERE LOWER(area) = LOWER(%s) ORDER BY name LIMIT 1", (area,))
                npc_data = cursor.fetchone()
            except Exception as e: print(f"⚠️ DB error fetching default NPC for {area}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return npc_data


    def list_npcs_by_area(self) -> List[Dict[str, str]]:
        # ... (existing implementation, ensure it adds 'code' for mockup like get_npc) ...
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs")
            npcs = []
            try:
                for filename in os.listdir(npc_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(npc_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f: npc_data = json.load(f)
                            # Ensure 'code' is present, deriving from filename if necessary
                            npc_code = npc_data.get('code', filename.replace('.json', ''))
                            npcs.append({
                                "code": npc_code, 
                                "area": npc_data.get('area', 'Unknown'), 
                                "name": npc_data.get('name', 'Unknown'), 
                                "role": npc_data.get('role', 'Unknown')
                            })
                        except: pass 
            except: pass 
            return sorted(npcs, key=lambda x: (x["area"].lower(), x["name"].lower()))
        else: # DB
            conn = None; cursor = None; rows = []
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT code, area, name, role FROM NPCs ORDER BY area, name")
                rows = cursor.fetchall()
            except Exception as e: print(f"⚠️ DB error listing NPCs: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return rows


    # --- Conversation History (Player Specific - Modified for Summaries in a later step) ---
    # For now, assuming it saves full history. Summarization changes would go here.
    def save_conversation(self, player_id: str, npc_code: str, conversation_history: List[Dict[str, str]]) -> None:
        # ... (existing implementation for saving full history) ...
        # This will be modified significantly when summarization is implemented.
        # For now, it saves the full list of messages.
        if not conversation_history or not player_id or not npc_code: print("⚠️ Save convo skipped: missing info."); return
        if self.use_mockup:
            player_conv_dir = self.conversation_dir_template.format(player_id=player_id)
            os.makedirs(player_conv_dir, exist_ok=True)
            conv_file = os.path.join(player_conv_dir, f"{npc_code}.json")
            try:
                with open(conv_file, 'w', encoding='utf-8') as f: json.dump(conversation_history, f, ensure_ascii=False, indent=2)
            except Exception as e: print(f"⚠️ Error saving convo file {conv_file}: {e}")
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(); conn.start_transaction()
                cursor.execute("DELETE FROM ConversationHistory WHERE player_id = %s AND npc_code = %s", (player_id, npc_code))
                if conversation_history:
                    insert_query = "INSERT INTO ConversationHistory (player_id, npc_code, sequence, role, content) VALUES (%s, %s, %s, %s, %s)"
                    values = [(player_id, npc_code, i, msg.get('role', ''), msg.get('content', '')) for i, msg in enumerate(conversation_history)]
                    cursor.executemany(insert_query, values)
                conn.commit()
            except Exception as e: print(f"DB error saving convo for P:{player_id},N:{npc_code}: {e}"); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def load_conversation(self, player_id: str, npc_code: str) -> List[Dict[str, str]]: # Returns full history for now
        # ... (existing implementation for loading full history) ...
        # This will be modified for summarization. For now, returns list of messages.
        if not player_id or not npc_code: return []
        if self.use_mockup:
            conv_file = os.path.join(self.conversation_dir_template.format(player_id=player_id), f"{npc_code}.json")
            if os.path.exists(conv_file):
                try:
                    with open(conv_file, 'r', encoding='utf-8') as f: return json.load(f)
                except Exception as e: print(f"⚠️ Error loading/parsing convo file {conv_file}: {e}"); return []
            return []
        else: # DB
            conn = None; cursor = None; conversation = []
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT role, content FROM ConversationHistory WHERE player_id = %s AND npc_code = %s ORDER BY sequence", (player_id, npc_code))
                conversation = cursor.fetchall() # Returns list of dicts
            except Exception as e: print(f"DB error loading convo for P:{player_id},N:{npc_code}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return conversation if conversation else []


    # --- Inventory Management (Player Specific) ---
    def load_inventory(self, player_id: str) -> List[str]:
        # ... (existing implementation) ...
        if not player_id: return []
        if self.use_mockup:
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            try:
                if not os.path.exists(inv_file):
                    with open(inv_file, 'w', encoding='utf-8') as f: json.dump([], f); return []
                with open(inv_file, 'r', encoding='utf-8') as f: inventory = json.load(f)
                return sorted([str(item) for item in inventory]) if isinstance(inventory, list) else []
            except Exception as e: print(f"⚠️ Error loading mockup inv {inv_file}: {e}. Returning empty."); return []
        else: # DB
            inventory = []
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                cursor.execute("SELECT item_name FROM PlayerInventory WHERE player_id = %s ORDER BY item_name", (player_id,))
                inventory = [row[0] for row in cursor.fetchall()]
            except Exception as e: print(f"DB error loading inv for {player_id}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return inventory

    def save_inventory(self, player_id: str, inventory_list: List[str]) -> None:
        # ... (existing implementation) ...
        if not player_id: return
        # Ensure unique, string items, sorted for consistency
        unique_string_inventory = sorted(list(set(str(item).strip() for item in inventory_list if str(item).strip())))
        if self.use_mockup:
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            os.makedirs(os.path.dirname(inv_file), exist_ok=True) # Ensure player_id dir part exists
            try:
                with open(inv_file, 'w', encoding='utf-8') as f: json.dump(unique_string_inventory, f, ensure_ascii=False, indent=2)
            except Exception as e: print(f"⚠️ Error saving mockup inv to {inv_file}: {e}")
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(); conn.start_transaction()
                cursor.execute("DELETE FROM PlayerInventory WHERE player_id = %s", (player_id,))
                if unique_string_inventory:
                    sql = "INSERT INTO PlayerInventory (player_id, item_name) VALUES (%s, %s)"
                    values = [(player_id, item) for item in unique_string_inventory]
                    cursor.executemany(sql, values)
                conn.commit()
            except Exception as e: print(f"DB error saving inv for {player_id}: {e}"); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()


    def add_item_to_inventory(self, player_id: str, item_name: str, state: Optional[Dict[str, Any]] = None) -> bool:
        TF = TerminalFormatter
        if state and 'TerminalFormatter' in state: TF = state['TerminalFormatter']
        if not item_name or not isinstance(item_name, str) or not player_id:
            print(f"{TF.RED}Error: Invalid item or player ID for adding to inventory.{TF.RESET}"); return False
        
        item_name_cleaned = item_name.strip()
        if not item_name_cleaned: print(f"{TF.RED}Error: Item name cannot be empty.{TF.RESET}"); return False

        current_inventory = self.load_inventory(player_id)
        if item_name_cleaned not in current_inventory:
            current_inventory.append(item_name_cleaned)
            self.save_inventory(player_id, current_inventory) # save_inventory sorts it
            print(f"{TF.BRIGHT_GREEN}[Game System]: '{item_name_cleaned}' added to your inventory!{TF.RESET}")
            if state and 'player_inventory' in state: state['player_inventory'] = self.load_inventory(player_id) # Refresh cache
            return True
        else:
            print(f"{TF.DIM}'{item_name_cleaned}' is already in your inventory.{TF.RESET}")
            return False # Or True if "already had it" is considered success

    def check_item_in_inventory(self, player_id: str, item_name: str) -> bool:
        if not item_name or not isinstance(item_name, str) or not player_id: return False
        item_name_cleaned = item_name.strip()
        inventory = self.load_inventory(player_id)
        return item_name_cleaned in inventory
        
    # --- NEW: remove_item_from_inventory ---
    def remove_item_from_inventory(self, player_id: str, item_name: str, state: Optional[Dict[str, Any]] = None) -> bool:
        """Removes an item from the player's inventory."""
        TF = TerminalFormatter
        if state and 'TerminalFormatter' in state: TF = state['TerminalFormatter']

        if not item_name or not isinstance(item_name, str) or not player_id:
            print(f"{TF.RED}Error: Invalid item name or player ID for item removal.{TF.RESET}")
            return False

        item_name_cleaned = item_name.strip()
        if not item_name_cleaned:
            print(f"{TF.RED}Error: Item name for removal cannot be empty.{TF.RESET}")
            return False

        current_inventory = self.load_inventory(player_id)
        item_found_and_removed = False

        if item_name_cleaned in current_inventory:
            current_inventory.remove(item_name_cleaned) # Removes the first occurrence
            self.save_inventory(player_id, current_inventory) # save_inventory will re-sort
            # Message moved to command_processor for better context
            # print(f"{TF.BRIGHT_YELLOW}[Game System]: '{item_name_cleaned}' removed from your inventory.{TF.RESET}")
            if state and 'player_inventory' in state: # Update cache if used
                state['player_inventory'] = current_inventory 
            item_found_and_removed = True
        # else: # Message about item not found handled by caller (e.g. /give command)
            # print(f"{TF.YELLOW}'{item_name_cleaned}' not found in your inventory to remove.{TF.RESET}")

        return item_found_and_removed
    # --- END NEW ---

    # --- Player State Management (Largely Unchanged) ---
    def load_player_state(self, player_id: str) -> Optional[Dict[str, Any]]:
        # ... (existing implementation) ...
        if not player_id: return None
        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f: state_data = json.load(f)
                    return state_data if isinstance(state_data, dict) else None
                except Exception as e: print(f"⚠️ Error loading player state file {state_file}: {e}. Assuming new."); return None
            return None # No state file, new player for this context
        else: # DB
            conn = None; cursor = None; state_data = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT current_area, current_npc_code, plot_flags FROM PlayerState WHERE player_id = %s", (player_id,))
                result = cursor.fetchone()
                if result:
                    state_data = {'current_area': result.get('current_area'), 'current_npc_code': result.get('current_npc_code'), 'plot_flags': {}}
                    plot_flags_json = result.get('plot_flags')
                    if plot_flags_json:
                        try: state_data['plot_flags'] = json.loads(plot_flags_json) if isinstance(plot_flags_json, str) else plot_flags_json
                        except json.JSONDecodeError: print(f"⚠️ Failed decode plot_flags for P:{player_id}")
            except Exception as e: print(f"DB error loading state for P:{player_id}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return state_data

    def save_player_state(self, player_id: str, state_data: Dict[str, Any]) -> None:
        # ... (existing implementation) ...
        if not player_id or not state_data: return
        # Ensure current_npc part handles if current_npc is None
        current_npc_val = state_data.get('current_npc')
        npc_code_to_save = current_npc_val.get('code') if isinstance(current_npc_val, dict) else None

        data_to_save = {
            'current_area': state_data.get('current_area'),
            'current_npc_code': npc_code_to_save,
            'plot_flags': state_data.get('plot_flags', {})
        }
        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            player_state_dir = os.path.dirname(state_file)
            os.makedirs(player_state_dir, exist_ok=True)
            try:
                with open(state_file, 'w', encoding='utf-8') as f: json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            except Exception as e: print(f"⚠️ Error saving player state file {state_file}: {e}")
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                sql = """
                      INSERT INTO PlayerState (player_id, current_area, current_npc_code, plot_flags, last_seen)
                      VALUES (%s, %s, %s, %s, NOW()) ON DUPLICATE KEY UPDATE
                      current_area = VALUES(current_area), current_npc_code = VALUES(current_npc_code),
                      plot_flags = VALUES(plot_flags), last_seen = NOW(); """
                plot_flags_json = json.dumps(data_to_save['plot_flags'])
                values = (player_id, data_to_save['current_area'], data_to_save['current_npc_code'], plot_flags_json)
                cursor.execute(sql, values); conn.commit()
            except Exception as e: print(f"DB error saving state for P:{player_id}: {e}"); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    # --- Optional: DB Schema Setup ---
    def ensure_db_schema(self):
        # ... (existing implementation, ensure PlayerInventory table is robust) ...
        if self.use_mockup: return
        print("Ensuring database schema exists..."); conn = None
        try:
            # Test connection first
            conn_test = self.connect(); conn_test.close()

            # PlayerInventory: player_id, item_name are primary keys.
            self._ensure_table_exists(
                table_name="PlayerInventory",
                create_sql="""
                    CREATE TABLE IF NOT EXISTS PlayerInventory (
                        player_id VARCHAR(255) NOT NULL,
                        item_name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (player_id, item_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
            )
            self._ensure_table_exists(
                table_name="PlayerState",
                create_sql="""
                    CREATE TABLE IF NOT EXISTS PlayerState (
                        player_id VARCHAR(255) NOT NULL PRIMARY KEY,
                        current_area VARCHAR(255) NULL,
                        current_npc_code VARCHAR(255) NULL,
                        plot_flags JSON NULL,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
            )
            # ConversationHistory: Add INDEX for faster lookups if not already there.
            self._ensure_table_exists(
                table_name="ConversationHistory",
                create_sql="""
                    CREATE TABLE IF NOT EXISTS ConversationHistory (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        player_id VARCHAR(255) NOT NULL,
                        npc_code VARCHAR(255) NOT NULL,
                        sequence INT NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_player_npc_sequence (player_id, npc_code, sequence)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
            )
            # PlayerProfiles table (NEW for later enhancement)
            self._ensure_table_exists(
                table_name="PlayerProfiles",
                create_sql="""
                    CREATE TABLE IF NOT EXISTS PlayerProfiles (
                        player_id VARCHAR(255) NOT NULL PRIMARY KEY,
                        profile_json JSON NULL, -- Store profile as JSON string
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
            )
            print("Database schema check complete.")
        except Exception as e: print(f"Schema check failed: {e}")


    def _ensure_table_exists(self, table_name: str, create_sql: str, check_column: Optional[str] = None):
        # ... (existing implementation) ...
        if self.use_mockup: return
        if not self.db_config or not self.db_config.get('database'): print("DB ensure_table_exists skipped: No DB config."); return
        conn = None; cursor = None
        try:
            conn = self.connect(); cursor = conn.cursor(); db_name = self.db_config['database']
            # No need to USE db_name here as it's part of the connection in self.connect()
            cursor.execute("SHOW TABLES LIKE %s;", (table_name,))
            if not cursor.fetchone():
                print(f"Table '{table_name}' not found. Creating..."); cursor.execute(create_sql); conn.commit(); print(f"Table '{table_name}' created.")
            elif check_column: # Basic check if a column exists, useful for ALTERs not covered here
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s;", (check_column,)) # Use backticks for safety
                if not cursor.fetchone(): print(f"⚠️ Warn: Table '{table_name}' exists but missing column '{check_column}'. Manual check needed.")
        except Exception as e: print(f"DB error checking/creating {table_name}: {e}")
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()


class MockConnection: # Minimal mock, does not simulate DB storage
    def __init__(self, mockup_dir): self.mockup_dir = mockup_dir; self._is_connected = True
    def cursor(self, dictionary=False): return MockCursor(self.mockup_dir, dictionary)
    def commit(self): pass # Mock does nothing on commit
    def rollback(self): pass # Mock does nothing on rollback
    def close(self): self._is_connected = False
    def is_connected(self): return self._is_connected
    def start_transaction(self, **kwargs): pass # Mock does nothing

class MockCursor: # Minimal mock
    def __init__(self, mockup_dir, dictionary=False):
        self.mockup_dir = mockup_dir; self.dictionary = dictionary
        self.lastrowid = None; self._results = []; self._description = None
    def execute(self, query, params=None, multi=False): self._results = [] # Clear previous mock results
    def executemany(self, query, params_list=None): self._results = []
    def fetchone(self): return self._results.pop(0) if self._results else None
    def fetchall(self): results = self._results; self._results = []; return results
    def close(self): pass
    @property
    def description(self): return self._description
    @property
    def rowcount(self): return 0 # Mock, can be improved if needed


# (Keep existing __main__ test block if you have one, or add tests for new methods)
if __name__ == "__main__":
    # Example usage (ensure TerminalFormatter is defined or imported for tests)
    class TF: RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_YELLOW=""; BRIGHT_GREEN = "";
    TerminalFormatter = TF

    print("--- Testing DbManager Inventory ---")
    # Create a temporary mockup directory for testing
    test_mockup_dir = "_temp_db_test_inventory"
    if not os.path.exists(test_mockup_dir): os.makedirs(test_mockup_dir)
    
    # Ensure subdirectories for mockup are created if they don't exist
    for subdir in ["PlayerProfiles", "ConversationHistory", "PlayerState"]:
        os.makedirs(os.path.join(test_mockup_dir, subdir), exist_ok=True)


    db_mock = DbManager(use_mockup=True, mockup_dir=test_mockup_dir)
    player_id_test = "TestPlayerInv"
    test_state_mock = {'TerminalFormatter': TerminalFormatter, 'player_inventory': []}

    print("\nInitial inventory:", db_mock.load_inventory(player_id_test))
    
    db_mock.add_item_to_inventory(player_id_test, "Health Potion", test_state_mock)
    db_mock.add_item_to_inventory(player_id_test, "Mana Potion", test_state_mock)
    db_mock.add_item_to_inventory(player_id_test, "Health Potion", test_state_mock) # Test adding duplicate
    print("Inventory after adds:", db_mock.load_inventory(player_id_test))
    assert "Health Potion" in db_mock.load_inventory(player_id_test)
    
    db_mock.remove_item_from_inventory(player_id_test, "Health Potion", test_state_mock)
    print("Inventory after one remove:", db_mock.load_inventory(player_id_test))
    assert "Health Potion" not in db_mock.load_inventory(player_id_test) # Assuming non-stackable for this test

    db_mock.remove_item_from_inventory(player_id_test, "NonExistentItem", test_state_mock) # Test remove non-existent
    print("Inventory after failed remove:", db_mock.load_inventory(player_id_test))

    # Clean up test directory
    import shutil
    try:
        shutil.rmtree(test_mockup_dir)
        print(f"Cleaned up test directory: {test_mockup_dir}")
    except OSError as e:
        print(f"Error cleaning up test directory {test_mockup_dir}: {e}")
    print("--- DbManager Inventory Test Done ---")
