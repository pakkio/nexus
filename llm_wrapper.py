# direct_openrouter_wrapper.py

import time
import os
import requests # Dependency: pip install requests
import json
import logging
from typing import List, Dict, Optional, Tuple, Any

from dotenv import load_dotenv

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# --- TerminalFormatter (Fallback included) ---
try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    logging.warning("terminal_formatter not found. Using basic fallback.")
    class TerminalFormatter:
        RED = "\033[91m"; YELLOW = "\033[93m"; RESET = "\033[0m"
        @staticmethod
        def format_terminal_text(text, width=80):
            import textwrap
            return "\n".join(textwrap.wrap(text, width=width))
        @staticmethod
        def get_terminal_width():
            try:
                import shutil
                return shutil.get_terminal_size((80, 24)).columns
            except Exception: return 80
# --- End TerminalFormatter ---


# --- process_direct_streaming_output ---
# Modified to handle SSE format from direct API call
def process_direct_streaming_output(response: requests.Response,
                                    formatting_function: callable,
                                    width: int,
                                    first_token_time: Optional[float]) -> Tuple[str, Optional[float]]:
    """Process streaming output directly from requests Response (SSE)."""
    output_text = ""
    buffer = ""
    start_marker = "data: "
    stop_marker = "[DONE]"

    try:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith(start_marker):
                    if stop_marker in decoded_line:
                        # logging.info("Received SSE stop marker.")
                        break
                    json_str = decoded_line[len(start_marker):]
                    try:
                        chunk_data = json.loads(json_str)
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")

                        if token:
                            if first_token_time is None:
                                first_token_time = time.time()
                            output_text += token
                            buffer += token

                            # Print formatting logic (same as before)
                            if '\n' in buffer:
                                lines = buffer.split('\n')
                                for l_idx, l_content in enumerate(lines[:-1]):
                                    try:
                                        # Pass width directly to print, not format_terminal_text if it handles it
                                        # formatted_line = formatting_function(l_content, width=width)
                                        # print(formatted_line, flush=True)
                                        # Simpler: let print handle wrapping if formatting_function is basic
                                        print(l_content, end='\n' if l_idx < len(lines) -2 else '', flush=True)
                                    except Exception as fmt_e:
                                        logging.error(f"Formatting error: {fmt_e} on line: {l_content}")
                                        print(f"{TerminalFormatter.RED}[FmtErr: {fmt_e}]{TerminalFormatter.RESET} {l_content}", flush=True)
                                buffer = lines[-1]
                            elif len(buffer) > 0: # Print partial buffer if no newline but content exists
                                print(buffer, end='', flush=True)
                                buffer = ""


                    except json.JSONDecodeError:
                        logging.warning(f"Failed to decode JSON from SSE line: {decoded_line}")
                    except Exception as e:
                        logging.exception(f"Error processing SSE chunk: {decoded_line}")

        # After loop, print any remaining buffer content WITHOUT an extra newline if it's the final part of a line.
        if buffer:
            try:
                # formatted_buffer = formatting_function(buffer, width=width)
                # print(formatted_buffer, flush=True)
                print(buffer, end='', flush=True) # Print remaining buffer, no auto newline from print()
            except Exception as fmt_e:
                logging.error(f"Formatting error on final buffer: {fmt_e} on buffer: {buffer}")
                print(f"{TerminalFormatter.RED}[FmtErr: {fmt_e}]{TerminalFormatter.RESET} {buffer}", flush=True)

        # Add a final newline if content was printed to ensure prompt appears on new line
        if output_text:
            print("", flush=True)


    except requests.exceptions.RequestException as req_e:
        logging.exception("Error reading streaming response.")
        print(f"\n{TerminalFormatter.RED}Errore durante lo streaming della risposta: {req_e}{TerminalFormatter.RESET}")
        output_text += f"\n[Errore streaming request: {req_e}]"
    except Exception as stream_e:
        logging.exception("Error during streaming output processing.")
        print(f"\n{TerminalFormatter.RED}Errore durante lo streaming: {stream_e}{TerminalFormatter.RESET}")
        output_text += f"\n[Errore streaming processing: {stream_e}]"

    return output_text, first_token_time
# --- End process_direct_streaming_output ---


