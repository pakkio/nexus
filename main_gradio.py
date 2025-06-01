#!/usr/bin/env python3
"""
Eldoria Dialogue System - Gradio Web Interface
A beautiful web UI for the Eldoria text-based RPG
"""

import gradio as gr
import os
import sys
import json
import traceback
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import game modules
try:
    from terminal_formatter import TerminalFormatter
    from db_manager import DbManager
    from main_core import run_interaction_loop
    from main_utils import get_help_text, format_npcs_list
    from wise_guide_selector import get_wise_guide_npc_name
    from chat_manager import ChatSession, format_stats
    from llm_wrapper import llm_wrapper
    import session_utils
    import command_processor
    from player_profile_manager import get_default_player_profile
except ImportError as e:
    print(f"❌ Fatal Error: Could not import required modules: {e}")
    sys.exit(1)

# Global game state
class GameState:
    def __init__(self):
        self.db = None
        self.story = ""
        self.session_state = {}
        self.wise_guide_npc_name = None
        self.initialized = False

    def initialize(self, use_mockup=True, mockup_dir="database",
                   model_name="openai/gpt-4o-mini", player_id="WebPlayer"):
        """Initialize the game state"""
        try:
            # Initialize DB Manager
            self.db = DbManager(use_mockup=use_mockup, mockup_dir=mockup_dir)
            self.db.ensure_db_schema()

            # Load storyboard
            story_data = self.db.get_storyboard()
            self.story = story_data.get("description", "[Storyboard missing]")

            # Determine wise guide
            self.wise_guide_npc_name = get_wise_guide_npc_name(
                self.story, self.db, model_name
            )

            # Initialize session state
            initial_player_credits = self.db.get_player_credits(player_id)
            player_profile_data = self.db.load_player_profile(player_id)

            self.session_state = {
                'db': self.db,
                'story': self.story,
                'current_area': None,
                'current_npc': None,
                'chat_session': None,
                'model_name': model_name,
                'profile_analysis_model_name': model_name,
                'use_stream': False,  # Disable streaming for web UI
                'auto_show_stats': False,
                'debug_mode': False,
                'player_id': player_id,
                'player_inventory': self.db.load_inventory(player_id),
                'player_credits_cache': initial_player_credits,
                'player_profile_cache': player_profile_data,
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
                'wise_guide_npc_name': self.wise_guide_npc_name,
                'nlp_command_interpretation_enabled': True,
                'nlp_command_confidence_threshold': 0.7,
                'nlp_command_debug': False,
            }

            self.initialized = True
            return True, "Game initialized successfully!"

        except Exception as e:
            return False, f"Error initializing game: {e}"

# Global game instance
game = GameState()

def initialize_game():
    """Initialize the game and return status"""
    success, message = game.initialize()
    if success:
        areas = get_available_areas()
        npcs = get_available_npcs()
        status = get_game_status()
        return (
            f"🎮 **{message}**\n\n"
            f"**Story**: {game.story[:200]}...\n\n"
            f"**Wise Guide**: {game.wise_guide_npc_name or 'None'}\n\n"
            f"Welcome to Eldoria! Use the buttons below to explore.",
            gr.update(choices=areas, value=""),
            gr.update(choices=npcs, value=""),
            status["inventory"],
            status["credits"],
            status["location"],
            status["profile"]
        )
    else:
        return message, gr.update(), gr.update(), "", "", "", ""

def get_available_areas():
    """Get list of available areas"""
    if not game.initialized:
        return []
    try:
        all_npcs = session_utils.refresh_known_npcs_list(game.db, TerminalFormatter)
        areas = session_utils.get_known_areas_from_list(all_npcs)
        return areas
    except:
        return []

def get_available_npcs():
    """Get list of available NPCs"""
    if not game.initialized:
        return []
    try:
        all_npcs = session_utils.refresh_known_npcs_list(game.db, TerminalFormatter)
        return [npc.get('name', 'Unknown') for npc in all_npcs if npc.get('name')]
    except:
        return []

def get_game_status():
    """Get current game status"""
    if not game.initialized:
        return {
            "inventory": "Game not initialized",
            "credits": "N/A",
            "location": "Unknown",
            "profile": "No profile data"
        }

    # Inventory
    inventory = game.session_state.get('player_inventory', [])
    inventory_text = "**Inventory:**\n" + "\n".join([f"• {item}" for item in inventory]) if inventory else "**Inventory:** Empty"

    # Credits
    credits = game.session_state.get('player_credits_cache', 0)
    credits_text = f"**Credits:** {credits}"

    # Current location
    current_area = game.session_state.get('current_area', 'Nowhere')
    current_npc = game.session_state.get('current_npc')
    npc_name = current_npc.get('name', 'None') if current_npc else 'None'
    location_text = f"**Location:** {current_area}\n**Talking to:** {npc_name}"

    # Profile summary
    profile = game.session_state.get('player_profile_cache', {})
    traits = profile.get('core_traits', {})
    style = profile.get('interaction_style_summary', 'Unknown')

    profile_text = "**Profile:**\n"
    if traits:
        profile_text += "**Traits:**\n"
        for trait, value in traits.items():
            profile_text += f"• {trait.capitalize()}: {value}/10\n"
    profile_text += f"**Style:** {style}"

    return {
        "inventory": inventory_text,
        "credits": credits_text,
        "location": location_text,
        "profile": profile_text
    }

