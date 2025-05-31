import os
import mysql.connector
import time
import json
import argparse
from datetime import datetime
import traceback
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not found. Skipping .env file loading.")
    def load_dotenv(): pass

class TerminalFormatter:
    DIM = ""; RESET = ""; YELLOW = ""; RED = ""; GREEN = ""; BOLD = "";
    BRIGHT_CYAN = ""
    @staticmethod
    def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))

def parse_storyboard(filepath):
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
    data = {
        'name': '', 'area': '', 'role': '', 'motivation': '',
        'goal': '', 'needed_object': '', 'treasure': '',
        'playerhint': '', 'dialogue_hooks': '', 'veil_connection': '', 'code': ''
    }
    known_keys_map = {
        'Name:': 'name', 'Area:': 'area', 'Role:': 'role',
        'Motivation:': 'motivation', 'Goal:': 'goal',
        'Needed Object:': 'needed_object', 'Treasure:': 'treasure',
        'PlayerHint:': 'playerhint',
        'Veil Connection:': 'veil_connection',
        'Dialogue Hooks:': 'dialogue_hooks_header' # Marker per iniziare a raccogliere i ganci
    }
    # Campi che possono estendersi su più righe semplici (senza struttura interna complessa)
    simple_multiline_fields = ['motivation', 'goal', 'playerhint', 'veil_connection']

    current_field_being_parsed = None # Tiene traccia del campo corrente per il testo multiriga

    # Per dialogue_hooks, accumuleremo le righe qui
    dialogue_hooks_lines = []
    parsing_dialogue_hooks = False

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        for line_raw in lines:
            line_stripped = line_raw.strip()
            # Rimuove solo i newline dalla fine della riga, preservando spazi iniziali
            original_line_content_for_hooks = line_raw.rstrip('\n\r')

            # Controlla se la riga inizia con una nuova chiave conosciuta
            matched_new_key = False
            for key_prefix, field_name_target in known_keys_map.items():
                if line_stripped.lower().startswith(key_prefix.lower()):
                    parsing_dialogue_hooks = False # Se troviamo una nuova chiave, usciamo dalla modalità dialogue_hooks
                    content_after_key = line_stripped[len(key_prefix):].strip()

                    if field_name_target == 'dialogue_hooks_header':
                        parsing_dialogue_hooks = True
                        current_field_being_parsed = None # Non stiamo più facendo parsing di un simple_multiline_field
                    else:
                        data[field_name_target] = content_after_key
                        if field_name_target in simple_multiline_fields:
                            current_field_being_parsed = field_name_target
                        else:
                            current_field_being_parsed = None # Campo a riga singola
                    matched_new_key = True
                    break

            if matched_new_key:
                continue

            # Se siamo in modalità parsing_dialogue_hooks, aggiungi la riga originale
            if parsing_dialogue_hooks:
                # Aggiungiamo la riga così com'è (preservando indentazione e righe vuote)
                # perché la logica in get_npc_opening_line si aspetta di poter splittare per newline
                # e trovare "(Iniziale):" e poi le righe che iniziano con "- ".
                dialogue_hooks_lines.append(original_line_content_for_hooks)
            # Altrimenti, se stiamo facendo parsing di un altro campo multiriga
            elif current_field_being_parsed in simple_multiline_fields:
                if line_stripped: # Accoda solo se la riga non è vuota per i campi semplici multiriga
                    if data[current_field_being_parsed]:
                        data[current_field_being_parsed] += '\n' + line_stripped
                    else:
                        data[current_field_being_parsed] = line_stripped

        # Unisci le righe dei dialogue_hooks
        if dialogue_hooks_lines:
            data['dialogue_hooks'] = "\n".join(dialogue_hooks_lines).strip() # Strip finale sull'intero blocco
        else:
            data['dialogue_hooks'] = "" # Assicura che sia una stringa vuota se non ci sono ganci

        # Pulizia finale degli altri campi (strip solo se necessario, dialogue_hooks già fatto)
        for key, value in data.items():
            if key != 'dialogue_hooks' and isinstance(value, str):
                data[key] = value.strip()

        if not data.get('name') or not data.get('area'):
            print(f"{TerminalFormatter.YELLOW}Warning: NPC file '{filepath}' missing Name or Area.{TerminalFormatter.RESET}")
        # if data.get('name', '').lower() == 'lyra':
        #     print(f"DEBUG LYRA HOOKS (in parse_npc_file):\n---\n{data.get('dialogue_hooks', 'N/A')}\n---")

        return data

    except FileNotFoundError: print(f"{TerminalFormatter.RED}Error: NPC file not found: '{filepath}'{TerminalFormatter.RESET}"); raise
    except Exception as e: print(f"{TerminalFormatter.RED}Error parsing NPC file '{filepath}': {e}{TerminalFormatter.RESET}"); traceback.print_exc(); raise

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
                    # DEBUG: Stampa i dialogue_hooks prima di salvarli
                    # print(f"DEBUG: NPC {npc_code}, Dialogue Hooks Parsed:\n---\n{npc_data.get('dialogue_hooks', 'N/A')}\n---")
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