# Path: load.py
# Updated Version

import os
import mysql.connector # Keep for structure, even if primarily using mockup
import time
import json
import argparse
from datetime import datetime
import traceback

# --- Load Environment Variables ---
try:
    from dotenv import load_dotenv
    print("Loading environment variables from .env file...")
    load_dotenv()
    print("Environment variables loaded (if .env file exists).")
except ImportError:
    print("python-dotenv not found. Skipping .env file loading.")
    def load_dotenv(): pass # Define dummy function

# --- Terminal Formatter (Optional but nice for consistency) ---
class TerminalFormatter: # Basic Fallback
    DIM = ""; RESET = ""; YELLOW = ""; RED = ""; GREEN = ""; BOLD = "";
    # Add colors if needed, or import the real one

# --- Function Definitions ---

def parse_storyboard(filepath):
    """Parses the storyboard file."""
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
                # Don't add the "Description:" line itself
            elif line.startswith("Temi:") or line.startswith("Themes:"):
                current_section = "themes"
                # Don't add the "Themes:" line itself
            elif current_section == "description":
                description_lines.append(line)
            elif current_section == "themes":
                themes_lines.append(line)

        description = "\n".join(description_lines).strip()
        # Assuming themes are also part of the description for the prompt
        if themes_lines:
            description += "\n\nTemi:\n" + "\n".join(themes_lines).strip()

        if not name and not description:
            print(f"{TerminalFormatter.YELLOW}Warning: Storyboard file '{filepath}' seems empty or incorrectly formatted.{TerminalFormatter.RESET}")
        return name, description
    except FileNotFoundError:
        print(f"{TerminalFormatter.RED}Error: Storyboard file not found at '{filepath}'{TerminalFormatter.RESET}")
        raise
    except Exception as e:
        print(f"{TerminalFormatter.RED}Error parsing storyboard file '{filepath}': {e}{TerminalFormatter.RESET}")
        raise

def parse_npc_file(filepath):
    """Parses an NPC definition file."""
    data = {
        'name': '', 'area': '', 'role': '', 'motivation': '',
        'goal': '', 'needed_object': '', 'treasure': '', # Added missing fields
        'playerhint': '', # NEW FIELD for PlayerHint
        'dialogue_hooks': '', 'veil_connection': '', 'code': ''
    }
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        current_key_for_multiline = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to match a key directly
            matched_key = False
            # Explicitly define all expected single-line keys
            single_line_keys_map = {
                'Name:': 'name', 'Area:': 'area', 'Role:': 'role',
                'Motivation:': 'motivation', 'Goal:': 'goal',
                'Needed Object:': 'needed_object', 'Treasure:': 'treasure',
                'PlayerHint:': 'playerhint', # NEW
                'Veil Connection:': 'veil_connection'
                # Dialogue Hooks are handled separately due to multi-line nature starting with '-'
            }

            for key_prefix, dict_key_name in single_line_keys_map.items():
                if line.lower().startswith(key_prefix.lower()):
                    data[dict_key_name] = line[len(key_prefix):].strip()
                    current_key_for_multiline = dict_key_name # Update context for potential continuation
                    matched_key = True
                    break

            if matched_key:
                continue

            # Handle dialogue hooks (always starts with '-')
            if line.startswith('-'):
                hook_content = line[1:].strip()
                if hook_content: # Ensure not an empty hook
                    if data['dialogue_hooks']:
                        data['dialogue_hooks'] += '\n' + hook_content
                    else:
                        data['dialogue_hooks'] = hook_content
                current_key_for_multiline = 'dialogue_hooks' # Update context
                continue

            # Handle continuation for specific known multi-line capable fields
            # This is if a line doesn't start with a new key or a hook marker
            # Add 'playerhint' to multi-line capable keys if desired, or keep it single line
            # For now, playerhint is treated as potentially multi-line if it continues without a new key
            multiline_capable_keys = ['motivation', 'goal', 'playerhint', 'veil_connection', 'dialogue_hooks']
            if current_key_for_multiline in multiline_capable_keys:
                if data[current_key_for_multiline]: # Append if there's already content
                    data[current_key_for_multiline] += '\n' + line
                else: # Start the content for this key
                    data[current_key_for_multiline] = line
                continue

            # If line wasn't processed, it might be an unknown format or stray line
            # print(f"{TerminalFormatter.YELLOW}Warning: Unrecognized line in NPC file '{filepath}': {line}{TerminalFormatter.RESET}")


        # Clean up whitespace at the end of multi-line fields
        for key in ['dialogue_hooks', 'veil_connection', 'motivation', 'goal', 'playerhint']:
            if isinstance(data.get(key), str): # Use .get() for safety
                data[key] = data[key].strip()

        if not data.get('name') or not data.get('area'):
            print(f"{TerminalFormatter.YELLOW}Warning: NPC file '{filepath}' is missing Name or Area.{TerminalFormatter.RESET}")

        return data
    except FileNotFoundError:
        print(f"{TerminalFormatter.RED}Error: NPC file not found at '{filepath}'{TerminalFormatter.RESET}")
        raise
    except Exception as e:
        print(f"{TerminalFormatter.RED}Error parsing NPC file '{filepath}': {e}{TerminalFormatter.RESET}")
        raise


