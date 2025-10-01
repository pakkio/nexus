import gradio as gr
import os
import sys
import traceback
import re
from typing import List, Dict, Any, Tuple, Optional # Added Optional

# --- Core Game System Imports (simulating project structure) ---
try:
    from game_system_api import GameSystem, clean_ansi_codes
    from main_utils import get_help_text
    class TerminalFormatter:
        RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN = ""; BG_GREEN = ""; BLACK = ""; BRIGHT_MAGENTA = ""; BRIGHT_GREEN = ""; BRIGHT_YELLOW = ""; ITALIC = "";
        @staticmethod
        def format_terminal_text(text, width=80): return text
        @staticmethod
        def get_terminal_width(): return 80
except ImportError as e:
    print(f"Warning: Could not import all game modules: {e}. Using fallbacks.")
    # Fallback definitions (as in previous responses)
    class GameSystem:
        def __init__(self, use_mockup=True, mockup_dir="db", model_name="dummy", debug_mode=False):
            self.debug_mode = debug_mode; self.player_systems = {}
            print(f"FALLBACK GameSystem initialized (mockup: {use_mockup}, model: {model_name})")
        def get_player_system(self, player_id): # player_id is owner_key
            if player_id not in self.player_systems:
                self.player_systems[player_id] = self._MockPlayerSystem(player_id, self.debug_mode)
            return self.player_systems[player_id]
        def close_player_session(self, player_id):
            if player_id in self.player_systems: del self.player_systems[player_id]
        class _MockPlayerSystem:
            def __init__(self, player_id, debug_mode):
                self.player_id = player_id; self.debug_mode = debug_mode
                self.current_npc_name = "Lyra"; self.status = "ok"; self.game_state = {}
            # GameSystem's process_player_input signature remains UNCHANGED for now
            def process_player_input(self, player_input: str) -> Dict[str, Any]:
                if self.debug_mode:
                    print(f"MockPlayerSystem processing for {self.player_id}: '{player_input}'")
                    # We could access self.game_state['sl_context_headers'] here if we were to store it
                    # from a hypothetical wrapper, but for now, it's not passed directly.
                response = f"Mock response from {self.current_npc_name} to '{player_input}' for {self.player_id}."
                # Example of how it *could* use headers if they were passed and stored:
                # if self.game_state.get('sl_context_headers', {}).get("X-SecondLife-Region"):
                #    response += f" You are in {self.game_state['sl_context_headers']['X-SecondLife-Region']}."
                if player_input.lower() == "/exit": self.status = "exit"; response = "You have mock-exited."
                if player_input.lower() == "/help": response = "Mock Help: /go, /talk, /exit"
                return {'npc_response': response, 'system_messages': ["Mock system message."],
                        'player_id': self.player_id, 'current_area': "MockRegion",
                        'current_npc_name': self.current_npc_name, 'inventory': ["Mock Item"],
                        'credits': 100, 'profile_summary': "Mock Profile.", 'status': self.status,
                        'last_speaker_for_suffix': self.current_npc_name}
    def clean_ansi_codes(text: str) -> str:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'); cleaned = ansi_escape.sub('', text)
        return re.sub(r'\033\[[0-9;]*m', '', cleaned)
    def get_help_text(game_session_state=None): return "Fallback Help: /go, /talk, /exit"
    class TerminalFormatter:
        RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN = ""; BG_GREEN = ""; BLACK = ""; BRIGHT_MAGENTA = ""; BRIGHT_GREEN = ""; BRIGHT_YELLOW = ""; ITALIC = "";

# --- Initialize Game System ---
print("Initializing Eldoria GameSystem for Gradio Context Simulator...")
try:
    game_system_manager = GameSystem(
        use_mockup=True,
        mockup_dir="database_gradio_context_sim", # Ensure this directory is populated
        model_name=os.environ.get("OPENROUTER_DEFAULT_MODEL", "google/gemma-2-9b-it:free"),
        debug_mode=True
    )
    print("Eldoria GameSystem initialized successfully.")
except Exception as e:
    print(f"FATAL ERROR initializing GameSystem: {e}")
    print(traceback.format_exc())
    game_system_manager = GameSystem(use_mockup=True, mockup_dir="fallback_db_context", debug_mode=True) # type: ignore
    print("Initialized with FALLBACK GameSystem due to error.")

