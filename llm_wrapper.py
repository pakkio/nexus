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
                                for l in lines[:-1]:
                                    try:
                                        formatted_line = formatting_function(l, width=width)
                                        print(formatted_line, flush=True)
                                    except Exception as fmt_e:
                                        logging.error(f"Formatting error: {fmt_e} on line: {l}")
                                        print(f"{TerminalFormatter.RED}[FmtErr: {fmt_e}]{TerminalFormatter.RESET} {l}")
                                buffer = lines[-1]

                    except json.JSONDecodeError:
                        logging.warning(f"Failed to decode JSON from SSE line: {decoded_line}")
                    except Exception as e:
                        logging.exception(f"Error processing SSE chunk: {decoded_line}")

        # Print any remaining buffer content
        if buffer:
            try:
                formatted_buffer = formatting_function(buffer, width=width)
                print(formatted_buffer, flush=True)
            except Exception as fmt_e:
                logging.error(f"Formatting error on final buffer: {fmt_e} on buffer: {buffer}")
                print(f"{TerminalFormatter.RED}[FmtErr: {fmt_e}]{TerminalFormatter.RESET} {buffer}")

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

        formatted_text = formatting_function(output_text, width=width)
        print(formatted_text)

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
                              formatting_function: Optional[callable] = None,
                              stream: bool = True,
                              width: Optional[int] = None,
                              collect_stats: bool = False) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Wrapper to call OpenRouter API directly using 'requests'.

    Args:
        messages: Full conversation history (list of {'role': ..., 'content': ...}).
                  System prompt should be messages[0] if used.
                  Last message must be 'user'.
        model_name: Full OpenRouter model identifier (e.g., "openrouter/anthropic/claude-3-haiku").
                    If None, tries OPENROUTER_DEFAULT_MODEL env var or raises error.
        formatting_function: Custom formatting function.
        stream: If True, stream output.
        width: Text width for formatting.
        collect_stats: If True, collect and return statistics.

    Returns:
        Tuple (output_text, stats). Stats dictionary might contain an 'error' key.
    """
    if not messages:
        logging.error("Direct wrapper called with empty messages list.")
        return "[Errore: Nessun messaggio]", {"error": "No messages provided"}

    if messages[-1].get("role") != "user":
        logging.warning("Direct wrapper: Last message role is not 'user'. Skipping API call.")
        print(f"{TerminalFormatter.YELLOW}Warning: L'ultimo messaggio non era un prompt utente. Nessuna nuova risposta generata.{TerminalFormatter.RESET}")
        output_text = ""
        if messages[-1].get("role") == 'assistant':
            output_text = messages[-1].get('content', '')
            # Print previous assistant message if relevant
        stats = None
        if collect_stats:
            stats = collect_direct_api_statistics(model_name or "N/A", messages, output_text, time.time(), None, None)
        return output_text, stats

    # --- Configuration ---
    api_key = os.environ.get("OPENROUTER_API_KEY")
    api_base = "https://openrouter.ai/api/v1"
    site_url = os.environ.get("OPENROUTER_APP_URL", "http://localhost") # Optional but recommended
    app_title = os.environ.get("OPENROUTER_APP_TITLE", "MyApiClient") # Optional

    if not api_key:
        logging.error("OPENROUTER_API_KEY environment variable not set.")
        return "[Errore: Chiave API OpenRouter mancante]", {"error": "OPENROUTER_API_KEY not set"}

    # Determine model name
    if model_name is None:
        model_name = os.environ.get("OPENROUTER_DEFAULT_MODEL")
        if model_name is None:
            logging.error("Model name not provided and OPENROUTER_DEFAULT_MODEL env var not set.")
            return "[Errore: Nome modello mancante]", {"error": "Model name not provided"}
        #logging.info(f"Using default model from env var: {model_name}")

    formatting_function = formatting_function or TerminalFormatter.format_terminal_text
    width = width or TerminalFormatter.get_terminal_width()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": site_url,
        "X-Title": app_title,
    }

    payload = {
        "model": model_name,
        "messages": messages,
        "stream": stream,
        # Add other parameters like temperature, max_tokens here if needed
        # "temperature": 0.7,
        # "max_tokens": 500,
    }

    # logging.info(f"Calling OpenRouter API: POST {api_base}/chat/completions")
    # logging.debug(f"  Model: {model_name}")
    # logging.debug(f"  Stream: {stream}")
    try:
        # Truncate long content for logging if necessary
        log_messages = [{k: (v[:100] + '...' if isinstance(v, str) and len(v) > 100 else v) for k, v in msg.items()} for msg in messages]
        # logging.info(f"  Payload (messages truncated): {json.dumps({'model': model_name, 'messages': log_messages, 'stream': stream}, indent=2, default=str)}")
    except Exception as log_e:
        logging.error(f"Error formatting payload for logging: {log_e}")

    # --- API Call ---
    start_time = time.time()
    first_token_time = None
    output_text = ""
    response_data = None # To store parsed JSON for non-streaming or errors
    stats = None

    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            stream=stream, # Let requests handle streaming connection
            timeout=120 # Add a reasonable timeout (e.g., 2 minutes)
        )

        # logging.info(f"API Response Status Code: {response.status_code}")

        if stream:
            # Check status *before* iterating for streams
            if response.status_code != 200:
                response.raise_for_status() # Will raise HTTPError for bad status
            output_text, first_token_time = process_direct_streaming_output(
                response, formatting_function, width, first_token_time
            )
            # Note: Getting usage stats from streams is unreliable via OpenRouter generally
            # We will collect stats using estimations based on output_text
            if collect_stats:
                stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, first_token_time, None) # Pass None for response_data

        else: # Non-streaming
            response.raise_for_status() # Raise HTTPError for bad status codes (4xx or 5xx)
            response_data = response.json() # Parse the JSON response
            # logging.debug(f"Non-streaming Response JSON: {json.dumps(response_data, indent=2)}")
            output_text, first_token_time = process_direct_non_streaming_output(
                response_data, formatting_function, width
            )
            # Collect stats using the parsed JSON data
            if collect_stats:
                stats = collect_direct_api_statistics(
                    model_name, messages, output_text, start_time, first_token_time, response_data
                )

    except requests.exceptions.Timeout:
        logging.exception(f"API call to {model_name} timed out.")
        print(f"\n{TerminalFormatter.RED}❌ Errore: Timeout durante la chiamata API.{TerminalFormatter.RESET}")
        output_text = "[Errore: Timeout API]"
        if collect_stats: stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, None); stats["error"] = "Timeout"

    except requests.exceptions.RequestException as e:
        logging.exception(f"API call to {model_name} failed.")
        error_content = f"Errore richiesta: {e}"
        try:
            # Attempt to get more detail from response body even on error
            error_body = e.response.text if hasattr(e, 'response') and e.response else str(e)
            # logging.error(f"API Error Body: {error_body}")
            # error_content = f"Errore richiesta: {e}. Dettagli: {error_body[:500]}" # Limit details length
            # response_data = {"error": {"message": error_content, "type": "request_error", "code": e.response.status_code if hasattr(e, 'response') else None}}
        except Exception as e_parse:
            logging.error(f"Could not parse error response body: {e_parse}")

        print(f"\n{TerminalFormatter.RED}❌ Errore durante la chiamata API: {e}{TerminalFormatter.RESET}")
        output_text = f"[Errore API: {e}]"
        if collect_stats: stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, response_data); stats["error"] = stats.get("error", str(e)) # Use error from response_data if available

    except Exception as e:
        logging.exception(f"An unexpected error occurred during direct API interaction with {model_name}.")
        print(f"\n{TerminalFormatter.RED}❌ Errore inatteso: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
        import traceback
        traceback.print_exc()
        output_text = f"[Errore Inatteso: {e}]"
        if collect_stats: stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, None); stats["error"] = f"{type(e).__name__}: {e}"

    # Ensure stats dictionary exists if collect_stats was True but an error occurred
    if collect_stats and stats is None:
        logging.warning("Collect_stats was True but stats object is None, creating basic error stats.")
        stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, response_data) # Use response_data if available
        if not stats.get("error"): stats["error"] = "Unknown error before stats collection"


    # logging.info(f"Direct API wrapper finished. Returning output ({len(output_text)} chars) and stats.")
    return output_text, stats
# --- End openrouter_direct_wrapper ---
if __name__ == "__main__":
    load_dotenv()
    # Esempio 1: Simple Stream
    print("\n--- Esempio 1: Conversazione Semplice (Streaming) ---")
    messages1 = [
        {"role": "system", "content": "Sei un assistente AI conciso."},
        {"role": "user", "content": "Qual è la capitale della Francia?"}
    ]
    # Use corrected model ID
    response1, stats1 = openrouter_direct_wrapper(messages1, stream=True, collect_stats=True) # REMOVED openrouter/ prefix
    print(f"\nStatistiche 1: {stats1}\n")

    # Esempio 2: Non-Streaming
    print("--- Esempio 2: Non-Streaming ---")
    messages2 = [
        {"role": "user", "content": "Scrivi una breve poesia sulla pioggia."}
    ]
    response2, stats2 = openrouter_direct_wrapper(messages2, stream=False, collect_stats=True) # REMOVED openrouter/ prefix
    print(f"Statistiche 2: {stats2}\n")

    # Esempio 5: Critical Memory Test (Claude 3 Haiku)
    print("--- Esempio 5: Test Memoria Critico (Claude 3 Haiku) ---")
    messages5 = [
        {"role": "system", "content": "Sei un assistente AI utile che ricorda i dettagli."},
        {"role": "user", "content": "Mi chiamo Marco. Il mio colore preferito è il blu."},
        {"role": "assistant", "content": "Ciao Marco! Ho capito, il tuo colore preferito è il blu. Come posso aiutarti oggi?"},
        {"role": "user", "content": "Qual è il mio nome e il mio colore preferito?"} # Ask for recall
    ]
    haiku_model_id = "anthropic/claude-3-haiku" # REMOVED openrouter/ prefix
    response5, stats5 = openrouter_direct_wrapper(messages5, stream=True, collect_stats=True)
    print(f"\nRisposta 5 ({haiku_model_id} - Si ricorda?): '{response5}'")
    print(f"Statistiche 5: {stats5}\n")

    # Esempio 5b: Critical Memory Test (GPT-4.1-Nano) - Expect to fail memory
    print("--- Esempio 5b: Test Memoria Critico (GPT-4.1-Nano) ---")
    nano_model_id = "openai/gpt-4.1-nano" # REMOVED openrouter/ prefix
    response5b, stats5b = openrouter_direct_wrapper(messages5, stream=True, collect_stats=True, model_name=nano_model_id)
    print(f"\nRisposta 5b ({nano_model_id} - Si ricorda?): '{response5b}'")
    print(f"Statistiche 5b: {stats5b}\n")

    # Esempio 6: Error Handling - Invalid Model Name
    print("--- Esempio 6: Test Errore (Modello Invalido) ---")
    messages6 = [{"role": "user", "content": "Test"}]
    # Using a format without 'openrouter/' might give a clearer error if invalid
    response6, stats6 = openrouter_direct_wrapper(messages6, stream=False, collect_stats=True, model_name="nonexistent/model")
    print(f"\nRisposta 6 (Errore atteso): '{response6}'")
    print(f"Statistiche 6: {stats6}\n")