# --- process_direct_non_streaming_output ---
# Modified to parse direct API JSON response
def process_direct_non_streaming_output(response_data: Dict[str, Any],
                                        formatting_function: callable,
                                        width: int) -> Tuple[str, Optional[float]]:
    """Process non-streaming output from parsed direct API response JSON."""
    output_text = ""
    first_token_time = time.time() # Approximation for non-streaming

    try:
        # Standard OpenAI/OpenRouter format
        output_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not output_text:
            logging.warning(f"No 'content' found in choices[0].message. Full response: {response_data}")
            output_text = f"[Warning: No content in response - {response_data.get('error', 'Unknown reason')}]"

        # Use the TerminalFormatter's own wrapping for non-streaming if available
        # The formatting_function passed is TerminalFormatter.format_terminal_text
        formatted_text = formatting_function(output_text, width=width)
        print(formatted_text) # This will handle wrapping.

    except (IndexError, KeyError, TypeError) as e:
        logging.exception(f"Error parsing non-streaming response structure: {response_data}")
        print(f"{TerminalFormatter.RED}Errore nella struttura della risposta non-streaming: {e}{TerminalFormatter.RESET}")
        output_text = f"[Errore parsing risposta: {e}]"
    except Exception as e:
        logging.exception("Error processing non-streaming output.")
        print(f"{TerminalFormatter.RED}Errore inatteso nell'output non-streaming: {e}{TerminalFormatter.RESET}")
        output_text = f"[Errore processing output: {e}]"

    return output_text, first_token_time
# --- End process_direct_non_streaming_output ---


# --- collect_direct_api_statistics ---
# Modified to parse usage data from direct API JSON response
def collect_direct_api_statistics(model_name: str,
                                  messages: List[Dict[str, str]],
                                  output_text: str,
                                  start_time: float,
                                  first_token_time: Optional[float],
                                  response_data: Optional[Dict[str, Any]]) -> Dict[str, Any]: # Takes JSON dict
    """Collect stats based on direct API response data."""
    end_time = time.time()
    # Basic estimations
    approx_input_tokens = sum(len(msg.get('content', '').split()) for msg in messages)
    approx_output_tokens = len(output_text.split())

    stats = {
        "model": model_name, # Pass model name directly
        "total_time": end_time - start_time,
        "time_to_first_token": first_token_time - start_time if first_token_time is not None else None,
        "input_tokens": approx_input_tokens,
        "output_tokens": approx_output_tokens,
        "total_tokens": approx_input_tokens + approx_output_tokens,
        "error": None # Initialize error
    }

    # Try to get precise tokens from 'usage' field in response JSON
    if response_data and isinstance(response_data, dict) and 'usage' in response_data:
        usage_info = response_data['usage']
        if isinstance(usage_info, dict):
            try:
                prompt_tokens = usage_info.get("prompt_tokens")
                completion_tokens = usage_info.get("completion_tokens")
                total_tokens = usage_info.get("total_tokens")

                if isinstance(prompt_tokens, (int, float)): stats["input_tokens"] = int(prompt_tokens)
                if isinstance(completion_tokens, (int, float)): stats["output_tokens"] = int(completion_tokens)
                if isinstance(total_tokens, (int, float)): stats["total_tokens"] = int(total_tokens)
                elif isinstance(stats["input_tokens"], int) and isinstance(stats["output_tokens"], int):
                    stats["total_tokens"] = stats["input_tokens"] + stats["output_tokens"]

            except (TypeError, KeyError, ValueError) as e:
                logging.warning(f"Could not extract precise token usage from usage dict: {e} in {usage_info}", exc_info=False)
        else:
            logging.warning(f"Response 'usage' field is not a dictionary: {usage_info}")
    elif response_data:
        logging.warning("Response data received but no 'usage' field found for token stats.")

    # Check for explicit error in response data
    if response_data and isinstance(response_data, dict) and 'error' in response_data:
        stats["error"] = json.dumps(response_data['error']) # Store error detail
        logging.warning(f"Direct API response indicated an error: {stats['error']}")

    logging.debug(f"Collected direct API stats: {stats}")
    return stats
# --- End collect_direct_api_statistics ---


