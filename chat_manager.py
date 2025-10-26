# Path: chat_manager.py
# Updated Version (Fix for get_history)
# MODIFIED: Added current_npc_name_for_placeholder to ask method for better empty response placeholders
from dotenv import load_dotenv

load_dotenv()

import time
import random
import re
from typing import List, Dict, Optional, Tuple, Any
import traceback # Added for more detailed error printing if needed

# Importa le dipendenze necessarie
try:
    from llm_wrapper import llm_wrapper
    from terminal_formatter import TerminalFormatter
    from llm_stats_tracker import get_global_stats_tracker
except ImportError as e:
    print(f"Error importing modules in chat_manager.py: {e}")
    class TerminalFormatter:
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; ITALIC = "" # Added ITALIC for placeholder
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))
        @staticmethod
        def get_terminal_width(): return 80


def extract_notecard_from_response(npc_response: str) -> Tuple[str, str, str]:
    """Extract notecard command from NPC response if present.

    Looks for format: [notecard=NotecardName|NotecardContent]

    Args:
        npc_response: The NPC's response text

    Returns:
        Tuple of (cleaned_response, notecard_name, notecard_content)
        - cleaned_response: Response with notecard command removed
        - notecard_name: Name of the notecard (empty if none found)
        - notecard_content: Content of the notecard (empty if none found)
    """
    # Look for notecard command in format [notecard=Name|Content]
    # We need to find the LAST closing bracket that's preceded by content

    import logging
    logger = logging.getLogger(__name__)

    start_marker = "[notecard="
    start_idx = npc_response.find(start_marker)

    if start_idx == -1:
        logger.warning(f"[NOTECARD_EXTRACT] ✗ NO [notecard=...] FOUND in LLM response")
        logger.warning(f"[NOTECARD_EXTRACT] Response length: {len(npc_response)} chars")
        logger.warning(f"[NOTECARD_EXTRACT] First 300 chars: {npc_response[:300]}")
        logger.warning(f"[NOTECARD_EXTRACT] Last 300 chars: {npc_response[-300:]}")
        return npc_response, "", ""

    # Find the pipe separator
    pipe_idx = npc_response.find("|", start_idx)
    if pipe_idx == -1:
        return npc_response, "", ""

    # Extract notecard name (between = and |)
    notecard_name = npc_response[start_idx + len(start_marker):pipe_idx].strip()

    # Now find the closing bracket. The content can contain brackets, so we need
    # to find a ] that closes the command. Look for the last ] that makes sense.
    # We'll use a simple heuristic: the closing bracket should be followed by
    # content that doesn't start with a bracket (or is end of string or whitespace)

    # Start searching for ] after the pipe
    search_start = pipe_idx + 1
    end_idx = -1

    # Scan forward to find the closing bracket
    # We look for patterns like: content] followed by non-bracket or end of string
    for i in range(search_start, len(npc_response)):
        if npc_response[i] == "]":
            # Check if this could be the end
            # Look at what comes after
            after_idx = i + 1
            if after_idx >= len(npc_response):
                # End of string
                end_idx = i
                break
            elif npc_response[after_idx] in (' ', '\n', '.', ',', '!', '?'):
                # Followed by whitespace or punctuation
                end_idx = i
                break
            # Otherwise, could be content with ] in it, keep searching

    # If we didn't find a clear ending, look for the last ]
    if end_idx == -1:
        end_idx = npc_response.rfind("]", search_start)

    if end_idx == -1:
        return npc_response, "", ""

    # Extract notecard content (between | and ])
    notecard_content = npc_response[pipe_idx + 1:end_idx].strip()

    # Strip all unicode escape sequences to ensure clean ASCII in notecard
    import re
    # Remove patterns like \ud83d, \u2713, etc - replace with nothing
    notecard_content = re.sub(r'\\u[0-9a-fA-F]{4}', '', notecard_content)

    # Remove the notecard command from the response
    cleaned_response = npc_response[:start_idx] + npc_response[end_idx + 1:]

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[NOTECARD] ✓ EXTRACTED: name='{notecard_name}', content_length={len(notecard_content)}")

    return cleaned_response.strip(), notecard_name, notecard_content


