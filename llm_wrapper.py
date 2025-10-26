# direct_openrouter_wrapper.py

import time
import os
import requests # Dependency: pip install requests
import json
import logging
from typing import List, Dict, Optional, Tuple, Any

from dotenv import load_dotenv

# Load environment variables at module import time
load_dotenv()

# Create a session with connection pooling for better performance
_request_session = None

def get_request_session():
    """Get a requests session with connection pooling."""
    global _request_session
    if _request_session is None:
        _request_session = requests.Session()
        # Configure connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=1
        )
        _request_session.mount('http://', adapter)
        _request_session.mount('https://', adapter)
    return _request_session

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# --- TerminalFormatter (Fallback included) ---
try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    logging.warning("terminal_formatter not found. Using basic fallback.")
    class TerminalFormatter: # Basic Fallback
        RED = "\033[91m"; YELLOW = "\033[93m"; RESET = "\033[0m"; BOLD = ""; ITALIC = ""; DIM = ""; MAGENTA = ""; CYAN = "";
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
TF = TerminalFormatter # Alias for convenience if needed within this file directly
# --- End TerminalFormatter ---


# --- process_direct_streaming_output ---
def process_direct_streaming_output(response: requests.Response,
                                    formatting_function: callable,
                                    width: int,
                                    first_token_time: Optional[float]) -> Tuple[str, Optional[float]]:
    output_text = ""
    buffer = ""
    start_marker = "data: " # For Server-Sent Events (SSE)
    stop_marker = "[DONE]"  # Common SSE stop signal from OpenAI-like APIs

    try:
        for line in response.iter_lines(): # Iterates over lines in the response
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith(start_marker):
                    if stop_marker in decoded_line: # Check for stop signal
                        break
                    json_str = decoded_line[len(start_marker):].strip()
                    if not json_str: continue # Skip empty data lines

                    try:
                        chunk_data = json.loads(json_str)
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")

                        if token:
                            if first_token_time is None:
                                first_token_time = time.time()
                            output_text += token
                            # Streaming print logic (token by token, line by line)
                            # This part needs to be careful about how it prints to avoid breaking terminal flow
                            # The original printing logic from your file is complex;
                            # a simpler approach for direct printing here:
                            print(token, end='', flush=True) # Print token immediately
                            # If you want line-based formatting during streaming, that adds more complexity.
                            # The previous buffer logic was an attempt at this.
                            # For simplicity and robustness, direct token printing is often safer.

                    except json.JSONDecodeError:
                        logging.warning(f"Failed to decode JSON from SSE line: {decoded_line}")
                    except Exception as e: # Catch other errors during chunk processing
                        logging.exception(f"Error processing SSE chunk: {decoded_line}")

        # After the loop, if any content was streamed, ensure a newline for the next prompt
        if output_text:
            print("", flush=True) # Moves to the next line

    except requests.exceptions.RequestException as req_e:
        logging.exception("Error reading streaming response.")
        # print(f"\n{TF.RED}Errore durante lo streaming della risposta: {req_e}{TF.RESET}") # User-facing if needed
        output_text += f"\n[Errore streaming request: {req_e}]" # Append to internal text
    except Exception as stream_e:
        logging.exception("Error during streaming output processing.")
        # print(f"\n{TF.RED}Errore durante lo streaming: {stream_e}{TF.RESET}")
        output_text += f"\n[Errore streaming processing: {stream_e}]"

    return output_text, first_token_time
# --- End process_direct_streaming_output ---


