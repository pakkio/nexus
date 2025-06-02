"""
Eldoria Dialogue System - Gradio Web Interface (Enhanced)
Integrated LLM profile analysis with robust error handling and immersive fantasy design
"""
import gradio as gr
import os
import sys
import json
import traceback
import copy 
import re 
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

try:
    from terminal_formatter import TerminalFormatter
    from db_manager import DbManager
    from main_utils import get_help_text, format_npcs_list
    from wise_guide_selector import get_wise_guide_npc_name
    from chat_manager import ChatSession, format_stats
    from llm_wrapper import llm_wrapper
    import session_utils
    import command_processor 
    from player_profile_manager import update_player_profile, get_default_player_profile
except ImportError as e:
    print(f"❌ Fatal Error: Could not import required modules: {e}")
    sys.exit(1)


class GameState:
    def __init__(self):
        self.db, self.story, self.session_state, self.wise_guide_npc_name = None, "", {}, None
        self.initialized, self.current_info_display = False, ""
        # Store LLM analysis of player's psychology
        self.latest_llm_profile_analysis_text = "🔮 LLM perspective not yet recorded for this session."

    def initialize(self, use_mockup=True, mockup_dir="database", model_name="openai/gpt-4o-mini", player_id="WebPlayer"):
        print("[DEBUG] GameState.initialize called")
        try:
            # Suppress initialization chatter unless in debug mode
            original_stdout = sys.stdout
            devnull = None
            if not os.environ.get('GRADIO_DEBUG'):
                devnull = open(os.devnull, 'w')
                sys.stdout = devnull
            
            self.db = DbManager(use_mockup=use_mockup, mockup_dir=mockup_dir)
            self.db.ensure_db_schema()
            
            story_data = self.db.get_storyboard()
            self.story = story_data.get("description", "[Storyboard missing]")
            
            self.wise_guide_npc_name = get_wise_guide_npc_name(self.story, self.db, model_name)
            print(f"[DEBUG] Wise guide selection result: {self.wise_guide_npc_name}")
            
            # Verify the wise guide selection with additional debug
            if self.wise_guide_npc_name:
                all_npcs_check = session_utils.refresh_known_npcs_list(self.db, TerminalFormatter)
                guide_found = any(npc.get('name', '').lower() == self.wise_guide_npc_name.lower() 
                                for npc in all_npcs_check)
                print(f"[DEBUG] Wise guide '{self.wise_guide_npc_name}' exists in NPCs: {guide_found}")
                
                # Show all available NPCs for debug
                print(f"[DEBUG] Available NPCs: {[npc.get('name') for npc in all_npcs_check]}")
                
                # Check if Lyra specifically exists
                lyra_exists = any(npc.get('name', '').lower() == 'lyra' for npc in all_npcs_check)
                print(f"[DEBUG] Lyra exists in NPCs: {lyra_exists}")
            else:
                print("[DEBUG] No wise guide was selected by the LLM")
            
            if devnull:
                sys.stdout.close()
                sys.stdout = original_stdout
                devnull = None
            
            initial_credits = self.db.get_player_credits(player_id)
            player_profile = self.db.load_player_profile(player_id)
            
            # Load previous LLM analysis if available
            self.latest_llm_profile_analysis_text = player_profile.get("last_llm_analysis_notes", self.latest_llm_profile_analysis_text)
            
            self.session_state = {
                'db': self.db, 'story': self.story, 'current_area': None, 'current_npc': None, 'chat_session': None, 
                'model_name': model_name, 'profile_analysis_model_name': model_name, 'use_stream': False, 
                'auto_show_stats': False, 'debug_mode': bool(os.environ.get('GRADIO_DEBUG')), 'player_id': player_id,
                'player_inventory': self.db.load_inventory(player_id), 'player_credits_cache': initial_credits, 
                'player_profile_cache': player_profile, 'ChatSession': ChatSession, 'TerminalFormatter': TerminalFormatter, 
                'format_stats': format_stats, 'llm_wrapper_func': llm_wrapper, 'npc_made_new_response_this_turn': False, 
                'actions_this_turn_for_profile': [], 'in_hint_mode': False, 'stashed_chat_session': None, 
                'stashed_npc': None, 'hint_cache': {}, 'wise_guide_npc_name': self.wise_guide_npc_name,
                'nlp_command_interpretation_enabled': True, 'nlp_command_confidence_threshold': 0.7,
                'nlp_command_debug': bool(os.environ.get('GRADIO_DEBUG')),
            }
            
            self._auto_start_with_wise_guide() 
            self.initialized = True
            print("[DEBUG] GameState.initialize completed.")
            return True, f"✨ Welcome to Eldoria! Your journey begins..."
        except Exception as e:
            print(f"[DEBUG] Error in GameState.initialize: {e}")
            traceback.print_exc()
            if devnull:
                sys.stdout.close()
                sys.stdout = original_stdout
            return False, f"Error initializing game: {e}"

    def _auto_start_with_wise_guide(self):
        print("[DEBUG] GameState._auto_start_with_wise_guide")
        if not self.wise_guide_npc_name:
            print("[DEBUG] No wise guide, skipping auto-start.")
            return
        
        try:
            original_stdout = sys.stdout
            devnull = None
            if not os.environ.get('GRADIO_DEBUG'):
                devnull = open(os.devnull, 'w')
                sys.stdout = devnull
            
            all_npcs = session_utils.refresh_known_npcs_list(self.db, TerminalFormatter)
            print(f"[DEBUG] Looking for wise guide '{self.wise_guide_npc_name}' in {len(all_npcs)} NPCs")
            
            guide_data = None
            for npc in all_npcs:
                npc_name = npc.get('name', '')
                print(f"[DEBUG] Checking NPC: '{npc_name}' vs '{self.wise_guide_npc_name}'")
                if npc_name.lower() == self.wise_guide_npc_name.lower():
                    guide_data = (npc.get('area'), npc.get('name'))
                    print(f"[DEBUG] Found wise guide! Area: {guide_data[0]}, Name: {guide_data[1]}")
                    break
            
            if guide_data:
                guide_area, guide_name = guide_data
                print(f"[DEBUG] Wise guide '{guide_name}' found in '{guide_area}'. Starting conversation.")
                self.session_state['current_area'] = guide_area
                
                npc_data, session = session_utils.start_conversation_with_specific_npc(
                    self.db, self.session_state['player_id'], guide_area, guide_name, 
                    self.session_state['model_name'], self.story, ChatSession, TerminalFormatter, 
                    self.session_state, llm_wrapper_for_profile_distillation=llm_wrapper)
                
                if npc_data and session:
                    self.session_state['current_npc'] = npc_data
                    self.session_state['chat_session'] = session
                    print(f"[DEBUG] Successfully started conversation with '{guide_name}'.")
                else:
                    print(f"[DEBUG] Failed to start conversation with '{guide_name}'. NPC data: {npc_data is not None}, Session: {session is not None}")
            else:
                print(f"[DEBUG] Wise guide '{self.wise_guide_npc_name}' not found in available NPCs!")
                print(f"[DEBUG] Available NPC names: {[npc.get('name', 'UNNAMED') for npc in all_npcs]}")
            
            if devnull:
                sys.stdout.close()
                sys.stdout = original_stdout
        except Exception as e:
            print(f"[DEBUG] Error in _auto_start_with_wise_guide: {e}")
            traceback.print_exc()
            if devnull:
                sys.stdout.close()
                sys.stdout = original_stdout


