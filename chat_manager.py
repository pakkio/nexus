# Path: chat_manager.py
# Updated Version (Fix for get_history)
# MODIFIED: Added current_npc_name_for_placeholder to ask method for better empty response placeholders
from dotenv import load_dotenv

load_dotenv()

import time
from typing import List, Dict, Optional, Tuple, Any
import traceback # Added for more detailed error printing if needed

# Importa le dipendenze necessarie
try:
    from llm_wrapper import llm_wrapper
    from terminal_formatter import TerminalFormatter
except ImportError as e:
    print(f"Error importing modules in chat_manager.py: {e}")
    class TerminalFormatter:
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; ITALIC = "" # Added ITALIC for placeholder
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))
        @staticmethod
        def get_terminal_width(): return 80


def format_stats(stats: Optional[Dict[str, Any]]) -> str:
    """Formatta il dizionario delle statistiche per una visualizzazione leggibile."""
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


class ChatSession:
    """Gestisce una sessione di chat interattiva con un LLM."""
    def __init__(self, model_name: Optional[str] = None, use_formatting: bool = True):
        self.model_name = model_name
        self._effective_model_name: Optional[str] = None
        self.system_prompt: Optional[str] = None
        self.messages: List[Dict[str, str]] = []
        self.last_stats: Optional[Dict[str, Any]] = None
        self.current_player_hint: Optional[str] = None
        self.session_start_time: float = time.time()
        self.total_session_calls: int = 0
        self.total_session_input_tokens: int = 0
        self.total_session_output_tokens: int = 0
        self.total_session_time: float = 0.0

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


    def ask(self, prompt: str, current_npc_name_for_placeholder: str = "NPC", stream: bool = True, collect_stats: bool = True) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Sends a prompt to the LLM and gets a response.
        MODIFIED: Added current_npc_name_for_placeholder for better empty response placeholders.
        """
        start_call_time = time.time()

        if not prompt.startswith("[") or not prompt.endswith("]"):
             self.add_message("user", prompt)

        messages_for_llm = self.get_history()

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
            self.total_session_calls += 1
            self.total_session_input_tokens += stats.get("input_tokens", 0)
            self.total_session_output_tokens += stats.get("output_tokens", 0)
            self.total_session_time += stats.get("total_time", 0.0)

        return output_text if output_text is not None else "", stats


    def get_history(self) -> List[Dict[str, str]]:
        full_history = []
        if self.system_prompt:
            full_history.append({"role": "system", "content": self.system_prompt})
        full_history.extend(self.messages)
        return full_history

    def get_last_stats(self) -> Optional[Dict[str, Any]]: return self.last_stats
    def get_model_name(self) -> str: return self._effective_model_name or self.model_name or "Default LLM Model"

    def format_session_stats(self) -> str:
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
