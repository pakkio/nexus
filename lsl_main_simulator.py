# lsl_main_simulator.py
import os
import sys
from dotenv import load_dotenv
import traceback
import re
from typing import List # Added for type hinting
from main_utils import get_help_text # Per il comando /help


# Ensure the parent directory is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

load_dotenv()

from game_system_api import GameSystem, clean_ansi_codes
from main_utils import get_help_text # For the /help command

game_system_manager = GameSystem(
    use_mockup=True,
    mockup_dir="database_lsl_sim",
    model_name=os.environ.get("OPENROUTER_DEFAULT_MODEL", "google/gemma-2-9b-it:free"),
    debug_mode=True
)

def item_pattern_match(message_line: str) -> bool:
    return bool(re.match(r"^\s*[-*•\w]", message_line))

def ask_lsl(avatar_name: str, what_it_says: str) -> str:
    """
        Produce una risposta singola e pulita per LSL.
        """
    print(f"\n--- LSL Request from '{avatar_name}' ---")
    print(f"Input: '{what_it_says}'")

    player_game_system = None
    try:
        player_game_system = game_system_manager.get_player_system(avatar_name)
        response_data = player_game_system.process_player_input(what_it_says)

        lsl_response = ""
        MAX_LSL_STRING_LENGTH = 1000

        npc_dialogue_this_turn = clean_ansi_codes(response_data['npc_response']).strip()
        actual_npc_speaker_name = response_data.get('current_npc_name')
        # Filtra i messaggi di sistema per escludere "profile updated" a meno che non sia l'unico messaggio,
        # o a meno che non sia specificamente richiesto per il debug LSL.
        # Per LSL minimale, di solito lo omettiamo se c'è altro output.
        system_msgs_cleaned = [
            clean_ansi_codes(msg).strip() for msg in response_data['system_messages']
            if clean_ansi_codes(msg).strip() and not "psychological profile has been updated" in msg.lower()
        ]
        # Se l'unico messaggio di sistema era quello del profilo, e non c'è altro output, potremmo volerlo includere.
        # Ma per ora, lo filtriamo per un output LSL più pulito.
        # Se system_msgs_cleaned è vuoto e c'era un messaggio di profilo, potremmo riconsiderarlo.
        if not system_msgs_cleaned and "psychological profile has been updated" in " ".join(response_data['system_messages']).lower():
            if game_system_manager.debug_mode: # Solo se il debug LSL è esplicitamente voluto
                system_msgs_cleaned = ["Profile updated (debug)."]


        is_command_input = what_it_says.startswith("/") or \
                           any(what_it_says.lower().startswith(cmd_start) for cmd_start in
                               ["go ", "talk ", "list ", "areas", "who", "whereami", "npcs", "inv", "inventory", "give ", "receive ", "profile", "stats", "clear", "history", "hint", "endhint"])

        is_command_handled_specifically = False
        command_produces_npc_dialogue = False

        # 1. Gestione specifica per comandi con output LSL prioritario
        if what_it_says.lower().startswith("/exit") and response_data['status'] == 'exit':
            game_system_manager.close_player_session(avatar_name)
            lsl_response = "You have exited the game. Farewell!"
            if actual_npc_speaker_name:
                lsl_response += f" (You were speaking with {actual_npc_speaker_name})"
            is_command_handled_specifically = True
        elif what_it_says.lower().startswith("/help"):
            help_text_content = get_help_text(player_game_system.game_state if player_game_system else None)
            lsl_response = clean_ansi_codes(help_text_content).strip()
            lsl_response = lsl_response[:MAX_LSL_STRING_LENGTH]
            is_command_handled_specifically = True
        elif what_it_says.lower().startswith(("/inventory", "inv")):
            # Cerca messaggi di sistema che contengono l'inventario
            # "--- Your Inventory ---" dovrebbe ora passare il filtro in _SinglePlayerGameSystem
            inv_parts = [msg for msg in system_msgs_cleaned if "Your Inventory" in msg or "Credits:" in msg or item_pattern_match(msg) or "Your Possessions" in msg]
            if inv_parts:
                # Rimuovi "--- Your Inventory ---" se è seguito da altre parti, per evitare ridondanza.
                # Unisci con spazio per LSL, dato che LSL non gestisce bene \n in una singola llSay.
                lsl_response = " ".join(inv_parts).replace("--- Your Inventory ---", "Inventory:").strip()
            else:
                lsl_response = "Your inventory is empty or could not be displayed."
            is_command_handled_specifically = True
        elif any(cmd_key in what_it_says.lower() for cmd_key in ["listareas", "/listareas", "/areas", "list areas", "areas"]):
            area_list_messages = [
                msg for msg in system_msgs_cleaned
                if msg.startswith("Available Areas:") or
                   ("➢" in msg and "Credits" not in msg) or
                   (msg.count(',') >= 2 and "Credits" not in msg and "profile" not in msg.lower())
            ]
            if area_list_messages:
                # Unisci con spazio per una singola linea LSL
                joined_areas = " ".join(area_list_messages)
                # Semplifica l'output se inizia con "Available Areas:"
                if joined_areas.startswith("Available Areas:"):
                    lsl_response = joined_areas.replace("Available Areas:", "Areas:").replace("➢", "").strip()
                else:
                    lsl_response = f"Areas: {joined_areas.replace('➢', '').strip()}"
                lsl_response = re.sub(r'\s{2,}', ' ', lsl_response) # Rimuovi spazi multipli
            else:
                lsl_response = "No areas found or an error occurred listing them."
            is_command_handled_specifically = True

        # 2. Se non gestito specificamente sopra, considera se è un comando o dialogo
        if not is_command_handled_specifically:
            if is_command_input: # È un comando, ma non uno di quelli con output LSL speciale
                if any(cmd_key in what_it_says.lower() for cmd_key in ["go ", "/go ", "talk ", "/talk"]):
                    if npc_dialogue_this_turn:
                        command_produces_npc_dialogue = True
                        is_ponder_message = "seems to ponder" in npc_dialogue_this_turn.lower()
                        if actual_npc_speaker_name and not is_ponder_message and \
                                not npc_dialogue_this_turn.lower().startswith(f"{actual_npc_speaker_name.lower()}:"):
                            lsl_response = f"{actual_npc_speaker_name}: {npc_dialogue_this_turn}"
                        else:
                            lsl_response = npc_dialogue_this_turn
                    else:
                        relevant_system_message = next((msg for msg in system_msgs_cleaned if "Moving to" in msg or "You are now in" in msg or "Started talking to" in msg or "already talking to" in msg or "not found in" in msg), None)
                        if relevant_system_message:
                            lsl_response = relevant_system_message
                        else:
                            lsl_response = "Action acknowledged."
                else: # Altri comandi non gestiti specificamente (es. /who, /whereami, /stats, ecc.)
                    if not npc_dialogue_this_turn:
                        # Prendi il primo messaggio di sistema rilevante se c'è
                        generic_cmd_message = next((msg for msg in system_msgs_cleaned), None)
                        if generic_cmd_message:
                            lsl_response = generic_cmd_message
                        else:
                            lsl_response = "Action acknowledged."
                    # Altrimenti, se npc_dialogue_this_turn è popolato (improbabile per questi comandi), verrà usato sotto.

            # Se non è un comando (dialogo diretto) E c'è una risposta NPC
            if not is_command_input and npc_dialogue_this_turn:
                is_ponder_message = "seems to ponder" in npc_dialogue_this_turn.lower()
                if actual_npc_speaker_name and not is_ponder_message and \
                        not npc_dialogue_this_turn.lower().startswith(f"{actual_npc_speaker_name.lower()}:"):
                    lsl_response = f"{actual_npc_speaker_name}: {npc_dialogue_this_turn}"
                else:
                    lsl_response = npc_dialogue_this_turn
            # Se era un comando ma lsl_response è ancora vuota e l'NPC ha parlato
            elif not lsl_response and npc_dialogue_this_turn and is_command_input:
                is_ponder_message = "seems to ponder" in npc_dialogue_this_turn.lower()
                if actual_npc_speaker_name and not is_ponder_message and \
                        not npc_dialogue_this_turn.lower().startswith(f"{actual_npc_speaker_name.lower()}:"):
                    lsl_response = f"{actual_npc_speaker_name}: {npc_dialogue_this_turn}"
                else:
                    lsl_response = npc_dialogue_this_turn

        # 3. Aggiunta del suffisso NPC
        should_add_suffix = False
        last_speaker_from_data = response_data.get('last_speaker_for_suffix')

        if last_speaker_from_data and npc_dialogue_this_turn and not ("seems to ponder" in npc_dialogue_this_turn.lower()):
            if not (what_it_says.lower().startswith("/help") or \
                    what_it_says.lower().startswith(("/inventory", "inv")) or \
                    any(cmd_key in what_it_says.lower() for cmd_key in ["listareas", "/listareas", "/areas", "list areas", "areas"])):
                if not is_command_input or command_produces_npc_dialogue: # Se è dialogo o un comando che fa parlare l'NPC
                    should_add_suffix = True

        if should_add_suffix and last_speaker_from_data:
            suffix = f" | {last_speaker_from_data} >"
            if len(lsl_response + suffix) <= MAX_LSL_STRING_LENGTH:
                lsl_response += suffix

        # 4. Troncatura finale e fallback
        lsl_response = lsl_response.strip()
        lsl_response = lsl_response[:MAX_LSL_STRING_LENGTH]

        if not lsl_response.strip():
            if not is_command_input and actual_npc_speaker_name:
                lsl_response = f"*{actual_npc_speaker_name} is quiet for a moment.*"
                if should_add_suffix and actual_npc_speaker_name:
                    suffix = f" | {actual_npc_speaker_name} >"
                    if len(lsl_response + suffix) <= MAX_LSL_STRING_LENGTH:
                        lsl_response += suffix
            elif not is_command_input:
                lsl_response = "The realm echoes your words, but no one answers directly."
            else:
                lsl_response = "Action acknowledged."
                if actual_npc_speaker_name and response_data.get('current_npc_name'):
                    current_npc_still_active = response_data.get('current_npc_name')
                    if current_npc_still_active and not is_command_handled_specifically: # Non aggiungere suffisso se il comando ha output speciale
                        suffix = f" | {current_npc_still_active} >"
                        if len(lsl_response + suffix) <= MAX_LSL_STRING_LENGTH:
                            lsl_response += suffix

        return lsl_response

    except Exception as e:
        error_msg = f"ERROR: Game system issue. ({type(e).__name__})"
        if game_system_manager.debug_mode:
            print(f"[ERROR TRACEBACK for {avatar_name}]: {traceback.format_exc()}")
        return error_msg


if __name__ == "__main__":
    print("\n--- LSL Interaction Simulation Started (Minimal Output Mode) ---")
    print("Type player's name, then their message. Type '/exit_sim' to quit.")

    while True:
        try:
            player_name_input = input("Enter Avatar Name (or /exit_sim): ").strip()
            if player_name_input.lower() == "/exit_sim":
                print("Exiting LSL simulation.")
                break
            if not player_name_input:
                print("Avatar name cannot be empty. Try again.")
                continue

            player_message_input = input(f"Enter {player_name_input}'s message: ").strip()

            response_from_game = ask_lsl(player_name_input, player_message_input)
            print(f"\n<<< RESPONSE TO LSL >>>\n{response_from_game}\n")

        except KeyboardInterrupt:
            print("\nSimulation interrupted.")
            break
        except Exception as e:
            print(f"\nUnhandled error in simulation loop: {e}")
            traceback.print_exc()
            continue