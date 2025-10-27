# game_system_api.py
import sys
import traceback
import copy
import threading
import time
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Callable
import re

# Assume all necessary modules are in PYTHONPATH or imported correctly
from db_manager import DbManager
from chat_manager import ChatSession, format_stats
from llm_wrapper import llm_wrapper
import session_utils
import command_processor
from player_profile_manager import update_player_profile, get_default_player_profile
from main_utils import get_nlp_command_config, format_npcs_list, get_help_text
from wise_guide_selector import get_wise_guide_npc_name

# Configure logger for async profile updates
logger = logging.getLogger(__name__)

from terminal_formatter import TerminalFormatter

# Helper to remove ANSI codes for LSL output
def clean_ansi_codes(text: str) -> str:
  ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
  cleaned = ansi_escape.sub('', text)
  cleaned = re.sub(r'\033\[[0-9;]*m', '', cleaned)
  return cleaned

class _SinglePlayerGameSystem:
    """
    Manages the game state and logic for a single player.
    This class is internal to GameSystem.
    """
    def __init__(self,
                 db: DbManager,
                 story: str,
                 wise_guide_npc_name: Optional[str],
                 player_id: str,
                 model_name: str,
                 profile_analysis_model_name: Optional[str],
                 debug_mode: bool):

        nlp_config = get_nlp_command_config()

        # Try to load persistent player state (including current_npc_code)
        saved_state = db.load_player_state(player_id)
        self.game_state: Dict[str, Any] = {
            'db': db,
            'story': story,
            'current_area': None,
            'current_npc': None,
            'chat_session': None,
            'model_name': model_name,
            'profile_analysis_model_name': profile_analysis_model_name or model_name,
            'use_stream': False,
            'auto_show_stats': False,
            'debug_mode': debug_mode,
            'player_id': player_id,
            'player_inventory': db.load_inventory(player_id),
            'player_credits_cache': db.get_player_credits(player_id),
            'player_profile_cache': db.load_player_profile(player_id),
            'ChatSession': ChatSession,
            'TerminalFormatter': TerminalFormatter,
            'format_stats': format_stats,
            'llm_wrapper_func': llm_wrapper,
            'npc_made_new_response_this_turn': False,
            'actions_this_turn_for_profile': [],
            'in_hint_mode': False,
            'stashed_chat_session': None,
            'stashed_npc': None,
            'hint_cache': {},
            'wise_guide_npc_name': wise_guide_npc_name,
            'nlp_command_interpretation_enabled': nlp_config['enabled'],
            'nlp_command_confidence_threshold': nlp_config['confidence_threshold'],
            'nlp_command_debug': nlp_config['debug_mode'] or debug_mode,
            'system_messages_buffer': [],
            'game_system_instance': self,  # Reference for accessing cached data
        }
        # Async profile update tracking
        self._profile_update_thread = None
        self._pending_profile_update = False
        self.output_buffer: List[str] = []
        
        # Context pre-loading cache for performance
        self._context_cache = {
            'npcs_list': None,
            'npcs_list_last_refresh': 0,
            'areas_list': None, 
            'system_prompt_cache': {},  # keyed by (npc_name, profile_hash)
            'conversation_history_cache': {},  # keyed by player_id + npc_name
            'cache_ttl': 300  # 5 minutes TTL
        }

        # Restore current_npc and chat_session from persistent state if available
        if saved_state and saved_state.get('current_npc_code'):
            npc_obj = db.get_npc_by_code(saved_state['current_npc_code'])
            if npc_obj:
                self.game_state['current_npc'] = npc_obj
                # Try to reconstruct chat session for this NPC
                area = npc_obj.get('area')
                name = npc_obj.get('name')
                if area and name:
                    _, chat_session = session_utils.load_and_prepare_conversation(
                        db, player_id, area, name, model_name, story, ChatSession, TerminalFormatter, self.game_state
                    )
                    if chat_session:
                        self.game_state['chat_session'] = chat_session

        self._auto_start_initial_conversation()

    def _async_profile_update(self, 
                             initial_profile_for_comparison,
                             interaction_log_for_profile, 
                             npc_name_for_profile_update):
        """Async profile update worker that runs in background thread."""
        start_time = time.time()
        try:
            logger.info(f"[PROFILE-ASYNC] Starting profile analysis for {self.game_state['player_id']}")
            
            current_profile_cache = self.game_state.get('player_profile_cache', get_default_player_profile())

            updated_profile, profile_changes_detected = update_player_profile(
                previous_profile=current_profile_cache,
                interaction_log=interaction_log_for_profile,
                player_actions_summary=self.game_state['actions_this_turn_for_profile'],
                llm_wrapper_func=self.game_state['llm_wrapper_func'],
                model_name=self.game_state['profile_analysis_model_name'],
                current_npc_name=npc_name_for_profile_update,
                TF=self.game_state['TerminalFormatter']
            )

            # Thread-safe update of profile
            elapsed_ms = int((time.time() - start_time) * 1000)
            if updated_profile != initial_profile_for_comparison:
                self.game_state['player_profile_cache'] = updated_profile
                self.game_state['db'].save_player_profile(self.game_state['player_id'], updated_profile)
                logger.info(f"[PROFILE-ASYNC] Profile updated for {self.game_state['player_id']} in {elapsed_ms}ms")
            else:
                logger.info(f"[PROFILE-ASYNC] No changes for {self.game_state['player_id']} in {elapsed_ms}ms")
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[PROFILE-ASYNC] Error for {self.game_state['player_id']} after {elapsed_ms}ms: {str(e)}")
        finally:
            self._pending_profile_update = False

    def _get_cached_npcs_list(self):
        """Get cached NPCs list or refresh if stale."""
        current_time = time.time()
        if (not self._context_cache['npcs_list'] or 
            current_time - self._context_cache['npcs_list_last_refresh'] > self._context_cache['cache_ttl']):
            
            logger.info(f"[CONTEXT-CACHE] Refreshing NPCs list for {self.game_state['player_id']}")
            self._context_cache['npcs_list'] = session_utils.refresh_known_npcs_list(
                self.game_state['db'], self.game_state['TerminalFormatter']
            )
            self._context_cache['areas_list'] = session_utils.get_known_areas_from_list(
                self._context_cache['npcs_list']
            )
            self._context_cache['npcs_list_last_refresh'] = current_time
        
        return self._context_cache['npcs_list']

    def _get_cached_areas_list(self):
        """Get cached areas list (depends on NPCs list)."""
        self._get_cached_npcs_list()  # Ensure NPCs are loaded
        return self._context_cache['areas_list']

    def _get_system_prompt_cache_key(self, npc_name: str, player_profile: dict) -> str:
        """Generate cache key for system prompts based on NPC and player profile."""
        profile_str = str(sorted(player_profile.items())) if player_profile else ""
        profile_hash = hashlib.md5(profile_str.encode()).hexdigest()[:8]
        return f"{npc_name}_{profile_hash}"

    def _preload_context_for_dialogue(self, npc_name: str = None):
        """Pre-load frequently accessed context data."""
        start_time = time.time()
        
        # Pre-load NPCs and areas
        self._get_cached_npcs_list()
        
        # Pre-load conversation history if we know the NPC and method exists
        if npc_name and hasattr(self.game_state['db'], 'get_conversation_history'):
            cache_key = f"{self.game_state['player_id']}_{npc_name}"
            if cache_key not in self._context_cache['conversation_history_cache']:
                try:
                    conversation_history = self.game_state['db'].get_conversation_history(
                        self.game_state['player_id'], npc_name
                    )
                    self._context_cache['conversation_history_cache'][cache_key] = conversation_history
                except Exception as e:
                    logger.error(f"[CONTEXT-CACHE] Error preloading conversation history: {e}")
        elif npc_name:
            logger.debug(f"[CONTEXT-CACHE] Conversation history caching not available for {npc_name}")
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[CONTEXT-CACHE] Context preloaded in {elapsed_ms}ms for {self.game_state['player_id']}")

    def wait_for_profile_update(self, timeout: float = 0.5) -> bool:
        """Wait for profile update to complete with timeout. Returns True if completed."""
        if self._profile_update_thread and self._profile_update_thread.is_alive():
            self._profile_update_thread.join(timeout=timeout)
            return not self._profile_update_thread.is_alive()
        return True

    def _auto_start_initial_conversation(self):
        if self.game_state['debug_mode']:
            print(f"[DEBUG] Attempting auto-start for {self.game_state['player_id']}...")

        if self.game_state['wise_guide_npc_name']:
            all_npcs = session_utils.refresh_known_npcs_list(self.game_state['db'], TerminalFormatter)
            guide_data = next(
                ((npc.get('area'), npc.get('name')) for npc in all_npcs
                 if npc.get('name', '').lower() == self.game_state['wise_guide_npc_name'].lower()),
                None
            )
            if guide_data:
                guide_area, guide_name = guide_data
                self.game_state['current_area'] = guide_area
                npc_obj, session = session_utils.start_conversation_with_specific_npc(
                    self.game_state['db'], self.game_state['player_id'], guide_area, guide_name,
                    self.game_state['model_name'], self.game_state['story'],
                    ChatSession, TerminalFormatter, self.game_state,
                    llm_wrapper_for_profile_distillation=llm_wrapper
                )
                if npc_obj and session:
                    self.game_state['current_npc'] = npc_obj
                    self.game_state['chat_session'] = session
                    return
        self.game_state['system_messages_buffer'].append(
            f"Welcome, {self.game_state['player_id']}! Type '/go <area>' to explore. '/help' for commands."
        )

    def process_player_input(self, player_input: str, skip_profile_update: bool = False) -> Dict[str, Any]:
        if self.game_state is None:
            self.game_state = {}
        self.game_state['system_messages_buffer'] = []
        self.output_buffer = []
        self.game_state['npc_made_new_response_this_turn'] = False
        self.game_state['actions_this_turn_for_profile'] = []

        # Pre-load context for better performance
        current_npc = self.game_state.get('current_npc', {})
        current_npc_name = current_npc.get('name') if current_npc else None
        if not player_input.startswith('/'):  # Only for dialogue interactions
            self._preload_context_for_dialogue(current_npc_name)

        initial_profile_for_comparison = copy.deepcopy(
            self.game_state.get('player_profile_cache', get_default_player_profile())
        )

        original_stdout = sys.stdout
        class CaptureStdout:
            def __init__(self, buffer_list):
                self.buffer_list = buffer_list
            def write(self, s):
                self.buffer_list.append(s)
            def flush(self):
                pass
        sys.stdout = CaptureStdout(self.output_buffer)

        try:
            if self.game_state is None:
                logger.warning(f"[DEBUG] game_state was None before process_input_revised, initializing to {{}}")
                self.game_state = {}
            logger.info(f"[DEBUG] Calling process_input_revised with player_input: {player_input[:50]}...")
            result = command_processor.process_input_revised(player_input, self.game_state)
            logger.info(f"[DEBUG] process_input_revised returned: {type(result)} - is None: {result is None}")
            if result is None:
                logger.error(f"[DEBUG] Command processor returned None for input: {player_input}")
                self.game_state['system_messages_buffer'].append("Error: Command processor returned None")
                return None
            self.game_state = result
            logger.info(f"[DEBUG] game_state updated, is None: {self.game_state is None}")

            if 'system_message_for_ui' in self.game_state:
                self.game_state['system_messages_buffer'].append(self.game_state.pop('system_message_for_ui'))

            # Start async profile update if needed (non-blocking) - only once per request
            if (self.game_state.get('npc_made_new_response_this_turn') or
                self.game_state.get('actions_this_turn_for_profile')) and \
               not self.game_state.get('in_hint_mode') and \
               not self._pending_profile_update and \
               not skip_profile_update:  # Skip profile updates for setup commands
                
                interaction_log_for_profile = []
                if self.game_state.get('chat_session') and self.game_state['chat_session'].messages:
                    interaction_log_for_profile = self.game_state['chat_session'].messages[-4:]

                current_npc_obj_for_profile = self.game_state.get('current_npc')
                npc_name_for_profile_update = current_npc_obj_for_profile.get('name') if current_npc_obj_for_profile else None

                # Start async profile update
                self._pending_profile_update = True
                self._profile_update_thread = threading.Thread(
                    target=self._async_profile_update,
                    args=(initial_profile_for_comparison, interaction_log_for_profile, npc_name_for_profile_update),
                    daemon=True
                )
                self._profile_update_thread.start()
                logger.info(f"[PROFILE-ASYNC] Started background thread for {self.game_state['player_id']}")

            logger.info(f"[DEBUG] End of try block, game_state is None: {self.game_state is None}")

        finally:
            sys.stdout = original_stdout
            logger.info(f"[DEBUG] Start of finally block, game_state is None: {self.game_state is None}, type: {type(self.game_state)}")

            current_npc_name_for_filter = None
            if self.game_state:
                current_npc = self.game_state.get('current_npc')
                if current_npc:
                    current_npc_name_for_filter = current_npc.get('name')
            npc_prompt_artifact_pattern = None
            if current_npc_name_for_filter:
                npc_prompt_artifact_pattern = re.compile(rf"^\s*{re.escape(current_npc_name_for_filter)}\s*>\s*$")

            LSL_EXCLUDE_PREFIXES = [
                "[DEBUG]", "[INIT]", "---", "NOW TALKING TO",
                "Type '/exit'", "===============", "[NLP]"
            ]

            for line in self.output_buffer:
                clean_line = clean_ansi_codes(line).strip()
                is_artifact = False
                if npc_prompt_artifact_pattern and npc_prompt_artifact_pattern.match(clean_line):
                    is_artifact = True

                is_excluded_for_lsl = any(clean_line.startswith(prefix) for prefix in LSL_EXCLUDE_PREFIXES)

                if clean_line and not is_artifact and not is_excluded_for_lsl:
                    self.game_state['system_messages_buffer'].append(clean_line)
                # Removed the elif that re-added debug lines with "[Captured STDOUT - Debug]:"

            self.game_state['db'].save_player_state(self.game_state['player_id'], self.game_state)
            if self.game_state.get('current_npc') and self.game_state.get('chat_session'):
                session_utils.save_current_conversation(
                    self.game_state['db'], self.game_state['player_id'], self.game_state['current_npc'],
                    self.game_state['chat_session'], TerminalFormatter, self.game_state
                )

        final_npc_dialogue_for_return = ""
        last_speaker_for_suffix = None

        if self.game_state.get('chat_session') and self.game_state['chat_session'].messages:
            if self.game_state.get('npc_made_new_response_this_turn', False):
                for i in range(len(self.game_state['chat_session'].messages) - 1, -1, -1):
                    msg = self.game_state['chat_session'].messages[i]
                    if msg.get('role') == 'assistant':
                        final_npc_dialogue_for_return = msg.get('content', '')

                        # Extract notecard if present
                        logger.info(f"[NOTECARD_CHECK] Response has [notecard=: {'[notecard=' in final_npc_dialogue_for_return}, length={len(final_npc_dialogue_for_return)}")
                        notecard_was_extracted = False
                        if '[notecard=' in final_npc_dialogue_for_return:
                            logger.info("[NOTECARD_EXTRACTION] Found notecard in response, extracting...")
                            from chat_manager import extract_notecard_from_response
                            cleaned_response, notecard_name, notecard_content = extract_notecard_from_response(final_npc_dialogue_for_return)
                            logger.info(f"[NOTECARD_EXTRACTION] Extracted: name='{notecard_name}', content_len={len(notecard_content)}")
                            if notecard_name and notecard_content:
                                # Store notecard info in game state for SL commands generation
                                self.game_state['notecard_extracted'] = {
                                    'name': notecard_name,
                                    'content': notecard_content
                                }
                                # Replace response with cleaned version (notecard removed)
                                final_npc_dialogue_for_return = cleaned_response
                                notecard_was_extracted = True
                                logger.info(f"[NOTECARD] Extracted '{notecard_name}' from NPC response ({len(notecard_content)} chars)")

                        # AUTO-TREASURE SYSTEM: If notecard given and NPC has treasure + player has required item
                        # automatically append treasure to [GIVEN_ITEMS:] tag
                        if notecard_was_extracted:
                            current_npc = self.game_state.get('current_npc', {})
                            npc_treasure = current_npc.get('treasure')
                            npc_required_item = current_npc.get('required_item')
                            player_inventory = self.game_state.get('player_inventory', [])
                            
                            logger.info(f"[AUTO_TREASURE] Notecard extracted. NPC treasure={npc_treasure}, required_item={npc_required_item}, player_inventory={player_inventory}")
                            
                            # Check if NPC has treasure defined and player has required item
                            if npc_treasure and npc_required_item:
                                # Check if player has the required item (case-insensitive)
                                player_has_required_item = any(
                                    item.lower() == npc_required_item.lower() 
                                    for item in player_inventory
                                )
                                
                                if player_has_required_item:
                                    logger.info(f"[AUTO_TREASURE] ✓ Player has '{npc_required_item}' - auto-adding treasure '{npc_treasure}'")
                                    
                                    # Check if [GIVEN_ITEMS:] already exists in response
                                    if '[GIVEN_ITEMS:' in final_npc_dialogue_for_return:
                                        # Append to existing tag
                                        tag_start = final_npc_dialogue_for_return.find('[GIVEN_ITEMS:')
                                        tag_end = final_npc_dialogue_for_return.find(']', tag_start)
                                        if tag_end != -1:
                                            existing_items = final_npc_dialogue_for_return[tag_start+13:tag_end].strip()
                                            if existing_items:
                                                new_items = f"{existing_items}, {npc_treasure}"
                                            else:
                                                new_items = npc_treasure
                                            final_npc_dialogue_for_return = (
                                                final_npc_dialogue_for_return[:tag_start+13] + 
                                                new_items + 
                                                final_npc_dialogue_for_return[tag_end:]
                                            )
                                            logger.info(f"[AUTO_TREASURE] Appended to existing [GIVEN_ITEMS:] tag")
                                    else:
                                        # Add new [GIVEN_ITEMS:] tag at the end
                                        final_npc_dialogue_for_return += f" [GIVEN_ITEMS: {npc_treasure}]"
                                        logger.info(f"[AUTO_TREASURE] Added new [GIVEN_ITEMS: {npc_treasure}] tag")
                                else:
                                    logger.info(f"[AUTO_TREASURE] ✗ Player doesn't have required item '{npc_required_item}'")
                            else:
                                logger.info(f"[AUTO_TREASURE] No auto-treasure applicable (treasure={npc_treasure}, required={npc_required_item})")

                        if self.game_state['debug_mode']:
                            self.game_state['system_messages_buffer'].append(f"[Debug] NPC response length: {len(final_npc_dialogue_for_return)}")
                        if self.game_state.get('current_npc'):
                            last_speaker_for_suffix = self.game_state.get('current_npc',{}).get('name')
                        break
                if final_npc_dialogue_for_return:
                    tag_marker_start = "[GIVEN_ITEMS:"
                    tag_marker_end = "]"
                    tag_start_idx = final_npc_dialogue_for_return.rfind(tag_marker_start)
                    if tag_start_idx != -1:
                        tag_end_idx = final_npc_dialogue_for_return.find(tag_marker_end, tag_start_idx)
                        if tag_end_idx != -1:
                            given_items_str = final_npc_dialogue_for_return[tag_start_idx + len(tag_marker_start):tag_end_idx].strip()
                            final_npc_dialogue_for_return = final_npc_dialogue_for_return[:tag_start_idx].strip()
                            if given_items_str:
                                self.game_state['system_messages_buffer'].append(f"You received: {given_items_str}")
                                
                                # Process items and credits (similar to main_core.py)
                                items_given_names = []
                                credits_given = 0
                                potential_items = [item.strip() for item in given_items_str.split(',') if item.strip()]
                                logger.info(f"[ITEM-PROCESSING] Processing items: {potential_items}")
                                
                                for item_str in potential_items:
                                    credit_match = re.match(r"(-?\d+)\s+credits?", item_str, re.IGNORECASE)
                                    if credit_match:
                                        credits_given += int(credit_match.group(1))
                                        logger.info(f"[ITEM-PROCESSING] Found credits: {credit_match.group(1)}")
                                    else:
                                        items_given_names.append(item_str)
                                        logger.info(f"[ITEM-PROCESSING] Found item: {item_str}")
                                
                                # Add items to inventory
                                player_id = self.game_state.get('player_id')
                                db = self.game_state.get('db')
                                current_npc = self.game_state.get('current_npc', {})
                                
                                if items_given_names and player_id and db:
                                    for item_name in items_given_names:
                                        logger.info(f"[ITEM-PROCESSING] Adding '{item_name}' to inventory for {player_id}")
                                        if db.add_item_to_inventory(player_id, item_name, self.game_state):
                                            logger.info(f"[ITEM-PROCESSING] Successfully added '{item_name}' to inventory")
                                            # Update profile actions
                                            npc_name = current_npc.get('name', 'NPC')
                                            if 'actions_this_turn_for_profile' not in self.game_state:
                                                self.game_state['actions_this_turn_for_profile'] = []
                                            self.game_state['actions_this_turn_for_profile'].append(f"Received '{item_name}' from {npc_name}")
                                        else:
                                            logger.error(f"[ITEM-PROCESSING] Failed to add '{item_name}' to inventory")
                                
                                # Handle credits
                                if credits_given != 0 and player_id and db:
                                    logger.info(f"[ITEM-PROCESSING] Processing {credits_given} credits for {player_id}")
                                    try:
                                        db.update_player_credits(player_id, credits_given, self.game_state)
                                        logger.info(f"[ITEM-PROCESSING] Successfully updated credits by {credits_given}")
                                        # Update cached credits in game state
                                        if 'player_info' in self.game_state:
                                            current_credits = self.game_state['player_info'].get('credits', 0)
                                            self.game_state['player_info']['credits'] = current_credits + credits_given
                                    except Exception as e:
                                        logger.error(f"[ITEM-PROCESSING] Failed to update credits: {e}")

                # Check for [OFFER_TELEPORT] tag and store flag
                # Also auto-detect teleport offers based on keywords
                teleport_offered = False
                if final_npc_dialogue_for_return:
                    if "[OFFER_TELEPORT]" in final_npc_dialogue_for_return:
                        logger.info(f"[TELEPORT] Detected teleport offer via [OFFER_TELEPORT] tag")
                        final_npc_dialogue_for_return = final_npc_dialogue_for_return.replace("[OFFER_TELEPORT]", "").strip()
                        teleport_offered = True
                    else:
                        # Fallback: Auto-detect teleport intent from keywords
                        teleport_keywords = ["teletrasport", "ti porto", "partiamo", "andiamo al", "vuoi venire"]
                        response_lower = final_npc_dialogue_for_return.lower()
                        if any(keyword in response_lower for keyword in teleport_keywords):
                            logger.info(f"[TELEPORT] Auto-detected teleport offer from keywords in response")
                            teleport_offered = True

                self.game_state['teleport_offered_this_turn'] = teleport_offered

            elif self.game_state['debug_mode']:
                 self.game_state['system_messages_buffer'].append("[Debug] No new NPC response marked this turn for API return construction.")


        if not final_npc_dialogue_for_return and self.game_state.get('npc_made_new_response_this_turn'):
            current_npc_obj_fallback = self.game_state.get('current_npc',{})
            last_speaker_for_suffix = current_npc_obj_fallback.get('name','The NPC')
            final_npc_dialogue_for_return = f"*{last_speaker_for_suffix} seems to ponder...*"
            if self.game_state['debug_mode']:
                 self.game_state['system_messages_buffer'].append(f"[Debug] Fallback ponder message used for {last_speaker_for_suffix}")

        current_npc_obj_for_return = self.game_state.get('current_npc')
        current_npc_name_for_return = current_npc_obj_for_return.get('name') if current_npc_obj_for_return else None

        return {
            'npc_response': final_npc_dialogue_for_return,
            'system_messages': self.game_state['system_messages_buffer'],
            'player_id': self.game_state['player_id'],
            'current_area': self.game_state['current_area'],
            'current_npc_name': current_npc_name_for_return,
            'inventory': self.game_state['player_inventory'],
            'credits': self.game_state['player_credits_cache'],
            'profile_summary': self._get_profile_summary_for_api(),
            'status': self.game_state.get('status', 'ok'),
            'last_speaker_for_suffix': last_speaker_for_suffix
        }

    def _get_profile_summary_for_api(self) -> str:
        profile = self.game_state.get('player_profile_cache', {})
        traits = profile.get('core_traits', {})
        if not traits:
            return "New adventurer profile."
        sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)[:2]
        trait_desc = ", ".join([f"{t.capitalize()}: {v}/10" for t, v in sorted_traits])
        llm_analysis_notes = profile.get("last_llm_analysis_notes", "LLM perspective not yet recorded.")
        return f"Traits: {trait_desc}. LLM notes: {llm_analysis_notes[:100]}..."