# --- process_direct_non_streaming_output ---
def process_direct_non_streaming_output(response_data: Dict[str, Any],
                                        formatting_function: callable,
                                        width: int) -> Tuple[str, Optional[float]]:
    output_text = ""
    first_token_time = time.time()

    try:
        message_obj = response_data.get("choices", [{}])[0].get("message", {})
        output_text = message_obj.get("content", "")

        # GPT-5/reasoning models may have reasoning in separate field
        reasoning = message_obj.get("reasoning", None)
        if reasoning and not output_text:
            # If content is empty but reasoning exists, use a summary
            output_text = "[Reasoning model generated internal reasoning but no direct response. Try a simpler prompt or different model.]"
            logging.info(f"GPT-5 reasoning detected but no content. Reasoning preview: {str(reasoning)[:200]}")

        if not output_text and "error" in response_data: # If no content but error field exists
            error_msg = response_data.get("error", {}).get("message", "Unknown error from API")
            output_text = f"[API Error: {error_msg}]"
            logging.warning(f"API returned error: {error_msg}. Full response: {response_data}")
        elif not output_text: # No content and no explicit error field in choices
            logging.warning(f"No 'content' found in choices[0].message. Full response: {response_data}")
            output_text = f"[Warning: No content in response]"


        # Print the complete non-streamed response using the formatter
        # (The caller, chat_manager.ask, handles printing if formatting_function is TerminalFormatter.format_terminal_text)
        # However, if this function is called directly for a utility that expects printing here:
        # formatted_text = formatting_function(output_text, width=width)
        # print(formatted_text)
        # For now, let's assume the caller (ChatSession) handles printing of the final text.

    except (IndexError, KeyError, TypeError) as e:
        logging.exception(f"Error parsing non-streaming response structure: {response_data}")
        # print(f"{TF.RED}Errore nella struttura della risposta non-streaming: {e}{TF.RESET}")
        output_text = f"[Errore parsing risposta: {e}]"
    except Exception as e:
        logging.exception("Error processing non-streaming output.")
        # print(f"{TF.RED}Errore inatteso nell'output non-streaming: {e}{TF.RESET}")
        output_text = f"[Errore processing output: {e}]"

    return output_text, first_token_time
# --- End process_direct_non_streaming_output ---