# --- NEW: openrouter_direct_wrapper ---
def llm_wrapper(messages: List[Dict[str, str]],
                              model_name: Optional[str] = "google/gemma-3-12b-it:free",
                              formatting_function: Optional[callable] = None, # This is TerminalFormatter.format_terminal_text
                              stream: bool = True,
                              width: Optional[int] = None, # Terminal width
                              collect_stats: bool = False) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Wrapper to call OpenRouter API directly using 'requests'.

    Args:
        messages: Full conversation history (list of {'role': ..., 'content': ...}).
                  System prompt should be messages[0] if used.
                  Last message must be 'user'.
        model_name: Full OpenRouter model identifier (e.g., "openrouter/anthropic/claude-3-haiku").
                    If None, tries OPENROUTER_DEFAULT_MODEL env var or raises error.
        formatting_function: Custom formatting function (TerminalFormatter.format_terminal_text).
                             Note: For streaming, this function is applied by process_direct_streaming_output
                             to completed lines. The direct print in streaming handles token-by-token output.
        stream: If True, stream output.
        width: Text width for formatting (used by formatting_function for non-streaming and line-wrapping in streaming).
        collect_stats: If True, collect and return statistics.

    Returns:
        Tuple (output_text, stats). Stats dictionary might contain an 'error' key.
    """
    if not messages:
        logging.error("Direct wrapper called with empty messages list.")
        return "[Errore: Nessun messaggio]", {"error": "No messages provided"}

    if messages[-1].get("role") != "user":
        logging.warning("Direct wrapper: Last message role is not 'user'. Skipping API call.")
        # print(f"{TerminalFormatter.YELLOW}Warning: L'ultimo messaggio non era un prompt utente. Nessuna nuova risposta generata.{TerminalFormatter.RESET}")
        output_text = ""
        if messages[-1].get("role") == 'assistant': # If last message was assistant, it's a repeat, so "print" it.
            output_text = messages[-1].get('content', '')
            if formatting_function and width:
                 print(formatting_function(output_text, width=width))
            else:
                 print(output_text)
        stats = None
        if collect_stats:
            stats = collect_direct_api_statistics(model_name or "N/A", messages, output_text, time.time(), None, None)
        return output_text, stats

    # --- Configuration ---
    api_key = os.environ.get("OPENROUTER_API_KEY")
    api_base = "https://openrouter.ai/api/v1"
    site_url = os.environ.get("OPENROUTER_APP_URL", "http://localhost")
    app_title = os.environ.get("OPENROUTER_APP_TITLE", "MyApiClient")

    if not api_key:
        logging.error("OPENROUTER_API_KEY environment variable not set.")
        return "[Errore: Chiave API OpenRouter mancante]", {"error": "OPENROUTER_API_KEY not set"}

    if model_name is None:
        model_name = os.environ.get("OPENROUTER_DEFAULT_MODEL")
        if model_name is None:
            logging.error("Model name not provided and OPENROUTER_DEFAULT_MODEL env var not set.")
            return "[Errore: Nome modello mancante]", {"error": "Model name not provided"}

    # Ensure formatting_function and width have defaults if not provided
    # These are passed from ChatSession.ask which gets them from TerminalFormatter
    if formatting_function is None: formatting_function = TerminalFormatter.format_terminal_text
    if width is None: width = TerminalFormatter.get_terminal_width()


    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": site_url,
        "X-Title": app_title,
    }

    payload = { "model": model_name, "messages": messages, "stream": stream }

    start_time = time.time()
    first_token_time = None
    output_text = ""
    response_data = None
    stats = None

    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            stream=stream,
            timeout=180 # Increased timeout
        )

        if stream:
            if response.status_code != 200: response.raise_for_status()
            # process_direct_streaming_output now handles its own printing of tokens/lines.
            # The formatting_function is used by it for completed lines.
            output_text, first_token_time = process_direct_streaming_output(
                response, formatting_function, width, first_token_time
            )
            if collect_stats:
                stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, first_token_time, None)
        else:
            response.raise_for_status()
            response_data = response.json()
            # process_direct_non_streaming_output uses formatting_function to print the whole response.
            output_text, first_token_time = process_direct_non_streaming_output(
                response_data, formatting_function, width
            )
            if collect_stats:
                stats = collect_direct_api_statistics(
                    model_name, messages, output_text, start_time, first_token_time, response_data
                )

    except requests.exceptions.Timeout:
        logging.exception(f"API call to {model_name} timed out.")
        print(f"\n{TerminalFormatter.RED}❌ Errore: Timeout durante la chiamata API ({model_name}).{TerminalFormatter.RESET}")
        output_text = "[Errore: Timeout API]"
        if collect_stats: stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, None); stats["error"] = "Timeout"

    except requests.exceptions.RequestException as e:
        logging.exception(f"API call to {model_name} failed.")
        error_detail_from_response = ""
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail_from_response = e.response.json().get("error",{}).get("message","")
                response_data = e.response.json() # For stats
            except json.JSONDecodeError:
                error_detail_from_response = e.response.text[:200] # First 200 chars of text if not json

        print(f"\n{TerminalFormatter.RED}❌ Errore chiamata API ({model_name}): {e}{TF.RESET}" + (f" Dettaglio: {error_detail_from_response}" if error_detail_from_response else ""))
        output_text = f"[Errore API: {e}]"
        if collect_stats: stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, response_data); stats["error"] = stats.get("error", str(e))

    except Exception as e:
        logging.exception(f"An unexpected error occurred during direct API interaction with {model_name}.")
        print(f"\n{TerminalFormatter.RED}❌ Errore inatteso ({model_name}): {type(e).__name__} - {e}{TerminalFormatter.RESET}")
        # traceback.print_exc() # Already logged by logging.exception
        output_text = f"[Errore Inatteso: {e}]"
        if collect_stats: stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, None); stats["error"] = f"{type(e).__name__}: {e}"

    if collect_stats and stats is None: # Ensure stats object exists if requested but error occurred early
        stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, response_data if response_data else None)
        if not stats.get("error"): stats["error"] = "Unknown error before stats collection"

    return output_text, stats
# --- End openrouter_direct_wrapper ---

if __name__ == "__main__":
    load_dotenv() # Ensure API key is loaded from .env
    print(f"{TerminalFormatter.YELLOW}--- LLM Wrapper Tests ---{TerminalFormatter.RESET}")

    # Test 1: Simple stream with a free model
    print(f"\n{TerminalFormatter.BOLD}Test 1: Streaming - Qual è la capitale della Francia?{TerminalFormatter.RESET}")
    messages1 = [
        {"role": "system", "content": "Sei un assistente AI conciso e utile."},
        {"role": "user", "content": "Qual è la capitale della Francia?"}
    ]
    # Using a known free model that's generally available
    response1, stats1 = llm_wrapper(messages1, model_name="mistralai/mistral-7b-instruct:free", stream=True, collect_stats=True)
    print(f"\n{TerminalFormatter.DIM}Statistiche Test 1: {stats1}{TerminalFormatter.RESET}\n")

    # Test 2: Non-streaming
    print(f"{TerminalFormatter.BOLD}Test 2: Non-Streaming - Scrivi una breve poesia sulla pioggia.{TerminalFormatter.RESET}")
    messages2 = [
        {"role": "user", "content": "Scrivi una breve poesia sulla pioggia."}
    ]
    response2, stats2 = llm_wrapper(messages2, model_name="mistralai/mistral-7b-instruct:free", stream=False, collect_stats=True)
    print(f"\n{TerminalFormatter.DIM}Statistiche Test 2: {stats2}{TerminalFormatter.RESET}\n")

    # Test 3: Error handling - Invalid Model
    print(f"{TerminalFormatter.BOLD}Test 3: Errore - Modello Invalido (nonexistent/model-v1){TerminalFormatter.RESET}")
    messages3 = [{"role": "user", "content": "Questo test fallirà?"}]
    response3, stats3 = llm_wrapper(messages3, model_name="nonexistent/model-v1", stream=False, collect_stats=True)
    print(f"\n{TerminalFormatter.DIM}Risposta Test 3 (errore atteso): '{response3}'{TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.DIM}Statistiche Test 3: {stats3}{TerminalFormatter.RESET}\n")

    # Test 4: Conversation Context (Memory)
    print(f"{TerminalFormatter.BOLD}Test 4: Contesto - Mi chiamo Marco, colore blu. Ricordi?{TerminalFormatter.RESET}")
    messages4 = [
        {"role": "system", "content": "Ricorda i dettagli. Il mio nome è Marco. Il mio colore preferito è il blu."},
        {"role": "user", "content": "Ciao! Come stai?"},
        {"role": "assistant", "content": "Ciao Marco! Sto bene, grazie. So che il tuo colore preferito è il blu. Come posso aiutarti?"},
        {"role": "user", "content": "Qual è il mio nome e il mio colore preferito?"}
    ]
    # Using a model known for better context retention if possible, like Claude Haiku if API key allows
    # For free tier, sticking to Mistral 7B
    chosen_model_for_context = "anthropic/claude-3-haiku-20240307" # Paid model
    # chosen_model_for_context = "mistralai/mistral-7b-instruct:free" # Free alternative

    # Check if OpenRouter API key is available, otherwise skip paid model test
    if os.environ.get("OPENROUTER_API_KEY"):
        print(f"{TerminalFormatter.DIM}(Utilizzando {chosen_model_for_context} per test di contesto){TerminalFormatter.RESET}")
        response4, stats4 = llm_wrapper(messages4, model_name=chosen_model_for_context, stream=True, collect_stats=True)
        print(f"\n{TerminalFormatter.DIM}Risposta Test 4: '{response4}'{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.DIM}Statistiche Test 4: {stats4}{TerminalFormatter.RESET}\n")
    else:
        print(f"{TerminalFormatter.YELLOW}Skipping context test with paid model ({chosen_model_for_context}) as OPENROUTER_API_KEY is not set.{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.DIM}(Riprova con un modello gratuito per il test di contesto){TerminalFormatter.RESET}")
        response4, stats4 = llm_wrapper(messages4, model_name="mistralai/mistral-7b-instruct:free", stream=True, collect_stats=True)
        print(f"\n{TerminalFormatter.DIM}Risposta Test 4 (con modello gratuito): '{response4}'{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.DIM}Statistiche Test 4: {stats4}{TerminalFormatter.RESET}\n")


    print(f"{TerminalFormatter.YELLOW}--- LLM Wrapper Tests Finiti ---{TerminalFormatter.RESET}")