def send_message(message, chat_history):
    """Send a message to the current NPC"""
    if not game.initialized:
        status = get_game_status()
        return chat_history, "", status["inventory"], status["credits"], status["location"], status["profile"]

    if not message.strip():
        status = get_game_status()
        return chat_history, "", status["inventory"], status["credits"], status["location"], status["profile"]

    # Add user message to chat
    chat_history.append({"role": "user", "content": message})

    try:
        # Process the input through the game system
        game.session_state = command_processor.process_input_revised(message, game.session_state)

        # Get the NPC response if there was one
        current_npc = game.session_state.get('current_npc')
        chat_session = game.session_state.get('chat_session')

        if chat_session and chat_session.messages:
            last_message = chat_session.messages[-1]
            if last_message.get('role') == 'assistant':
                npc_response = last_message.get('content', '')
                # Clean up system tags
                npc_response = npc_response.replace('[GIVEN_ITEMS:', '\n🎁 **Given items:**').replace(']', '')
                chat_history.append({"role": "assistant", "content": npc_response})
            else:
                chat_history.append({"role": "assistant", "content": "*No response*"})
        else:
            chat_history.append({"role": "assistant", "content": "*Use the area/NPC selectors to start a conversation*"})

    except Exception as e:
        chat_history.append({"role": "assistant", "content": f"❌ Error: {e}"})

    status = get_game_status()
    return chat_history, "", status["inventory"], status["credits"], status["location"], status["profile"]

def go_to_area(area_name):
    """Go to a specific area"""
    if not game.initialized or not area_name:
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], gr.update(), ""

    try:
        # Use the /go command
        game.session_state = command_processor.process_input_revised(f"/go {area_name}", game.session_state)

        status = get_game_status()

        # Get NPCs in current area for dropdown update
        current_area = game.session_state.get('current_area')
        if current_area:
            all_npcs = session_utils.refresh_known_npcs_list(game.db, TerminalFormatter)
            area_npcs = [npc.get('name', '') for npc in all_npcs
                         if npc.get('area', '') == current_area and npc.get('name')]

            return [], status["inventory"], status["credits"], status["location"], status["profile"], gr.update(choices=area_npcs, value=""), f"📍 Moved to **{current_area}**"
        else:
            return [], status["inventory"], status["credits"], status["location"], status["profile"], gr.update(), f"❌ Could not move to {area_name}"

    except Exception as e:
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], gr.update(), f"❌ Error: {e}"

def talk_to_npc(npc_name):
    """Start talking to an NPC"""
    if not game.initialized or not npc_name:
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], ""

    try:
        # Use the /talk command
        game.session_state = command_processor.process_input_revised(f"/talk {npc_name}", game.session_state)

        # Get the opening message if any
        chat_history = []
        current_npc = game.session_state.get('current_npc')
        chat_session = game.session_state.get('chat_session')

        if current_npc and chat_session and chat_session.messages:
            last_message = chat_session.messages[-1]
            if last_message.get('role') == 'assistant':
                npc_response = last_message.get('content', '')
                npc_response = npc_response.replace('[GIVEN_ITEMS:', '\n🎁 **Given items:**').replace(']', '')
                chat_history.append({"role": "assistant", "content": npc_response})

        status = get_game_status()
        return chat_history, status["inventory"], status["credits"], status["location"], status["profile"], f"💬 Now talking to **{npc_name}**"

    except Exception as e:
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], f"❌ Error: {e}"

def use_hint():
    """Use the hint system"""
    if not game.initialized:
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], ""

    try:
        # Use the /hint command
        game.session_state = command_processor.process_input_revised("/hint", game.session_state)

        # Get Lyra's response
        chat_history = []
        chat_session = game.session_state.get('chat_session')

        if chat_session and chat_session.messages:
            last_message = chat_session.messages[-1]
            if last_message.get('role') == 'assistant':
                lyra_response = last_message.get('content', '')
                chat_history.append({"role": "assistant", "content": f"🔮 **{game.wise_guide_npc_name or 'Guide'}:** {lyra_response}"})

        status = get_game_status()
        return chat_history, status["inventory"], status["credits"], status["location"], status["profile"], f"🔮 Consulting with **{game.wise_guide_npc_name or 'Guide'}**"

    except Exception as e:
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], f"❌ Error: {e}"