# --- collect_direct_api_statistics ---
def collect_direct_api_statistics(model_name: str,
                                  messages: List[Dict[str, str]],
                                  output_text: str,
                                  start_time: float,
                                  first_token_time: Optional[float],
                                  response_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    end_time = time.time()
    approx_input_tokens = sum(len(str(msg.get('content', '')).split()) for msg in messages) # Ensure content is string
    approx_output_tokens = len(str(output_text).split()) # Ensure output_text is string

    stats = {
        "model": model_name,
        "total_time": end_time - start_time,
        "time_to_first_token": first_token_time - start_time if first_token_time is not None else None,
        "input_tokens": approx_input_tokens,
        "output_tokens": approx_output_tokens,
        "total_tokens": approx_input_tokens + approx_output_tokens,
        "error": None
    }

    if response_data and isinstance(response_data, dict) and 'usage' in response_data:
        usage_info = response_data['usage']
        if isinstance(usage_info, dict):
            try:
                # ... (usage parsing logic from your file) ...
                prompt_tokens = usage_info.get("prompt_tokens")
                completion_tokens = usage_info.get("completion_tokens")
                total_tokens = usage_info.get("total_tokens")

                if isinstance(prompt_tokens, (int, float)): stats["input_tokens"] = int(prompt_tokens)
                if isinstance(completion_tokens, (int, float)): stats["output_tokens"] = int(completion_tokens)
                if isinstance(total_tokens, (int, float)): stats["total_tokens"] = int(total_tokens)
                elif isinstance(stats["input_tokens"], int) and isinstance(stats["output_tokens"], int):
                    stats["total_tokens"] = stats["input_tokens"] + stats["output_tokens"]
            except (TypeError, KeyError, ValueError) as e:
                logging.warning(f"Could not extract precise token usage: {e} in {usage_info}", exc_info=False)
    elif response_data and isinstance(response_data, dict) and 'error' in response_data : # Error came from response_data
        stats["error"] = json.dumps(response_data['error'])
        logging.warning(f"Direct API response indicated an error: {stats['error']}")


    logging.debug(f"Collected direct API stats: {stats}")
    return stats
# --- End collect_direct_api_statistics ---


def _try_anthropic_api(messages: List[Dict[str, str]],
                       model_name: str,
                       formatting_function: Optional[callable],
                       stream: bool,
                       width: Optional[int],
                       collect_stats: bool) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Try to use Anthropic API directly for claude-haiku-4.5.
    Returns (text, stats) tuple. If fails, stats will contain error.

    Note: Anthropic API uses a separate top-level 'system' parameter,
    not 'system' role in messages array.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logging.warning("ANTHROPIC_API_KEY not set, skipping Anthropic API")
        return "", {"error": "ANTHROPIC_API_KEY not set"}

    api_base = "https://api.anthropic.com/v1"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Map model name to Anthropic's Haiku 4.5
    # claude-haiku-4-5 is the correct model ID for Haiku 4.5 on Anthropic API
    # API will resolve it to claude-haiku-4-5-20251001
    anthropic_model = "claude-haiku-4-5"
    if "4.5" in model_name or model_name == "claude-haiku-4.5":
        anthropic_model = "claude-haiku-4-5"  # Haiku 4.5

    # Extract system message from messages array (Anthropic API requires it separately)
    system_message = ""
    user_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            system_message = msg.get("content", "")
        else:
            user_messages.append(msg)

    payload = {
        "model": anthropic_model,
        "max_tokens": 2048,  # Increased from 512 to allow notecard generation
        "messages": user_messages,
        "stream": stream,
    }

    # Add system message if present
    if system_message:
        payload["system"] = system_message

    start_time = time.time()
    first_token_time = None
    output_text = ""

    try:
        session = get_request_session()
        response = session.post(
            f"{api_base}/messages",
            headers=headers,
            json=payload,
            stream=stream,
            timeout=60
        )

        if response.status_code != 200:
            logging.error(f"Anthropic API failed with status {response.status_code}: {response.text}")
            return "", {"error": f"Anthropic API error {response.status_code}"}

        if stream:
            # Handle streaming from Anthropic
            output_text, first_token_time = _process_anthropic_stream(response, formatting_function, width, first_token_time)
        else:
            # Handle non-streaming
            response_data = response.json()
            content = response_data.get("content", [])
            if content and isinstance(content[0], dict):
                output_text = content[0].get("text", "")

        if collect_stats:
            stats = {
                "model": anthropic_model,
                "total_time": time.time() - start_time,
                "time_to_first_token": first_token_time - start_time if first_token_time else None,
                "input_tokens": 0,  # Would need to parse from response
                "output_tokens": 0,
                "total_tokens": 0,
            }
            return output_text, stats

        return output_text, None

    except Exception as e:
        logging.exception(f"Anthropic API call failed: {e}")
        return "", {"error": f"Anthropic API error: {str(e)}"}


def _process_anthropic_stream(response, formatting_function, width, first_token_time):
    """Process Anthropic API streaming response"""
    output_text = ""
    try:
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8').strip()
                if not decoded.startswith("data:"):
                    continue

                json_str = decoded[5:].strip()
                if not json_str:
                    continue

                try:
                    chunk = json.loads(json_str)
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            token = delta.get("text", "")
                            if token:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                output_text += token
                                print(token, end='', flush=True)
                except json.JSONDecodeError:
                    pass

        if output_text:
            print("", flush=True)
    except Exception as e:
        logging.exception(f"Error processing Anthropic stream: {e}")

    return output_text, first_token_time


def llm_wrapper(messages: List[Dict[str, str]],
                model_name: Optional[str] = None,
                formatting_function: Optional[callable] = None,
                stream: bool = True,
                width: Optional[int] = None,
                collect_stats: bool = False) -> Tuple[str, Optional[Dict[str, Any]]]:
    if not messages:
        logging.error("llm_wrapper: Called with empty messages list.")
        return "[Errore: Nessun messaggio]", {"error": "No messages provided"}

    # DUAL-PROVIDER SUPPORT: Try Anthropic API first for Haiku 4.5, fallback to OpenRouter
    if model_name and model_name == "claude-haiku-4.5":
        result = _try_anthropic_api(messages, model_name, formatting_function, stream, width, collect_stats)
        if result[1] is None or "error" not in result[1]:  # Success or no error
            return result
        # If Anthropic API fails, log and fall through to OpenRouter fallback
        logging.warning(f"Anthropic API failed for {model_name}, falling back to OpenRouter with claude-3.5-haiku")
        model_name = "anthropic/claude-3.5-haiku"  # Fallback

    # DEFAULT: Use OpenRouter
    api_key = os.environ.get("OPENROUTER_API_KEY")
    api_base = "https://openrouter.ai/api/v1"
    site_url = os.environ.get("OPENROUTER_APP_URL", "http://localhost")
    app_title = os.environ.get("OPENROUTER_APP_TITLE", "MyNexusClient") # Or your app's name

    if not api_key:
        logging.error("OPENROUTER_API_KEY environment variable not set.")
        return "[Errore: Chiave API OpenRouter mancante]", {"error": "OPENROUTER_API_KEY not set"}

    if model_name is None:
        model_name = os.environ.get("OPENROUTER_DEFAULT_MODEL", "google/gemini-2.0-flash-exp:free") # Default model

    if formatting_function is None: formatting_function = TerminalFormatter.format_terminal_text
    if width is None: width = TerminalFormatter.get_terminal_width()

    # --- MODIFIED Check for Last Message Role ---
    # This check allows system-only prompts if they are for specific utility tasks.
    is_utility_call_with_system_prompt_only = False
    if len(messages) == 1 and messages[0].get("role") == "system":
        system_content = messages[0].get("content", "")
        # The marker phrase from player_profile_manager.py
        if system_content.strip().startswith("You are an AI analyzing a player's recent interactions"):
            is_utility_call_with_system_prompt_only = True
            #logging.info("llm_wrapper: Detected system-only utility call (profile analysis). Proceeding with API call.")
        # Add elif for other utility markers if needed in the future.

    if not is_utility_call_with_system_prompt_only and messages[-1].get("role") != "user":
        last_role = messages[-1].get("role", "unknown")
        logging.warning(f"llm_wrapper: Last message role is '{last_role}' (expected 'user') and not a recognized utility call. Skipping API call.")

        output_text = "" # Default for skipped call
        # If the last message was an assistant trying to speak (e.g., from a previous turn),
        # we might want to "echo" it. This is primarily for when llm_wrapper might be used in a loop
        # where the last AI response is fed back in. In our current game loop, this isn't typical.
        if messages[-1].get("role") == 'assistant':
            output_text = messages[-1].get('content', '')
            # The printing of this echoed output should be handled by the caller (ChatSession.ask)
            # if formatting_function and width: print(formatting_function(output_text, width=width))
            # else: print(output_text)

        stats = None
        if collect_stats:
            stats = {
                "model": model_name, "total_time": 0.0, "time_to_first_token": None,
                "input_tokens": sum(len(str(msg.get('content', '')).split()) for msg in messages),
                "output_tokens": 0, "total_tokens": sum(len(str(msg.get('content', '')).split()) for msg in messages),
                "error": "Skipped API call - last message not user or not recognized utility"
            }
        return output_text, stats
    # --- End MODIFIED Check ---

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": site_url,
        "X-Title": app_title,
    }
    # Special handling for GPT-5 models
    if model_name and model_name.startswith("openai/gpt-5"):
        # GPT-5 is a reasoning model - increase max_tokens to allow for reasoning + content
        payload = { "model": model_name, "messages": messages, "stream": stream }
        payload["max_tokens"] = 2048  # Higher limit for reasoning models
        payload["temperature"] = 0.7
        payload["top_p"] = 0.9
        payload["reasoning_effort"] = "low"  # Enable reasoning: low/medium/high
        logging.info(f"GPT-5 reasoning enabled with effort=low")
    else:
        payload = { "model": model_name, "messages": messages, "stream": stream }
        payload["max_tokens"] = 2048  # Increased from 512 to allow notecard generation
        payload["temperature"] = 0.7
        payload["top_p"] = 0.9

    start_time = time.time()
    first_token_time = None
    output_text = ""
    response_data_for_stats = None # For non-streaming, to pass full JSON to stats
    stats = None

    try:
        #logging.info(f"llm_wrapper: Calling model {model_name}. Stream: {stream}.")
        # logging.debug(f"llm_wrapper: Payload: {json.dumps(payload, indent=2)[:500]}...") # Careful with logging full payload

        # Optimize timeout based on request type
        if stream:
            timeout = 120  # Shorter timeout for streaming (more responsive)
        else:
            timeout = 60   # Even shorter for non-streaming requests
        
        session = get_request_session()
        response = session.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            stream=stream,
            timeout=timeout
        )

        if stream:
            if response.status_code != 200:
                # Attempt to get error detail from streaming error response if possible
                error_content = ""
                try: error_content = response.text[:500] # Read some text
                except: pass
                logging.error(f"Streaming API call failed with status {response.status_code}. Response text: {error_content}")
                response.raise_for_status() # This will then raise an HTTPError

            # process_direct_streaming_output handles its own printing of tokens
            output_text, first_token_time = process_direct_streaming_output(
                response, formatting_function, width, first_token_time
            )
            # For streaming, OpenRouter doesn't typically send usage stats in chunks.
            # If the API sends a final JSON with usage in the stream, process_direct_streaming_output would need to capture it.
            # Assuming no separate stats payload in stream for now.
        else: # Non-streaming
            if response.status_code != 200:
                logging.error(f"Non-streaming API call failed with status {response.status_code}. Response: {response.text}")
                response.raise_for_status()

            response_data_for_stats = response.json()
            # process_direct_non_streaming_output extracts text but does NOT print by default.
            # Printing is handled by the caller (ChatSession)
            output_text, first_token_time = process_direct_non_streaming_output(
                response_data_for_stats, formatting_function, width
            )

        # Collect stats after successful call (or attempt)
        if collect_stats:
            stats = collect_direct_api_statistics(
                model_name, messages, output_text, start_time, first_token_time, response_data_for_stats
            )

    except requests.exceptions.Timeout:
        logging.exception(f"API call to {model_name} timed out.")
        output_text = "[Errore: Timeout API]"
        if collect_stats: stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, None); stats["error"] = "Timeout"
    except requests.exceptions.RequestException as e: # Catches HTTPError, ConnectionError etc.
        logging.exception(f"API call to {model_name} failed: {e}")
        error_detail = ""
        response_from_error = None
        if hasattr(e, 'response') and e.response is not None:
            response_from_error = e.response
            try:
                err_json = response_from_error.json()
                error_detail = err_json.get("error",{}).get("message","N/A")
                response_data_for_stats = err_json # Use error JSON for stats if available
            except json.JSONDecodeError:
                error_detail = response_from_error.text[:200] # First 200 chars if not JSON
        # print(f"\n{TF.RED}❌ Errore chiamata API ({model_name}): {e}{TF.RESET}" + (f" Dettaglio: {error_detail}" if error_detail else ""))
        output_text = f"[Errore API: {str(e)} - {error_detail}]"
        if collect_stats:
            stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, response_data_for_stats)
            if not stats.get("error"): stats["error"] = str(e) # Ensure error is captured
    except Exception as e:
        logging.exception(f"An unexpected error occurred during API interaction with {model_name}: {e}")
        # print(f"\n{TF.RED}❌ Errore inatteso ({model_name}): {type(e).__name__} - {e}{TF.RESET}")
        output_text = f"[Errore Inatteso: {e}]"
        if collect_stats: stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, None, None); stats["error"] = f"{type(e).__name__}: {e}"

    # Fallback stats creation if an error occurred very early or collect_stats was true but stats is still None
    if collect_stats and stats is None:
        stats = collect_direct_api_statistics(model_name, messages, output_text, start_time, first_token_time, response_data_for_stats)
        if not stats.get("error") and not output_text.startswith("[Errore"): # If no error was set and output doesn't indicate one
            stats["error"] = "Unknown issue, stats object was None before final collection"
        elif not stats.get("error") and output_text.startswith("[Errore"):
            stats["error"] = output_text # Capture error from output_text if not already in stats

    return output_text, stats