class GameSystem:
    """
    Manages multiple single-player game systems.
    This is the main entry point for an external system like LSL.
    """
    def __init__(self,
                 use_mockup: bool = True,
                 mockup_dir: str = "database",
                 model_name: str = "google/gemma-2-9b-it:free",
                 profile_analysis_model_name: Optional[str] = None,
                 wise_guide_model_name: Optional[str] = None,
                 debug_mode: bool = False):
        self.db = DbManager(use_mockup=use_mockup, mockup_dir=mockup_dir)
        self.db.ensure_db_schema()

        story_data = self.db.get_storyboard()
        self.story = story_data.get("description", "[Storyboard description missing or failed to load]")

        self.wise_guide_npc_name = get_wise_guide_npc_name(
            self.story, self.db, wise_guide_model_name or model_name
        )
        if self.wise_guide_npc_name:
            print(f"[GameSystem Manager Init] Wise guide selected: {self.wise_guide_npc_name}")
        else:
            print("[GameSystem Manager Init] No specific wise guide determined.")

        self.model_name = model_name
        self.profile_analysis_model_name = profile_analysis_model_name
        self.debug_mode = debug_mode

        self._player_systems: Dict[str, _SinglePlayerGameSystem] = {}

    def get_player_system(self, player_id: str) -> _SinglePlayerGameSystem:
        if player_id not in self._player_systems:
            print(f"[GameSystem Manager] Creating new session for player: {player_id}")
            self._player_systems[player_id] = _SinglePlayerGameSystem(
                db=self.db,
                story=self.story,
                wise_guide_npc_name=self.wise_guide_npc_name,
                player_id=player_id,
                model_name=self.model_name,
                profile_analysis_model_name=self.profile_analysis_model_name,
                debug_mode=self.debug_mode
            )
        return self._player_systems[player_id]

    def close_player_session(self, player_id: str) -> None:
        if player_id in self._player_systems:
            # Wait for any pending profile updates before closing
            player_system = self._player_systems[player_id]
            if hasattr(player_system, 'wait_for_profile_update'):
                player_system.wait_for_profile_update(timeout=2.0)
            del self._player_systems[player_id]
            print(f"[GameSystem Manager] Closed session for player: {player_id}")