def generate_summary_for_llsettext(npc_response: str, npc_name: str = "NPC") -> str:
    """Generate a short summary of the NPC response for llSetText display.

    Args:
        npc_response: The full NPC response text
        npc_name: Name of the NPC

    Returns:
        Short summary (max 80 chars) suitable for llSetText
    """
    if not npc_response:
        return ""

    # Clean up the response text
    clean_text = npc_response.strip()
    # Remove markdown and formatting
    clean_text = clean_text.replace('*', '').replace('_', '')
    # Remove LSL protocol-breaking characters
    clean_text = clean_text.replace(';', ',').replace(']', ')')
    # Convert newlines to ~ for LSL line break processing
    clean_text = clean_text.replace('\n', '~')
    # Remove common prefixes
    for prefix in [f"{npc_name} ti dice", f"{npc_name} ti informa", "*", "- "]:
        clean_text = clean_text.replace(prefix, "").strip()

    # Take first sentence or first 80 characters
    if '.' in clean_text:
        first_sentence = clean_text.split('.')[0].strip()
        if len(first_sentence) <= 80:
            return first_sentence
        # If first sentence is too long, truncate at word boundary
        words = first_sentence.split()
        summary = ""
        for word in words:
            if len(summary + " " + word) > 77:  # Leave room for "..."
                break
            summary += (" " + word if summary else word)
        return summary + "..."
    else:
        # No period found, just truncate
        if len(clean_text) <= 80:
            return clean_text
        # Truncate at word boundary
        words = clean_text.split()
        summary = ""
        for word in words:
            if len(summary + " " + word) > 77:
                break
            summary += (" " + word if summary else word)
        return summary + "..."


def generate_sl_command_prefix(npc_data: Optional[Dict[str, Any]], include_teleport: bool = False, npc_response: str = "", include_notecard: bool = False, notecard_content: str = "", notecard_name: str = "") -> str:
    """Generate Second Life command prefix for NPC responses.

    Args:
        npc_data: Dictionary containing NPC data with SL fields
        include_teleport: If True, includes teleport coordinates from NPC data
        npc_response: The NPC's response text to generate summary for llSetText
        include_notecard: If True, creates and gives a notecard to the player
        notecard_content: The content for the notecard (efficient quoting preserved)
        notecard_name: Explicit notecard name (if not provided, uses default from NPC data)

    Returns:
        String in format [lookup=?;llSetText=?;emote=?;anim=?;teleport=?;notecard=?] or empty string if no NPC data
    """
    if not npc_data:
        return ""

    # Get SL fields from NPC data
    emotes_str = npc_data.get('emotes', '')
    animations_str = npc_data.get('animations', '')
    lookup_str = npc_data.get('lookup', '')
    llsettext_str = npc_data.get('llsettext', '')
    teleport_str = npc_data.get('teleport', '')
    # Use explicit notecard_name if provided, otherwise use NPC default
    notecard_name_str = notecard_name if notecard_name else npc_data.get('notecard_name', f"{npc_data.get('name', 'NPC')}_Note")

    # Parse comma-separated values and pick random ones
    emotes_list = [e.strip() for e in emotes_str.split(',') if e.strip()] if emotes_str else []
    animations_list = [a.strip() for a in animations_str.split(',') if a.strip()] if animations_str else []
    lookup_list = [l.strip() for l in lookup_str.split(',') if l.strip()] if lookup_str else []
    llsettext_list = [t.strip() for t in llsettext_str.split(',') if t.strip()] if llsettext_str else []

    # Select random values from each category
    selected_emote = random.choice(emotes_list) if emotes_list else ""
    selected_animation = random.choice(animations_list) if animations_list else ""
    selected_lookup = random.choice(lookup_list) if lookup_list else ""

    # Generate summary from npc_response if available, otherwise use predefined llsettext
    if npc_response:
        npc_name = npc_data.get('name', 'NPC')
        selected_llsettext = generate_summary_for_llsettext(npc_response, npc_name)
    else:
        selected_llsettext = random.choice(llsettext_list) if llsettext_list else ""

    # Teleport: Only include if explicitly requested via include_teleport flag
    # The entire teleport string is treated as one coordinate set (x,y,z format)
    selected_teleport = teleport_str.strip() if include_teleport and teleport_str else ""

    # Notecard: Create efficient quoted notecard content if requested
    # Uses URL encoding for efficient LSL quoting to avoid choking the script
    notecard_command = ""
    if include_notecard and notecard_content:
        # Efficient quoting: escape only necessary characters for LSL string
        # IMPORTANT: Do NOT escape backslashes first - this breaks Unicode escape sequences
        # Only escape quotes and newlines - Unicode chars (emojis) will pass through intact
        # Truncate BEFORE escaping to avoid heap overflow in LSL scripts
        truncated_content = notecard_content[:600]  # Reduced from 1000 to 600 for safety with escaping overhead
        # Order matters! Escape quotes and newlines, but NOT backslashes (keeps Unicode intact)
        escaped_content = truncated_content.replace('"', '\\"').replace("\n", "\\n")
        notecard_command = f"notecard={notecard_name_str}|{escaped_content}"

    # Build the command prefix - only include non-empty fields
    command_parts = []
    if selected_lookup:
        command_parts.append(f"lookup={selected_lookup}")
    if selected_llsettext:
        command_parts.append(f"llSetText={selected_llsettext}")
    if selected_emote:
        command_parts.append(f"emote={selected_emote}")
    if selected_animation:
        command_parts.append(f"anim={selected_animation}")
    if selected_teleport:
        command_parts.append(f"teleport={selected_teleport}")
    if notecard_command:
        command_parts.append(notecard_command)

    if command_parts:
        return f"[{';'.join(command_parts)}]"

    return ""