def wait_for_db(db_config, max_retries=5, delay=3):
    """Waits for the real database connection (if used)."""
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
    """Loads data into the real MySQL database."""
    print("\n--- Loading Data to MySQL Database ---")
    if not wait_for_db(db_config):
        print("Exiting script: Database connection failed or configuration incomplete.")
        return False

    conn = None
    cursor = None
    success = False
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        print("Clearing existing data (NPCs, Storyboards)...")
        try:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            cursor.execute("TRUNCATE TABLE NPCs")
            cursor.execute("TRUNCATE TABLE Storyboards")
            # Add other tables if they also need to be cleared and are static world data
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conn.commit()
            print("Existing static world data cleared.")
        except mysql.connector.Error as err:
            print(f"{TerminalFormatter.RED}Error clearing data: {err}{TerminalFormatter.RESET}")
            conn.rollback()
            raise

        print(f"{TerminalFormatter.DIM}Loading storyboard...{TerminalFormatter.RESET}")
        storyboard_name, storyboard_desc = parse_storyboard(storyboard_filepath)
        try:
            cursor.execute(
                "INSERT INTO Storyboards (name, description) VALUES (%s, %s)",
                (storyboard_name, storyboard_desc)
            )
            conn.commit()
            storyboard_id = cursor.lastrowid
            print(f"Storyboard '{storyboard_name}' inserted with ID: {storyboard_id}")
            if not storyboard_id:
                raise ValueError("Failed to get storyboard ID after insert.")
        except mysql.connector.Error as err:
            print(f"{TerminalFormatter.RED}Database error inserting storyboard: {err}{TerminalFormatter.RESET}")
            conn.rollback()
            raise

        print(f"{TerminalFormatter.DIM}Loading NPCs...{TerminalFormatter.RESET}")
        npc_count = 0
        base_dir = os.path.dirname(storyboard_filepath) or '.'
        for filename in os.listdir(base_dir):
            if filename.startswith('NPC.') and filename.endswith('.txt'):
                filepath = os.path.join(base_dir, filename)
                # Extract code: remove "NPC." prefix and ".txt" suffix
                # e.g., NPC.city.cassian.txt -> city.cassian
                # e.g., NPC.anqar.baruch.txt -> anqar.baruch
                path_parts = filename.replace('NPC.', '', 1).replace('.txt', '').split('.')
                if len(path_parts) >= 2: # Ensure there's at least area.name
                    npc_code = ".".join(path_parts) # Rejoin if name had dots, though convention seems to be area.name
                else:
                    npc_code = filename.replace('NPC.', '', 1).replace('.txt', '') # Fallback

                try:
                    npc_data = parse_npc_file(filepath)
                    query = """
                            INSERT INTO NPCs
                            (code, name, area, role, motivation, goal, needed_object, treasure, playerhint, dialogue_hooks, veil_connection, storyboard_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                    values = (
                        npc_code,
                        npc_data.get('name', ''),
                        npc_data.get('area', ''),
                        npc_data.get('role', ''),
                        npc_data.get('motivation', ''),
                        npc_data.get('goal', ''),
                        npc_data.get('needed_object', ''), # New
                        npc_data.get('treasure', ''),      # New
                        npc_data.get('playerhint', ''),    # NEW
                        npc_data.get('dialogue_hooks', ''),
                        npc_data.get('veil_connection', ''),
                        storyboard_id
                    )
                    cursor.execute(query, values)
                    print(f"  ✔ Inserted NPC: {npc_data.get('name', 'N/A')} (Code: {npc_code})")
                    npc_count += 1
                except mysql.connector.Error as err:
                    print(f"  ❌ Database error inserting NPC {npc_code} from {filename}: {err}")
                    conn.rollback()
                except Exception as e:
                    print(f"  ❌ Error processing or inserting NPC from file {filename}: {e}")

        conn.commit()
        print(f"✅ Successfully loaded storyboard and {npc_count} NPCs into the database.")
        success = True

    except (FileNotFoundError, ValueError, mysql.connector.Error) as err:
        print(f"{TerminalFormatter.RED}Database loading script failed: {err}{TerminalFormatter.RESET}")
        if conn and conn.is_connected(): conn.rollback()
    except Exception as e:
        print(f"{TerminalFormatter.RED}An unexpected error occurred during database loading: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()
        if conn and conn.is_connected(): conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close(); print("Database connection closed.")
        return success


def load_to_mockup(storyboard_filepath, mockup_dir="database"):
    """Loads data into a file-based mockup database."""
    print(f"\n--- Loading Data to Mockup Directory: {mockup_dir} ---")
    success = False
    try:
        if not os.path.exists(mockup_dir):
            try: os.makedirs(mockup_dir); print(f"Created base mockup directory: {mockup_dir}")
            except OSError as e: print(f"{TerminalFormatter.RED}Fatal: Could not create {mockup_dir}: {e}{TerminalFormatter.RESET}"); return False

        print(f"{TerminalFormatter.DIM}Preparing mockup subdirectories...{TerminalFormatter.RESET}")
        # Directories for static world data that load.py manages
        static_data_dirs = ["NPCs", "Storyboards"]
        for table in static_data_dirs: # Only clean dirs managed by this script
            table_dir = os.path.join(mockup_dir, table)
            if os.path.exists(table_dir):
                try:
                    for filename in os.listdir(table_dir):
                        if filename.endswith('.json'): os.remove(os.path.join(table_dir, filename))
                except OSError as e: print(f"{TerminalFormatter.YELLOW}Warn: Could not clean {table_dir}: {e}{TerminalFormatter.RESET}")
            else:
                try: os.makedirs(table_dir)
                except OSError as e: print(f"{TerminalFormatter.RED}Err: Could not create {table_dir}: {e}{TerminalFormatter.RESET}")

        # Ensure other directories used by db_manager also exist, but don't clean them here
        player_data_dirs_to_ensure = [
            os.path.join(mockup_dir, "ConversationHistory"), # For player subfolders
            os.path.join(mockup_dir, "PlayerState"),       # For player state files
            os.path.join(mockup_dir, "PlayerProfiles")     # For player profile files
        ]
        for p_dir_base in player_data_dirs_to_ensure:
            os.makedirs(p_dir_base, exist_ok=True) # exist_ok=True makes it safe


        print(f"{TerminalFormatter.DIM}Loading storyboard into mockup...{TerminalFormatter.RESET}")
        storyboard_name, storyboard_desc = parse_storyboard(storyboard_filepath)
        storyboard_id = 1 # Mockup can use a simple ID
        storyboard_data = {
            "id": storyboard_id, "name": storyboard_name, "description": storyboard_desc,
            "created_at": datetime.now().isoformat()
        }
        storyboard_file = os.path.join(mockup_dir, "Storyboards", f"{storyboard_id}.json")
        try:
            with open(storyboard_file, 'w', encoding='utf-8') as f: json.dump(storyboard_data, f, ensure_ascii=False, indent=2)
            print(f"Storyboard '{storyboard_name}' saved to mockup.")
        except IOError as e: print(f"{TerminalFormatter.RED}Err writing storyboard {storyboard_file}: {e}{TerminalFormatter.RESET}"); return False
        except Exception as e: print(f"{TerminalFormatter.RED}Unexpected err writing storyboard: {e}{TerminalFormatter.RESET}"); traceback.print_exc(); return False

        print(f"{TerminalFormatter.DIM}Loading NPCs into mockup...{TerminalFormatter.RESET}")
        npc_count = 0
        npc_dir_path = os.path.join(mockup_dir, "NPCs")
        base_dir = os.path.dirname(storyboard_filepath) or '.'
        for filename in os.listdir(base_dir):
            if filename.startswith('NPC.') and filename.endswith('.txt'):
                filepath = os.path.join(base_dir, filename)
                path_parts = filename.replace('NPC.', '', 1).replace('.txt', '').split('.')
                npc_code = ".".join(path_parts) if len(path_parts) >= 1 else filename.replace('NPC.', '', 1).replace('.txt', '')


                try:
                    npc_data = parse_npc_file(filepath)
                    npc_data['code'] = npc_code
                    npc_data['storyboard_id'] = storyboard_id
                    npc_data['created_at'] = datetime.now().isoformat()

                    npc_file_path = os.path.join(npc_dir_path, f"{npc_code}.json")
                    try:
                        with open(npc_file_path, 'w', encoding='utf-8') as f: json.dump(npc_data, f, ensure_ascii=False, indent=2)
                        print(f"  ✔ Saved NPC to mockup: {npc_data.get('name', 'N/A')} (Code: {npc_code})")
                        npc_count += 1
                    except IOError as e: print(f"  ❌ Error writing NPC file {npc_file_path}: {e}")
                    except Exception as e: print(f"  ❌ Unexpected err writing NPC file {npc_file_path}: {e}"); traceback.print_exc()
                except (FileNotFoundError, ValueError) as parse_err:
                    print(f"  ❌ Skipping NPC file {filename} due to parsing error: {parse_err}")
                except Exception as e: print(f"  ❌ Unexpected error processing NPC file {filename}: {e}"); traceback.print_exc()

        print(f"✅ Successfully loaded storyboard and {npc_count} NPCs into mockup.")
        success = True

    except FileNotFoundError as e: print(f"{TerminalFormatter.RED}Loading script failed: File not found: {e}{TerminalFormatter.RESET}")
    except Exception as e: print(f"{TerminalFormatter.RED}An unexpected error during mockup loading: {e}{TerminalFormatter.RESET}"); traceback.print_exc()
    finally: return success


# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load Storyboard and NPC data into a database or file-based mockup.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
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
    use_real_db = False
    db_config = None

    if args.db and not args.mockup:
        print("Real database mode requested.")
        db_config = {
            'host': args.host, 'port': args.port or int(os.environ.get('DB_PORT', 3306)),
            'user': args.user, 'password': args.password, 'database': args.dbname,
            'connection_timeout': int(os.environ.get('DB_TIMEOUT', 10))
        }
        if all([db_config['host'], db_config['user'], db_config['database']]):
            print(f"Attempting connection to {db_config['host']}:{db_config['port']} as {db_config['user']}")
            use_real_db = True
        else:
            print(f"{TerminalFormatter.YELLOW}Warn: Real DB mode (--db) requested but essential config (host, user, dbname) is missing. Falling back to mockup.{TerminalFormatter.RESET}")
    else:
        if args.mockup: print("Mockup mode explicitly forced (--mockup).")
        else: print("Defaulting to mockup mode (use --db and set ENV vars for real database).")

    load_successful = False
    if use_real_db and db_config:
        load_successful = load_to_mysql(args.storyboard, db_config)
    else:
        load_successful = load_to_mockup(args.storyboard, args.mockup_dir)

    if load_successful: print("\nData loading process completed successfully."); exit(0)