def quick_command(command):
    """Execute a quick command"""
    if not game.initialized:
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], ""

    try:
        game.session_state = command_processor.process_input_revised(command, game.session_state)
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], f"✅ Executed: {command}"
    except Exception as e:
        status = get_game_status()
        return [], status["inventory"], status["credits"], status["location"], status["profile"], f"❌ Error: {e}"

# Create the Gradio interface
def create_interface():
    """Create the main Gradio interface"""

    with gr.Blocks(title="Eldoria Dialogue System", theme=gr.themes.Soft()) as interface:
        gr.Markdown("""
        # 🏰 Eldoria Dialogue System
        **An AI-Assisted Text-Based RPG Adventure**
        
        Welcome to the mystical world of Eldoria, where the Veil between worlds grows thin...
        """)

        # Initialize button
        with gr.Row():
            init_btn = gr.Button("🎮 Initialize Game", variant="primary", size="lg")

        init_output = gr.Markdown("")

        # Main game interface
        with gr.Row():
            # Left column - Chat and controls
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=400,
                    show_label=True,
                    container=True,
                    type="messages"
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Type your message or use the buttons below...",
                        label="Your Message",
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary")

                status_message = gr.Markdown("", visible=True)

                # Navigation controls
                with gr.Row():
                    area_dropdown = gr.Dropdown(
                        choices=[],
                        label="🗺️ Go to Area",
                        scale=2
                    )
                    go_btn = gr.Button("Go", scale=1)

                with gr.Row():
                    npc_dropdown = gr.Dropdown(
                        choices=[],
                        label="👥 Talk to NPC",
                        scale=2
                    )
                    talk_btn = gr.Button("Talk", scale=1)

                # Quick action buttons
                with gr.Row():
                    hint_btn = gr.Button("🔮 Ask for Hint", variant="secondary")
                    inventory_btn = gr.Button("🎒 Check Inventory", variant="secondary")
                    areas_btn = gr.Button("🗺️ List Areas", variant="secondary")

            # Right column - Game status
            with gr.Column(scale=1):
                gr.Markdown("## 📊 Game Status")

                inventory_display = gr.Markdown("**Inventory:** Not loaded")
                credits_display = gr.Markdown("**Credits:** Not loaded")
                location_display = gr.Markdown("**Location:** Not loaded")
                profile_display = gr.Markdown("**Profile:** Not loaded")

                gr.Markdown("---")
                gr.Markdown("### 🎮 Quick Commands")
                with gr.Column():
                    profile_btn = gr.Button("📜 Show Profile", size="sm")
                    npcs_btn = gr.Button("👥 List NPCs", size="sm")
                    stats_btn = gr.Button("📊 Show Stats", size="sm")

        # Event handlers

        # Initialize game
        init_btn.click(
            fn=initialize_game,
            outputs=[
                init_output,
                area_dropdown,
                npc_dropdown,
                inventory_display,
                credits_display,
                location_display,
                profile_display
            ]
        )

        # Send message
        send_btn.click(
            fn=send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, inventory_display, credits_display, location_display, profile_display]
        )

        # Enter key for sending messages
        msg_input.submit(
            fn=send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, inventory_display, credits_display, location_display, profile_display]
        )

        # Go to area
        go_btn.click(
            fn=go_to_area,
            inputs=[area_dropdown],
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_display, npc_dropdown, status_message]
        )

        # Talk to NPC
        talk_btn.click(
            fn=talk_to_npc,
            inputs=[npc_dropdown],
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_display, status_message]
        )

        # Hint button
        hint_btn.click(
            fn=use_hint,
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_display, status_message]
        )

        # Quick command buttons
        inventory_btn.click(
            fn=lambda: quick_command("/inventory"),
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_display, status_message]
        )

        areas_btn.click(
            fn=lambda: quick_command("/areas"),
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_display, status_message]
        )

        # Sidebar quick command buttons
        profile_btn.click(
            fn=lambda: quick_command("/profile"),
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_display, status_message]
        )

        npcs_btn.click(
            fn=lambda: quick_command("/npcs"),
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_display, status_message]
        )

        stats_btn.click(
            fn=lambda: quick_command("/stats"),
            outputs=[chatbot, inventory_display, credits_display, location_display, profile_display, status_message]
        )

    return interface

if __name__ == "__main__":
    # Create and launch the interface
    interface = create_interface()

    print("🚀 Starting Eldoria Dialogue System Web Interface...")
    print("🌐 The game will be available at: http://localhost:7860")

    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,  # Set to True if you want a public link
        debug=False
    )