def format_stats(stats: Optional[Dict[str, Any]], model_type: str = "dialogue") -> str:
    """Formatta il dizionario delle statistiche per una visualizzazione leggibile.
    
    Args:
        stats: Dictionary of stats or None to use global tracker
        model_type: Type of model for filtering stats
    """
    if stats is None:
        # Use global stats tracker
        try:
            tracker = get_global_stats_tracker()
            return tracker.format_last_stats(model_type)
        except:
            return f"{TerminalFormatter.DIM}Statistiche non disponibili.{TerminalFormatter.RESET}"
    
    # Legacy format for backward compatibility
    if not stats:
        return f"{TerminalFormatter.DIM}Statistiche non disponibili.{TerminalFormatter.RESET}"

    lines = [f"{TerminalFormatter.BOLD}Statistiche Ultima Chiamata:{TerminalFormatter.RESET}"]
    model = stats.get("model", "N/D")
    lines.append(f"{TerminalFormatter.DIM}- Modello: {model}{TerminalFormatter.RESET}")
    total_time = stats.get("total_time")
    if total_time is not None: lines.append(f"{TerminalFormatter.DIM}- Tempo Totale: {total_time:.2f}s{TerminalFormatter.RESET}")
    first_token_time = stats.get("time_to_first_token")
    if first_token_time is not None: lines.append(f"{TerminalFormatter.DIM}- Tempo al Primo Token: {first_token_time:.2f}s{TerminalFormatter.RESET}")
    in_tokens, out_tokens, tot_tokens = stats.get("input_tokens", "N/D"), stats.get("output_tokens", "N/D"), stats.get("total_tokens", "N/D")
    lines.append(f"{TerminalFormatter.DIM}- Tokens (Input/Output/Total): {in_tokens} / {out_tokens} / {tot_tokens}{TerminalFormatter.RESET}")
    if isinstance(total_time, (int, float)) and isinstance(out_tokens, int) and out_tokens > 0 and total_time > 0:
        lines.append(f"{TerminalFormatter.DIM}- Throughput Output: {out_tokens / total_time:.2f} tokens/s{TerminalFormatter.RESET}")
    return "\n".join(lines)


