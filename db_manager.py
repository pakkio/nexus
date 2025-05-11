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
            self.db_config = { 
                'host': os.environ.get('DB_HOST'), 'user': os.environ.get('DB_USER'),
                'password': os.environ.get('DB_PASSWORD'), 'database': os.environ.get('DB_NAME'),
                'port': int(os.environ.get('DB_PORT', 3306)),
                'connection_timeout': int(os.environ.get('DB_TIMEOUT', 10))
            }
        if self.use_mockup:
            os.makedirs(self.mockup_dir, exist_ok=True)
            for subdir_tmpl in [self.conversation_dir_template, self.player_state_file_template, self.player_profile_file_template]:
                base_dir = os.path.dirname(subdir_tmpl.split("{player_id}")[0])
                os.makedirs(base_dir, exist_ok=True)
            for static_dir in ["NPCs", "Storyboards"]: os.makedirs(os.path.join(self.mockup_dir, static_dir), exist_ok=True)
            # print(f"DbManager: Mockup filesystem checked/initialized in '{self.mockup_dir}'")
        elif self.db_config and self.db_config.get('host'):
             pass # print(f"DbManager: Configured for Real Database.")


    def connect(self) -> Any:
        if self.use_mockup: return MockConnection(self.mockup_dir)
        else:
            if not self.db_config or not all([self.db_config['host'], self.db_config['user'], self.db_config['database']]):
                raise ValueError("Database configuration incomplete.")
            try:
                if 'mysql' not in sys.modules: import mysql.connector
                return mysql.connector.connect(**self.db_config)
            except Exception as e: print(f"Database connection error: {e}"); raise

    # --- NPC / Storyboard Methods (Unchanged from previous versions with hints) ---
    def get_storyboard(self) -> Dict[str, Any]:
        # ... (Keep existing implementation)
        if self.use_mockup:
            s_dir = os.path.join(self.mockup_dir, "Storyboards")
            try:
                files = [f for f in os.listdir(s_dir) if f.endswith('.json')]; files.sort()
                if files:
                    with open(os.path.join(s_dir, files[0]), 'r', encoding='utf-8') as f: return json.load(f)
            except Exception: pass
            return {"description": "[No storyboard]"}
        else: # DB
            # ... (DB logic) ...
            return {"description": "[No DB storyboard]"}


    def get_npc(self, area: str, name: str) -> Optional[Dict[str, Any]]:
        # ... (Keep existing implementation)
        if self.use_mockup:
            npc_file = os.path.join(self.mockup_dir, "NPCs", f"{area.lower().replace(' ', '_')}.{name.lower().replace(' ', '_')}.json") # Example naming
            # A more robust way is to iterate through files in NPCs dir as before.
            npc_dir_path = os.path.join(self.mockup_dir, "NPCs")
            if os.path.exists(npc_dir_path):
                for filename in os.listdir(npc_dir_path):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(npc_dir_path, filename), 'r', encoding='utf-8') as f:
                                npc_data = json.load(f)
                                if npc_data.get('area','').lower() == area.lower() and \
                                   npc_data.get('name','').lower() == name.lower():
                                    if 'code' not in npc_data: npc_data['code'] = filename.replace('.json','')
                                    return npc_data
                        except Exception: pass
            return None
        else: # DB
            # ... (DB logic) ...
            return None

    def get_default_npc(self, area: str) -> Optional[Dict[str, Any]]:
        # ... (Keep existing implementation)
        if self.use_mockup:
            npc_dir = os.path.join(self.mockup_dir, "NPCs"); npcs_in_area = []
            if os.path.exists(npc_dir):
                for filename in os.listdir(npc_dir):
                    if filename.endswith('.json'):
                        try:
                            with open(os.path.join(npc_dir, filename), 'r', encoding='utf-8') as f: npc = json.load(f)
                            if npc.get('area', '').lower() == area.lower():
                                if 'code' not in npc: npc['code'] = filename.replace('.json', '')
                                npcs_in_area.append(npc)
                        except: pass
            if npcs_in_area: return sorted(npcs_in_area, key=lambda x: x.get('name', '').lower())[0]
            return None
        else: # DB
            # ... (DB logic) ...
            return None

    def list_npcs_by_area(self) -> List[Dict[str, str]]:
        # ... (Keep existing implementation)
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
                                    "name": data.get("name","Unknown"),
                                    "area": data.get("area","Unknown"),
                                    "role": data.get("role","Unknown")
                                })
                        except Exception: pass
            return sorted(npcs_list, key=lambda x: (x['area'].lower(), x['name'].lower()))
        else: # DB
            # ... (DB logic) ...
            return []


    # --- Conversation History (Unchanged for this request's scope) ---
    def save_conversation(self, player_id: str, npc_code: str, conversation_history: List[Dict[str, str]]) -> None:
        # ... (Keep existing implementation for saving full history for now) ...
        if not conversation_history or not player_id or not npc_code: return
        if self.use_mockup:
            p_dir = self.conversation_dir_template.format(player_id=player_id); os.makedirs(p_dir, exist_ok=True)
            file = os.path.join(p_dir, f"{npc_code}.json")
            try:
                with open(file, 'w', encoding='utf-8') as f: json.dump(conversation_history, f, indent=2)
            except Exception as e: print(f"Err saving convo {file}: {e}")
        else: # DB
            # ... (DB logic) ...
            pass


    def load_conversation(self, player_id: str, npc_code: str) -> List[Dict[str, str]]: 
        # ... (Keep existing implementation for loading full history for now) ...
        if not player_id or not npc_code: return []
        if self.use_mockup:
            file = os.path.join(self.conversation_dir_template.format(player_id=player_id), f"{npc_code}.json")
            if os.path.exists(file):
                try:
                    with open(file, 'r', encoding='utf-8') as f: return json.load(f)
                except Exception: return []
            return []
        else: # DB
            # ... (DB logic) ...
            return []

    # --- Inventory Management (Player Specific - UPDATED for Case-Insensitivity) ---
    def _clean_item_name(self, item_name: str) -> str:
        """Helper to standardize item names (lowercase, stripped)."""
        return str(item_name).strip().lower()

    def load_inventory(self, player_id: str) -> List[str]:
        """Loads player inventory. Items are assumed to be stored in lowercase."""
        if not player_id: return []
        inventory_list = []
        if self.use_mockup:
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            try:
                if not os.path.exists(inv_file):
                    with open(inv_file, 'w', encoding='utf-8') as f: json.dump([], f) # Create if not exists
                    return []
                with open(inv_file, 'r', encoding='utf-8') as f: 
                    loaded_data = json.load(f)
                    # Ensure it's a list and items are clean (should be if save_inventory is used)
                    inventory_list = sorted([self._clean_item_name(item) for item in loaded_data if item]) if isinstance(loaded_data, list) else []
            except Exception as e: 
                print(f"⚠️ Error loading mockup inventory {inv_file}: {e}. Returning empty list.")
                inventory_list = [] # Fallback to empty on error
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                # Assumes items in DB are already stored consistently (e.g., lowercase)
                cursor.execute("SELECT item_name FROM PlayerInventory WHERE player_id = %s ORDER BY item_name", (player_id,))
                inventory_list = [row[0] for row in cursor.fetchall()] # Assumes stored as lowercase
            except Exception as e: print(f"DB error loading inventory for {player_id}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        return sorted(list(set(inventory_list))) # Ensure unique and sorted

    def save_inventory(self, player_id: str, inventory_list: List[str]) -> None:
        """Saves player inventory. Ensures items are unique, lowercase, and sorted."""
        if not player_id: return
        # Clean, lowercase, unique, and sort items before saving
        cleaned_inventory = sorted(list(set(self._clean_item_name(item) for item in inventory_list if item and str(item).strip())))
        
        if self.use_mockup:
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            os.makedirs(os.path.dirname(inv_file), exist_ok=True)
            try:
                with open(inv_file, 'w', encoding='utf-8') as f: json.dump(cleaned_inventory, f, ensure_ascii=False, indent=2)
            except Exception as e: print(f"⚠️ Error saving mockup inventory to {inv_file}: {e}")
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
            except Exception as e: print(f"DB error saving inventory for {player_id}: {e}"); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def add_item_to_inventory(self, player_id: str, item_name: str, state: Optional[Dict[str, Any]] = None) -> bool:
        TF = TerminalFormatter; लोकल_स्टेट = state or {} # Use local copy
        if 'TerminalFormatter' in लोकल_स्टेट: TF = लोकल_स्टेट['TerminalFormatter']
        
        cleaned_item_name = self._clean_item_name(item_name)
        if not cleaned_item_name: print(f"{TF.RED}Error: Item name cannot be empty.{TF.RESET}"); return False
        if not player_id: print(f"{TF.RED}Error: Player ID required.{TF.RESET}"); return False

        current_inventory = self.load_inventory(player_id) # Loads cleaned items
        if cleaned_item_name not in current_inventory:
            current_inventory.append(cleaned_item_name)
            self.save_inventory(player_id, current_inventory) # Saves cleaned, sorted, unique list
            print(f"{TF.BRIGHT_GREEN}[Game System]: '{item_name.strip()}' added to your inventory! (as '{cleaned_item_name}'){TF.RESET}")
            if 'player_inventory' in लोकल_स्टेट: लोकल_स्टेट['player_inventory'] = self.load_inventory(player_id)
            return True
        else:
            print(f"{TF.DIM}'{item_name.strip()}' (as '{cleaned_item_name}') is already in your inventory.{TF.RESET}")
            return False

    def check_item_in_inventory(self, player_id: str, item_name: str) -> bool:
        cleaned_item_name = self._clean_item_name(item_name)
        if not cleaned_item_name or not player_id: return False
        inventory = self.load_inventory(player_id)
        return cleaned_item_name in inventory
        
    def remove_item_from_inventory(self, player_id: str, item_name: str, state: Optional[Dict[str, Any]] = None) -> bool:
        TF = TerminalFormatter; लोकल_स्टेट = state or {}
        if 'TerminalFormatter' in लोकल_स्टेट: TF = लोकल_स्टेट['TerminalFormatter']

        cleaned_item_name = self._clean_item_name(item_name)
        if not cleaned_item_name: print(f"{TF.RED}Error: Item name for removal cannot be empty.{TF.RESET}"); return False
        if not player_id: print(f"{TF.RED}Error: Player ID required for item removal.{TF.RESET}"); return False

        current_inventory = self.load_inventory(player_id)
        if cleaned_item_name in current_inventory:
            current_inventory.remove(cleaned_item_name)
            self.save_inventory(player_id, current_inventory)
            # Message now in command_processor for /give
            if 'player_inventory' in लोकल_स्टेट: लोकल_स्टेट['player_inventory'] = current_inventory
            return True
        return False

    # --- Player State & Credits Management ---
    def load_player_state(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Loads player state, defaulting credits to 220 for new players."""
        if not player_id: return None
        default_credits = 220 # Starting credits
        state_data = None

        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f: loaded_data = json.load(f)
                    state_data = {
                        'current_area': loaded_data.get('current_area'),
                        'current_npc_code': loaded_data.get('current_npc_code'),
                        'plot_flags': loaded_data.get('plot_flags', {}),
                        'credits': int(loaded_data.get('credits', default_credits)) # Ensure int, default
                    }
                except Exception as e: print(f"⚠️ Error loading state {state_file}: {e}")
            if not state_data: # File not found or error, create default
                state_data = {'current_area': None, 'current_npc_code': None, 'plot_flags': {}, 'credits': default_credits}
                self.save_player_state(player_id, state_data) # Save initial state
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT current_area, current_npc_code, plot_flags, credits FROM PlayerState WHERE player_id = %s", (player_id,))
                result = cursor.fetchone()
                if result:
                    state_data = {
                        'current_area': result.get('current_area'),
                        'current_npc_code': result.get('current_npc_code'),
                        'plot_flags': json.loads(result.get('plot_flags', '{}')) if result.get('plot_flags') else {},
                        'credits': int(result.get('credits', default_credits)) # Default if column is NULL
                    }
                else: # New player for DB
                    state_data = {'current_area': None, 'current_npc_code': None, 'plot_flags': {}, 'credits': default_credits}
                    # Save this initial state (including credits)
                    self.save_player_state(player_id, state_data) # This will insert new row
            except Exception as e: print(f"DB error loading state P:{player_id}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        return state_data

    def save_player_state(self, player_id: str, state_data: Dict[str, Any]) -> None:
        if not player_id or not state_data: return
        
        current_npc_val = state_data.get('current_npc') # Could be dict or None
        npc_code_to_save = current_npc_val.get('code') if isinstance(current_npc_val, dict) else None
        
        # Ensure credits are part of what's being saved
        credits_to_save = state_data.get('player_credits_cache', state_data.get('credits', 0)) # Prioritize cache

        data_to_save = {
            'current_area': state_data.get('current_area'),
            'current_npc_code': npc_code_to_save,
            'plot_flags': state_data.get('plot_flags', {}),
            'credits': int(credits_to_save) # Ensure it's an int
        }
        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            try:
                with open(state_file, 'w', encoding='utf-8') as f: json.dump(data_to_save, f, indent=2)
            except Exception as e: print(f"⚠️ Error saving state {state_file}: {e}")
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
                plot_flags_json = json.dumps(data_to_save['plot_flags'])
                values = (player_id, data_to_save['current_area'], data_to_save['current_npc_code'], plot_flags_json, data_to_save['credits'])
                cursor.execute(sql, values); conn.commit()
            except Exception as e: print(f"DB error saving state P:{player_id}: {e}"); conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def get_player_credits(self, player_id: str) -> int:
        """Retrieves current credits for a player, defaults to 220 if new."""
        player_state = self.load_player_state(player_id) # load_player_state handles defaulting
        return player_state.get('credits', 220) if player_state else 220

    def update_player_credits(self, player_id: str, amount_change: int, state_context: Dict[str, Any]) -> bool:
        """Updates player credits by amount_change. Returns True on success."""
        TF = state_context.get('TerminalFormatter', TerminalFormatter)
        current_credits = self.get_player_credits(player_id)
        new_credits = current_credits + amount_change

        if new_credits < 0:
            print(f"{TF.RED}[Game System]: Insufficient credits. You only have {current_credits} Credits.{TF.RESET}")
            return False

        # To save, we need to load the full player state, modify credits, then save state
        player_state = self.load_player_state(player_id)
        if not player_state: # Should not happen if get_player_credits worked
            player_state = {'player_id': player_id, 'credits': 0} # Create minimal state
        
        player_state['credits'] = new_credits
        if 'player_credits_cache' in state_context: # Update cache in passed state
            state_context['player_credits_cache'] = new_credits
        
        self.save_player_state(player_id, player_state) # Save the whole state dict

        if amount_change > 0:
            print(f"{TF.BRIGHT_GREEN}[Game System]: +{amount_change} Credits received! Total: {new_credits} Credits.{TF.RESET}")
        elif amount_change < 0:
            print(f"{TF.BRIGHT_YELLOW}[Game System]: {-amount_change} Credits spent. Remaining: {new_credits} Credits.{TF.RESET}")
        return True

    # --- DB Schema ---
    def ensure_db_schema(self):
        if self.use_mockup: return
        print("Ensuring database schema...")
        try:
            conn_test = self.connect(); conn_test.close()
            # ... (PlayerInventory, ConversationHistory table creation as before) ...
            self._ensure_table_exists(
                table_name="PlayerState",
                create_sql="""
                    CREATE TABLE IF NOT EXISTS PlayerState (
                        player_id VARCHAR(255) NOT NULL PRIMARY KEY,
                        current_area VARCHAR(255) NULL,
                        current_npc_code VARCHAR(255) NULL,
                        plot_flags JSON NULL,
                        credits INT NOT NULL DEFAULT 220, -- ADDED CREDITS
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """,
                check_column='credits' # Check if 'credits' column exists
            )
            # ... (PlayerProfiles table creation as before) ...
            print("DB schema check complete.")
        except Exception as e: print(f"Schema check failed: {e}")

    def _ensure_table_exists(self, table_name: str, create_sql: str, check_column: Optional[str] = None):
        # ... (Keep existing implementation, or slightly improved one from previous PAK) ...
        if self.use_mockup: return
        if not self.db_config or not self.db_config.get('database'): return
        conn = None; cursor = None
        try:
            conn = self.connect(); cursor = conn.cursor(); 
            cursor.execute("SHOW TABLES LIKE %s;", (table_name,))
            if not cursor.fetchone(): # Table does not exist
                print(f"Table '{table_name}' not found. Creating..."); cursor.execute(create_sql); conn.commit(); print(f"Table '{table_name}' created.")
            elif check_column: # Table exists, check if column exists
                cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s", 
                               (self.db_config['database'], table_name, check_column))
                if cursor.fetchone()[0] == 0:
                    print(f"⚠️ Warn: Table '{table_name}' exists but column '{check_column}' is MISSING. Manual schema update likely needed for existing DBs if this column is new.")
                    # Attempt to add it if simple (e.g. ALTER TABLE PlayerState ADD COLUMN credits INT NOT NULL DEFAULT 220;)
                    # This is risky for general auto-alter, better to instruct user or handle in migration script.
        except Exception as e: print(f"DB error for {table_name}: {e}")
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()


class MockConnection: # ... (keep as is) ...
    def __init__(self, mockup_dir): self.mockup_dir = mockup_dir; self._is_connected = True
    def cursor(self, dictionary=False): return MockCursor(self.mockup_dir, dictionary)
    def commit(self): pass 
    def rollback(self): pass 
    def close(self): self._is_connected = False
    def is_connected(self): return self._is_connected
    def start_transaction(self, **kwargs): pass 

class MockCursor: # ... (keep as is) ...
    def __init__(self, mockup_dir, dictionary=False): self.mockup_dir = mockup_dir; self.dictionary = dictionary; self.lastrowid = None; self._results = []; self._description = None
    def execute(self, query, params=None, multi=False): self._results = [] 
    def executemany(self, query, params_list=None): self._results = []
    def fetchone(self): return self._results.pop(0) if self._results else None
    def fetchall(self): results = self._results; self._results = []; return results
    def close(self): pass
    @property
    def description(self): return self._description
    @property
    def rowcount(self): return 0 

if __name__ == "__main__":
    # ... (Add tests for get_player_credits, update_player_credits) ...
    class TF: RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_YELLOW=""; BRIGHT_GREEN = ""; BRIGHT_CYAN = "";
    TerminalFormatter = TF
    test_dir = "_db_credits_test"
    os.makedirs(os.path.join(test_dir, "PlayerState"), exist_ok=True) # Ensure dir for state files

    db = DbManager(use_mockup=True, mockup_dir=test_dir)
    p_id = "CreditTester"
    test_state = {'TerminalFormatter': TerminalFormatter, 'player_credits_cache': 0}


    print(f"Initial credits for {p_id}: {db.get_player_credits(p_id)}") # Should default to 220
    assert db.get_player_credits(p_id) == 220

    db.update_player_credits(p_id, 50, test_state)
    print(f"Credits after +50: {db.get_player_credits(p_id)}")
    assert db.get_player_credits(p_id) == 270
    assert test_state['player_credits_cache'] == 270

    db.update_player_credits(p_id, -70, test_state)
    print(f"Credits after -70: {db.get_player_credits(p_id)}")
    assert db.get_player_credits(p_id) == 200

    print(f"Trying to spend 300 (should fail): {db.update_player_credits(p_id, -300, test_state)}")
    assert db.get_player_credits(p_id) == 200 # Should not change

    print("Case-insensitive item test:")
    db.add_item_to_inventory(p_id, "Test Item", test_state)
    db.add_item_to_inventory(p_id, "test item ", test_state) # Should be treated as same
    print(f"Inv: {db.load_inventory(p_id)}")
    assert len(db.load_inventory(p_id)) == 1
    assert db.check_item_in_inventory(p_id, "TeSt ItEm  ") == True
    db.remove_item_from_inventory(p_id, "tEsT iTeM", test_state)
    assert len(db.load_inventory(p_id)) == 0

    import shutil; shutil.rmtree(test_dir)
    print("DB Manager Credits & Case-Insensitive tests done.")
