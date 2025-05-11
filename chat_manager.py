# Path: chat_manager.py
# Updated Version (Fix for get_history)
from dotenv import load_dotenv

load_dotenv()

import time
from typing import List, Dict, Optional, Tuple, Any

# Importa le dipendenze necessarie
# Make sure these imports work in your environment
try:
    from llm_wrapper import llm_wrapper
    from terminal_formatter import TerminalFormatter
except ImportError as e:
    print(f"Error importing modules in chat_manager.py: {e}")
    # Define fallbacks or re-raise if critical
    # Fallback TerminalFormatter
    class TerminalFormatter:
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))
        @staticmethod
        def get_terminal_width(): return 80
    # Cannot easily fallback llm_wrapper, raise error?
    raise ImportError("Could not import llm_wrapper or terminal_formatter.") from e


def format_stats(stats: Optional[Dict[str, Any]]) -> str:
    """
    Formatta il dizionario delle statistiche per una visualizzazione leggibile.
    """
    if not stats:
        return f"{TerminalFormatter.DIM}Statistiche non disponibili.{TerminalFormatter.RESET}"

    lines = [f"{TerminalFormatter.BOLD}Statistiche Ultima Chiamata:{TerminalFormatter.RESET}"]

    model = stats.get("model", "N/D")
    lines.append(f"{TerminalFormatter.DIM}- Modello: {model}{TerminalFormatter.RESET}")

    total_time = stats.get("total_time")
    if total_time is not None:
        lines.append(f"{TerminalFormatter.DIM}- Tempo Totale: {total_time:.2f}s{TerminalFormatter.RESET}")

    first_token_time = stats.get("time_to_first_token")
    if first_token_time is not None:
        lines.append(f"{TerminalFormatter.DIM}- Tempo al Primo Token: {first_token_time:.2f}s{TerminalFormatter.RESET}")

    in_tokens = stats.get("input_tokens", "N/D")
    out_tokens = stats.get("output_tokens", "N/D")
    tot_tokens = stats.get("total_tokens", "N/D")
    lines.append(f"{TerminalFormatter.DIM}- Tokens (Input/Output/Total): {in_tokens} / {out_tokens} / {tot_tokens}{TerminalFormatter.RESET}")

    # Calcolo Throughput (opzionale)
    if isinstance(total_time, (int, float)) and isinstance(out_tokens, int) and out_tokens > 0 and total_time > 0:
        throughput = out_tokens / total_time
        lines.append(f"{TerminalFormatter.DIM}- Throughput Output: {throughput:.2f} tokens/s{TerminalFormatter.RESET}")

    return "\n".join(lines)


