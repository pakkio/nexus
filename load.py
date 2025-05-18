# Path: load.py
# Updated Version with corrected NPC parser

import os
import mysql.connector
import time
import json
import argparse
from datetime import datetime
import traceback

try:
    from dotenv import load_dotenv
    # print("Loading environment variables from .env file...") # Less verbose
    load_dotenv()
    # print("Environment variables loaded (if .env file exists).")
except ImportError:
    print("python-dotenv not found. Skipping .env file loading.")
    def load_dotenv(): pass

class TerminalFormatter:
    DIM = ""; RESET = ""; YELLOW = ""; RED = ""; GREEN = ""; BOLD = "";
    # Add other colors if your script uses them directly here, e.g. BRIGHT_CYAN
    BRIGHT_CYAN = ""
    @staticmethod
    def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))

def parse_storyboard(filepath):
    # ... (keep your existing parse_storyboard or the one from previous correct PAK) ...
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        name = ""
        description_lines = []
        themes_lines = []
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("Name:"):
                name = line.replace("Name:", "").strip()
                current_section = "name"
            elif line.startswith("Description:"):
                current_section = "description"
            elif line.startswith("Temi:") or line.startswith("Themes:"):
                current_section = "themes"
            elif current_section == "description":
                description_lines.append(line)
            elif current_section == "themes":
                themes_lines.append(line)
        description = "\n".join(description_lines).strip()
        if themes_lines:
            description += "\n\nTemi:\n" + "\n".join(themes_lines).strip()
        if not name and not description:
            print(f"{TerminalFormatter.YELLOW}Warning: Storyboard file '{filepath}' seems empty.{TerminalFormatter.RESET}")
        return name, description
    except FileNotFoundError: print(f"{TerminalFormatter.RED}Error: Storyboard file not found: '{filepath}'{TerminalFormatter.RESET}"); raise
    except Exception as e: print(f"{TerminalFormatter.RED}Error parsing storyboard '{filepath}': {e}{TerminalFormatter.RESET}"); raise