game = GameState()


def get_npc_avatar(npc_name):
    """Get appropriate avatar for each NPC"""
    npc_avatars = {
        'lyra': '🔮',
        'theron': '⚖️', 
        'alto giudice theron': '⚖️',
        'cassian': '🏛️',
        'irenna': '🎭',
        'elira': '🌿',
        'erasmus': '🌫️',
        'boros': '🏔️',
        'meridia': '✨',
        'jorin': '🍺',
        'garin': '🔨',
        'mara': '🌿',
        'syra': '🏛️'
    }
    
    if not npc_name:
        return '🎭'
    
    name_lower = npc_name.lower()
    if name_lower in npc_avatars:
        return npc_avatars[name_lower]
    
    # Try partial matches
    for npc_key, avatar in npc_avatars.items():
        if npc_key in name_lower:
            return avatar
    
    return '🎭'


def get_profile_summary(): 
    """Enhanced profile summary with FULL LLM analysis (no truncation)"""
    if not game.initialized:
        return "🧙 **Profile:** Not loaded"
    
    profile = game.session_state.get('player_profile_cache', {})
    traits = profile.get('core_traits', {})
    
    if not traits:
        return "🧙 **Profile:** New adventurer"
    
    # Show top 2 traits numerically
    sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)[:2] 
    trait_desc = ", ".join([f"{t.capitalize()}: {v}/10" for t, v in sorted_traits])
    player_summary = f"🧙 **Traits:** {trait_desc}"
    
    # Add COMPLETE LLM analysis (no truncation for rich psychological insight)
    llm_analysis_preview = game.latest_llm_profile_analysis_text
    llm_preview_text = ""
    
    if llm_analysis_preview and "not yet recorded" not in llm_analysis_preview:
        # Show the FULL LLM analysis - no truncation for complete psychological insight
        preview_candidate = llm_analysis_preview.strip()
        
        # Only clean up obvious repetitions or very long texts (800+ chars)
        if len(preview_candidate) > 800:
            # Find a natural break point after 600 characters for extremely long analyses
            break_points = ['. ', '! ', '? ']
            best_break = 600
            
            for bp in break_points:
                idx = preview_candidate.find(bp, 500)  # Look for break after 500 chars
                if idx != -1 and idx < 750:  # But before 750 chars
                    best_break = idx + len(bp)
                    break
            
            preview_candidate = preview_candidate[:best_break].strip()
            if len(preview_candidate) < len(llm_analysis_preview):
                preview_candidate += "..."
        
        # Format for display with full psychological detail
        llm_preview_text = f"\n📜 *LLM Psychology: {preview_candidate}*"
    
    return player_summary + llm_preview_text