class ChatSession:
    """
    Gestisce una sessione di chat interattiva con un LLM,
    mantenendo la cronologia e aggregando statistiche.
    """
    def __init__(self, model_name: Optional[str] = None, use_formatting: bool = True):
        """
        Inizializza la sessione di chat.

        Args:
            model_name: Nome del modello LLM da utilizzare (es. 'google/gemma-2-9b-it:free'). Se None, llm_wrapper userà il suo default.
            use_formatting: Se usare TerminalFormatter (generalmente gestito da llm_wrapper).
        """
        self.model_name = model_name # The requested model name
        self._effective_model_name: Optional[str] = None # Actual model name reported by llm_wrapper
        self.system_prompt: Optional[str] = None
        # self.messages stores only user and assistant turns primarily.
        # System prompt is stored separately in self.system_prompt.
        self.messages: List[Dict[str, str]] = []
        self.last_stats: Optional[Dict[str, Any]] = None

        # Statistiche aggregate della sessione
        self.session_start_time: float = time.time()
        self.total_session_calls: int = 0
        self.total_session_input_tokens: int = 0
        self.total_session_output_tokens: int = 0
        self.total_session_time: float = 0.0
        # use_formatting is mainly for the wrapper, not directly used here

    def set_system_prompt(self, prompt: str):
        """Imposta o aggiorna il system prompt per la sessione."""
        self.system_prompt = prompt
        # We don't add the system prompt to self.messages here.
        # get_history() will prepend it when needed.

    def get_system_prompt(self) -> Optional[str]:
        """Restituisce il system prompt corrente."""
        return self.system_prompt

    def add_message(self, role: str, content: str):
        """
        Aggiunge un messaggio (user o assistant) alla cronologia interna (self.messages).
        Non aggiungere messaggi 'system' qui; usa set_system_prompt.
        """
        # Prevent adding system messages directly to the list
        if role == "system":
            print(f"{TerminalFormatter.YELLOW}Nota: Usa set_system_prompt() per impostare il prompt di sistema, non add_message(). Ignorato.{TerminalFormatter.RESET}")
            return

        # Prevent adding empty messages
        if not content or not content.strip():
            print(f"{TerminalFormatter.YELLOW}Nota: Tentativo di aggiungere messaggio vuoto per ruolo '{role}' ignorato.{TerminalFormatter.RESET}")
            return

        # Prevent duplicate consecutive messages (simple check)
        if self.messages and self.messages[-1].get('role') == role and self.messages[-1].get('content') == content:
            print(f"{TerminalFormatter.YELLOW}Nota: Tentativo di aggiungere messaggio duplicato consecutivo ignorato.{TerminalFormatter.RESET}")
            return

        self.messages.append({"role": role, "content": content})

    def clear_memory(self):
        """
        Resetta la cronologia dei messaggi utente/assistente (self.messages),
        mantenendo il system prompt e resettando le statistiche di sessione.
        """
        self.messages = [] # Clear only user/assistant messages
        self.last_stats = None
        # Reset session stats
        self.total_session_calls = 0
        self.total_session_input_tokens = 0
        self.total_session_output_tokens = 0
        self.total_session_time = 0.0
        # self.session_start_time = time.time() # Optional: reset session timer too? Usually not.
        print(f"{TerminalFormatter.YELLOW}Memoria messaggi resettata (System Prompt mantenuto).{TerminalFormatter.RESET}")

    def ask(self, prompt: str, stream: bool = True, collect_stats: bool = True) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Invia un prompt utente all'LLM, gestisce la cronologia e restituisce la risposta.
        """
        start_call_time = time.time()

        # 1. Add user message to internal history (self.messages)
        self.add_message("user", prompt)

        # 2. Prepare the *full* message list for the LLM wrapper
        #    This includes the system prompt + all user/assistant messages.
        messages_for_llm = self.get_history() # Use the corrected get_history()

        # 3. Call the llm_wrapper
        output_text = ""
        stats = None
        try:
            # llm_wrapper handles printing (stream or non-stream)
            output_text, stats = llm_wrapper(
                messages=messages_for_llm, # Pass the correctly formatted history
                model_name=self.model_name, # Pass the requested model
                formatting_function=TerminalFormatter.format_terminal_text,
                stream=stream,
                width=TerminalFormatter.get_terminal_width(),
                collect_stats=collect_stats
            )

            # Store the actual model name used if reported back
            if stats and self._effective_model_name is None:
                self._effective_model_name = stats.get("model")

        except Exception as e:
            print(f"\n{TerminalFormatter.RED}❌ Errore durante la chiamata a llm_wrapper: {e}{TerminalFormatter.RESET}")
            # LLM call failed. Add an error message as the assistant's response.
            error_message = f"[Errore interno durante la chiamata LLM: {type(e).__name__}]"
            self.add_message("assistant", error_message) # Log internal error in history

            # Build minimal stats for the failed call
            end_call_time = time.time()
            failed_input_tokens = sum(len(msg.get('content','').split()) for msg in messages_for_llm) # Estimate
            self.last_stats = {
                "model": self._effective_model_name or self.model_name or "N/A (Error)",
                "total_time": end_call_time - start_call_time,
                "time_to_first_token": None,
                "input_tokens": failed_input_tokens, # Input tokens were likely processed
                "output_tokens": 0,
                "total_tokens": failed_input_tokens,
                "error": str(e)
            }
            # Optionally remove the user message that caused the error?
            # if self.messages and self.messages[-2]['role'] == 'user': self.messages.pop(-2)
            return error_message, self.last_stats # Return error message and failure stats

        # 4. Add the successful assistant response to internal history (self.messages)
        if output_text is not None and not (stats and stats.get("error")):
            self.add_message("assistant", output_text)
        elif output_text is None and not (stats and stats.get("error")):
            # Handle case where wrapper returns None without an explicit error
            print(f"{TerminalFormatter.YELLOW}Warning: llm_wrapper returned None output without error.{TerminalFormatter.RESET}")
            self.add_message("assistant", "[Risposta LLM vuota o non restituita]")

        # 5. Update statistics
        self.last_stats = stats # Store stats from the call
        if stats and not stats.get("error"): # Update session totals only on success
            self.total_session_calls += 1
            # Use get() with default 0 for safety
            self.total_session_input_tokens += stats.get("input_tokens", 0)
            self.total_session_output_tokens += stats.get("output_tokens", 0)
            self.total_session_time += stats.get("total_time", 0.0)

        return output_text if output_text is not None else "", stats


    # --------------------------------------
    # --- CORRECTED get_history METHOD ---
    # --------------------------------------
    def get_history(self) -> List[Dict[str, str]]:
        """
        Restituisce la cronologia completa della conversazione nel formato
        richiesto dall'API (System Prompt + User/Assistant messaggi).
        """
        full_history = []
        # 1. Aggiungi il system prompt corrente (se esiste)
        if self.system_prompt:
            full_history.append({"role": "system", "content": self.system_prompt})

        # 2. Aggiungi i messaggi utente e assistente dalla cronologia interna
        #    (self.messages dovrebbe contenere solo user/assistant turns)
        full_history.extend(self.messages)

        return full_history # Restituisce la lista combinata pronta per l'LLM
    # --------------------------------------
    # --- END CORRECTION ---
    # --------------------------------------

    def get_last_stats(self) -> Optional[Dict[str, Any]]:
        """Restituisce le statistiche dell'ultima chiamata a 'ask'."""
        return self.last_stats

    def get_model_name(self) -> str:
        """Restituisce il nome del modello (quello effettivo se noto, altrimenti quello richiesto o default)."""
        # Prioritize effective name, then requested name, then a generic default
        return self._effective_model_name or self.model_name or "Default LLM Model"

    def format_session_stats(self) -> str:
        """Formatta un riepilogo delle statistiche aggregate dell'intera sessione."""
        total_runtime = time.time() - self.session_start_time
        lines = [f"{TerminalFormatter.BOLD}Statistiche Sessione Totali ({self.get_model_name()}):{TerminalFormatter.RESET}"]
        lines.append(f"{TerminalFormatter.DIM}- Durata Sessione Attiva: {total_runtime:.2f}s{TerminalFormatter.RESET}")
        lines.append(f"{TerminalFormatter.DIM}- Chiamate LLM Totali: {self.total_session_calls}{TerminalFormatter.RESET}")

        if self.total_session_calls > 0:
            lines.append(f"{TerminalFormatter.DIM}- Tempo Totale in LLM: {self.total_session_time:.2f}s{TerminalFormatter.RESET}")
            avg_call_time = self.total_session_time / self.total_session_calls
            lines.append(f"{TerminalFormatter.DIM}- Tempo Medio per Chiamata LLM: {avg_call_time:.2f}s{TerminalFormatter.RESET}")

            total_tokens = self.total_session_input_tokens + self.total_session_output_tokens
            lines.append(f"{TerminalFormatter.DIM}- Tokens Totali (In/Out/Sum): {self.total_session_input_tokens} / {self.total_session_output_tokens} / {total_tokens}{TerminalFormatter.RESET}")

            # Calculate average throughput only if time and tokens are valid
            if self.total_session_time > 0 and self.total_session_output_tokens > 0:
                avg_throughput = self.total_session_output_tokens / self.total_session_time
                lines.append(f"{TerminalFormatter.DIM}- Throughput Medio Output: {avg_throughput:.2f} tokens/s{TerminalFormatter.RESET}")
            else:
                lines.append(f"{TerminalFormatter.DIM}- Throughput Medio Output: N/A{TerminalFormatter.RESET}")
        else:
            lines.append(f"{TerminalFormatter.DIM}- Nessuna chiamata LLM effettuata.{TerminalFormatter.RESET}")

        return "\n".join(lines)


