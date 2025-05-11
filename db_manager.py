# Path: db_manager.py
# Updated Version - FIX SyntaxError on line 317, Includes player_id, Player State, AND Original Methods

from dotenv import load_dotenv
import mysql.connector # Import for real DB
import os
import sys # Import sys for module check
import json
from typing import List, Dict, Optional, Any, Set, Tuple # Added Tuple
from datetime import datetime
import traceback

# --- Terminal Formatter (Assume available or provide basic fallback) ---
try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    print("Warning (db_manager): terminal_formatter not found. Using basic fallback.")
    class TerminalFormatter: # Basic Fallback
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; BRIGHT_YELLOW=""
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))

class DbManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None, use_mockup: bool = False, mockup_dir: str = "database"):
        """Initializes the DbManager."""
        self.use_mockup = use_mockup
        self.mockup_dir = mockup_dir
        # Define templates for player-specific mockup files/dirs
        self.inventory_file_path_template = os.path.join(self.mockup_dir, "{player_id}_inventory.json")
        self.conversation_dir_template = os.path.join(self.mockup_dir, "ConversationHistory", "{player_id}")
        self.player_state_file_template = os.path.join(self.mockup_dir, "PlayerState", "{player_id}.json")

        # --- Database Configuration Loading ---
        if config:
            self.db_config = config
            print(f"DbManager: Using provided database configuration.")
        else:
            self.db_config = { # Load from env vars
                'host': os.environ.get('DB_HOST'), 'user': os.environ.get('DB_USER'),
                'password': os.environ.get('DB_PASSWORD'), 'database': os.environ.get('DB_NAME'),
                'port': int(os.environ.get('DB_PORT', 3306)),
                'connection_timeout': int(os.environ.get('DB_TIMEOUT', 10))
            }
            if not self.use_mockup and not all([self.db_config['host'], self.db_config['user'], self.db_config['database']]):
                print("DbManager Warning: Real database mode selected, but DB config is missing.")

        # --- Mockup Directory Setup (Only if using mockup) ---
        if self.use_mockup:
            if not os.path.exists(self.mockup_dir):
                try: os.makedirs(self.mockup_dir)
                except OSError as e: print(f"⚠️ Error creating base mockup directory {self.mockup_dir}: {e}")
            for subdir_tmpl in [self.conversation_dir_template, self.player_state_file_template]:
                base_dir = os.path.dirname(subdir_tmpl)
                if not os.path.exists(base_dir):
                    try: os.makedirs(base_dir)
                    except OSError as e: print(f"⚠️ Error creating mockup subdirectory {base_dir}: {e}")
            # Non-player-specific dirs
            for table in ["NPCs", "Storyboards", "Dialogues"]: # Excl. ConversationHistory, PlayerState handled above
                table_dir = os.path.join(self.mockup_dir, table)
                if not os.path.exists(table_dir):
                    try: os.makedirs(table_dir)
                    except OSError as e: print(f"⚠️ Error creating mockup subdirectory {table_dir}: {e}")
            print(f"DbManager: Mockup filesystem initialized in '{self.mockup_dir}'")

        elif self.db_config and self.db_config.get('host'):
            print(f"DbManager: Configured for Real Database ({self.db_config.get('host')}:{self.db_config.get('port')}/{self.db_config.get('database')})")
            # Optional: Ensure tables exist on init for real DB mode
            # self.ensure_db_schema()


    def connect(self) -> Any:
        """Connects to the database or returns a mock connection."""
        if self.use_mockup:
            return MockConnection(self.mockup_dir)
        else:
            if not self.db_config or not all([self.db_config['host'], self.db_config['user'], self.db_config['database']]):
                raise ValueError("Database configuration is incomplete.")
            try:
                # Ensure mysql.connector is imported if needed
                if 'mysql' not in sys.modules:
                    import mysql.connector
                return mysql.connector.connect(**self.db_config)
            except mysql.connector.Error as err: print(f"Database connection error: {err}"); raise
            except ImportError: print("ERROR: mysql.connector not installed. Run 'pip install mysql-connector-python'"); raise


    # --- NPC / Storyboard Methods (Re-included) ---

    def get_storyboard(self) -> Dict[str, Any]:
        """Fetches the first storyboard."""
        if self.use_mockup:
            storyboard_dir = os.path.join(self.mockup_dir, "Storyboards")
            try:
                storyboard_files = os.listdir(storyboard_dir)
                if storyboard_files:
                    storyboard_files.sort() # Consistent read
                    file_path = os.path.join(storyboard_dir, storyboard_files[0])
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    except json.JSONDecodeError: print(f"⚠️ Error decoding storyboard file: {file_path}"); return {"description": "[Error - invalid JSON]"}
                    except IOError as e: print(f"⚠️ Error reading storyboard file {file_path}: {e}"); return {"description": "[Error - read error]"}
                    except Exception as e: print(f"⚠️ Unexpected error with storyboard file {file_path}: {e}"); traceback.print_exc(); return {"description": "[Error - unexpected]"}
            except FileNotFoundError: print(f"⚠️ Storyboard directory not found: {storyboard_dir}")
            except OSError as e: print(f"⚠️ Error listing storyboard directory {storyboard_dir}: {e}")
            return {"description": "[No storyboard found or error occurred]"}
        else:
            conn = None; cursor = None; row = None
            try:
                conn = self.connect()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM Storyboards LIMIT 1")
                row = cursor.fetchone()
            except mysql.connector.Error as err: print(f"Database error fetching storyboard: {err}")
            except Exception as e: print(f"⚠️ Unexpected error fetching DB storyboard: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return row if row else {"description": "[No storyboard found in DB]"}

    def get_npc(self, area: str, name: str) -> Optional[Dict[str, Any]]:
        """Fetches a specific NPC by area and name (case-insensitive)."""
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs")
            try:
                for filename in os.listdir(npc_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(npc_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f: npc = json.load(f)
                            if npc.get('area', '').lower() == area.lower() and npc.get('name', '').lower() == name.lower():
                                if 'code' not in npc: npc['code'] = filename.replace('.json', '')
                                return npc
                        except json.JSONDecodeError: print(f"⚠️ Skipping invalid JSON NPC file: {file_path}")
                        except IOError: print(f"⚠️ Error reading NPC file: {file_path}")
                        except Exception as e: print(f"⚠️ Unexpected error processing NPC file {file_path}: {e}"); traceback.print_exc()
            except FileNotFoundError: print(f"⚠️ NPC directory not found: {npc_dir}")
            except OSError as e: print(f"⚠️ Error listing NPC directory {npc_dir}: {e}")
            return None
        else:
            conn = None; cursor = None; npc = None
            try:
                conn = self.connect()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM NPCs WHERE LOWER(area) = LOWER(%s) AND LOWER(name) = LOWER(%s)", (area, name))
                npc = cursor.fetchone()
            except mysql.connector.Error as err: print(f"Database error fetching NPC {name} in {area}: {err}")
            except Exception as e: print(f"⚠️ Unexpected error fetching DB NPC: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return npc

    def get_default_npc(self, area: str) -> Optional[Dict[str, Any]]:
        """Fetches the first NPC alphabetically in a given area (case-insensitive)."""
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
                        except: pass # Ignore errors when just finding default
            except: pass # Ignore errors when just finding default
            if npcs_in_area: return sorted(npcs_in_area, key=lambda x: x.get('name', '').lower())[0]
            return None
        else:
            conn = None; cursor = None; npc = None
            try:
                conn = self.connect()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM NPCs WHERE LOWER(area) = LOWER(%s) ORDER BY name LIMIT 1", (area,))
                npc = cursor.fetchone()
            except mysql.connector.Error as err: print(f"Database error fetching default NPC for {area}: {err}")
            except Exception as e: print(f"⚠️ Unexpected error fetching default DB NPC: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return npc

    def get_all_areas_and_npcs(self) -> List[Dict[str, str]]:
        """Gets a list of areas and the NPCs in them."""
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs")
            areas = {}
            try:
                for filename in os.listdir(npc_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(npc_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f: npc = json.load(f)
                            area_name = npc.get('area', 'Unknown'); npc_name = npc.get('name', 'Unknown'); area_key = area_name.lower()
                            if area_key not in areas: areas[area_key] = {"name": area_name, "npcs": set()}
                            areas[area_key]["npcs"].add(npc_name)
                        except: pass # Ignore file errors
            except: pass # Ignore directory errors
            result = [{"area": area_data["name"], "npcs": ", ".join(sorted(list(area_data["npcs"])))} for area_key, area_data in areas.items()]
            return sorted(result, key=lambda x: x['area'].lower())
        else:
            conn = None; cursor = None; areas_npcs = []
            try:
                conn = self.connect()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT area, GROUP_CONCAT(name ORDER BY name SEPARATOR ', ') as npcs FROM NPCs GROUP BY area ORDER BY area")
                areas_npcs = cursor.fetchall()
            except mysql.connector.Error as err: print(f"Database error fetching all areas and NPCs: {err}")
            except Exception as e: print(f"⚠️ Unexpected error fetching DB areas/NPCs: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return areas_npcs

    def list_npcs_by_area(self) -> List[Dict[str, str]]:
        """Gets a flat list of all NPCs with their area, name, role, and code."""
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs")
            npcs = []
            try:
                for filename in os.listdir(npc_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(npc_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f: npc_data = json.load(f)
                            npc_code = npc_data.get('code', filename.replace('.json', ''))
                            npcs.append({"code": npc_code, "area": npc_data.get('area', 'Unknown'), "name": npc_data.get('name', 'Unknown'), "role": npc_data.get('role', 'Unknown')})
                        except: pass # Ignore file errors
            except: pass # Ignore directory errors
            return sorted(npcs, key=lambda x: (x["area"].lower(), x["name"].lower()))
        else:
            conn = None; cursor = None; rows = []
            try:
                conn = self.connect()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT code, area, name, role FROM NPCs ORDER BY area, name")
                rows = cursor.fetchall()
            except mysql.connector.Error as err: print(f"Database error listing NPCs by area: {err}")
            except Exception as e: print(f"⚠️ Unexpected error listing DB NPCs: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return rows

    # --- Conversation History (Player Specific) ---
    def save_conversation(self, player_id: str, npc_code: str, conversation_history: List[Dict[str, str]]) -> None:
        # ... (Keep implementation from previous response) ...
        if not conversation_history or not player_id or not npc_code: print("⚠️ Save convo skipped: missing info."); return
        if self.use_mockup:
            player_conv_dir = self.conversation_dir_template.format(player_id=player_id)
            if not os.path.exists(player_conv_dir):
                try: os.makedirs(player_conv_dir)
                except OSError as e: print(f"⚠️ Error creating dir {player_conv_dir}: {e}"); return
            conv_file = os.path.join(player_conv_dir, f"{npc_code}.json")
            formatted_history = [{"sequence": i, "role": msg.get('role', ''), "content": msg.get('content', '')} for i, msg in enumerate(conversation_history)]
            try:
                with open(conv_file, 'w', encoding='utf-8') as f: json.dump(formatted_history, f, ensure_ascii=False, indent=2)
            except IOError as e: print(f"⚠️ Error saving convo file {conv_file}: {e}")
            except Exception as e: print(f"⚠️ Unexpected error saving convo file {conv_file}: {e}"); traceback.print_exc()
        else:
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(); conn.start_transaction()
                cursor.execute("DELETE FROM ConversationHistory WHERE player_id = %s AND npc_code = %s", (player_id, npc_code))
                if conversation_history:
                    insert_query = "INSERT INTO ConversationHistory (player_id, npc_code, sequence, role, content) VALUES (%s, %s, %s, %s, %s)"
                    values = [(player_id, npc_code, i, msg.get('role', ''), msg.get('content', '')) for i, msg in enumerate(conversation_history)]
                    cursor.executemany(insert_query, values)
                conn.commit()
            except mysql.connector.Error as err: print(f"DB error saving convo for P:{player_id},N:{npc_code}: {err}"); conn.rollback()
            except Exception as e: print(f"⚠️ Unexpected error saving DB convo: {e}"); traceback.print_exc(); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def load_conversation(self, player_id: str, npc_code: str) -> List[Dict[str, str]]:
        # ... (Keep implementation from previous response) ...
        if not player_id or not npc_code: return []
        if self.use_mockup:
            player_conv_dir = self.conversation_dir_template.format(player_id=player_id)
            conv_file = os.path.join(player_conv_dir, f"{npc_code}.json")
            if os.path.exists(conv_file):
                try:
                    with open(conv_file, 'r', encoding='utf-8') as f: formatted_history = json.load(f)
                    return [{"role": msg.get("role"), "content": msg.get("content")} for msg in sorted(formatted_history, key=lambda x: x.get("sequence", 0))]
                except json.JSONDecodeError: print(f"⚠️ Error decoding convo file: {conv_file}"); return []
                except IOError as e: print(f"⚠️ Error reading convo file {conv_file}: {e}"); return []
                except Exception as e: print(f"⚠️ Unexpected error loading convo file {conv_file}: {e}"); traceback.print_exc(); return []
            return []
        else:
            conn = None; cursor = None; conversation = []
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT role, content FROM ConversationHistory WHERE player_id = %s AND npc_code = %s ORDER BY sequence", (player_id, npc_code))
                conversation = cursor.fetchall()
            except mysql.connector.Error as err: print(f"DB error loading convo for P:{player_id},N:{npc_code}: {err}")
            except Exception as e: print(f"⚠️ Unexpected error loading DB convo: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return conversation if conversation else []

    # --- Inventory Management (Player Specific) ---
    def load_inventory(self, player_id: str) -> List[str]:
        """Loads the player inventory list."""
        if not player_id: return []
        if self.use_mockup:
            # --- Mockup Logic ---
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            try:
                if not os.path.exists(inv_file):
                    # Create file if it doesn't exist for this player yet
                    with open(inv_file, 'w', encoding='utf-8') as f: json.dump([], f)
                    return []
                with open(inv_file, 'r', encoding='utf-8') as f:
                    inventory = json.load(f)
                if isinstance(inventory, list):
                    return sorted([str(item) for item in inventory])
                else:
                    # Invalid format, reset it
                    print(f"⚠️ Invalid format in inventory file {inv_file}. Resetting.")
                    self.save_inventory(player_id, []) # Reset to empty list
                    return []
            except (IOError, json.JSONDecodeError) as e:
                print(f"⚠️ Error loading mockup inv {inv_file}: {e}. Resetting.")
                # --- SYNTAX FIX APPLIED BELOW ---
                try:
                    self.save_inventory(player_id, [])
                except Exception as save_err:
                    print(f"⚠️ Also failed to reset inventory file during error handling: {save_err}")
                return [] # Return empty list after attempting reset
            except Exception as e:
                print(f"⚠️ Unexpected error loading mockup inv: {e}"); traceback.print_exc(); return []
        else:
            # --- Real DB Logic ---
            inventory = []
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                cursor.execute("SELECT item_name FROM PlayerInventory WHERE player_id = %s ORDER BY item_name", (player_id,))
                results = cursor.fetchall(); inventory = [row[0] for row in results]
            except mysql.connector.Error as err: print(f"DB error loading inv for {player_id}: {err}")
            except Exception as e: print(f"⚠️ Unexpected error loading DB inv: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return inventory

    def save_inventory(self, player_id: str, inventory_list: List[str]) -> None:
        # ... (Keep implementation from previous response) ...
        if not player_id: return
        unique_string_inventory = sorted(list(set(str(item).strip() for item in inventory_list if str(item).strip())))
        if self.use_mockup:
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            try:
                with open(inv_file, 'w', encoding='utf-8') as f: json.dump(unique_string_inventory, f, ensure_ascii=False, indent=2)
            except IOError as e: print(f"⚠️ Error saving mockup inv to {inv_file}: {e}")
            except Exception as e: print(f"⚠️ Unexpected error saving mockup inv: {e}"); traceback.print_exc()
        else:
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(); conn.start_transaction()
                cursor.execute("DELETE FROM PlayerInventory WHERE player_id = %s", (player_id,))
                if unique_string_inventory:
                    sql = "INSERT INTO PlayerInventory (player_id, item_name) VALUES (%s, %s)"
                    values = [(player_id, item) for item in unique_string_inventory]
                    cursor.executemany(sql, values)
                conn.commit()
            except mysql.connector.Error as err: print(f"DB error saving inv for {player_id}: {err}"); conn.rollback()
            except Exception as e: print(f"⚠️ Unexpected error saving DB inv: {e}"); traceback.print_exc(); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def add_item_to_inventory(self, player_id: str, item_name: str, state: Dict[str, Any]) -> bool:
        # ... (Keep implementation from previous response) ...
        TF = state.get('TerminalFormatter', TerminalFormatter)
        if not item_name or not isinstance(item_name, str) or not player_id: print(f"{TF.RED}Error: Invalid item/player ID.{TF.RESET}"); return False
        item_name_cleaned = item_name.strip(); item_added = False
        if self.use_mockup:
            inventory = self.load_inventory(player_id)
            if item_name_cleaned not in inventory: inventory.append(item_name_cleaned); self.save_inventory(player_id, inventory); item_added = True
        else:
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                sql = "INSERT IGNORE INTO PlayerInventory (player_id, item_name) VALUES (%s, %s)"
                cursor.execute(sql, (player_id, item_name_cleaned)); conn.commit()
                if cursor.rowcount > 0: item_added = True
            except mysql.connector.Error as err: print(f"DB error adding item '{item_name_cleaned}': {err}"); conn.rollback()
            except Exception as e: print(f"⚠️ Unexpected error adding DB item: {e}"); traceback.print_exc(); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        if item_added:
            print(f"{TF.BRIGHT_YELLOW}[Master]: {item_name_cleaned} added to inventory!{TF.RESET}")
            state['player_inventory'] = self.load_inventory(player_id) # Update state
            return True
        else: return False

    def check_item_in_inventory(self, player_id: str, item_name: str) -> bool:
        # ... (Keep implementation from previous response) ...
        if not item_name or not isinstance(item_name, str) or not player_id: return False
        item_name_cleaned = item_name.strip()
        if self.use_mockup:
            inventory = self.load_inventory(player_id); return item_name_cleaned in inventory
        else:
            conn = None; cursor = None; count = 0
            try:
                conn = self.connect(); cursor = conn.cursor()
                sql = "SELECT COUNT(*) FROM PlayerInventory WHERE player_id = %s AND item_name = %s"
                cursor.execute(sql, (player_id, item_name_cleaned)); result = cursor.fetchone()
                if result: count = result[0]
            except mysql.connector.Error as err: print(f"DB error checking item '{item_name_cleaned}': {err}")
            except Exception as e: print(f"⚠️ Unexpected error checking DB item: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return count > 0

    # --- Player State Management ---
    def load_player_state(self, player_id: str) -> Optional[Dict[str, Any]]:
        # ... (Keep implementation from previous response) ...
        if not player_id: return None
        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f: state_data = json.load(f)
                    return state_data if isinstance(state_data, dict) else None
                except (IOError, json.JSONDecodeError) as e: print(f"⚠️ Error loading player state file {state_file}: {e}. Assuming new."); return None
                except Exception as e: print(f"⚠️ Unexpected error loading mockup player state: {e}"); traceback.print_exc(); return None
            return None
        else:
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
            except mysql.connector.Error as err: print(f"DB error loading state for P:{player_id}: {err}")
            except Exception as e: print(f"⚠️ Unexpected error loading DB player state: {e}"); traceback.print_exc()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
            return state_data

    def save_player_state(self, player_id: str, state_data: Dict[str, Any]) -> None:
        # ... (Keep implementation from previous response) ...
        if not player_id or not state_data: return
        data_to_save = {
            'current_area': state_data.get('current_area'),
            'current_npc_code': state_data.get('current_npc', {}).get('code') if state_data.get('current_npc') else None,
            'plot_flags': state_data.get('plot_flags', {})
        }
        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            player_state_dir = os.path.dirname(state_file)
            if not os.path.exists(player_state_dir):
                try: os.makedirs(player_state_dir)
                except OSError as e: print(f"⚠️ Error creating player state dir {player_state_dir}: {e}"); return
            try:
                with open(state_file, 'w', encoding='utf-8') as f: json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            except IOError as e: print(f"⚠️ Error saving player state file {state_file}: {e}")
            except Exception as e: print(f"⚠️ Unexpected error saving mockup player state: {e}"); traceback.print_exc()
        else:
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
            except mysql.connector.Error as err: print(f"DB error saving state for P:{player_id}: {err}"); conn.rollback()
            except Exception as e: print(f"⚠️ Unexpected error saving DB player state: {e}"); traceback.print_exc(); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    # --- Optional: DB Schema Setup ---
    def ensure_db_schema(self):
        # ... (Keep implementation from previous response) ...
        if self.use_mockup: return
        print("Ensuring database schema exists..."); conn = None
        try:
            conn = self.connect(); conn.close() # Test connection
            self._ensure_table_exists( table_name="PlayerInventory", create_sql=""" CREATE TABLE PlayerInventory (player_id VARCHAR(255) NOT NULL, item_name VARCHAR(255) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (player_id, item_name)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;""" )
            self._ensure_table_exists( table_name="PlayerState", create_sql=""" CREATE TABLE PlayerState (player_id VARCHAR(255) NOT NULL, current_area VARCHAR(255) NULL, current_npc_code VARCHAR(255) NULL, plot_flags JSON NULL, last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, PRIMARY KEY (player_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;""")
            self._ensure_table_exists( table_name="ConversationHistory", create_sql=""" CREATE TABLE ConversationHistory (id INT AUTO_INCREMENT PRIMARY KEY, player_id VARCHAR(255) NOT NULL, npc_code VARCHAR(255) NOT NULL, sequence INT NOT NULL, role VARCHAR(50) NOT NULL, content TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, INDEX idx_player_npc_sequence (player_id, npc_code, sequence)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;""", check_column="player_id" )
            print("Database schema check complete.")
        except Exception as e: print(f"Schema check failed: {e}")

    def _ensure_table_exists(self, table_name: str, create_sql: str, check_column: Optional[str] = None):
        # ... (Keep implementation from previous response) ...
        if self.use_mockup: return
        if not self.db_config or not self.db_config.get('database'): return
        conn = None; cursor = None
        try:
            conn = self.connect(); cursor = conn.cursor(); db_name = self.db_config['database']; cursor.execute(f"USE {db_name};")
            cursor.execute("SHOW TABLES LIKE %s;", (table_name,)); result = cursor.fetchone()
            if not result:
                print(f"{table_name} table not found. Creating..."); cursor.execute(create_sql); conn.commit(); print(f"{table_name} table created.")
            elif check_column:
                cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s;", (check_column,)); col_result = cursor.fetchone()
                if not col_result: print(f"⚠️ Warning: Table '{table_name}' missing column '{check_column}'. Manual update may be needed.")
        except mysql.connector.Error as err: print(f"DB error checking/creating {table_name}: {err}")
        except Exception as e: print(f"Unexpected error during {table_name} check: {e}"); traceback.print_exc()
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()


# --- Mock Connection Classes ---
# ... (Keep MockConnection and MockCursor classes as they are) ...
class MockConnection:
    def __init__(self, mockup_dir): self.mockup_dir = mockup_dir
    def cursor(self, dictionary=False): return MockCursor(self.mockup_dir, dictionary)
    def commit(self): pass
    def close(self): pass
    def is_connected(self): return True
class MockCursor:
    def __init__(self, mockup_dir, dictionary=False): self.mockup_dir = mockup_dir; self.dictionary = dictionary; self.last_query = None; self.last_params = None; self.lastrowid = None
    def execute(self, query, params=None): self.last_query = query; self.last_params = params; pass
    def executemany(self, query, params_list=None): self.last_query = query; self.last_params = "Multiple sets"; pass
    def fetchone(self): return None
    def fetchall(self): return []
    def close(self): pass


# ===========================================
# Main Test Block (Updated for Player ID Separation)
# ===========================================
if __name__ == "__main__":
    import shutil
    # import sys # Already imported above

    TEST_MOCKUP_DIR = "_temp_db_manager_test_playerid"
    print(f"--- Running DbManager Mockup Test (Player ID Separation) ---")
    print(f"Using temporary directory: {TEST_MOCKUP_DIR}")

    # --- Helper Functions ---
    def setup_minimal_mockup_data(mockup_dir):
        print("Setting up minimal mockup data...")
        if not os.path.exists(mockup_dir): os.makedirs(mockup_dir)
        npc_dir = os.path.join(mockup_dir, "NPCs"); story_dir = os.path.join(mockup_dir, "Storyboards")
        if not os.path.exists(npc_dir): os.makedirs(npc_dir)
        if not os.path.exists(story_dir): os.makedirs(story_dir)
        story_data = {"id": 1, "name": "Test Story", "description": "A minimal test storyboard."}
        with open(os.path.join(story_dir, "1.json"), 'w', encoding='utf-8') as f: json.dump(story_data, f, indent=2)
        npc_data = {"code": "GUARD01", "name": "Guard Captain Maya", "area": "TestArea", "role": "City Guard"}
        with open(os.path.join(npc_dir, "GUARD01.json"), 'w', encoding='utf-8') as f: json.dump(npc_data, f, indent=2)
        print("Minimal data created.")

    def cleanup_mockup_data(mockup_dir):
        print(f"Cleaning up temporary data: {mockup_dir}")
        if os.path.exists(mockup_dir):
            try: shutil.rmtree(mockup_dir); print("Cleanup successful.")
            except OSError as e: print(f"Error during cleanup: {e}")
        else: print("Directory already removed.")
    # --- End Helper Functions ---

    # --- Test Variables ---
    player1_id = "Alice"
    player2_id = "Bob"
    npc_code = "GUARD01"
    # Mock state needs player_id now for add_item_to_inventory's TF lookup, but not strictly needed otherwise for tests
    test_state_p1 = {'TerminalFormatter': TerminalFormatter(), 'player_id': player1_id, 'player_inventory': []} # Add inventory to state
    test_state_p2 = {'TerminalFormatter': TerminalFormatter(), 'player_id': player2_id, 'player_inventory': []} # Add inventory to state

    # --- Run the Test ---
    try:
        # 1. Setup
        cleanup_mockup_data(TEST_MOCKUP_DIR)
        setup_minimal_mockup_data(TEST_MOCKUP_DIR)

        # 2. Initialize DbManager in Mockup Mode
        db = DbManager(use_mockup=True, mockup_dir=TEST_MOCKUP_DIR)
        print("\nDbManager initialized in mockup mode.")

        # 3. Basic Tests (These should now work)
        print("\nTesting get_storyboard():")
        story = db.get_storyboard()
        print(f"  Result: {story}")
        assert story and story.get('name') == "Test Story"

        print("\nTesting get_npc('TestArea', 'Guard Captain Maya'):")
        npc = db.get_npc("TestArea", "Guard Captain Maya")
        print(f"  Result: {npc}")
        assert npc and npc.get('code') == "GUARD01"

        # 4. Inventory Separation Tests
        print("\n--- Testing Inventory Separation ---")
        # Initialize state inventory
        test_state_p1['player_inventory'] = db.load_inventory(player1_id)
        test_state_p2['player_inventory'] = db.load_inventory(player2_id)
        print(f"Initial inventory for {player1_id}: {test_state_p1['player_inventory']}")
        print(f"Initial inventory for {player2_id}: {test_state_p2['player_inventory']}")

        print(f"\nAdding items for {player1_id}...")
        db.add_item_to_inventory(player1_id, "Magic Amulet", test_state_p1) # state_p1 updated internally
        db.add_item_to_inventory(player1_id, "Rusty Sword", test_state_p1)  # state_p1 updated internally

        print(f"\nAdding items for {player2_id}...")
        db.add_item_to_inventory(player2_id, "Healing Potion", test_state_p2) # state_p2 updated internally
        db.add_item_to_inventory(player2_id, "Shiny Key", test_state_p2)      # state_p2 updated internally

        print(f"\nVerifying inventories (from state)...")
        inv_p1_state = test_state_p1['player_inventory']
        inv_p2_state = test_state_p2['player_inventory']
        print(f"  {player1_id} Inventory (state): {inv_p1_state}")
        print(f"  {player2_id} Inventory (state): {inv_p2_state}")

        # Also verify by loading directly from DB manager again
        inv_p1_load = db.load_inventory(player1_id)
        inv_p2_load = db.load_inventory(player2_id)
        print(f"  {player1_id} Inventory (load): {inv_p1_load}")
        print(f"  {player2_id} Inventory (load): {inv_p2_load}")

        assert inv_p1_state == ["Magic Amulet", "Rusty Sword"]
        assert inv_p1_load == ["Magic Amulet", "Rusty Sword"]
        assert "Healing Potion" not in inv_p1_state and "Shiny Key" not in inv_p1_state
        assert inv_p2_state == ["Healing Potion", "Shiny Key"]
        assert inv_p2_load == ["Healing Potion", "Shiny Key"]
        assert "Magic Amulet" not in inv_p2_state and "Rusty Sword" not in inv_p2_state
        print("  ✅ Inventory separation verified (state & load).")

        print(f"\nOverwriting {player1_id}'s inventory...")
        db.save_inventory(player1_id, ["Worn Boots"])
        inv_p1_new = db.load_inventory(player1_id)
        inv_p2_after_p1_save = db.load_inventory(player2_id)
        print(f"  {player1_id} New Inventory: {inv_p1_new}")
        print(f"  {player2_id} Inventory (should be unchanged): {inv_p2_after_p1_save}")
        assert inv_p1_new == ["Worn Boots"]
        assert inv_p2_after_p1_save == ["Healing Potion", "Shiny Key"] # Verify P2 unchanged
        print("  ✅ Inventory overwrite separation verified.")


        # 5. Dialogue (Conversation) Separation Tests
        print("\n--- Testing Dialogue Separation ---")
        # ... (Keep dialogue tests exactly as in the previous response) ...
        convo_p1_npc1 = [{"role": "system", "content": "Guard Prompt"}, {"role": "user", "content": f"Hi I'm {player1_id}"}, {"role": "assistant", "content": f"Hello {player1_id}"}]
        convo_p2_npc1 = [{"role": "system", "content": "Guard Prompt"}, {"role": "user", "content": f"Yo, it's {player2_id}"}, {"role": "assistant", "content": f"State business {player2_id}"}, {"role": "user", "content": "Nunya"}]
        print(f"\nSaving conversations for {npc_code}..."); db.save_conversation(player1_id, npc_code, convo_p1_npc1); print(f"  Saved {player1_id}'s convo.")
        db.save_conversation(player2_id, npc_code, convo_p2_npc1); print(f"  Saved {player2_id}'s convo.")
        print(f"\nLoading conversations..."); loaded_p1 = db.load_conversation(player1_id, npc_code); loaded_p2 = db.load_conversation(player2_id, npc_code)
        loaded_p1_othernpc = db.load_conversation(player1_id, "NONEXISTENT_NPC")
        print(f"  Loaded P1/{npc_code} (Len:{len(loaded_p1)}): {loaded_p1}"); print(f"  Loaded P2/{npc_code} (Len:{len(loaded_p2)}): {loaded_p2}")
        print(f"  Loaded P1/OTHER (Len:{len(loaded_p1_othernpc)}): {loaded_p1_othernpc}")
        assert len(loaded_p1) == len(convo_p1_npc1) and loaded_p1[-1]['content'] == f"Hello {player1_id}"
        assert len(loaded_p2) == len(convo_p2_npc1) and loaded_p2[-1]['content'] == "Nunya"
        assert loaded_p1_othernpc == []
        print("  ✅ Dialogue separation verified.")


        # 6. Player State Tests (Basic)
        print("\n--- Testing Player State Separation ---")
        # ... (Keep player state tests exactly as in the previous response) ...
        # Note: save_player_state now extracts npc code automatically
        state_p1_save = { 'current_area': 'Tavern', 'current_npc': {'code': 'TAVERNKEEP'}, 'plot_flags': {'met_mayor': True}}
        state_p2_save = { 'current_area': 'Forest', 'current_npc': None, 'plot_flags': {'found_cave': True, 'met_mayor': False}}
        print("\nSaving player states..."); db.save_player_state(player1_id, state_p1_save); print(f"  Saved {player1_id}'s state.")
        db.save_player_state(player2_id, state_p2_save); print(f"  Saved {player2_id}'s state.")
        print("\nLoading player states..."); loaded_state_p1 = db.load_player_state(player1_id); loaded_state_p2 = db.load_player_state(player2_id)
        print(f"  Loaded {player1_id}'s state: {loaded_state_p1}"); print(f"  Loaded {player2_id}'s state: {loaded_state_p2}")
        assert loaded_state_p1['current_area'] == 'Tavern' and loaded_state_p1['plot_flags']['met_mayor'] is True and loaded_state_p1['current_npc_code'] == 'TAVERNKEEP'
        assert loaded_state_p2['current_area'] == 'Forest' and loaded_state_p2['plot_flags']['found_cave'] is True and loaded_state_p2['current_npc_code'] is None
        print("  ✅ Player state separation verified.")


        print(f"\n{TerminalFormatter.GREEN}--- All Player ID Separation Tests Passed ---{TerminalFormatter.RESET}")

    except AssertionError as e:
        print(f"\n{TerminalFormatter.RED}--- TEST FAILED: Assertion Error ---{TerminalFormatter.RESET}"); print(e); traceback.print_exc()
    except Exception as e:
        print(f"\n{TerminalFormatter.RED}--- TEST FAILED: Unexpected Error ---{TerminalFormatter.RESET}"); print(e); traceback.print_exc()
    finally:
        # 7. Cleanup
        cleanup_mockup_data(TEST_MOCKUP_DIR)