# --- Header Stripping Function (for message payload) ---
def strip_lsl_headers_from_payload(raw_message: str) -> Tuple[str, str]:
    stripped_headers = ""
    cleaned_message = raw_message
    uuid_match = re.match(r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*[:|\s]?\s*(.*)$", raw_message)
    if uuid_match: return uuid_match.group(1), uuid_match.group(2).strip()
    channel_match = re.match(r"^(-?\d+)\s*[:|\s]\s*(.*)$", raw_message)
    if channel_match:
        potential_message_part = channel_match.group(2).strip()
        if not potential_message_part.replace('.','',1).isdigit(): return channel_match.group(1), potential_message_part
    custom_prefix_match = re.match(r"^([a-zA-Z0-9_]{1,20})\s*[:|]\s*(.*)$", raw_message)
    if custom_prefix_match:
        potential_command = custom_prefix_match.group(1).lower()
        if potential_command not in ["go", "talk", "give", "receive"]: return custom_prefix_match.group(1), custom_prefix_match.group(2).strip()
    return stripped_headers, cleaned_message

# --- Adapted ask_lsl function ---
def item_pattern_match(message_line: str) -> bool:
    return bool(re.match(r"^\s*[-*•\w]", message_line))

def ask_lsl_with_context_frontend_only(
        owner_key: str,
        owner_name: str,
        region_info: str,
        object_name: str,
        object_key: str,
        local_pos: str,
        shard: str,
        raw_lsl_message_payload: str # This is just the string part of the message
) -> Tuple[str, str, str, str]:
    player_id_for_system = owner_key

    if not player_id_for_system.strip():
        return "Error: X-SecondLife-Owner-Key (Player ID) cannot be empty.", "", raw_lsl_message_payload, "Player ID missing."
    # Message payload can be empty if the "command" is implicit in an HTTP-in URL, for example.
    # Or if it's a touch event with no message.
    if not raw_lsl_message_payload.strip():
        raw_lsl_message_payload = ""

    print(f"\n--- Gradio LSL Context Request from OwnerKey '{player_id_for_system}' ---")
    print(f"Raw Input Message Payload: '{raw_lsl_message_payload}'")

    # 1. Construct and Display SL Headers (Simulated)
    sl_headers_data_for_display = {
        "X-SecondLife-Owner-Key": owner_key,
        "X-SecondLife-Owner-Name": owner_name,
        "X-SecondLife-Region": region_info,
        "X-SecondLife-Object-Name": object_name,
        "X-SecondLife-Object-Key": object_key,
        "X-SecondLife-Local-Position": local_pos,
        "X-SecondLife-Shard": shard,
    }
    # Create a string representation of the headers that *would* be sent/available
    sl_context_display = "Simulated HTTP Headers (X-SecondLife-*):\n" + \
                         "\n".join([f"  {k}: '{v}'" for k,v in sl_headers_data_for_display.items() if v.strip()])
    print(sl_context_display) # For console debugging

    # 2. Strip any headers *prefixed to the message payload itself*
    stripped_payload_headers, cleaned_message_for_game = strip_lsl_headers_from_payload(raw_lsl_message_payload)
    stripped_headers_display = f"Headers stripped from payload string: '{stripped_payload_headers}'" if stripped_payload_headers else "No headers stripped from payload string."
    cleaned_message_display = f"Message payload string to Game: '{cleaned_message_for_game}'"
    print(stripped_headers_display) # For console
    print(cleaned_message_display)  # For console

    player_game_system = None
    try:
        player_game_system = game_system_manager.get_player_system(player_id_for_system) # type: ignore

        # !!! IMPORTANT: For this iteration, we are NOT passing sl_headers_data_for_display
        # !!! to process_player_input. The GameSystem remains unchanged.
        # !!! We are only *simulating* the collection of these headers on the frontend.
        response_data = player_game_system.process_player_input(cleaned_message_for_game)

        if not isinstance(response_data, dict):
            print(f"Error: process_player_input did not return a dict. Got: {type(response_data)}")
            return "Error: Internal game system response format error.", stripped_headers_display, cleaned_message_display, sl_context_display

        # --- Formatting logic (same as before, using 'cleaned_message_for_game' for command checks) ---
        lsl_response = ""; MAX_LSL_STRING_LENGTH = 800
        what_it_says_for_command_check = cleaned_message_for_game
        npc_dialogue_this_turn = clean_ansi_codes(response_data.get('npc_response', '')).strip()
        actual_npc_speaker_name = response_data.get('current_npc_name')
        system_msgs_cleaned = [clean_ansi_codes(msg).strip() for msg in response_data.get('system_messages', []) if clean_ansi_codes(msg).strip() and not ("psychological profile has been updated" in msg.lower() and not game_system_manager.debug_mode)] # type: ignore
        if not system_msgs_cleaned and "psychological profile has been updated" in " ".join(response_data.get('system_messages', [])).lower():
            if game_system_manager.debug_mode: system_msgs_cleaned = ["Profile updated (debug)."] # type: ignore
        is_command_input = what_it_says_for_command_check.startswith("/") or any(what_it_says_for_command_check.lower().startswith(cmd_start) for cmd_start in ["go ", "talk ", "list ", "areas", "who", "whereami", "npcs", "inv", "inventory", "give ", "receive ", "profile", "stats", "clear", "history", "hint", "endhint"])
        is_command_handled_specifically = False; command_produces_npc_dialogue = False
        if what_it_says_for_command_check.lower().startswith("/exit") and response_data.get('status') == 'exit':
            game_system_manager.close_player_session(player_id_for_system); lsl_response = "You have exited the game. Farewell!" # type: ignore
            if actual_npc_speaker_name: lsl_response += f" (You were speaking with {actual_npc_speaker_name})"
            is_command_handled_specifically = True
        elif what_it_says_for_command_check.lower().startswith("/help"):
            current_player_state = player_game_system.game_state if hasattr(player_game_system, 'game_state') else None
            help_text_content = get_help_text(current_player_state); lsl_response = clean_ansi_codes(help_text_content).strip()[:MAX_LSL_STRING_LENGTH]
            is_command_handled_specifically = True
        elif what_it_says_for_command_check.lower().startswith(("/inventory", "/inv")):
            inv_parts = [msg for msg in system_msgs_cleaned if "Your Inventory" in msg or "Credits:" in msg or item_pattern_match(msg) or "Your Possessions" in msg]
            if inv_parts: lsl_response = " ".join(inv_parts).replace("--- Your Inventory ---", "Inventory:").strip()
            else: lsl_response = "Your inventory is empty or could not be displayed."
            is_command_handled_specifically = True
        elif any(cmd_key in what_it_says_for_command_check.lower() for cmd_key in ["listareas", "/listareas", "/areas", "list areas", "areas"]):
            area_list_messages = [ msg for msg in system_msgs_cleaned if msg.startswith("Available Areas:") or ("➢" in msg and "Credits" not in msg) or (msg.count(',') >= 2 and "Credits" not in msg and "profile" not in msg.lower())]
            if area_list_messages:
                joined_areas = " ".join(area_list_messages)
                if joined_areas.startswith("Available Areas:"): lsl_response = joined_areas.replace("Available Areas:", "Areas:").replace("➢", "").strip()
                else: lsl_response = f"Areas: {joined_areas.replace('➢', '').strip()}"
                lsl_response = re.sub(r'\s{2,}', ' ', lsl_response)
            else: lsl_response = "No areas found or an error occurred listing them."
            is_command_handled_specifically = True
        if not is_command_handled_specifically:
            if is_command_input:
                if any(cmd_key in what_it_says_for_command_check.lower() for cmd_key in ["go ", "/go ", "talk ", "/talk"]):
                    if npc_dialogue_this_turn:
                        command_produces_npc_dialogue = True; is_ponder_message = "seems to ponder" in npc_dialogue_this_turn.lower()
                        if actual_npc_speaker_name and not is_ponder_message and not npc_dialogue_this_turn.lower().startswith(f"{actual_npc_speaker_name.lower()}:"): lsl_response = f"{actual_npc_speaker_name}: {npc_dialogue_this_turn}"
                        else: lsl_response = npc_dialogue_this_turn
                    else:
                        relevant_system_message = next((msg for msg in system_msgs_cleaned if "Moving to" in msg or "You are now in" in msg or "Started talking to" in msg or "already talking to" in msg or "not found in" in msg), None)
                        if relevant_system_message: lsl_response = relevant_system_message
                        else: lsl_response = "Action acknowledged."
                else:
                    if not npc_dialogue_this_turn:
                        generic_cmd_message = next((msg for msg in system_msgs_cleaned), None)
                        if generic_cmd_message: lsl_response = generic_cmd_message
                        else: lsl_response = "Action acknowledged."
            if (not is_command_input and npc_dialogue_this_turn) or (not lsl_response and npc_dialogue_this_turn and is_command_input):
                is_ponder_message = "seems to ponder" in npc_dialogue_this_turn.lower()
                if actual_npc_speaker_name and not is_ponder_message and not npc_dialogue_this_turn.lower().startswith(f"{actual_npc_speaker_name.lower()}:"): lsl_response = f"{actual_npc_speaker_name}: {npc_dialogue_this_turn}"
                else: lsl_response = npc_dialogue_this_turn
        should_add_suffix = False; last_speaker_from_data = response_data.get('last_speaker_for_suffix')
        if last_speaker_from_data and npc_dialogue_this_turn and not ("seems to ponder" in npc_dialogue_this_turn.lower()):
            if not (what_it_says_for_command_check.lower().startswith("/help") or what_it_says_for_command_check.lower().startswith(("/inventory", "/inv")) or any(cmd_key in what_it_says_for_command_check.lower() for cmd_key in ["listareas", "/listareas", "/areas", "list areas", "areas"])):
                if not is_command_input or command_produces_npc_dialogue: should_add_suffix = True
        if should_add_suffix and last_speaker_from_data:
            suffix = f" | {last_speaker_from_data} >"
            if len(lsl_response + suffix) <= MAX_LSL_STRING_LENGTH: lsl_response += suffix
        lsl_response = lsl_response.strip()[:MAX_LSL_STRING_LENGTH]
        if not lsl_response.strip():
            if not is_command_input and actual_npc_speaker_name:
                lsl_response = f"*{actual_npc_speaker_name} is quiet for a moment.*"
                if should_add_suffix and actual_npc_speaker_name:
                    suffix = f" | {actual_npc_speaker_name} >"
                    if len(lsl_response + suffix) <= MAX_LSL_STRING_LENGTH: lsl_response += suffix
            elif not is_command_input: lsl_response = "The realm echoes your words, but no one answers directly."
            else:
                lsl_response = "Action acknowledged."
                if actual_npc_speaker_name and response_data.get('current_npc_name'):
                    current_npc_still_active = response_data.get('current_npc_name')
                    if current_npc_still_active and not is_command_handled_specifically:
                        suffix = f" | {current_npc_still_active} >"
                        if len(lsl_response + suffix) <= MAX_LSL_STRING_LENGTH: lsl_response += suffix
        # END OF COPIED LSL FORMATTING LOGIC

        return lsl_response, stripped_headers_display, cleaned_message_display, sl_context_display

    except Exception as e:
        error_msg = f"ERROR: Game system issue. ({type(e).__name__})"
        if game_system_manager.debug_mode: # type: ignore
            print(f"[ERROR TRACEBACK for {player_id_for_system}]: {traceback.format_exc()}")
        return error_msg, stripped_headers_display, cleaned_message_display, sl_context_display


# --- Gradio Interface Definition ---
fantasy_css = """
body, .gradio-container { font-family: 'Merriweather', serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: #e6e6fa; }
.gr-button { background: linear-gradient(45deg, #4a148c, #6a1b9a) !important; border: 1px solid #7b1fa2 !important; color: #e1bee7 !important; border-radius: 8px !important; font-weight: bold !important; }
.gr-button:hover { background: linear-gradient(45deg, #6a1b9a, #8e24aa) !important; box-shadow: 0 2px 8px rgba(106, 27, 154, 0.4) !important; }
.gr-input input, .gr-textbox textarea { background: rgba(30, 30, 60, 0.8) !important; border: 1px solid #7b1fa2 !important; color: #e6e6fa !important; border-radius: 6px !important; }
.gr-panel { background: rgba(25, 25, 50, 0.7) !important; border: 1px solid #4a148c !important; border-radius: 8px !important; padding: 15px !important; }
.gr-markdown { color: #e6e6fa !important; } 
.gr-markdown h1, .gr-markdown h2, .gr-markdown h3 { color: #bb86fc !important; text-shadow: 1px 1px 3px #301934; }
.gr-markdown strong { color: #cf9fff !important; } 
.gr-markdown code { background-color: rgba(74, 20, 140, 0.5); color: #f3e5f5; padding: 2px 5px; border-radius: 4px;}
.gr-label > .label-text { color: #ce93d8 !important; font-weight: bold; }
.info_display_box { background-color: rgba(40,40,70,0.5); border: 1px solid #5e35b1; padding: 10px; border-radius: 5px; margin-top: 5px; font-size: 0.9em; }
"""

title_html = """
<div style="text-align: center; margin-bottom: 20px;">
    <h1 style="color: #bb86fc; font-size: 2.5em; text-shadow: 2px 2px 5px #301934;">🔮 Eldoria LSL Context Simulator 🔮</h1>
    <p style="color: #cf9fff; font-size: 1.1em;">Simulate LSL messages with full context headers.</p>
</div>
"""

with gr.Blocks(theme=gr.themes.Base(font=[gr.themes.GoogleFont("Merriweather"), "serif"]), css=fantasy_css) as interface:
    gr.HTML(title_html)

    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### LSL Requester Info (Simulated Headers)")
            owner_key_input = gr.Textbox(label="🔑 X-SecondLife-Owner-Key (Player ID)", placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", value="00000000-0000-0000-0000-000000000001")
            owner_name_input = gr.Textbox(label="👤 X-SecondLife-Owner-Name", placeholder="e.g., Player Resident", value="Player Resident")
            region_info_input = gr.Textbox(label="🗺️ X-SecondLife-Region", placeholder="e.g., Eldoria (1000,1000)", value="Simulated Region (1024,1024)")
            object_name_input = gr.Textbox(label="📦 X-SecondLife-Object-Name", placeholder="e.g., Communication HUD", value="Eldoria HUD")
            object_key_input = gr.Textbox(label="🗝️ X-SecondLife-Object-Key", placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", value="11111111-1111-1111-1111-111111111111")
            local_pos_input = gr.Textbox(label="📍 X-SecondLife-Local-Position", placeholder="e.g., (128.0, 128.0, 30.0)", value="(128.5, 60.2, 25.0)")
            shard_input = gr.Textbox(label="🌐 X-SecondLife-Shard", placeholder="e.g., Production or Agni", value="Production")

            gr.Markdown("### Message Payload")
            raw_message_payload_input = gr.Textbox(label="📜 LSL Message Payload (Can still include prefixed headers)", placeholder="e.g., /go tavern OR 12345:Hello", lines=3)

            send_button = gr.Button("⚡ Send to Eldoria", variant="primary")

        with gr.Column(scale=3):
            gr.Markdown("### ➡️ Processing & Response")
            sl_context_info_display = gr.Textbox(label="🛰️ Simulated SL Headers (Passed to Game if Backend Supports)", interactive=False, lines=8, elem_classes="info_display_box")
            stripped_payload_headers_info = gr.Textbox(label="✂️ Headers Stripped from Payload String", interactive=False, elem_classes="info_display_box")
            cleaned_payload_info = gr.Textbox(label="✉️ Message Payload String to Game", interactive=False, elem_classes="info_display_box")

            gr.Markdown("### 💬 Eldoria's Response to LSL")
            response_output = gr.Textbox(label="", lines=6, interactive=False, placeholder="Eldoria's reply will appear here...")

    gr.Markdown("---")
    with gr.Accordion("ℹ️ Simulator Guide & Header Info", open=False):
        gr.Markdown("""
        ### How to Use:
        1.  **LSL Requester Info:** Fill in the `X-SecondLife-*` header values as they would be sent by the simulator. The `Owner-Key` is used as the Player ID for session management.
        2.  **Message Payload:** Enter the string part of the message. This payload can *also* have script-prefixed headers (like a channel or another UUID), which the "Headers Stripped from Payload String" logic will try to remove.
        3.  **Send to Eldoria:** The simulator will:
            *   Package the `X-SecondLife-*` fields as a simulated header context.
            *   Attempt to strip any *additional* prefixes from the "Message Payload" string itself.
            *   Send the cleaned payload string to the game logic.
            *   **Currently, the backend `GameSystem` is NOT modified to directly use the `X-SecondLife-*` headers.** This frontend just shows you what *would* be available.
        4.  **Processing & Response:** Shows the simulated SL headers, what was stripped from the payload string, the final payload string sent to the game, and Eldoria's reply.

        ### Common Game Commands (for the Message Payload):
        *   `/help`, `/go <area>`, `/talk <npc>`, `/inventory`, `/hint`, `/exit`
        """)

    send_button.click(
        fn=ask_lsl_with_context_frontend_only,
        inputs=[owner_key_input, owner_name_input, region_info_input, object_name_input, object_key_input, local_pos_input, shard_input, raw_message_payload_input],
        outputs=[response_output, stripped_payload_headers_info, cleaned_payload_info, sl_context_info_display]
    )
    raw_message_payload_input.submit(
        fn=ask_lsl_with_context_frontend_only,
        inputs=[owner_key_input, owner_name_input, region_info_input, object_name_input, object_key_input, local_pos_input, shard_input, raw_message_payload_input],
        outputs=[response_output, stripped_payload_headers_info, cleaned_payload_info, sl_context_info_display]
    )

if __name__ == "__main__":
    print("Launching Eldoria LSL Context Simulator Gradio Interface...")
    from dotenv import load_dotenv
    load_dotenv()
    if "OPENROUTER_API_KEY" not in os.environ and "free" not in os.environ.get("OPENROUTER_DEFAULT_MODEL", ""):
        print("Warning: OPENROUTER_API_KEY not found. Some models may not work.")

    interface.launch(
        server_name="0.0.0.0",
        server_port=7863, # Yet another port
        share=os.environ.get('GRADIO_SHARE', 'True').lower() == 'true',
        debug=True
    )