if __name__ == "__main__":
    load_dotenv()
    print(f"{TF.YELLOW}--- LLM Wrapper Self-Tests ---{TF.RESET}")

    # Test 1: Utility call (system prompt only) - NON-STREAMING for profile analysis
    print(f"\n{TF.BOLD}Test 1: System-only utility call (Profile Analysis - Non-Streaming){TF.RESET}")
    # This marker is what player_profile_manager.py should put at the start of its system prompt
    profile_analysis_system_prompt = """You are an AI analyzing a player's recent interactions
The player's current profile is:
{"core_traits": {"curiosity": 6}}
Recent interaction:
[{"role": "user", "content": "Tell me more about the Veil."}]
Actions:
["Asked about Veil"]
Suggest updates as JSON: {"trait_adjustments": {"curiosity": "+1"}, "analysis_notes": "Player showed high curiosity."}"""

    messages_utility = [{"role": "system", "content": profile_analysis_system_prompt}]
    response_utility, stats_utility = llm_wrapper(
        messages_utility,
        model_name="mistralai/mistral-7b-instruct:free", # Or your preferred model
        stream=False, # Utility calls are often better non-streamed to get full JSON
        collect_stats=True
    )
    print(f"\n{TF.DIM}LLM Response (Utility - should be JSON parsable):{TF.RESET}\n{response_utility}")
    print(f"{TF.DIM}Stats (Utility): {stats_utility}{TF.RESET}\n")
    try:
        parsed_utility_response = json.loads(response_utility)
        assert "trait_adjustments" in parsed_utility_response or "analysis_notes" in parsed_utility_response
        print(f"{TF.GREEN}✓ Utility call JSON parsing successful.{TF.RESET}")
    except json.JSONDecodeError as je:
        print(f"{TF.RED}✗ Utility call JSON parsing FAILED: {je}{TF.RESET}")
        print(f"  LLM returned: {response_utility}") # Print what it returned

    # Test 2: Standard dialogue call (user prompt last) - STREAMING
    print(f"\n{TF.BOLD}Test 2: Standard dialogue (Streaming){TF.RESET}")
    messages_dialogue = [
        {"role": "system", "content": "You are a helpful pirate captain."},
        {"role": "user", "content": "Ahoy there! What be the news?"}
    ]
    response_dialogue, stats_dialogue = llm_wrapper(
        messages_dialogue,
        model_name="mistralai/mistral-7b-instruct:free",
        stream=True,
        collect_stats=True
    )
    # Streaming output is printed by process_direct_streaming_output
    print(f"\n{TF.DIM}Stats (Dialogue): {stats_dialogue}{TF.RESET}\n")
    assert "Skipped API call" not in str(stats_dialogue.get("error", ""))

    # Test 3: Skipped call (last message not user and not utility)
    print(f"\n{TF.BOLD}Test 3: Skipped call (last message assistant, not utility){TF.RESET}")
    messages_skipped = [
        {"role": "system", "content": "You are a merchant."},
        {"role": "assistant", "content": "Welcome to my shop! What can I get for you?"} # Last is assistant
    ]
    response_skipped, stats_skipped = llm_wrapper(
        messages_skipped,
        model_name="mistralai/mistral-7b-instruct:free",
        stream=False, # Easier to see outcome
        collect_stats=True
    )
    print(f"\n{TF.DIM}LLM Response (Skipped): '{response_skipped}' (should be empty or echo assistant){TF.RESET}")
    print(f"{TF.DIM}Stats (Skipped): {stats_skipped}{TF.RESET}\n")
    assert "Skipped API call" in str(stats_skipped.get("error", ""))

    # --- Test 4: GPT-5 Pro Reasoning Token Handling ---
    print(f"\n{TF.BOLD}Test 4: GPT-5 Pro (no reasoning){TF.RESET}")
    messages_gpt5 = [
        {"role": "system", "content": "You are a wise oracle."},
        {"role": "user", "content": "What is the meaning of life?"}
    ]
    response_gpt5, stats_gpt5 = llm_wrapper(
        messages_gpt5,
        model_name="openai/gpt-5-mini",
        stream=False,
        collect_stats=True
    )
    print(f"\n{TF.DIM}LLM Response (GPT-5 Mini, no reasoning):{TF.RESET}\n{response_gpt5}")
    print(f"{TF.DIM}Stats (GPT-5 Mini, no reasoning): {stats_gpt5}{TF.RESET}\n")

    print(f"\n{TF.BOLD}Test 5: GPT-5 Mini (Capital of France, no reasoning){TF.RESET}")
    messages_gpt5_france = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    response_gpt5_france, stats_gpt5_france = llm_wrapper(
        messages_gpt5_france,
        model_name="openai/gpt-5-mini",
        stream=False,
        collect_stats=True
    )
    print(f"\n{TF.DIM}LLM Response (GPT-5 Mini, capital of France):{TF.RESET}\n{response_gpt5_france}")
    print(f"{TF.DIM}Stats (GPT-5 Mini, capital of France): {stats_gpt5_france}{TF.RESET}\n")

    print(f"\n{TF.BOLD}Test 4b: GPT-5 Mini (with reasoning tokens){TF.RESET}")
    # Add reasoning parameter to payload by monkey-patching llm_wrapper for this test
    def llm_wrapper_with_reasoning(messages, model_name=None, formatting_function=None, stream=True, width=None, collect_stats=False):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        api_base = "https://openrouter.ai/api/v1"
        site_url = os.environ.get("OPENROUTER_APP_URL", "http://localhost")
        app_title = os.environ.get("OPENROUTER_APP_TITLE", "MyNexusClient")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": site_url,
            "X-Title": app_title,
        }
        payload = { "model": model_name, "messages": messages, "stream": stream, "include_reasoning": True }
        payload["max_tokens"] = 2048  # Increased from 512 to allow notecard generation
        payload["temperature"] = 0.7
        payload["top_p"] = 0.9
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            stream=stream,
            timeout=60
        )
        response_data = response.json()
        output_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        reasoning = response_data.get("choices", [{}])[0].get("message", {}).get("reasoning", None)
        if reasoning:
            print(f"{TF.MAGENTA}Reasoning tokens:{TF.RESET}\n{reasoning}")
        return output_text, response_data

    response_gpt5_reasoning, stats_gpt5_reasoning = llm_wrapper_with_reasoning(
        messages_gpt5,
        model_name="openai/gpt-5-mini",
        stream=False
    )
    print(f"\n{TF.DIM}LLM Response (GPT-5 Mini, with reasoning):{TF.RESET}\n{response_gpt5_reasoning}")
    print(f"{TF.DIM}Raw API Response (GPT-5 Mini, with reasoning): {stats_gpt5_reasoning}{TF.RESET}\n")

    print(f"{TF.YELLOW}--- LLM Wrapper Self-Tests Done ---{TF.RESET}")