def clean_ansi_codes(text: str) -> str:
    """Remove all ANSI escape codes"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', text)
    cleaned = re.sub(r'\033\[[0-9;]*m', '', cleaned)
    return cleaned


def format_help_for_web():
    """Create a web-friendly version of the help text"""
    guide_name = game.session_state.get('wise_guide_npc_name', "the Wise Guide") if game.initialized else "the Wise Guide"
    raw_help = get_help_text(game.session_state if game.initialized else None)
    cleaned = clean_ansi_codes(raw_help)
    
    # Convert to markdown
    md_help = cleaned.replace("Available Commands:", "## 📜 Available Commands")
    
    # Add emoji headers
    for title in ["Navigation & Interaction", "Guidance & Information", "Player Profile & Debug", "Session Management & Stats", "Natural Language Commands"]:
        emoji_map = {'N':'🗺️ N','G':'🔮 G','Pl':'🧙 Pl','S':'📊 S','Na':'💡 Na'}
        md_help = re.sub(rf"{title}:", f"\n**{emoji_map[title[:2]]} {title}:**", md_help)
    
    # Format commands
    md_help = re.sub(r"^\s*(/[a-zA-Z_]+.*?)\s*-\s*(.*)", r"• `\1` - \2", md_help, flags=re.MULTILINE) 
    
    return md_help


def get_trait_qualitative_level(value: int) -> str:
    """Get qualitative description of trait level"""
    if value <= 2: return "Very Low"
    elif value <= 3: return "Low"
    elif value <= 4: return "Mod. Low" 
    elif value <= 6: return "Moderate"
    elif value <= 7: return "Mod. High"
    elif value <= 8: return "High"
    return "Very High"


def get_detailed_info(info_type: str):
    """Get detailed information for the info panel"""
    print(f"[DEBUG] get_detailed_info: {info_type}")
    if not game.initialized:
        return "Game not initialized."
    
    if info_type == "profile":
        profile = game.session_state.get('player_profile_cache', {})
        traits = profile.get('core_traits', {})
        patterns = profile.get('decision_patterns', [])
        experiences = profile.get('key_experiences_tags', [])
        motivations = profile.get('inferred_motivations', [])
        
        result = "### 🧙 Detailed Character Profile\n\n"
        
        # LLM Analysis at the top
        result += f"**📜 LLM's Perspective on the Seeker:**\n\n_{game.latest_llm_profile_analysis_text}_\n\n---\n\n"
        
        if traits:
            result += "**🎭 Core Traits (Numeric Values):**\n\n"
            sorted_trait_items = sorted(traits.items())
            
            # Create a proper table with better alignment
            result += "| Trait | Value | Level | Visual | Trait | Value | Level | Visual |\n"
            result += "|-------|-------|-------|--------|-------|-------|-------|--------|\n"
            
            half_len = (len(sorted_trait_items) + 1) // 2
            col1_traits = sorted_trait_items[:half_len]
            col2_traits = sorted_trait_items[half_len:]
            
            max_rows = max(len(col1_traits), len(col2_traits))
            
            for i in range(max_rows):
                row_parts = []
                
                # Left column
                if i < len(col1_traits):
                    trait, value = col1_traits[i]
                    bar = "█" * min(int(value), 10) + "░" * max(0, 10 - int(value))
                    level = get_trait_qualitative_level(value)
                    row_parts.extend([
                        f"**{trait.capitalize()}**", 
                        f"{value}/10", 
                        level, 
                        f"`{bar}`"
                    ])
                else:
                    row_parts.extend(["", "", "", ""])
                
                # Right column  
                if i < len(col2_traits):
                    trait, value = col2_traits[i]
                    bar = "█" * min(int(value), 10) + "░" * max(0, 10 - int(value))
                    level = get_trait_qualitative_level(value)
                    row_parts.extend([
                        f"**{trait.capitalize()}**", 
                        f"{value}/10", 
                        level, 
                        f"`{bar}`"
                    ])
                else:
                    row_parts.extend(["", "", "", ""])
                
                result += "| " + " | ".join(row_parts) + " |\n"
            
            result += "\n"
        
        if patterns:
            result += "**🎯 Decision Patterns (Recent):**\n" + "\n".join([f"• _{p}_" for p in patterns[-3:]]) + "\n\n"
        
        if experiences:
            result += "**⭐ Key Experiences (Recent):**\n" + "\n".join([f"• _{e}_" for e in experiences[-5:]]) + "\n\n"
        
        if motivations:
            result += "**💡 Inferred Motivations:**\n" + "\n".join([f"• **{m.replace('_', ' ').capitalize()}**" for m in motivations]) + "\n"
        
        return result
        
    elif info_type == "npcs":
        all_npcs_raw = session_utils.refresh_known_npcs_list(game.db, TerminalFormatter)
        web_formatted_list = "### 👥 Known Characters\n\n"
        current_area_web = None
        
        for npc_info in sorted(all_npcs_raw, key=lambda x: (x.get('area', '').lower(), x.get('name', '').lower())):
            area, name, role = npc_info.get('area','N/A'), npc_info.get('name','N/A'), npc_info.get('role','N/A')
            if area != current_area_web:
                if current_area_web:
                    web_formatted_list += "\n"
                current_area_web = area
                web_formatted_list += f"**📍 {area}**\n"
            web_formatted_list += f"  • {name} (*{role}*)\n"
        
        return web_formatted_list
        
    elif info_type == "areas":
        all_npcs_raw = session_utils.refresh_known_npcs_list(game.db, TerminalFormatter)
        areas = session_utils.get_known_areas_from_list(all_npcs_raw)
        result = "### 🗺️ Known Realms\n\n"
        
        for area in areas:
            area_npcs = [npc.get('name') for npc in all_npcs_raw if npc.get('area') == area and npc.get('name')]
            result += f"**📍 {area}**\n  Known characters: {', '.join(area_npcs) if area_npcs else 'None discovered'}\n\n"
        
        return result
        
    elif info_type == "inventory":
        inventory = game.session_state.get('player_inventory', [])
        credits = game.session_state.get('player_credits_cache', 0)
        result = f"### 🎒 Your Possessions\n\n💰 **Mystical Credits:** {credits}\n\n"
        result += "**🏺 Items:**\n" + ("\n".join([f"• {item.capitalize()}" for item in inventory]) if inventory else "Your pouch is remarkably light.")
        return result
        
    elif info_type == "help":
        return format_help_for_web()
    
    return "Info not available."


def format_chat_for_clipboard(chat_history): 
    """Format chat history for clipboard copying"""
    if not chat_history:
        return "No conversation."
    
    formatted_lines = ["=== ELDORIA: CHAT LOG ==="]
    area, npc_name_chatting_with = "Unknown", "N/A"
    
    if game.initialized:
        area = game.session_state.get('current_area', 'The Void')
        if game.session_state.get('in_hint_mode'):
            npc_name_chatting_with = f"Guide: {game.session_state.get('wise_guide_npc_name', 'Lyra')}"
        elif game.session_state.get('current_npc'):
            npc_name_chatting_with = game.session_state.get('current_npc').get('name', 'Figure')
    
    formatted_lines.extend([
        f"Area: {area}",
        f"With: {npc_name_chatting_with}",
        f"Player: {game.session_state.get('player_id', 'Seeker')}",
        "-"*20
    ])
    
    for msg_obj in chat_history:
        role, content = msg_obj.get('role', ''), msg_obj.get('content', '')
        # Clean up formatting
        plain_content = re.sub(r'\*\*|(\*(?!\s))|(\:(?=\s))', '', content)
        plain_content = plain_content.replace('🎁 Received:', 'Received:').replace('📍 ', '').replace('💬 ', '').replace('🧙 ', '').replace('🎭 ', '').replace('🔮 ','')
        
        if role == 'user':
            formatted_lines.append(f"Player: {plain_content}")
        elif role == 'assistant':
            # Try to extract NPC name from formatted message
            match = re.match(r"^(.*?):(.*)", plain_content, re.DOTALL) 
            if match and match.group(1).strip() != npc_name_chatting_with and len(match.group(1)) < 30:
                formatted_lines.append(f"{match.group(1).strip()}: {match.group(2).strip()}")
            else:
                formatted_lines.append(f"NPC: {plain_content}")
        
        formatted_lines.append("")
    
    formatted_lines.append("=== END ===")
    return "\n".join(formatted_lines)


def copy_chat_to_clipboard(chat_history):
    """Prepare chat for clipboard"""
    return gr.update(value=format_chat_for_clipboard(chat_history), visible=True)


def update_info_panel(info_type: str):
    """Update the information panel with detailed info"""
    game.current_info_display = get_detailed_info(info_type)
    return game.current_info_display


def get_main_status_displays(): 
    """Get main status displays for the right panel"""
    print("[DEBUG] get_main_status_displays called")
    if not game.initialized:
        return "🎒 Empty", "💰 0", "### 📍 Unknown", "🧙 N/A"
    
    # Inventory
    inv_text = f"🎒 **{len(game.session_state.get('player_inventory', []))} items**" if game.session_state.get('player_inventory') else "🎒 **Empty pouch**"
    
    # Credits
    cred_text = f"💰 **{game.session_state.get('player_credits_cache', 0)} Credits**"
    
    # Location with enhanced NPC display
    area = game.session_state.get('current_area', 'The Void')
    current_npc = game.session_state.get('current_npc')
    location_header = f"### 📍 In: {area}"
    
    interaction_status = ""
    if game.session_state.get('in_hint_mode'):
        guide_name = game.session_state.get('wise_guide_npc_name', 'Guide')
        interaction_status = f"🔮 **Consulting:** _{guide_name}_"
    elif current_npc:
        npc_name = current_npc.get('name', 'Mysterious Figure')
        npc_avatar = get_npc_avatar(npc_name)
        interaction_status = f"{npc_avatar} **Speaking with:** **{npc_name}**" 
    else:
        interaction_status = "⏳ *Exploring...*"
    
    return inv_text, cred_text, f"{location_header}\n{interaction_status}", get_profile_summary()


def send_message(message: str, chat_history: List[Dict[str, str]]):
    """Send a message and update all displays with enhanced LLM profiling"""
    print(f"[DEBUG] send_message: '{message}'")
    if not game.initialized:
        return chat_history, "", *get_main_status_displays(), "Game not initialized."
    
    if not message.strip():
        return chat_history, "", *get_main_status_displays(), ""
    
    chat_history.append({"role": "user", "content": message})
    status_text_for_ui = ""
    
    try:
        # Store previous profile for comparison
        prev_prof_comp = copy.deepcopy(game.session_state.get('player_profile_cache', get_default_player_profile()))
        
        # Process the input
        game.session_state = command_processor.process_input_revised(message, game.session_state)
        
        chat_s = game.session_state.get('chat_session')
        current_npc_prefix = game.session_state.get('current_npc')

        # Handle NPC responses
        if chat_s and chat_s.messages and game.session_state.get('npc_made_new_response_this_turn'):
            last_msg_s = chat_s.messages[-1]
            if last_msg_s.get('role') == 'assistant':
                npc_resp_cont = last_msg_s.get('content','').replace('[GIVEN_ITEMS:','\n🎁 **Received:**').replace(']','')
                
                # Add NPC avatar and name
                if current_npc_prefix:
                    npc_name = current_npc_prefix.get('name', 'NPC')
                    npc_avatar = get_npc_avatar(npc_name)
                    
                    # Special formatting for hint mode
                    is_guide = game.session_state.get('in_hint_mode') and \
                              npc_name.lower() == game.session_state.get('wise_guide_npc_name','').lower()
                    
                    if is_guide:
                        formatted_response = f"🌟 **{game.session_state.get('wise_guide_npc_name','Guide')} (Guidance):** {npc_resp_cont}"
                    else:
                        formatted_response = f"{npc_avatar} **{npc_name}:** {npc_resp_cont}"
                    
                    chat_history.append({"role":"assistant","content":formatted_response})
                else:
                    chat_history.append({"role": "assistant", "content": npc_resp_cont})
        
        # Handle system messages
        elif not game.session_state.get('npc_made_new_response_this_turn'): 
            sys_msg_ui = game.session_state.pop('system_message_for_ui', None)
            if sys_msg_ui:
                chat_history.append({"role":"assistant","content":f"*{sys_msg_ui}*"})
                status_text_for_ui = sys_msg_ui
                print(f"[DEBUG] Command UI: {sys_msg_ui}")

        # LLM Profile Update (Enhanced from v9)
        if (game.session_state.get('npc_made_new_response_this_turn', False) and 
            not game.session_state.get('in_hint_mode', False) and 
            game.session_state.get('actions_this_turn_for_profile')):
            
            curr_prof_cache = game.session_state.get('player_profile_cache', get_default_player_profile())
            inter_log = chat_s.messages[-6:] if chat_s and chat_s.messages else []
            npc_name_prof = game.session_state.get('current_npc', {}).get('name')
            
            print(f"[DEBUG] LLM profile update for {game.session_state['player_id']} with NPC {npc_name_prof or 'General'}")
            
            # Call the existing LLM profile analysis system
            upd_prof, prof_chgs = update_player_profile(
                curr_prof_cache, inter_log, game.session_state['actions_this_turn_for_profile'],
                game.session_state['llm_wrapper_func'], game.session_state['profile_analysis_model_name'], 
                npc_name_prof, TerminalFormatter)
            
            # Extract LLM analysis text
            llm_notes = next((s.replace("LLM Analysis:","").strip() for s in prof_chgs if "LLM Analysis:" in s), "LLM analysis completed.")
            if not llm_notes or "LLM analysis completed" in llm_notes:
                llm_notes = next((s for s in prof_chgs if "Interaction style" in s), llm_notes)
            
            game.latest_llm_profile_analysis_text = llm_notes if llm_notes.strip() else "LLM provided contextual feedback."
            upd_prof['last_llm_analysis_notes'] = game.latest_llm_profile_analysis_text

            if upd_prof != prev_prof_comp:
                game.session_state['player_profile_cache'] = upd_prof 
                game.db.save_player_profile(game.session_state['player_id'], upd_prof) 
                status_text_for_ui += " (Profile Updated)"
                print(f"[DEBUG] Profile saved. LLM: '{game.latest_llm_profile_analysis_text}'. Changes: {prof_chgs}")
            elif prof_chgs:
                print(f"[DEBUG] LLM ran, no DB update. Reported: {prof_chgs}")
            else:
                print(f"[DEBUG] Profile analyzed, no LLM changes.")
            
            game.session_state['actions_this_turn_for_profile'] = [] 
        
        if not status_text_for_ui:
            status_text_for_ui = "Echoes..." if not game.session_state.get('npc_made_new_response_this_turn') else f"With {game.session_state.get('current_npc',{}).get('name','NPC')}..."
    
    except Exception as e:
        print(f"[DEBUG] Error send_message (Gradio): {e}")
        traceback.print_exc()
        chat_history.append({"role":"assistant","content":f"❌ Error: {type(e).__name__}."})
        status_text_for_ui = f"Error: {type(e).__name__}"
    
    # Limit chat history size
    MAX_CHAT_UI = 30
    chat_history = chat_history[-MAX_CHAT_UI:] if len(chat_history) > MAX_CHAT_UI else chat_history
    
    return chat_history, "", *get_main_status_displays(), status_text_for_ui.strip()


def auto_initialize():
    """Auto-initialize the game when interface loads"""
    print("[DEBUG] auto_initialize called")
    success, message = game.initialize()
    chat_history = []
    
    if success:
        if game.session_state.get('chat_session') and game.session_state['chat_session'].messages:
            last_msg = game.session_state['chat_session'].messages[-1]
            if last_msg.get('role') == 'assistant':
                welcome_msg_content = last_msg.get('content', '')
                
                # Add wise guide formatting for welcome message
                if (game.session_state.get('current_npc',{}).get('name','').lower() == 
                    game.session_state.get('wise_guide_npc_name','').lower()):
                    guide_avatar = get_npc_avatar(game.session_state.get('wise_guide_npc_name','Lyra'))
                    welcome_msg_content = f"{guide_avatar} **{game.session_state.get('wise_guide_npc_name','Guide')}:** {welcome_msg_content}"
                
                chat_history.append({"role":"assistant","content":welcome_msg_content})
            else:
                chat_history.append({"role":"assistant","content":"The realm awaits..."})
        else:
            chat_history.append({"role":"assistant","content":"Welcome, Seeker. Guide: /help."})
        
        game.current_info_display = get_detailed_info("profile") 
        return chat_history, *get_main_status_displays(), game.current_info_display, message
    else:
        return [], "Error", "Error", "Error", "Error", f"Init Fail: {message}", message


def use_hint():
    """Use the hint system"""
    print("[DEBUG] use_hint (Gradio)")
    status_txt = ""
    chat_hist_ui = []
    
    if not game.initialized:
        return [], *get_main_status_displays(), "Game not ready."
    
    try:
        game.session_state = command_processor.process_input_revised("/hint", game.session_state)
        chat_s_guide = game.session_state.get('chat_session') 
        
        if chat_s_guide and chat_s_guide.messages:
            last_guide_msg = chat_s_guide.messages[-1]
            if last_guide_msg.get('role') == 'assistant':
                guide_resp = last_guide_msg.get('content','')
                guide_name = game.session_state.get('wise_guide_npc_name','Guide')
                guide_avatar = get_npc_avatar(guide_name)
                
                chat_hist_ui.append({"role":"assistant","content":f"🌟 **{guide_name} (Guidance):** {guide_resp}"})
                status_txt = f"Consulting {guide_name}. '/endhint' to return."
            else:
                chat_hist_ui.append({"role":"assistant","content":"*Guide ponders...*"})
                status_txt = "Awaiting wisdom."
        else:
            chat_hist_ui.append({"role":"assistant","content":"*Connection unclear...*"})
            status_txt = "Could not contact."
    
    except Exception as e:
        print(f"[DEBUG] Error use_hint: {e}")
        traceback.print_exc()
        chat_hist_ui.append({"role":"assistant","content":f"❌ Error: {e}"})
        status_txt = f"Error: {e}"
    
    return chat_hist_ui, *get_main_status_displays(), status_txt


# Enhanced Fantasy CSS
fantasy_css = """
body { font-family: 'Merriweather', serif; }
.gradio-container { 
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); 
    color: #e6e6fa; 
}
.gr-button { 
    background: linear-gradient(45deg, #4a148c, #6a1b9a) !important; 
    border: 1px solid #7b1fa2 !important; 
    color: #e1bee7 !important; 
    border-radius: 8px !important; 
    font-weight: bold !important; 
    transition: all 0.3s ease !important; 
}
.gr-button:hover { 
    background: linear-gradient(45deg, #6a1b9a, #8e24aa) !important; 
    transform: translateY(-2px) !important; 
    box-shadow: 0 4px 12px rgba(106, 27, 154, 0.5) !important; 
}
.gr-input input, .gr-textbox textarea { 
    background: rgba(30, 30, 60, 0.8) !important; 
    border: 1px solid #7b1fa2 !important; 
    color: #e6e6fa !important; 
    border-radius: 6px !important; 
}
.gr-chatbot { 
    background: rgba(20, 20, 40, 0.9) !important; 
    border: 1px solid #4a148c !important; 
    border-radius: 12px !important; 
}
.gr-panel { 
    background: rgba(25, 25, 50, 0.7) !important; 
    border: 1px solid #4a148c !important; 
    border-radius: 8px !important; 
    padding: 15px !important; 
}
.gr-markdown { color: #e6e6fa !important; } 
.gr-markdown h1, .gr-markdown h2, .gr-markdown h3 { 
    color: #bb86fc !important; 
    text-shadow: 1px 1px 3px #301934; 
}
.gr-markdown strong { color: #cf9fff !important; } 
.gr-markdown code { 
    background-color: rgba(74, 20, 140, 0.5); 
    color: #f3e5f5; 
    padding: 2px 5px; 
    border-radius: 4px;
}
.gr-label > .label-text { color: #ce93d8 !important; font-weight: bold; } 
.message-wrap .message.user { 
    background: #301934 !important; 
    color: #f3e5f5 !important; 
    border-radius: 10px 10px 0 10px !important; 
    margin-left: auto !important; 
}
.message-wrap .message.bot { 
    background: #4a0072 !important; 
    color: #e1bee7 !important; 
    border-radius: 10px 10px 10px 0 !important; 
    margin-right: auto !important; 
}
.message-wrap .avatar-container img { 
    border-radius: 50% !important; 
    border: 2px solid #7b1fa2 !important; 
}
#status_message_display_id .gr-markdown { 
    font-style: italic; 
    color: #b39ddb !important; 
    text-align: center; 
    padding: 5px; 
    background-color: rgba(0,0,0,0.1); 
    border-radius: 5px; 
}
"""


def create_interface():
    """Create the enhanced fantasy-themed Gradio interface"""
    print("[DEBUG] create_interface called")
    
    # Auto-initialize
    (initial_chat_history, initial_inv_text, initial_cred_text, initial_loc_text, 
     initial_prof_sum, initial_info_panel_content, initial_status_message) = auto_initialize()
    
    with gr.Blocks(
        title="Eldoria", 
        theme=gr.themes.Base(font=[gr.themes.GoogleFont("Merriweather"), "serif"]), 
        css=fantasy_css
    ) as interface:
        
        gr.Markdown("# ✨ Eldoria: Realm of Mystical Dialogues ✨\n*Where ancient wisdom meets modern magic...*")
        
        status_message_display = gr.Markdown(
            initial_status_message, 
            label="✨ System Messages", 
            elem_id="status_message_display_id"
        )
        
        with gr.Row():
            with gr.Column(scale=2): 
                chatbot = gr.Chatbot(
                    value=initial_chat_history, 
                    label="🗣️ Mystical Conversations", 
                    height=500, 
                    show_label=True, 
                    type="messages", 
                    avatar_images=("🧙‍♂️", "🎭")
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Speak your thoughts into the mystical realm...", 
                        label="✨ Your Words", 
                        scale=4, 
                        container=False 
                    )
                    send_btn = gr.Button("🌟 Send", variant="primary", scale=1)
                
                with gr.Accordion("Quick Actions & Info", open=False): 
                    with gr.Row():
                        hint_btn = gr.Button("🔮 Seek Wisdom", variant="secondary", size="sm")
                        inventory_info_btn = gr.Button("🎒 Possessions", variant="secondary", size="sm") 
                        guide_info_btn = gr.Button("📜 Guide", variant="secondary", size="sm") 
                        copy_btn = gr.Button("📋 Copy Chat", variant="secondary", size="sm")
                    
                    copy_output_textbox = gr.Textbox(
                        label="📋 Chat Export", 
                        placeholder="Chat export will appear here...",
                        lines=5, 
                        max_lines=10, 
                        visible=False, 
                        interactive=False
                    )
            
            with gr.Column(scale=1): 
                gr.Markdown("## 🌟 Realm Status")
                
                inventory_display = gr.Markdown(initial_inv_text)
                credits_display = gr.Markdown(initial_cred_text)
                location_display = gr.Markdown(initial_loc_text) 
                profile_summary_display = gr.Markdown(initial_prof_sum) 
                
                gr.Markdown("---")
                gr.Markdown("### 🔍 Detailed Views")
                
                with gr.Row():
                    profile_detail_btn = gr.Button("🧙 Profile", size="sm")
                    npcs_btn = gr.Button("👥 Characters", size="sm")
                    areas_btn = gr.Button("🗺️ Realms", size="sm")
                
                info_panel = gr.Markdown(
                    value=initial_info_panel_content, 
                    label="📋 Detailed Information"
                ) 

        # Event handlers
        send_btn.click(
            fn=send_message, 
            inputs=[msg_input, chatbot], 
            outputs=[chatbot, msg_input, inventory_display, credits_display, location_display, profile_summary_display, status_message_display]
        )
        
        msg_input.submit(
            fn=send_message, 
            inputs=[msg_input, chatbot], 
            outputs=[chatbot, msg_input, inventory_display, credits_display, location_display, profile_summary_display, status_message_display]
        )
        
        hint_btn.click(
            fn=use_hint, 
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_summary_display, status_message_display]
        )
        
        inventory_info_btn.click(
            fn=lambda: update_info_panel("inventory"), 
            outputs=[info_panel]
        )
        
        guide_info_btn.click(
            fn=lambda: update_info_panel("help"), 
            outputs=[info_panel]
        )
        
        copy_btn.click(
            fn=copy_chat_to_clipboard, 
            inputs=[chatbot], 
            outputs=[copy_output_textbox]
        )
        
        profile_detail_btn.click(
            fn=lambda: update_info_panel("profile"), 
            outputs=[info_panel]
        )
        
        npcs_btn.click(
            fn=lambda: update_info_panel("npcs"), 
            outputs=[info_panel]
        )
        
        areas_btn.click(
            fn=lambda: update_info_panel("areas"), 
            outputs=[info_panel]
        )
    
    return interface


if __name__ == "__main__":
    # Suppress warnings unless in debug mode
    if not os.environ.get('GRADIO_DEBUG'):
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="gradio")
        warnings.filterwarnings("ignore", category=UserWarning, module="gradio_client")
    
    interface = create_interface()
    print("🚀 Starting Eldoria: Realm of Mystical Dialogues...")
    print("🌟 The realm awaits at: http://localhost:7860")
    
    interface.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        share=os.environ.get('GRADIO_SHARE', 'True').lower() == 'true', 
        debug=bool(os.environ.get('GRADIO_DEBUG')), 
        show_error=bool(os.environ.get('GRADIO_DEBUG')), 
        quiet=not bool(os.environ.get('GRADIO_DEBUG'))
    )