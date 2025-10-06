# Path: db_manager.py
# Fully Implemented Player Profile methods and schema handling.

from dotenv import load_dotenv
import mysql.connector
import os
import sys
import json
from typing import List, Dict, Optional, Any, Set, Tuple # Tuple added
from datetime import datetime
import traceback
import copy # For deepcopy

try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    print("Warning (db_manager): terminal_formatter not found.")
    class TerminalFormatter:
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; BRIGHT_YELLOW=""; BRIGHT_GREEN = ""; BRIGHT_CYAN = ""; ITALIC = "";
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))

try:
    # Attempt to import the default profile structure
    from player_profile_manager import get_default_player_profile
except ImportError:
    print("Warning (db_manager): player_profile_manager not found. Using basic default profile.")
    def get_default_player_profile(): # Fallback definition
        return {
            "core_traits": {
                "curiosity": 5, "caution": 5, "empathy": 5, "skepticism": 5,
                "pragmatism": 5, "aggression": 3, "deception": 2, "honor": 5
            },
            "decision_patterns": [],
            "veil_perception": "neutral_curiosity",
            "interaction_style_summary": "Observant and typically polite.",
            "key_experiences_tags": [],
            "trust_levels": {"general": 5},
            "inferred_motivations": ["understand_the_veil_crisis", "survive"]
        }


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
            load_dotenv()
            self.db_config = {
                'host': os.environ.get('DB_HOST'), 'user': os.environ.get('DB_USER'),
                'password': os.environ.get('DB_PASSWORD'), 'database': os.environ.get('DB_NAME'),
                'port': int(os.environ.get('DB_PORT', 3306)),
                'connection_timeout': int(os.environ.get('DB_TIMEOUT', 10))
            }
        if self.use_mockup:
            os.makedirs(self.mockup_dir, exist_ok=True)
            for subdir_tmpl in [
                self.conversation_dir_template,
                self.player_state_file_template,
                self.player_profile_file_template
            ]:
                base_dir_path = os.path.dirname(subdir_tmpl.format(player_id="dummy").rstrip(os.sep))
                if base_dir_path:
                    os.makedirs(base_dir_path, exist_ok=True)
            for static_dir in ["NPCs", "Storyboards", "Locations"]:
                os.makedirs(os.path.join(self.mockup_dir, static_dir), exist_ok=True)
        elif self.db_config and self.db_config.get('host'):
            pass # print(f"DbManager: Configured for Real Database.")
        # else:
        # print("DbManager: No DB host configured and not in mockup mode. DB operations might fail if attempted.")


    def connect(self) -> Any:
        if self.use_mockup: return MockConnection(self.mockup_dir)
        else:
            if not self.db_config or not all([self.db_config.get('host'), self.db_config.get('user'), self.db_config.get('database')]):
                raise ValueError("Database configuration incomplete for real DB connection.")
            try:
                import mysql.connector
                return mysql.connector.connect(**self.db_config)
            except mysql.connector.Error as err:
                raise
            except Exception as e:
                raise


    # --- NPC / Storyboard Methods ---
    def get_storyboard(self) -> Dict[str, Any]:
        default_story = {"name": "Default Story", "description": "[No storyboard data found or loaded]"}
        if self.use_mockup:
            s_dir = os.path.join(self.mockup_dir, "Storyboards")
            try:
                if os.path.exists(s_dir):
                    files = [f for f in os.listdir(s_dir) if f.endswith('.json')]
                    files.sort()
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
        """Get NPC by area and name (existing)."""
        if self.use_mockup:
            npc_dir_path = os.path.join(self.mockup_dir, "NPCs")
            if os.path.exists(npc_dir_path):
                for filename in os.listdir(npc_dir_path):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(npc_dir_path, filename), 'r', encoding='utf-8') as f:
                                npc_data = json.load(f)
                            if npc_data.get('area','').strip().lower() == area.strip().lower() and \
                                    npc_data.get('name','').strip().lower() == name.strip().lower():
                                if 'code' not in npc_data or not npc_data['code']:
                                    npc_data['code'] = filename.replace('.json','')
                                return npc_data
                        except Exception: pass
            return None
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                query = "SELECT * FROM NPCs WHERE LOWER(area) = LOWER(%s) AND LOWER(name) = LOWER(%s) LIMIT 1"
                cursor.execute(query, (area.strip(), name.strip()))
                return cursor.fetchone()
            except Exception as e:
                return None
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def get_npc_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get NPC by unique code (new helper)."""
        if not code:
            return None
        if self.use_mockup:
            npc_dir_path = os.path.join(self.mockup_dir, "NPCs")
            if os.path.exists(npc_dir_path):
                for filename in os.listdir(npc_dir_path):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(npc_dir_path, filename), 'r', encoding='utf-8') as f:
                                npc_data = json.load(f)
                            if npc_data.get('code', filename.replace('.json','')) == code:
                                return npc_data
                        except Exception: pass
            return None
        else:
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                query = "SELECT * FROM NPCs WHERE code = %s LIMIT 1"
                cursor.execute(query, (code,))
                return cursor.fetchone()
            except Exception as e:
                return None
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        if self.use_mockup:
            npc_dir_path = os.path.join(self.mockup_dir, "NPCs")
            if os.path.exists(npc_dir_path):
                for filename in os.listdir(npc_dir_path):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(npc_dir_path, filename), 'r', encoding='utf-8') as f:
                                npc_data = json.load(f)
                            if npc_data.get('area','').strip().lower() == area.strip().lower() and \
                                    npc_data.get('name','').strip().lower() == name.strip().lower():
                                if 'code' not in npc_data or not npc_data['code']:
                                    npc_data['code'] = filename.replace('.json','')
                                return npc_data
                        except Exception: pass
            return None
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
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
            if npcs_in_area: return sorted(npcs_in_area, key=lambda x: x.get('name', '').lower())[0]
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

    def get_areas(self) -> List[str]:
        """Get a list of unique area names from locations."""
        if self.use_mockup:
            location_dir = os.path.join(self.mockup_dir, "Locations")
            areas = set()
            if os.path.exists(location_dir):
                for filename in os.listdir(location_dir):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(location_dir, filename), 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if 'name' in data and data['name']:
                                    areas.add(data['name'].strip())
                        except Exception:
                            pass
            return sorted(list(areas))
        else:  # DB
            conn = None
            cursor = None
            try:
                conn = self.connect()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM Locations WHERE name IS NOT NULL AND name != '' ORDER BY name")
                return [row[0] for row in cursor.fetchall()]
            except Exception as e:
                return []
            finally:
                if cursor:
                    cursor.close()
                if conn and conn.is_connected():
                    conn.close()

    # --- Location Methods ---
    def get_location(self, location_id: str) -> Optional[Dict[str, Any]]:
        if self.use_mockup:
            location_dir_path = os.path.join(self.mockup_dir, "Locations")
            location_file = os.path.join(location_dir_path, f"{location_id}.json")
            if os.path.exists(location_file):
                try:
                    with open(location_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    pass
            return None
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                query = "SELECT * FROM Locations WHERE id = %s LIMIT 1"
                cursor.execute(query, (location_id,))
                return cursor.fetchone()
            except Exception as e:
                return None
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def get_location_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        if self.use_mockup:
            location_dir_path = os.path.join(self.mockup_dir, "Locations")
            if os.path.exists(location_dir_path):
                for filename in os.listdir(location_dir_path):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(location_dir_path, filename), 'r', encoding='utf-8') as f:
                                location_data = json.load(f)
                            if location_data.get('name','').strip().lower() == name.strip().lower():
                                return location_data
                        except Exception: pass
            return None
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                query = "SELECT * FROM Locations WHERE LOWER(name) = LOWER(%s) LIMIT 1"
                cursor.execute(query, (name.strip(),))
                return cursor.fetchone()
            except Exception as e:
                return None
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def list_locations(self) -> List[Dict[str, str]]:
        locations_list = []
        if self.use_mockup:
            location_dir = os.path.join(self.mockup_dir, "Locations")
            if os.path.exists(location_dir):
                for filename in os.listdir(location_dir):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(location_dir, filename), 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                locations_list.append({
                                    "id": data.get("id", filename.replace(".json","")),
                                    "name": data.get("name","Unknown Location"),
                                    "area_type": data.get("area_type","Unknown Type"),
                                    "access_level": data.get("access_level","Unknown Access")
                                })
                        except Exception: pass
            return sorted(locations_list, key=lambda x: x.get('name','').lower())
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id, name, area_type, access_level FROM Locations ORDER BY name")
                return cursor.fetchall()
            except Exception as e:
                return []
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    # --- Conversation History ---
    def save_conversation(self, player_id: str, npc_code: str, conversation_history: List[Dict[str, str]]) -> None:
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
                sql = """
                      INSERT INTO ConversationHistory (player_id, npc_code, history, last_updated)
                      VALUES (%s, %s, %s, NOW())
                          ON DUPLICATE KEY UPDATE history = VALUES(history), last_updated = NOW(); \
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
                except Exception: return []
            return []
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

    def get_conversation_history(self, player_id: str, npc_name: str = None) -> List[Dict[str, Any]]:
        """Get conversation history for a player, optionally filtered by NPC."""
        if not player_id: return []
        
        if self.use_mockup:
            conversations = []
            player_conv_dir = self.conversation_dir_template.format(player_id=player_id)
            if os.path.exists(player_conv_dir):
                try:
                    for filename in os.listdir(player_conv_dir):
                        if filename.endswith('.json'):
                            npc_code = filename[:-5]  # Remove .json extension
                            # Filter by NPC if specified
                            if npc_name and npc_code != npc_name:
                                continue
                            file_path = os.path.join(player_conv_dir, filename)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                history = json.load(f)
                                if history:
                                    conversations.append({
                                        'npc_code': npc_code,
                                        'history': history,
                                        'last_updated': os.path.getmtime(file_path)
                                    })
                except Exception as e:
                    print(f"Error getting conversation history for {player_id}: {e}")
            return conversations
        else:  # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                if npc_name:
                    cursor.execute("""
                        SELECT npc_code, history, last_updated 
                        FROM ConversationHistory 
                        WHERE player_id = %s AND npc_code = %s
                        ORDER BY last_updated DESC
                    """, (player_id, npc_name))
                else:
                    cursor.execute("""
                        SELECT npc_code, history, last_updated 
                        FROM ConversationHistory 
                        WHERE player_id = %s 
                        ORDER BY last_updated DESC
                    """, (player_id,))
                results = cursor.fetchall()
                conversations = []
                for row in results:
                    npc_code, history_json, last_updated = row
                    history = json.loads(history_json) if history_json else []
                    conversations.append({
                        'npc_code': npc_code,
                        'history': history,
                        'last_updated': last_updated.isoformat() if last_updated else None
                    })
                return conversations
            except Exception as e:
                print(f"DB error getting conversation history for {player_id}: {e}")
                return []
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def clear_conversations(self, player_id: str) -> bool:
        """Clear all conversation history for a player."""
        if not player_id: return False
        
        if self.use_mockup:
            try:
                player_conv_dir = self.conversation_dir_template.format(player_id=player_id)
                if os.path.exists(player_conv_dir):
                    import shutil
                    shutil.rmtree(player_conv_dir)
                    os.makedirs(player_conv_dir, exist_ok=True)
                return True
            except Exception as e:
                print(f"Error clearing conversation history for {player_id}: {e}")
                return False
        else:  # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                cursor.execute("DELETE FROM ConversationHistory WHERE player_id = %s", (player_id,))
                conn.commit()
                return True
            except Exception as e:
                print(f"DB error clearing conversation history for {player_id}: {e}")
                if conn: conn.rollback()
                return False
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def get_player_storage_info(self, player_id: str) -> Dict[str, Any]:
        """Get detailed storage information for a player."""
        if not player_id:
            return {}
        
        info = {
            'player_id': player_id,
            'conversations': {
                'total_size_kb': 0,
                'npc_count': 0,
                'npcs_talked_to': [],
                'conversation_details': []
            },
            'profile': {
                'size_kb': 0,
                'exists': False
            },
            'inventory': {
                'size_kb': 0,
                'item_count': 0
            },
            'total_storage_kb': 0
        }
        
        if self.use_mockup:
            # Get conversation info
            player_conv_dir = self.conversation_dir_template.format(player_id=player_id)
            if os.path.exists(player_conv_dir):
                try:
                    total_conv_size = 0
                    for filename in os.listdir(player_conv_dir):
                        if filename.endswith('.json'):
                            npc_code = filename[:-5]
                            file_path = os.path.join(player_conv_dir, filename)
                            file_size = os.path.getsize(file_path)
                            total_conv_size += file_size
                            
                            # Get conversation length
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    history = json.load(f)
                                    message_count = len(history) if isinstance(history, list) else 0
                            except:
                                message_count = 0
                            
                            info['conversations']['npcs_talked_to'].append(npc_code)
                            info['conversations']['conversation_details'].append({
                                'npc_code': npc_code,
                                'size_kb': round(file_size / 1024, 2),
                                'message_count': message_count,
                                'last_modified': os.path.getmtime(file_path)
                            })
                    
                    info['conversations']['total_size_kb'] = round(total_conv_size / 1024, 2)
                    info['conversations']['npc_count'] = len(info['conversations']['npcs_talked_to'])
                except Exception as e:
                    print(f"Error getting conversation info for {player_id}: {e}")
            
            # Get profile info
            profile_file = self.player_profile_file_template.format(player_id=player_id)
            if os.path.exists(profile_file):
                try:
                    profile_size = os.path.getsize(profile_file)
                    info['profile']['size_kb'] = round(profile_size / 1024, 2)
                    info['profile']['exists'] = True
                except Exception as e:
                    print(f"Error getting profile info for {player_id}: {e}")
            
            # Get inventory info
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            if os.path.exists(inv_file):
                try:
                    inv_size = os.path.getsize(inv_file)
                    info['inventory']['size_kb'] = round(inv_size / 1024, 2)
                    
                    # Get item count
                    with open(inv_file, 'r', encoding='utf-8') as f:
                        inventory = json.load(f)
                        info['inventory']['item_count'] = len(inventory) if isinstance(inventory, list) else 0
                except Exception as e:
                    print(f"Error getting inventory info for {player_id}: {e}")
        
        else:  # DB mode
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                
                # Get conversation info
                cursor.execute("""
                    SELECT npc_code, history, last_updated,
                           LENGTH(history) as size_bytes
                    FROM ConversationHistory 
                    WHERE player_id = %s 
                    ORDER BY last_updated DESC
                """, (player_id,))
                conv_results = cursor.fetchall()
                
                total_conv_size = 0
                for row in conv_results:
                    npc_code, history_json, last_updated, size_bytes = row
                    size_bytes = size_bytes or 0
                    total_conv_size += size_bytes
                    
                    # Count messages
                    try:
                        history = json.loads(history_json) if history_json else []
                        message_count = len(history) if isinstance(history, list) else 0
                    except:
                        message_count = 0
                    
                    info['conversations']['npcs_talked_to'].append(npc_code)
                    info['conversations']['conversation_details'].append({
                        'npc_code': npc_code,
                        'size_kb': round(size_bytes / 1024, 2),
                        'message_count': message_count,
                        'last_modified': last_updated.isoformat() if last_updated else None
                    })
                
                info['conversations']['total_size_kb'] = round(total_conv_size / 1024, 2)
                info['conversations']['npc_count'] = len(info['conversations']['npcs_talked_to'])
                
                # Get profile info
                cursor.execute("SELECT LENGTH(profile_data) FROM PlayerProfiles WHERE player_id = %s", (player_id,))
                profile_result = cursor.fetchone()
                if profile_result and profile_result[0]:
                    info['profile']['size_kb'] = round(profile_result[0] / 1024, 2)
                    info['profile']['exists'] = True
                
                # Get inventory info (approximate)
                cursor.execute("SELECT COUNT(*), GROUP_CONCAT(item_name) FROM PlayerInventory WHERE player_id = %s", (player_id,))
                inv_result = cursor.fetchone()
                if inv_result and inv_result[0]:
                    item_count = inv_result[0]
                    items_text = inv_result[1] or ""
                    info['inventory']['item_count'] = item_count
                    info['inventory']['size_kb'] = round(len(items_text.encode('utf-8')) / 1024, 2)
                
            except Exception as e:
                print(f"DB error getting storage info for {player_id}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        
        # Calculate total storage
        info['total_storage_kb'] = round(
            info['conversations']['total_size_kb'] + 
            info['profile']['size_kb'] + 
            info['inventory']['size_kb'], 2
        )
        
        return info

    def get_all_conversations_for_analysis(self, player_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a player formatted for LLM analysis."""
        if not player_id:
            return []
        
        conversations = []
        
        if self.use_mockup:
            player_conv_dir = self.conversation_dir_template.format(player_id=player_id)
            if os.path.exists(player_conv_dir):
                try:
                    for filename in os.listdir(player_conv_dir):
                        if filename.endswith('.json'):
                            npc_code = filename[:-5]
                            file_path = os.path.join(player_conv_dir, filename)
                            
                            with open(file_path, 'r', encoding='utf-8') as f:
                                history = json.load(f)
                                if history and isinstance(history, list):
                                    conversations.append({
                                        'npc_code': npc_code,
                                        'history': history,
                                        'last_modified': os.path.getmtime(file_path)
                                    })
                except Exception as e:
                    print(f"Error getting conversations for analysis for {player_id}: {e}")
        else:  # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                cursor.execute("""
                    SELECT npc_code, history, last_updated 
                    FROM ConversationHistory 
                    WHERE player_id = %s 
                    ORDER BY last_updated ASC
                """, (player_id,))
                results = cursor.fetchall()
                
                for row in results:
                    npc_code, history_json, last_updated = row
                    if history_json:
                        try:
                            history = json.loads(history_json)
                            if history and isinstance(history, list):
                                conversations.append({
                                    'npc_code': npc_code,
                                    'history': history,
                                    'last_modified': last_updated.isoformat() if last_updated else None
                                })
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"DB error getting conversations for analysis for {player_id}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        
        return conversations

    def save_conversation_analysis(self, player_id: str, analysis: str) -> bool:
        """Save LLM conversation analysis for a player."""
        if not player_id or not analysis:
            return False
        
        if self.use_mockup:
            try:
                analysis_dir = os.path.join(self.mockup_dir, "ConversationAnalysis")
                os.makedirs(analysis_dir, exist_ok=True)
                analysis_file = os.path.join(analysis_dir, f"{player_id}_analysis.txt")
                
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    f.write(f"Analysis generated on: {datetime.now().isoformat()}\n")
                    f.write("="*80 + "\n\n")
                    f.write(analysis)
                return True
            except Exception as e:
                print(f"Error saving conversation analysis for {player_id}: {e}")
                return False
        else:  # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                sql = """
                    INSERT INTO ConversationAnalysis (player_id, analysis, created_at)
                    VALUES (%s, %s, NOW())
                    ON DUPLICATE KEY UPDATE 
                        analysis = VALUES(analysis), 
                        created_at = NOW()
                """
                cursor.execute(sql, (player_id, analysis))
                conn.commit()
                return True
            except Exception as e:
                print(f"DB error saving conversation analysis for {player_id}: {e}")
                if conn: conn.rollback()
                return False
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    def get_conversation_analysis(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get saved conversation analysis for a player."""
        if not player_id:
            return None
        
        if self.use_mockup:
            try:
                analysis_file = os.path.join(self.mockup_dir, "ConversationAnalysis", f"{player_id}_analysis.txt")
                if os.path.exists(analysis_file):
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return {
                        'player_id': player_id,
                        'analysis': content,
                        'created_at': os.path.getmtime(analysis_file)
                    }
            except Exception as e:
                print(f"Error getting conversation analysis for {player_id}: {e}")
            return None
        else:  # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                cursor.execute("""
                    SELECT analysis, created_at 
                    FROM ConversationAnalysis 
                    WHERE player_id = %s
                """, (player_id,))
                result = cursor.fetchone()
                
                if result:
                    analysis, created_at = result
                    return {
                        'player_id': player_id,
                        'analysis': analysis,
                        'created_at': created_at.isoformat() if created_at else None
                    }
            except Exception as e:
                print(f"DB error getting conversation analysis for {player_id}: {e}")
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        
        return None

    # --- Inventory Management (Player Specific) ---
    def _clean_item_name(self, item_name: str) -> str:
        return str(item_name).strip().lower()

    def load_inventory(self, player_id: str) -> List[str]:
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
                inventory_list_cleaned = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error loading inventory for {player_id}: {e}{TerminalFormatter.RESET}")
                pass
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        return inventory_list_cleaned

    def save_inventory(self, player_id: str, inventory_list: List[str]) -> None:
        if not player_id: return
        cleaned_inventory = sorted(list(set(self._clean_item_name(item) for item in inventory_list if item and str(item).strip())))

        if self.use_mockup:
            inv_file = self.inventory_file_path_template.format(player_id=player_id)
            os.makedirs(os.path.dirname(inv_file), exist_ok=True)
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
        TF = TerminalFormatter;
        if game_state and 'TerminalFormatter' in game_state: TF = game_state['TerminalFormatter']

        cleaned_item_name = self._clean_item_name(item_name)
        if not cleaned_item_name: print(f"{TF.RED}Error: Item name cannot be empty.{TF.RESET}"); return False
        if not player_id: print(f"{TF.RED}Error: Player ID required.{TF.RESET}"); return False

        current_inventory = self.load_inventory(player_id)
        if cleaned_item_name not in current_inventory:
            current_inventory.append(cleaned_item_name)
            self.save_inventory(player_id, current_inventory)
            print(f"{TF.BRIGHT_GREEN}[Game System]: '{item_name.strip()}' added to your inventory! (as '{cleaned_item_name}'){TF.RESET}")
            if game_state and 'player_inventory' in game_state:
                game_state['player_inventory'] = self.load_inventory(player_id)
            return True
        else:
            # print(f"{TF.DIM}'{item_name.strip()}' (as '{cleaned_item_name}') is already in your inventory.{TF.RESET}")
            return False

    def find_item_by_partial_name(self, player_id: str, partial_name: str) -> str:
        """Find an item in inventory by partial name. Returns exact name if unique match found, empty string otherwise."""
        cleaned_partial = self._clean_item_name(partial_name)
        if not cleaned_partial or not player_id: 
            return ""
        
        inventory = self.load_inventory(player_id)
        matches = [item for item in inventory if cleaned_partial in item]
        
        # Return exact match if found
        if cleaned_partial in inventory:
            return cleaned_partial
        
        # Return unique partial match
        if len(matches) == 1:
            return matches[0]
        
        # No match or multiple matches
        return ""

    def check_item_in_inventory(self, player_id: str, item_name: str) -> bool:
        cleaned_item_name = self._clean_item_name(item_name)
        if not cleaned_item_name or not player_id: return False
        inventory = self.load_inventory(player_id)
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
            if game_state and 'player_inventory' in game_state:
                game_state['player_inventory'] = current_inventory
            return True
        return False

    # --- Player State & Credits Management ---
    def load_player_state(self, player_id: str) -> Dict[str, Any]:
        default_credits = 220
        default_state_data = {'current_area': None, 'current_npc_code': None, 'plot_flags': {}, 'credits': default_credits}
        if not player_id: return copy.deepcopy(default_state_data)

        loaded_state_data = None
        if self.use_mockup:
            state_file = self.player_state_file_template.format(player_id=player_id)
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f: loaded_raw = json.load(f)
                    loaded_state_data = {
                        'current_area': loaded_raw.get('current_area'),
                        'current_npc_code': loaded_raw.get('current_npc_code'),
                        'plot_flags': loaded_raw.get('plot_flags', {}),
                        'credits': int(loaded_raw.get('credits', default_credits))
                    }
                except Exception as e:
                    # print(f"{TerminalFormatter.YELLOW}Warning: Error loading state file {state_file}: {e}. Using defaults.{TerminalFormatter.RESET}")
                    pass
            if not loaded_state_data:
                self.save_player_state(player_id, default_state_data)
                return copy.deepcopy(default_state_data)
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
                else:
                    self.save_player_state(player_id, default_state_data)
                    return copy.deepcopy(default_state_data)
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error loading state for P:{player_id}: {e}{TerminalFormatter.RESET}")
                return copy.deepcopy(default_state_data)
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        return loaded_state_data if loaded_state_data else copy.deepcopy(default_state_data)

    def save_player_state(self, player_id: str, state_data: Dict[str, Any]) -> None:
        if not player_id or not state_data: return

        current_npc_val = state_data.get('current_npc')
        npc_code_to_save = current_npc_val.get('code') if isinstance(current_npc_val, dict) else state_data.get('current_npc_code')
        credits_to_save = state_data.get('player_credits_cache', state_data.get('credits', 0)) # Prioritize cache
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
                                               plot_flags = VALUES(plot_flags), credits = VALUES(credits), last_seen = NOW(); \
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
        player_state = self.load_player_state(player_id)
        return player_state.get('credits', 220)

    def update_player_credits(self, player_id: str, amount_change: int, game_state_context: Dict[str, Any]) -> bool:
        TF = game_state_context.get('TerminalFormatter', TerminalFormatter)
        current_credits = self.get_player_credits(player_id)
        new_credits = current_credits + amount_change
        if new_credits < 0: return False
        player_state = self.load_player_state(player_id)
        player_state['credits'] = new_credits
        self.save_player_state(player_id, player_state)
        if 'player_credits_cache' in game_state_context:
            game_state_context['player_credits_cache'] = new_credits
        return True

    # --- Player Profile Management (IMPLEMENTED) ---
    def load_player_profile(self, player_id: str) -> Dict[str, Any]:
        default_profile = get_default_player_profile()
        if not player_id:
            return copy.deepcopy(default_profile)

        profile_data = None
        if self.use_mockup:
            profile_file = self.player_profile_file_template.format(player_id=player_id)
            if os.path.exists(profile_file):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        loaded_data = json.load(f)
                    profile_data = copy.deepcopy(default_profile)
                    profile_data.update(loaded_data)
                except Exception as e:
                    # print(f"{TerminalFormatter.YELLOW}Warning: Error loading profile file {profile_file}: {e}. Using defaults.{TerminalFormatter.RESET}")
                    profile_data = copy.deepcopy(default_profile)
            else:
                self.save_player_profile(player_id, default_profile) # Save default if file doesn't exist
                return copy.deepcopy(default_profile)
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT profile_data FROM PlayerProfiles WHERE player_id = %s", (player_id,))
                result = cursor.fetchone()
                if result and result.get('profile_data'):
                    loaded_db_data = json.loads(result['profile_data']) if isinstance(result['profile_data'], str) else result['profile_data']
                    profile_data = copy.deepcopy(default_profile)
                    profile_data.update(loaded_db_data)
                else:
                    self.save_player_profile(player_id, default_profile) # Save default if no DB record
                    return copy.deepcopy(default_profile)
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error loading profile for P:{player_id}: {e}{TerminalFormatter.RESET}")
                return copy.deepcopy(default_profile)
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()
        return profile_data if profile_data else copy.deepcopy(default_profile)

    def save_player_profile(self, player_id: str, profile_data: Dict[str, Any]) -> None:
        if not player_id or not profile_data:
            return

        complete_profile_to_save = copy.deepcopy(get_default_player_profile())
        complete_profile_to_save.update(profile_data)

        if self.use_mockup:
            profile_file = self.player_profile_file_template.format(player_id=player_id)
            os.makedirs(os.path.dirname(profile_file), exist_ok=True)
            try:
                with open(profile_file, 'w', encoding='utf-8') as f:
                    json.dump(complete_profile_to_save, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"{TerminalFormatter.YELLOW}Warning (save_player_profile): Error saving profile to {profile_file}: {e}{TerminalFormatter.RESET}")
        else: # DB
            conn = None; cursor = None
            try:
                conn = self.connect(); cursor = conn.cursor()
                profile_json = json.dumps(complete_profile_to_save)
                sql = """
                      INSERT INTO PlayerProfiles (player_id, profile_data, last_updated)
                      VALUES (%s, %s, NOW())
                          ON DUPLICATE KEY UPDATE profile_data = VALUES(profile_data), last_updated = NOW(); \
                      """
                cursor.execute(sql, (player_id, profile_json))
                conn.commit()
            except Exception as e:
                # print(f"{TerminalFormatter.RED}DB error saving profile for P:{player_id}: {e}{TerminalFormatter.RESET}")
                if conn: conn.rollback()
            finally:
                if cursor: cursor.close()
                if conn and conn.is_connected(): conn.close()

    # --- Database Reset Methods ---
    def reset_database(self):
        """Reset the entire database by clearing all player data."""
        if self.use_mockup:
            self._reset_mockup_database()
        else:
            self._reset_real_database()
    
    def _reset_mockup_database(self):
        """Reset mockup database by deleting all player data files."""
        import shutil
        
        # Remove player-specific directories and files
        dirs_to_clear = [
            os.path.join(self.mockup_dir, "ConversationHistory"),
            os.path.join(self.mockup_dir, "PlayerState"),
            os.path.join(self.mockup_dir, "PlayerProfiles")
        ]
        
        for dir_path in dirs_to_clear:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                os.makedirs(dir_path, exist_ok=True)
        
        # Remove inventory files
        try:
            for file in os.listdir(self.mockup_dir):
                if file.endswith("_inventory.json"):
                    os.remove(os.path.join(self.mockup_dir, file))
        except FileNotFoundError:
            # Directory doesn't exist, nothing to clean
            pass
    
    def _reset_real_database(self):
        """Reset real database by truncating all player data tables."""
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Truncate all player data tables
            tables_to_truncate = [
                "PlayerState",
                "PlayerInventory", 
                "ConversationHistory",
                "PlayerProfiles",
                "NPCs"
            ]
            
            for table in tables_to_truncate:
                try:
                    cursor.execute(f"TRUNCATE TABLE {table}")
                except Exception as e:
                    print(f"Warning: Could not truncate table {table}: {e}")
            
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn and conn.is_connected():
                conn.close()
    
    def reload_data(self):
        """Reload NPC and story data from files."""
        # This method doesn't need to do anything special since NPCs and storyboards
        # are loaded dynamically from files. The caching mechanisms will pick up
        # any file changes on the next access.
        pass

    # --- DB Schema ---
    def ensure_db_schema(self):
        if self.use_mockup: return
        try:
            conn_test = self.connect()
            conn_test.close()

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
                check_column='credits'
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
            self._ensure_table_exists(
                table_name="PlayerProfiles",
                create_sql="""
                           CREATE TABLE IF NOT EXISTS PlayerProfiles (
                                                                         player_id VARCHAR(255) NOT NULL PRIMARY KEY,
                               profile_data JSON NOT NULL,
                               last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                               FOREIGN KEY (player_id) REFERENCES PlayerState(player_id) ON DELETE CASCADE
                               ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                           """,
                check_column='profile_data'
            )
            # print(f"{TerminalFormatter.DIM}DB schema check complete.{TerminalFormatter.RESET}")
        except Exception as e:
            print(f"{TerminalFormatter.RED}Database schema check/ensure failed: {e}{TerminalFormatter.RESET}")
            print(f"{TerminalFormatter.YELLOW}Ensure DB is configured and accessible, or run in --mockup mode.{TerminalFormatter.RESET}")


    def _ensure_table_exists(self, table_name: str, create_sql: str, check_column: Optional[str] = None):
        if self.use_mockup: return
        if not self.db_config or not self.db_config.get('database'): return
        conn = None; cursor = None
        try:
            conn = self.connect(); cursor = conn.cursor();
            cursor.execute("SHOW TABLES LIKE %s;", (table_name,))
            if not cursor.fetchone():
                # print(f"{TerminalFormatter.DIM}Table '{table_name}' not found. Creating...{TerminalFormatter.RESET}")
                for statement in create_sql.split(';'):
                    if statement.strip(): cursor.execute(statement)
                conn.commit()
                # print(f"{TerminalFormatter.GREEN}Table '{table_name}' created.{TerminalFormatter.RESET}")
            elif check_column:
                cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
                               (self.db_config['database'], table_name, check_column))
                if cursor.fetchone()[0] == 0:
                    print(f"{TerminalFormatter.YELLOW}⚠️ Warning: Table '{table_name}' exists but crucial column '{check_column}' is MISSING.{TerminalFormatter.RESET}")
                    print(f"{TerminalFormatter.YELLOW}   Manual schema update or reset might be needed if this is an existing database.{TerminalFormatter.RESET}")
        except Exception as e:
            # print(f"{TerminalFormatter.RED}DB error ensuring table '{table_name}': {e}{TerminalFormatter.RESET}")
            pass
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
    def start_transaction(self, **kwargs): pass

class MockCursor:
    def __init__(self, mockup_dir, dictionary=False):
        self.mockup_dir = mockup_dir
        self.dictionary = dictionary
        self.lastrowid = None
        self._results: List[Any] = []
        self._description: Optional[Tuple[Any, ...]] = None
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
    # This ensures TerminalFormatter is available if db_manager.py is run directly
    class TFGlobal: RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_YELLOW=""; BRIGHT_GREEN = ""; BRIGHT_CYAN = ""; ITALIC = "";
    TerminalFormatter = TFGlobal

    print("--- DbManager Self-Tests (with Profile) ---")
    test_dir = "_db_manager_selftest_profile_full" # New dir to avoid conflict with prior partial tests
    if os.path.exists(test_dir): import shutil; shutil.rmtree(test_dir)
    os.makedirs(os.path.join(test_dir, "PlayerState"), exist_ok=True)
    os.makedirs(os.path.join(test_dir, "PlayerProfiles"), exist_ok=True)
    os.makedirs(os.path.join(test_dir, "PlayerInventory"), exist_ok=True) # Though inv uses player_id directly in filename
    os.makedirs(os.path.join(test_dir, "NPCs"), exist_ok=True)
    os.makedirs(os.path.join(test_dir, "Storyboards"), exist_ok=True)


    db = DbManager(use_mockup=True, mockup_dir=test_dir)
    p_id = "TestPlayerFullDB123"
    game_state_sim = {'TerminalFormatter': TerminalFormatter, 'player_credits_cache': 0, 'player_inventory': []}

    # Test Player State (briefly, ensures it still works alongside profile)
    print(f"Initial credits for {p_id} (via PlayerState): {db.get_player_credits(p_id)}")
    assert db.get_player_credits(p_id) == 220, "Default credits should be 220 from PlayerState"

    # Test Player Profile Load/Save
    print(f"Loading initial profile for {p_id}...")
    profile1 = db.load_player_profile(p_id)
    print(f"Initial profile (should be default): {json.dumps(profile1, indent=2)}")
    default_test_profile = get_default_player_profile()
    assert profile1 == default_test_profile, f"Initial profile does not match default. Got: {profile1}"

    profile1["core_traits"]["curiosity"] = 8
    profile1["key_experiences_tags"].append("discovered_ancient_ruins")
    db.save_player_profile(p_id, profile1)
    print(f"Saved modified profile: {json.dumps(profile1, indent=2)}")

    profile2 = db.load_player_profile(p_id)
    print(f"Reloaded profile: {json.dumps(profile2, indent=2)}")
    assert profile2["core_traits"]["curiosity"] == 8
    assert "discovered_ancient_ruins" in profile2["key_experiences_tags"]
    assert profile2["veil_perception"] == default_test_profile["veil_perception"], "Unchanged fields should remain default."


    # Test that PlayerState and PlayerProfile are distinct but linked by player_id
    player_state_data = db.load_player_state(p_id)
    assert player_state_data['credits'] == 220 # Should still be default from PlayerState init

    # Test saving a partial profile - should merge with default
    partial_profile_update = {"interaction_style_summary": "Very direct and sometimes blunt."}
    db.save_player_profile(p_id, partial_profile_update)
    profile3 = db.load_player_profile(p_id)
    print(f"Profile after saving partial update: {json.dumps(profile3, indent=2)}")
    assert profile3["interaction_style_summary"] == "Very direct and sometimes blunt."
    assert profile3["core_traits"]["caution"] == default_test_profile["core_traits"]["caution"] # Check a trait that wasn't in partial update


    # Clean up test directory
    if os.path.exists(test_dir): import shutil; shutil.rmtree(test_dir)
    print("--- DbManager Self-Tests Done (Full Profile Logic) ---")