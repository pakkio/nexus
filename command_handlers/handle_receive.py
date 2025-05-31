from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_receive(args: str, state: Dict[str, Any]) -> HandlerResult:
  """
  Handle the /receive command - explicitly request an item from the current NPC.
  
  This is different from /give (player gives to NPC) and different from dialogue.
  /receive is for direct, imperative requests: "I want X", "Give me Y".
  
  Usage: /receive <item_name>
  Examples:
    /receive diary
    /receive Ancient Scroll
    /receive 100 Credits
  """
  TF = state.get('TerminalFormatter')
  current_npc = state.get('current_npc')
  chat_session = state.get('chat_session')
  
  if not current_npc or not chat_session:
    print(f"{TF.YELLOW}You need to be talking to an NPC to use /receive.{TF.RESET}")
    print(f"{TF.DIM}Use /go <area> and /talk <npc> first.{TF.RESET}")
    return state
  
  if not args.strip():
    print(f"{TF.YELLOW}Usage: /receive <item_name>{TF.RESET}")
    print(f"{TF.DIM}Examples:{TF.RESET}")
    print(f"{TF.DIM}  /receive diary{TF.RESET}")
    print(f"{TF.DIM}  /receive Ancient Scroll{TF.RESET}")
    print(f"{TF.DIM}  /receive 100 Credits{TF.RESET}")
    return state
  
  item_requested = args.strip()
  npc_name = current_npc.get('name', 'this NPC')
  
  # Create an imperative request message for the LLM
  if item_requested.lower().endswith('credits') or item_requested.lower().startswith('credits'):
    # Handle credits request
    request_message = f"Dammi {item_requested}."
  else:
    # Handle item request
    request_message = f"Dammi {item_requested}."
  
  print(f"{TF.DIM}[Requesting '{item_requested}' from {npc_name}]{TF.RESET}")
  
  # Add the request to chat history as user message
  chat_session.add_message("user", request_message)
  
  # Add to profile actions
  _add_profile_action(state, f"Directly requested '{item_requested}' from {npc_name} using /receive command")
  
  # Set flag to force NPC response
  state['force_npc_turn_after_command'] = True
  
  return state

def handle_receive_help():
  """Return help text for the /receive command."""
  return """
/receive <item_name> - Directly request an item from the current NPC

This command makes an imperative request to the NPC. Unlike polite dialogue 
questions like "do you have something for me?", /receive is direct: "Give me X".

Examples:
  /receive diary               → "Dammi diary."
  /receive Ancient Scroll      → "Dammi Ancient Scroll."  
  /receive 100 Credits         → "Dammi 100 Credits."

The NPC may:
- Give you the item if they have it and trust you
- Refuse if they don't trust you or want something in return
- Ask for payment or a trade
- Simply not have the item

This is different from:
- /give (you give items TO the NPC)
- Normal dialogue like "hai qualcosa per me?" (polite asking)
"""

if __name__ == "__main__":
  # Test the receive handler
  from unittest.mock import MagicMock
  
  # Create mock state
  mock_tf = type('MockTF', (), {
    'YELLOW': '', 'RESET': '', 'DIM': '', 'GREEN': ''
  })
  
  mock_npc = {'name': 'Test NPC', 'code': 'test_npc'}
  mock_session = MagicMock()
  
  test_state = {
    'TerminalFormatter': mock_tf,
    'current_npc': mock_npc,
    'chat_session': mock_session,
    'actions_this_turn_for_profile': []
  }
  
  # Test with valid args
  result = handle_receive("Ancient Diary", test_state)
  assert result['force_npc_turn_after_command'] == True
  assert len(result['actions_this_turn_for_profile']) > 0
  mock_session.add_message.assert_called_with("user", "Dammi Ancient Diary.")
  
  # Test with credits
  result = handle_receive("50 Credits", test_state)
  mock_session.add_message.assert_called_with("user", "Dammi 50 Credits.")
  
  print("✓ handle_receive tests passed")