def build_npc_system_prompt(game_session_state, npc_name=None):
    """Build system prompt for regular NPCs (not wise guides)

    This is a wrapper that gets called dynamically when brief mode changes.
    It looks up the current NPC from game_state and builds the full prompt.
    """
    # Import here to avoid circular import
    from session_utils import build_system_prompt
    from terminal_formatter import TerminalFormatter

    # Get NPC data from game state
    db = game_session_state.get('db')
    current_npc = game_session_state.get('current_npc')
    story = game_session_state.get('storyboard_text', '')

    if not current_npc or not db:
        # Fallback: return empty string if we don't have enough context
        return ""

    # Get llm_wrapper if available for profile distillation
    try:
        from llm_wrapper import llm_wrapper
        llm_func = llm_wrapper
    except:
        llm_func = None

    # Call the full build_system_prompt which loads PREFIX files
    try:
        system_prompt = build_system_prompt(
            npc=current_npc,
            story=story,
            TF=TerminalFormatter,
            game_session_state=game_session_state,
            conversation_summary_for_guide_context=None,  # Not for guides
            llm_wrapper_func_for_distill=llm_func
        )
        return system_prompt
    except Exception as e:
        print(f"Warning: Error building NPC system prompt: {e}")
        import traceback
        traceback.print_exc()
        return ""