def parse_npc_file(filepath):
    """Parses an NPC definition file more robustly to prevent hint corruption."""
    data = {
        'name': '', 'area': '', 'role': '', 'motivation': '',
        'goal': '', 'needed_object': '', 'treasure': '',
        'playerhint': '', 'dialogue_hooks': '', 'veil_connection': '', 'code': ''
    }

    # Order matters if keys are substrings of others, but not with ":"
    known_keys_map = {
        'Name:': 'name', 'Area:': 'area', 'Role:': 'role',
        'Motivation:': 'motivation', 'Goal:': 'goal',
        'Needed Object:': 'needed_object', 'Treasure:': 'treasure',
        'PlayerHint:': 'playerhint', # Player hint
        'Veil Connection:': 'veil_connection',
        'Dialogue Hooks:': 'dialogue_hooks_header' # Special marker for the header
    }
    # Fields that can span multiple lines IF NOT interrupted by a new known key.
    # 'dialogue_hooks' itself is not here, as its items are handled by '-'.
    multiline_capable_dict_keys = ['motivation', 'goal', 'playerhint', 'veil_connection']
    current_dict_key_for_multiline = None

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        for line_raw in lines:
            line_stripped = line_raw.strip()
            if not line_stripped:
                current_dict_key_for_multiline = None # Reset on empty lines
                continue

            original_line_content = line_stripped # Keep original for appending if it's a continuation
            new_key_matched_this_line = False

            # 1. Check if the line starts a new known section
            for key_prefix_in_map, dict_key_name_target in known_keys_map.items():
                if line_stripped.lower().startswith(key_prefix_in_map.lower()):
                    content_after_key = line_stripped[len(key_prefix_in_map):].strip()

                    if dict_key_name_target == 'dialogue_hooks_header':
                        # This line is "Dialogue Hooks:", it just sets the context
                        # for subsequent '-' lines. Initialize/clear the actual dialogue_hooks field.
                        data['dialogue_hooks'] = ""
                        current_dict_key_for_multiline = 'dialogue_hooks' # Context for '-' lines
                    else:
                        data[dict_key_name_target] = content_after_key
                        # Check if this newly matched key is one that can be multiline
                        if dict_key_name_target in multiline_capable_dict_keys:
                            current_dict_key_for_multiline = dict_key_name_target
                        else: # It's a single-line key
                            current_dict_key_for_multiline = None

                    new_key_matched_this_line = True
                    break  # Found a key, process it and move to next line

            if new_key_matched_this_line:
                continue # Go to the next line in the file

            # 2. If not a new key, check if it's a dialogue hook item
            if line_stripped.startswith('-') and current_dict_key_for_multiline == 'dialogue_hooks':
                hook_content = line_stripped[1:].strip()
                if hook_content:
                    if data['dialogue_hooks']: # Append if already started
                        data['dialogue_hooks'] += '\n' + hook_content
                    else: # First hook item
                        data['dialogue_hooks'] = hook_content
                continue # Processed as a hook item, move to next line

            # 3. If not a new key or hook item, check if it's a continuation of a known multiline key
            if current_dict_key_for_multiline in multiline_capable_dict_keys:
                # This line is a continuation of the field stored in current_dict_key_for_multiline
                if data.get(current_dict_key_for_multiline): # Check if key exists and has prior content
                    data[current_dict_key_for_multiline] += '\n' + original_line_content
                else: # Should have been initialized by its key; this might be data for an unexpected key
                      # Or it's the first line of content for a key that was just matched and is multiline capable.
                      # This case is handled when new_key_matched_this_line is true.
                      # This specific 'else' here would mean current_dict_key_for_multiline is set,
                      # but data[current_dict_key_for_multiline] is empty/None, which implies
                      # the key line itself was empty "Key: " which is fine.
                    data[current_dict_key_for_multiline] = original_line_content
                continue # Processed as a continuation, move to next line

            # 4. If none of the above, it's an unhandled/stray line or format issue
            # print(f"{TerminalFormatter.YELLOW}Notice: Unhandled line in NPC file '{filepath}': '{original_line_content}'{TerminalFormatter.RESET}")

        # Cleanup: Remove the temporary header key if it exists from map.
        if 'dialogue_hooks_header' in data: # Should not be in data if logic is correct
            del data['dialogue_hooks_header']
        # Final strip for all fields that might have collected leading/trailing whitespace from multiline appends
        for key_to_strip in data.keys():
            if isinstance(data[key_to_strip], str):
                data[key_to_strip] = data[key_to_strip].strip()

        if not data.get('name') or not data.get('area'):
            print(f"{TerminalFormatter.YELLOW}Warning: NPC file '{filepath}' missing Name or Area.{TerminalFormatter.RESET}")
        return data

    except FileNotFoundError: print(f"{TerminalFormatter.RED}Error: NPC file not found: '{filepath}'{TerminalFormatter.RESET}"); raise
    except Exception as e: print(f"{TerminalFormatter.RED}Error parsing NPC file '{filepath}': {e}{TerminalFormatter.RESET}"); traceback.print_exc(); raise

# ... (rest of load.py: wait_for_db, load_to_mysql, load_to_mockup, __main__ block) ...
# Ensure these functions use the corrected parse_npc_file.
# The load_to_mysql and load_to_mockup will correctly handle the 'playerhint' field.

def wait_for_db(db_config, max_retries=5, delay=3):
    if not db_config or not all([db_config['host'], db_config['user'], db_config['database']]):
        print("DB connection check skipped: Configuration incomplete.")
        return False
    retries = 0
    print(f"Attempting to connect to database {db_config['host']}...")
    while retries < max_retries:
        try:
            conn = mysql.connector.connect(**db_config, connection_timeout=5)
            conn.close()
            print("Database connection successful!")
            return True
        except mysql.connector.Error as err:
            print(f"Database connection failed: {err}")
            retries += 1
            if retries < max_retries:
                print(f"Retrying in {delay} seconds... ({retries}/{max_retries})")
                time.sleep(delay)
            else:
                print("Maximum retries reached. Could not connect to the database.")
                return False
    return False