# ===========================================
#  Blocco di Test Eseguibile (__main__)
# ===========================================
# (Keep the existing if __name__ == '__main__' block as it was)
if __name__ == '__main__':

    print(f"\n{TerminalFormatter.BOLD}{TerminalFormatter.YELLOW}--- Testing ChatManager ---{TerminalFormatter.RESET}")

    # --- 1. Test format_stats ---
    print(f"\n{TerminalFormatter.BOLD}1. Testing format_stats function:{TerminalFormatter.RESET}")
    sample_stats_ok = { "model": "dummy-model-v1", "total_time": 1.2345, "time_to_first_token": 0.4567, "input_tokens": 50, "output_tokens": 150, "total_tokens": 200, }
    sample_stats_min = { "model": "minimal-model", "total_time": 0.8, "input_tokens": 10, "output_tokens": 5 }
    print(f"{TerminalFormatter.CYAN}Test con stats complete:{TerminalFormatter.RESET}")
    print(format_stats(sample_stats_ok))
    print(f"{TerminalFormatter.CYAN}Test con stats minimali:{TerminalFormatter.RESET}")
    print(format_stats(sample_stats_min))
    print(f"{TerminalFormatter.CYAN}Test con stats None:{TerminalFormatter.RESET}")
    print(format_stats(None))

    # --- 2. Test ChatSession ---
    print(f"\n{TerminalFormatter.BOLD}2. Testing ChatSession class:{TerminalFormatter.RESET}")
    test_model = None # Use default llm from wrapper

    try:
        chat = ChatSession(model_name=test_model)
        print(f"{TerminalFormatter.GREEN}✅ ChatSession istanziata.{TerminalFormatter.RESET}")
        print(f"   Modello richiesto: {test_model or 'Default'}")

        chat.set_system_prompt("Sei un assistente AI di test, breve e conciso.")
        print(f"{TerminalFormatter.GREEN}✅ System prompt impostato.{TerminalFormatter.RESET}")
        print(f"   System Prompt corrente: '{chat.get_system_prompt()}'") # Verify get_system_prompt

        chat.add_message("user", "Messaggio utente 1.")
        chat.add_message("assistant", "Risposta assistente 1.")
        print(f"{TerminalFormatter.GREEN}✅ Messaggi iniziali aggiunti.{TerminalFormatter.RESET}")

        print(f"\n{TerminalFormatter.CYAN}--- Storia Iniziale (Test get_history) ---{TerminalFormatter.RESET}")
        history1 = chat.get_history() # Use the UPDATED get_history
        print(f"History 1 (Length: {len(history1)}):")
        for i, msg in enumerate(history1): print(f"  {i}: {msg.get('role')}: {msg.get('content')[:80]}...")
        assert len(history1) == 3 # Should be System + User + Assistant

        print(f"\n{TerminalFormatter.CYAN}--- Prima Chiamata 'ask' (stream=False) ---{TerminalFormatter.RESET}")
        prompt1 = "Ciao! Come stai oggi?"
        print(f"{TerminalFormatter.BOLD}{TerminalFormatter.GREEN}User > {prompt1}{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.BOLD}{TerminalFormatter.MAGENTA}Assistant >{TerminalFormatter.RESET} (Attendere risposta...)")
        # NOTE: This calls the actual llm_wrapper, requires API key etc. configured
        response1, stats1 = chat.ask(prompt1, stream=False, collect_stats=True)
        print(f"\n{TerminalFormatter.GREEN}✅ Chiamata 'ask' completata.{TerminalFormatter.RESET}")
        print(format_stats(chat.get_last_stats()))

        print(f"\n{TerminalFormatter.CYAN}--- Storia Dopo Ask 1 (Test get_history) ---{TerminalFormatter.RESET}")
        history2 = chat.get_history()
        print(f"History 2 (Length: {len(history2)}):")
        for i, msg in enumerate(history2): print(f"  {i}: {msg.get('role')}: {msg.get('content')[:80]}...")
        # Should be System + User1 + Assistant1 + User2 (prompt1) + Assistant2 (response1) = 5
        assert len(history2) == 5

        # Test clear memory
        print(f"\n{TerminalFormatter.CYAN}--- Test clear_memory() ---{TerminalFormatter.RESET}")
        chat.clear_memory()
        history3 = chat.get_history() # Get history AFTER clear
        print(f"Numero messaggi dopo clear (via get_history): {len(history3)}")
        # After clear, only the system prompt should remain when retrieved by get_history
        assert len(history3) == 1 and history3[0]['role'] == 'system'
        if len(history3) == 1 and history3[0]['role'] == 'system':
            print(f"{TerminalFormatter.GREEN}✅ Cronologia corretta dopo clear (solo system prompt).{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.RED}❌ Errore: La cronologia non è corretta dopo clear_memory().{TerminalFormatter.RESET}")
            for i, msg in enumerate(history3): print(f"  {i}: {msg.get('role')}: {msg.get('content')[:80]}...")


        print(f"\n{TerminalFormatter.CYAN}--- Statistiche Sessione Dopo Clear ---{TerminalFormatter.RESET}")
        print(chat.format_session_stats()) # Should be reset

        print(f"\n{TerminalFormatter.CYAN}--- Chiamata 'ask' (dopo clear) ---{TerminalFormatter.RESET}")
        prompt3 = "Sei ancora lì?"
        print(f"{TerminalFormatter.BOLD}{TerminalFormatter.GREEN}User > {prompt3}{TerminalFormatter.RESET}")
        response3, stats3 = chat.ask(prompt3, stream=False, collect_stats=True) # Call ask again
        print(f"\n{TerminalFormatter.GREEN}✅ Chiamata 'ask' post-clear completata.{TerminalFormatter.RESET}")
        print(format_stats(chat.get_last_stats()))

        history4 = chat.get_history()
        print(f"Storia dopo chiamata post-clear (Length: {len(history4)}):")
        # Should be System + User3 (prompt3) + Assistant3 (response3) = 3
        assert len(history4) == 3
        for i, msg in enumerate(history4): print(f"  {i}: {msg.get('role')}: {msg.get('content')[:80]}...")

        print(f"\n{TerminalFormatter.CYAN}--- Statistiche Sessione Finali ---{TerminalFormatter.RESET}")
        print(chat.format_session_stats()) # Should reflect only the last call

    except ImportError as ie:
        print(f"\n{TerminalFormatter.RED}❌ ERRORE DI IMPORTAZIONE: {ie}{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.YELLOW}   Assicurati che 'llm_wrapper.py' e 'terminal_formatter.py' siano accessibili.{TerminalFormatter.RESET}")
    except Exception as e:
        print(f"\n{TerminalFormatter.RED}❌ ERRORE DURANTE IL TEST: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
        import traceback
        traceback.print_exc()

    print(f"\n{TerminalFormatter.BOLD}{TerminalFormatter.YELLOW}--- ChatManager Test Finished ---{TerminalFormatter.RESET}")
