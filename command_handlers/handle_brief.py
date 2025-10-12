"""
Command handler for /brief - Toggle brief mode for concise NPC responses
"""
from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_brief(state: Dict[str, Any]) -> HandlerResult:
    """
    Toggle brief mode: NPCs respond concisely without narrative flourishes.

    Usage: /brief [on|off]
    """
    args = state.get('args', [])

    # Get current brief mode state
    current_brief_mode = state.get('brief_mode', False)

    # Determine new state
    if args:
        arg = args[0].lower()
        if arg in ['on', 'true', '1', 'yes', 'attiva', 'si']:
            new_state = True
        elif arg in ['off', 'false', '0', 'no', 'disattiva']:
            new_state = False
        else:
            print(f"Argomento non valido: '{arg}'. Usa: /brief [on|off]")
            return {**state, 'status': 'error', 'continue_loop': True}
    else:
        # Toggle if no argument provided
        new_state = not current_brief_mode

    # Update game state
    state['brief_mode'] = new_state

    # Prepare response
    if new_state:
        print("✓ Modalità Brief ATTIVATA - Gli NPC risponderanno in modo conciso ed essenziale.")
    else:
        print("✓ Modalità Brief DISATTIVATA - Gli NPC risponderanno con dettagli narrativi completi.")

    _add_profile_action(state, f"Toggled brief mode to {new_state}")

    return {**state, 'status': 'ok', 'continue_loop': True}