def load_to_mysql(storyboard_filepath, db_config):
    print("\n--- Loading Data to MySQL Database ---")
    if not wait_for_db(db_config): print("Exiting: DB connection failed."); return False
    conn = None; cursor = None; success = False
    try:
        conn = mysql.connector.connect(**db_config); cursor = conn.cursor()
        print("Clearing existing static world data (NPCs, Storyboards)...")
        try:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            cursor.execute("TRUNCATE TABLE NPCs"); cursor.execute("TRUNCATE TABLE Storyboards")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;"); conn.commit()
            print("Existing static world data cleared.")
        except mysql.connector.Error as err: print(f"{TerminalFormatter.RED}Error clearing data: {err}{TerminalFormatter.RESET}"); conn.rollback(); raise

        storyboard_name, storyboard_desc = parse_storyboard(storyboard_filepath)
        try:
            cursor.execute("INSERT INTO Storyboards (name, description) VALUES (%s, %s)", (storyboard_name, storyboard_desc))
            conn.commit(); storyboard_id = cursor.lastrowid
            print(f"Storyboard '{storyboard_name}' inserted with ID: {storyboard_id}")
            if not storyboard_id: raise ValueError("Failed to get storyboard ID.")
        except mysql.connector.Error as err: print(f"{TerminalFormatter.RED}DB error inserting storyboard: {err}{TerminalFormatter.RESET}"); conn.rollback(); raise

        npc_count = 0; base_dir = os.path.dirname(storyboard_filepath) or '.'
        for filename in os.listdir(base_dir):
            if filename.startswith('NPC.') and filename.endswith('.txt'):
                filepath = os.path.join(base_dir, filename)
                path_parts = filename.replace('NPC.', '', 1).replace('.txt', '').split('.')
                npc_code = ".".join(path_parts)
                try:
                    npc_data = parse_npc_file(filepath) # Uses corrected parser
                    query = """
                        INSERT INTO NPCs (code, name, area, role, motivation, goal, needed_object, treasure, playerhint, dialogue_hooks, veil_connection, storyboard_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                    values = (
                        npc_code, npc_data.get('name', ''), npc_data.get('area', ''), npc_data.get('role', ''),
                        npc_data.get('motivation', ''), npc_data.get('goal', ''), npc_data.get('needed_object', ''),
                        npc_data.get('treasure', ''), npc_data.get('playerhint', ''), npc_data.get('dialogue_hooks', ''),
                        npc_data.get('veil_connection', ''), storyboard_id )
                    cursor.execute(query, values)
                    npc_count += 1
                except Exception as e: print(f"  ❌ Error processing/inserting NPC {npc_code} from {filename}: {e}"); conn.rollback()
        conn.commit()
        print(f"✅ Successfully loaded storyboard and {npc_count} NPCs.")
        success = True
    except Exception as err: print(f"{TerminalFormatter.RED}DB loading script failed: {err}{TerminalFormatter.RESET}");
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close(); print("DB connection closed.")
        return success

def load_to_mockup(storyboard_filepath, mockup_dir="database"):
    print(f"\n--- Loading Data to Mockup Directory: {mockup_dir} ---")
    success = False
    try:
        if not os.path.exists(mockup_dir): os.makedirs(mockup_dir)
        static_data_dirs = ["NPCs", "Storyboards"]
        for table in static_data_dirs:
            table_dir = os.path.join(mockup_dir, table)
            if os.path.exists(table_dir):
                try: [os.remove(os.path.join(table_dir, f)) for f in os.listdir(table_dir) if f.endswith('.json')]
                except OSError as e: print(f"{TerminalFormatter.YELLOW}Warn: Could not clean {table_dir}: {e}{TerminalFormatter.RESET}")
            else: os.makedirs(table_dir, exist_ok=True) # Ensure it exists

        player_data_dirs = [os.path.join(mockup_dir, d) for d in ["ConversationHistory", "PlayerState", "PlayerProfiles"]]
        for p_dir in player_data_dirs: os.makedirs(p_dir, exist_ok=True)

        storyboard_name, storyboard_desc = parse_storyboard(storyboard_filepath)
        storyboard_data = {"id": 1, "name": storyboard_name, "description": storyboard_desc, "created_at": datetime.now().isoformat()}
        storyboard_file = os.path.join(mockup_dir, "Storyboards", "1.json") # Standardized to 1.json for simplicity
        with open(storyboard_file, 'w', encoding='utf-8') as f: json.dump(storyboard_data, f, indent=2)
        print(f"Storyboard '{storyboard_name}' saved.")

        npc_count = 0; npc_dir_path = os.path.join(mockup_dir, "NPCs")
        base_dir = os.path.dirname(storyboard_filepath) or '.'
        for filename in os.listdir(base_dir):
            if filename.startswith('NPC.') and filename.endswith('.txt'):
                filepath = os.path.join(base_dir, filename)
                path_parts = filename.replace('NPC.', '', 1).replace('.txt', '').split('.')
                npc_code = ".".join(path_parts) if path_parts else filename.replace('NPC.','').replace('.txt','')
                try:
                    npc_data = parse_npc_file(filepath) # Uses corrected parser
                    npc_data['code'] = npc_code
                    npc_data['storyboard_id'] = 1
                    npc_data['created_at'] = datetime.now().isoformat()
                    with open(os.path.join(npc_dir_path, f"{npc_code}.json"), 'w', encoding='utf-8') as f: json.dump(npc_data, f, indent=2)
                    npc_count += 1
                except Exception as e: print(f"  ❌ Error processing NPC {filename}: {e}")
        print(f"✅ Loaded storyboard and {npc_count} NPCs to mockup.")
        success = True
    except Exception as e: print(f"{TerminalFormatter.RED}Mockup loading failed: {e}{TerminalFormatter.RESET}"); traceback.print_exc()
    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load game data.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--mockup", action="store_true", help="Force using the mockup file system.")
    parser.add_argument("--mockup-dir", default="database", help="Directory for the mockup file system.")
    parser.add_argument("--storyboard", default="Storyboard.TheQuadCosmos.txt", help="Path to the storyboard definition file.")
    parser.add_argument("--db", action='store_true', help="Attempt to use the real MySQL database.")
    parser.add_argument("--host", default=os.environ.get('DB_HOST'), help="Override DB_HOST env var.")
    parser.add_argument("--port", type=int, default=os.environ.get('DB_PORT'), help="Override DB_PORT env var.")
    parser.add_argument("--user", default=os.environ.get('DB_USER'), help="Override DB_USER env var.")
    parser.add_argument("--password", default=os.environ.get('DB_PASSWORD'), help="Override DB_PASSWORD env var.")
    parser.add_argument("--dbname", default=os.environ.get('DB_NAME'), help="Override DB_NAME env var.")
    args = parser.parse_args()
    use_real_db = False; db_config = None
    if args.db and not args.mockup:
        db_config = {
            'host': args.host, 'port': args.port or int(os.environ.get('DB_PORT', 3306)),
            'user': args.user, 'password': args.password, 'database': args.dbname,
            'connection_timeout': int(os.environ.get('DB_TIMEOUT', 10))
        }
        if all([db_config['host'], db_config['user'], db_config['database']]): use_real_db = True
        else: print(f"{TerminalFormatter.YELLOW}Warn: Real DB mode requested but config missing. Falling back to mockup.{TerminalFormatter.RESET}")

    load_successful = load_to_mysql(args.storyboard, db_config) if use_real_db else load_to_mockup(args.storyboard, args.mockup_dir)

    if load_successful: print("\nData loading process completed successfully."); exit(0)
    else: print("\nData loading process FAILED. Please check errors."); exit(1)