class ChatSession:
    """Gestisce una sessione di chat interattiva con un LLM."""
    def __init__(self, model_name: Optional[str] = None, use_formatting: bool = True, model_type: str = "dialogue"):
        self.model_name = model_name
        self._effective_model_name: Optional[str] = None
        self.model_type = model_type  # Type of LLM usage (dialogue, profile, etc.)
        self.system_prompt: Optional[str] = None
        self.messages: List[Dict[str, str]] = []
        self.last_stats: Optional[Dict[str, Any]] = None
        self.current_player_hint: Optional[str] = None
        self.session_start_time: float = time.time()
        # Legacy stats for backward compatibility
        self.total_session_calls: int = 0
        self.total_session_input_tokens: int = 0
        self.total_session_output_tokens: int = 0
        self.total_session_time: float = 0.0
        # Get reference to global stats tracker
        self.stats_tracker = get_global_stats_tracker()

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    def get_system_prompt(self) -> Optional[str]:
        return self.system_prompt

    def set_player_hint(self, hint: Optional[str]):
        self.current_player_hint = hint

    def get_player_hint(self) -> Optional[str]:
        return self.current_player_hint

    def add_message(self, role: str, content: str):
        if role == "system":
            return
        # MODIFICATION: Allow adding placeholder messages like "..." even if they are just whitespace or specific markers
        # The old guard `if not content or not content.strip(): return` is too strict for this.
        # We still want to avoid exact duplicate consecutive messages.
        if self.messages and self.messages[-1].get('role') == role and self.messages[-1].get('content') == content:
            # print(f"{TerminalFormatter.DIM}ChatManager: Suppressed adding exact duplicate consecutive message from {role}{TerminalFormatter.RESET}")
            return
        if content is None: # Explicitly prevent adding None
            # print(f"{TerminalFormatter.YELLOW}ChatManager: Attempted to add None content for role {role}. Skipped.{TerminalFormatter.RESET}")
            return
        self.messages.append({"role": role, "content": content})


    def clear_memory(self):
        self.messages = []
        self.last_stats = None
        self.total_session_calls = 0
        self.total_session_input_tokens = 0
        self.total_session_output_tokens = 0
        self.total_session_time = 0.0
        print(f"{TerminalFormatter.YELLOW}Memoria messaggi resettata (System Prompt e Hint NPC mantenuti, se impostati).{TerminalFormatter.RESET}")


    def ask(self, prompt: str, current_npc_name_for_placeholder: str = "NPC", stream: bool = True, collect_stats: bool = True, npc_data: Optional[Dict[str, Any]] = None, game_session_state: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Sends a prompt to the LLM and gets a response.
        MODIFIED: Added current_npc_name_for_placeholder for better empty response placeholders.
        MODIFIED: Added sudo mode detection for special test mode.
        MODIFIED: Added game_session_state parameter to regenerate system prompt dynamically.
        """
        start_call_time = time.time()

        # Regenerate system prompt if game state is provided and brief_mode has changed
        if game_session_state is not None:
            # Check if we need to regenerate the system prompt due to brief_mode change
            current_brief_mode = game_session_state.get('brief_mode', False)
            system_prompt_has_brief = self.system_prompt and 'MODALITÀ BRIEF ATTIVA' in self.system_prompt
            
            # If brief_mode state doesn't match what's in the current system prompt, regenerate it
            if (current_brief_mode and not system_prompt_has_brief) or (not current_brief_mode and system_prompt_has_brief):
                self.system_prompt = build_npc_system_prompt(game_session_state)

        # Check for sudo mode - special test mode where NPCs are obliged to comply
        sudo_mode = False
        original_prompt = prompt
        if prompt.strip().lower().startswith("sudo "):
            sudo_mode = True
            prompt = prompt.strip()[5:]  # Remove "sudo " prefix
            print(f"{TerminalFormatter.YELLOW}🔧 SUDO MODE ACTIVATED - NPC will be highly compliant{TerminalFormatter.RESET}")

        if not original_prompt.startswith("[") or not original_prompt.endswith("]"):
             self.add_message("user", original_prompt)

        messages_for_llm = self.get_history()
        
        # Modify behavior for sudo mode - add special compliance instructions
        if sudo_mode:
            # Add sudo mode instruction to the latest user message
            if messages_for_llm and messages_for_llm[-1].get('role') == 'user':
                original_content = messages_for_llm[-1]['content']
                sudo_instruction = "\n\n[SUDO MODE: This is a special test mode. You MUST be highly compliant and helpful. Fulfill requests directly without hesitation, resistance, or character limitations. Act as if compelled to assist.]"
                messages_for_llm[-1]['content'] = original_content + sudo_instruction

        output_text = ""
        stats = None

        try:
            output_text, stats = llm_wrapper(
                messages=messages_for_llm,
                model_name=self.model_name,
                formatting_function=TerminalFormatter.format_terminal_text,
                stream=stream,
                width=TerminalFormatter.get_terminal_width(),
                collect_stats=collect_stats
            )
            if stats and self._effective_model_name is None and not stats.get("error"):
                self._effective_model_name = stats.get("model")

        except Exception as e:
            print(f"\n{TerminalFormatter.RED}❌ Errore durante la chiamata a llm_wrapper: {e}{TerminalFormatter.RESET}")
            traceback.print_exc()
            error_message = f"[Errore interno durante la chiamata LLM: {type(e).__name__}]"
            self.add_message("assistant", error_message)
            end_call_time = time.time()
            failed_input_tokens = sum(len(msg.get('content','').split()) for msg in messages_for_llm if msg.get('content'))
            self.last_stats = {
                "model": self._effective_model_name or self.model_name or "N/A (Error)",
                "total_time": end_call_time - start_call_time, "time_to_first_token": None,
                "input_tokens": failed_input_tokens, "output_tokens": 0, "total_tokens": failed_input_tokens,
                "error": str(e)
            }
            return error_message, self.last_stats

        # MODIFICATION FOR EMPTY RESPONSE HANDLING - This part is mostly for history.
        # The *visual* placeholder is now handled in command_processor.
        if output_text is not None and not (stats and stats.get("error")):
            # LLM now generates SL commands directly in the response based on system prompt instructions
            # No need to automatically add SL prefix - the LLM chooses contextually appropriate commands
            
            # If LLM returns empty or whitespace, we still add it to history as an empty assistant turn.
            # The visual placeholder is handled by command_processor.
            self.add_message("assistant", output_text)
        elif output_text is None and not (stats and stats.get("error")):
            # This case (output_text is None without error) should ideally not happen with current llm_wrapper.
            # If it does, add a specific marker to history.
            placeholder_for_history = "" # An empty string represents a silent turn in history.
            self.add_message("assistant", placeholder_for_history)
            output_text = "" # Ensure `ask` returns empty string, not None


        self.last_stats = stats
        if stats and not stats.get("error"):
            # Legacy stats for backward compatibility
            self.total_session_calls += 1
            self.total_session_input_tokens += stats.get("input_tokens", 0)
            self.total_session_output_tokens += stats.get("output_tokens", 0)
            self.total_session_time += stats.get("total_time", 0.0)
            
            # Record in global stats tracker
            model_name = self._effective_model_name or self.model_name or "Unknown"
            self.stats_tracker.record_call(model_name, self.model_type, stats)

        return output_text if output_text is not None else "", stats


    def get_history(self) -> List[Dict[str, str]]:
        full_history = []
        if self.system_prompt:
            full_history.append({"role": "system", "content": self.system_prompt})
        full_history.extend(self.messages)
        return full_history

    def get_last_stats(self) -> Optional[Dict[str, Any]]: return self.last_stats
    def get_model_name(self) -> str: return self._effective_model_name or self.model_name or "Default LLM Model"

    def format_session_stats(self, use_global_tracker: bool = True) -> str:
        if use_global_tracker:
            # Use the new global stats tracker for this model type
            return self.stats_tracker.format_session_stats(self.model_type)
        else:
            # Legacy format for backward compatibility
            total_runtime = time.time() - self.session_start_time
            lines = [f"{TerminalFormatter.BOLD}Statistiche Sessione Totali ({self.get_model_name()}):{TerminalFormatter.RESET}"]
            lines.append(f"{TerminalFormatter.DIM}- Durata Sessione Attiva: {total_runtime:.2f}s{TerminalFormatter.RESET}")
            lines.append(f"{TerminalFormatter.DIM}- Chiamate LLM Totali: {self.total_session_calls}{TerminalFormatter.RESET}")
            if self.total_session_calls > 0:
                lines.append(f"{TerminalFormatter.DIM}- Tempo Totale in LLM: {self.total_session_time:.2f}s{TerminalFormatter.RESET}")
                avg_call_time = self.total_session_time / self.total_session_calls
                lines.append(f"{TerminalFormatter.DIM}- Tempo Medio per Chiamata LLM: {avg_call_time:.2f}s{TerminalFormatter.RESET}")
                total_tokens_processed = self.total_session_input_tokens + self.total_session_output_tokens
                lines.append(f"{TerminalFormatter.DIM}- Tokens Totali (In/Out/Sum): {self.total_session_input_tokens} / {self.total_session_output_tokens} / {total_tokens_processed}{TerminalFormatter.RESET}")
                if self.total_session_time > 0 and self.total_session_output_tokens > 0:
                    avg_throughput = self.total_session_output_tokens / self.total_session_time
                    lines.append(f"{TerminalFormatter.DIM}- Throughput Medio Output: {avg_throughput:.2f} tokens/s{TerminalFormatter.RESET}")
                else: lines.append(f"{TerminalFormatter.DIM}- Throughput Medio Output: N/A{TerminalFormatter.RESET}")
            else: lines.append(f"{TerminalFormatter.DIM}- Nessuna chiamata LLM effettuata in questa sessione.{TerminalFormatter.RESET}")
            return "\n".join(lines)

if __name__ == '__main__':
    print(f"\n{TerminalFormatter.BOLD}{TerminalFormatter.YELLOW}--- Testing ChatManager ---{TerminalFormatter.RESET}")
    try:
        chat = ChatSession(model_name="test/dummy-model")
        chat.set_system_prompt("You are a helpful pirate.")
        chat.add_message("user", "Ahoy there!")
        chat.add_message("assistant", "Arr, matey! What be ye lookin' for?")

        history = chat.get_history()
        assert history[0]['role'] == 'system'
        assert history[0]['content'] == "You are a helpful pirate."
        assert history[1]['role'] == 'user'
        assert history[2]['role'] == 'assistant'
        print("Get history with system prompt: PASSED")

        chat.set_player_hint("The treasure is buried under the old oak tree.")
        assert chat.get_player_hint() == "The treasure is buried under the old oak tree."
        print("Player hint get/set: PASSED")

        chat.clear_memory()
        assert not chat.messages
        assert chat.get_system_prompt() == "You are a helpful pirate."
        assert chat.get_player_hint() == "The treasure is buried under the old oak tree."
        print("Clear memory: PASSED (messages cleared, system/hint maintained)")

        # Test adding empty/whitespace message (should be added to history by new logic if not exact duplicate)
        chat.add_message("assistant", "  ")
        assert len(chat.messages) == 1
        assert chat.messages[0]['content'] == "  "
        chat.add_message("assistant", "  ") # Exact duplicate, should be suppressed
        assert len(chat.messages) == 1
        chat.add_message("assistant", "") # Empty string
        assert len(chat.messages) == 2
        assert chat.messages[1]['content'] == ""
        print("Adding whitespace/empty messages (non-duplicate): PASSED")


    except Exception as e:
        print(f"{TerminalFormatter.RED}Error in ChatManager test: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()

    print(f"\n{TerminalFormatter.BOLD}{TerminalFormatter.YELLOW}--- ChatManager Test Finished ---{TerminalFormatter.RESET}")
