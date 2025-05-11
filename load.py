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
# You can copy the TerminalFormatter class here or import it
# For simplicity, we'll skip adding it here, but you could.
class TerminalFormatter: # Basic Fallback
    DIM = ""
    RESET = ""
    YELLOW = ""
    RED = ""
    GREEN = ""
    BOLD = ""
    # Add colors if needed, or import the real one

# --- Function Definitions ---

def parse_storyboard(filepath):
    """Parses the storyboard file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        name = ""
        description_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("Name:"):
                name = line.replace("Name:", "").strip()
            elif line.startswith("Description:"):
                continue # skip this label
            else:
                description_lines.append(line)
        description = "\n".join(description_lines).strip()
        if not name and not description:
            print(f"Warning: Storyboard file '{filepath}' seems empty or incorrectly formatted.")
        return name, description
    except FileNotFoundError:
        print(f"{TerminalFormatter.RED}Error: Storyboard file not found at '{filepath}'{TerminalFormatter.RESET}")
        raise # Re-raise to stop the script
    except Exception as e:
        print(f"{TerminalFormatter.RED}Error parsing storyboard file '{filepath}': {e}{TerminalFormatter.RESET}")
        raise # Re-raise

def parse_npc_file(filepath):
    """Parses an NPC definition file."""
    data = {
        'name': '', 'area': '', 'role': '', 'motivation': '',
        'goal': '', 'dialogue_hooks': '', 'veil_connection': '', 'code': ''
    }
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        current_key = None # Tracks the last multi-line key encountered

        for line in lines:
            line = line.strip()
            if not line: # Skip empty lines
                continue

            processed = False
            # Handle single-line key-value pairs
            for key_prefix in ['Name:', 'Area:', 'Role:', 'Motivation:', 'Goal:', 'Veil Connection:']:
                if line.startswith(key_prefix):
                    # Convert "Key Name:" to "key_name"
                    dict_key = key_prefix.lower().replace(':', '').replace(' ', '_')
                    data[dict_key] = line.replace(key_prefix, '').strip()
                    current_key = dict_key # Update current key context
                    processed = True
                    break

            # Handle multi-line dialogue hooks (starting with '-')
            if not processed and line.startswith('- '):
                hook = line[2:].strip()
                if hook: # Avoid adding empty hooks
                    if data['dialogue_hooks']:
                        data['dialogue_hooks'] += '\n' + hook
                    else:
                        data['dialogue_hooks'] = hook
                current_key = 'dialogue_hooks' # Update context
                processed = True

            # Handle continuation lines for specific multi-line fields
            if not processed and current_key in ['motivation', 'goal', 'dialogue_hooks', 'veil_connection']:
                # Append to the current multi-line field if it wasn't processed otherwise
                if data[current_key]: # Check if it already has content
                    data[current_key] += '\n' + line
                else:
                    data[current_key] = line
                # Keep current_key context

        # Clean up whitespace at the end of multi-line fields
        for key in ['dialogue_hooks', 'veil_connection', 'motivation', 'goal']:
            if isinstance(data[key], str):
                data[key] = data[key].strip()

        if not data.get('name') or not data.get('area'):
            print(f"{TerminalFormatter.YELLOW}Warning: NPC file '{filepath}' is missing Name or Area.{TerminalFormatter.RESET}")

        return data
    except FileNotFoundError:
        print(f"{TerminalFormatter.RED}Error: NPC file not found at '{filepath}'{TerminalFormatter.RESET}")
        raise # Re-raise
    except Exception as e:
        print(f"{TerminalFormatter.RED}Error parsing NPC file '{filepath}': {e}{TerminalFormatter.RESET}")
        raise # Re-raise


def wait_for_db(db_config, max_retries=5, delay=3):
    """Waits for the real database connection (if used)."""
    if not db_config or not all([db_config['host'], db_config['user'], db_config['database']]):
        print("DB connection check skipped: Configuration incomplete.")
        return False # Cannot connect if config is bad

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

        # --- Clear existing data (optional, be careful!) ---
        print("Clearing existing data (NPCs, Storyboards)...")
        try:
            # Disable foreign key checks to allow truncation
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            # Truncate tables (faster than DELETE for full clear)
            cursor.execute("TRUNCATE TABLE NPCs")
            cursor.execute("TRUNCATE TABLE Storyboards")
            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conn.commit()
            print("Existing data cleared.")
        except mysql.connector.Error as err:
            print(f"{TerminalFormatter.RED}Error clearing data: {err}{TerminalFormatter.RESET}")
            conn.rollback() # Rollback changes if clearing failed
            raise # Stop execution if clearing fails

        # --- Load Storyboard ---
        print(f"{TerminalFormatter.DIM}Loading storyboard...{TerminalFormatter.RESET}")
        storyboard_name, storyboard_desc = parse_storyboard(storyboard_filepath)
        try:
            cursor.execute(
                "INSERT INTO Storyboards (name, description) VALUES (%s, %s)",
                (storyboard_name, storyboard_desc)
            )
            conn.commit()
            storyboard_id = cursor.lastrowid # Get the ID of the inserted storyboard
            print(f"Storyboard '{storyboard_name}' inserted with ID: {storyboard_id}")
            if not storyboard_id:
                raise ValueError("Failed to get storyboard ID after insert.")
        except mysql.connector.Error as err:
            print(f"{TerminalFormatter.RED}Database error inserting storyboard: {err}{TerminalFormatter.RESET}")
            conn.rollback()
            raise # Stop if storyboard fails


        # --- Load NPCs ---
        print(f"{TerminalFormatter.DIM}Loading NPCs...{TerminalFormatter.RESET}")
        npc_count = 0
        base_dir = os.path.dirname(storyboard_filepath) or '.' # Assume NPC files are near storyboard
        for filename in os.listdir(base_dir):
            if filename.startswith('NPC.') and filename.endswith('.txt'):
                filepath = os.path.join(base_dir, filename)
                npc_code = filename.replace('NPC.', '').replace('.txt', '')
                try:
                    npc_data = parse_npc_file(filepath)
                    # Use the actual storyboard_id obtained above
                    query = """
                            INSERT INTO NPCs
                            (code, name, area, role, motivation, goal, dialogue_hooks, veil_connection, storyboard_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) \
                            """
                    values = (
                        npc_code,
                        npc_data.get('name', ''),
                        npc_data.get('area', ''),
                        npc_data.get('role', ''),
                        npc_data.get('motivation', ''),
                        npc_data.get('goal', ''),
                        npc_data.get('dialogue_hooks', ''),
                        npc_data.get('veil_connection', ''), # Add Veil Connection
                        storyboard_id # Link to the loaded storyboard
                    )
                    cursor.execute(query, values)
                    print(f"  ✔ Inserted NPC: {npc_data.get('name', 'N/A')} (Code: {npc_code})")
                    npc_count += 1

                except mysql.connector.Error as err:
                    print(f"  ❌ Database error inserting NPC {npc_code} from {filename}: {err}")
                    # Decide whether to rollback this specific NPC or continue
                    conn.rollback() # Rollback the failed NPC insert
                except Exception as e:
                    print(f"  ❌ Error processing or inserting NPC from file {filename}: {e}")
                    # Decide if script should stop or continue

        conn.commit() # Commit all successful NPC inserts
        print(f"✅ Successfully loaded storyboard and {npc_count} NPCs into the database.")
        success = True

    except (FileNotFoundError, ValueError, mysql.connector.Error) as err:
        print(f"{TerminalFormatter.RED}Database loading script failed: {err}{TerminalFormatter.RESET}")
        if conn and conn.is_connected():
            conn.rollback() # Rollback any partial changes on error
    except Exception as e:
        print(f"{TerminalFormatter.RED}An unexpected error occurred during database loading: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()
        if conn and conn.is_connected():
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("Database connection closed.")
        return success


def load_to_mockup(storyboard_filepath, mockup_dir="database"):
    """Loads data into a file-based mockup database."""
    print(f"\n--- Loading Data to Mockup Directory: {mockup_dir} ---")
    success = False
    try:
        # Create base directory if needed
        if not os.path.exists(mockup_dir):
            try:
                os.makedirs(mockup_dir)
                print(f"Created base mockup directory: {mockup_dir}")
            except OSError as e:
                print(f"{TerminalFormatter.RED}Fatal Error: Could not create base mockup directory {mockup_dir}: {e}{TerminalFormatter.RESET}")
                return False # Cannot proceed

        # Create subdirectories & clean them
        print(f"{TerminalFormatter.DIM}Preparing mockup subdirectories...{TerminalFormatter.RESET}")
        for table in ["NPCs", "Storyboards", "Dialogues", "ConversationHistory"]:
            table_dir = os.path.join(mockup_dir, table)
            if os.path.exists(table_dir):
                # Clean existing JSON files
                try:
                    for filename in os.listdir(table_dir):
                        if filename.endswith('.json'):
                            os.remove(os.path.join(table_dir, filename))
                except OSError as e:
                    print(f"{TerminalFormatter.YELLOW}Warning: Could not clean directory {table_dir}: {e}{TerminalFormatter.RESET}")
            else:
                # Create directory if it doesn't exist
                try:
                    os.makedirs(table_dir)
                except OSError as e:
                    print(f"{TerminalFormatter.RED}Error: Could not create mockup subdirectory {table_dir}: {e}{TerminalFormatter.RESET}")
                    # Decide if this is fatal or can be skipped

        # --- Load Storyboard ---
        print(f"{TerminalFormatter.DIM}Loading storyboard into mockup...{TerminalFormatter.RESET}")
        storyboard_name, storyboard_desc = parse_storyboard(storyboard_filepath)
        storyboard_id = 1 # Mockup can use a simple ID
        storyboard_data = {
            "id": storyboard_id,
            "name": storyboard_name,
            "description": storyboard_desc,
            "created_at": datetime.now().isoformat() # Use ISO format
        }
        storyboard_file = os.path.join(mockup_dir, "Storyboards", f"{storyboard_id}.json")
        try:
            with open(storyboard_file, 'w', encoding='utf-8') as f:
                json.dump(storyboard_data, f, ensure_ascii=False, indent=2)
            print(f"Storyboard '{storyboard_name}' saved to mockup.")
        except IOError as e:
            print(f"{TerminalFormatter.RED}Error writing storyboard file {storyboard_file}: {e}{TerminalFormatter.RESET}")
            return False # Stop if storyboard fails
        except Exception as e:
            print(f"{TerminalFormatter.RED}Unexpected error writing storyboard file: {e}{TerminalFormatter.RESET}")
            traceback.print_exc()
            return False

        # --- Load NPCs ---
        print(f"{TerminalFormatter.DIM}Loading NPCs into mockup...{TerminalFormatter.RESET}")
        npc_count = 0
        npc_dir_path = os.path.join(mockup_dir, "NPCs")
        base_dir = os.path.dirname(storyboard_filepath) or '.' # Assume NPC files are near storyboard
        for filename in os.listdir(base_dir):
            if filename.startswith('NPC.') and filename.endswith('.txt'):
                filepath = os.path.join(base_dir, filename)
                npc_code = filename.replace('NPC.', '').replace('.txt', '')
                try:
                    npc_data = parse_npc_file(filepath)
                    # Add mockup-specific fields
                    npc_data['code'] = npc_code # Ensure code is in the dict
                    npc_data['storyboard_id'] = storyboard_id
                    npc_data['created_at'] = datetime.now().isoformat()

                    # Save NPC to its JSON file
                    npc_file = os.path.join(npc_dir_path, f"{npc_code}.json")
                    try:
                        with open(npc_file, 'w', encoding='utf-8') as f:
                            json.dump(npc_data, f, ensure_ascii=False, indent=2)
                        print(f"  ✔ Saved NPC to mockup: {npc_data.get('name', 'N/A')} (Code: {npc_code})")
                        npc_count += 1
                    except IOError as e:
                        print(f"  ❌ Error writing NPC file {npc_file}: {e}")
                    except Exception as e:
                        print(f"  ❌ Unexpected error writing NPC file {npc_file}: {e}")
                        traceback.print_exc()
                        # Decide whether to continue

                except (FileNotFoundError, ValueError):
                    # Errors already printed in parse_npc_file
                    print(f"  ❌ Skipping NPC file {filename} due to parsing error.")
                except Exception as e:
                    print(f"  ❌ Unexpected error processing NPC file {filename}: {e}")
                    traceback.print_exc()

        print(f"✅ Successfully loaded storyboard and {npc_count} NPCs into mockup.")
        success = True

    except FileNotFoundError as e:
        print(f"{TerminalFormatter.RED}Loading script failed: Required file not found: {e}{TerminalFormatter.RESET}")
    except Exception as e:
        print(f"{TerminalFormatter.RED}An unexpected error occurred during mockup loading: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()
    finally:
        return success


# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load Storyboard and NPC data into a database or file-based mockup.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help
    )
    parser.add_argument(
        "--mockup",
        action="store_true",
        help="Force using the mockup file system even if DB variables are set."
    )
    parser.add_argument(
        "--mockup-dir",
        default="database",
        help="Directory path for the mockup file system."
    )
    parser.add_argument(
        "--storyboard",
        default="Storyboard.TheQuadCosmos.txt",
        help="Path to the storyboard definition file."
    )
    # --- Database Arguments (Optional - for real DB mode) ---
    parser.add_argument(
        "--db",
        action='store_true',
        help="Attempt to use the real MySQL database. Requires DB environment variables (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME) to be set."
    )
    # These arguments allow overriding environment variables but default to None
    parser.add_argument("--host", default=os.environ.get('DB_HOST'), help="Override DB_HOST env var.")
    parser.add_argument("--port", type=int, default=os.environ.get('DB_PORT'), help="Override DB_PORT env var.")
    parser.add_argument("--user", default=os.environ.get('DB_USER'), help="Override DB_USER env var.")
    parser.add_argument("--password", default=os.environ.get('DB_PASSWORD'), help="Override DB_PASSWORD env var.")
    parser.add_argument("--dbname", default=os.environ.get('DB_NAME'), help="Override DB_NAME env var.")

    args = parser.parse_args()

    # Determine mode
    use_real_db = False
    db_config = None
    if args.db and not args.mockup: # Only try real DB if --db is set AND --mockup is not forced
        print("Real database mode requested.")
        # Construct config prioritising args over environment variables
        db_config = {
            'host': args.host, # Takes arg if provided, otherwise env var (which could be None)
            'port': args.port or int(os.environ.get('DB_PORT', 3306)), # Ensure port has a fallback
            'user': args.user,
            'password': args.password,
            'database': args.dbname,
            'connection_timeout': int(os.environ.get('DB_TIMEOUT', 10))
        }
        # Check if essential config is present
        if all([db_config['host'], db_config['user'], db_config['database']]):
            print(f"Attempting connection to {db_config['host']}:{db_config['port']} as {db_config['user']}")
            use_real_db = True # Config looks plausible
        else:
            print(f"{TerminalFormatter.YELLOW}Warning: Real DB mode requested (--db) but essential configuration (host, user, dbname) is missing.{TerminalFormatter.RESET}")
            print(f"{TerminalFormatter.YELLOW}Falling back to mockup mode.{TerminalFormatter.RESET}")
            use_real_db = False
    else:
        if args.mockup:
            print("Mockup mode explicitly forced (--mockup).")
        else:
            print("Defaulting to mockup mode (use --db and set ENV vars for real database).")

    # Execute loading based on mode
    load_successful = False
    if use_real_db and db_config:
        load_successful = load_to_mysql(args.storyboard, db_config)
    else:
        # Use mockup mode
        load_successful = load_to_mockup(args.storyboard, args.mockup_dir)

    # Final status message
    if load_successful:
        print("\nData loading process completed successfully.")
        exit(0)
    else:
        print("\nData loading process failed. Please check errors above.")
        exit(1)
