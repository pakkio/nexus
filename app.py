#!/usr/bin/env python3
"""
Flask API for Nexus - AI-powered text-based RPG engine.
Provides RESTful endpoints for game interaction and session management.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from typing import Dict, Any, Optional

from game_system_api import GameSystem
from llm_stats_tracker import get_global_stats_tracker
import json
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global game system instance
game_system: Optional[GameSystem] = None

# Constants
GAME_SYSTEM_NOT_INITIALIZED = 'Game system not initialized'

def parse_npc_file(filepath):
    """Parse NPC file and return NPC data dictionary."""
    data = {
        'name': '', 'area': '', 'role': '', 'motivation': '',
        'goal': '', 'needed_object': '', 'treasure': '',
        'playerhint': '', 'dialogue_hooks': '', 'veil_connection': '', 'code': '',
        'emotes': '', 'animations': '', 'lookup': '', 'llsettext': ''
    }
    known_keys_map = {
        'Name:': 'name', 'Area:': 'area', 'Role:': 'role',
        'Motivation:': 'motivation', 'Goal:': 'goal',
        'Needed Object:': 'needed_object', 'Treasure:': 'treasure',
        'PlayerHint:': 'playerhint',
        'Veil Connection:': 'veil_connection',
        'Dialogue Hooks:': 'dialogue_hooks_header',
        'Emotes:': 'emotes', 'Animations:': 'animations',
        'Lookup:': 'lookup', 'Llsettext:': 'llsettext'
    }
    simple_multiline_fields = ['motivation', 'goal', 'playerhint', 'veil_connection', 'emotes', 'animations', 'lookup', 'llsettext']
    
    current_field_being_parsed = None
    dialogue_hooks_lines = []
    parsing_dialogue_hooks = False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        for line_raw in lines:
            line_stripped = line_raw.strip()
            original_line_content_for_hooks = line_raw.rstrip('\n\r')
            
            matched_new_key = False
            for key_prefix, field_name_target in known_keys_map.items():
                if line_stripped.lower().startswith(key_prefix.lower()):
                    parsing_dialogue_hooks = False
                    content_after_key = line_stripped[len(key_prefix):].strip()
                    
                    if field_name_target == 'dialogue_hooks_header':
                        parsing_dialogue_hooks = True
                        current_field_being_parsed = None
                    else:
                        data[field_name_target] = content_after_key
                        if field_name_target in simple_multiline_fields:
                            current_field_being_parsed = field_name_target
                        else:
                            current_field_being_parsed = None
                    matched_new_key = True
                    break
            
            if not matched_new_key:
                if parsing_dialogue_hooks:
                    dialogue_hooks_lines.append(original_line_content_for_hooks)
                elif current_field_being_parsed:
                    if data[current_field_being_parsed]:
                        data[current_field_being_parsed] += "\n" + line_stripped
                    else:
                        data[current_field_being_parsed] = line_stripped
        
        data['dialogue_hooks'] = "\n".join(dialogue_hooks_lines)
        return data
        
    except Exception as e:
        logger.error(f"Error parsing NPC file {filepath}: {e}")
        raise

def preload_npcs():
    """Preload NPCs from .txt files into the database after reset."""
    try:
        if not game_system:
            return False
            
        npc_count = 0
        base_dir = '.'  # Current directory where NPC files are located
        
        # Get all NPC files
        for filename in os.listdir(base_dir):
            if filename.startswith('NPC.') and filename.endswith('.txt'):
                filepath = os.path.join(base_dir, filename)
                path_parts = filename.replace('NPC.', '', 1).replace('.txt', '').split('.')
                npc_code = ".".join(path_parts) if path_parts else filename.replace('NPC.','').replace('.txt','')
                
                try:
                    npc_data = parse_npc_file(filepath)
                    npc_data['code'] = npc_code
                    npc_data['storyboard_id'] = 1
                    npc_data['created_at'] = datetime.now().isoformat()
                    
                    # Save NPC to database
                    if game_system.db.use_mockup:
                        npc_dir_path = os.path.join(game_system.db.mockup_dir, "NPCs")
                        os.makedirs(npc_dir_path, exist_ok=True)
                        with open(os.path.join(npc_dir_path, f"{npc_code}.json"), 'w', encoding='utf-8') as f:
                            json.dump(npc_data, f, indent=2)
                    else:
                        # For real database, would need to implement NPC insertion logic
                        logger.warning("Real database NPC preloading not implemented yet")
                    
                    npc_count += 1
                    logger.info(f"Loaded NPC: {npc_code}")
                    
                except Exception as e:
                    logger.error(f"Error processing NPC {filename}: {e}")
        
        logger.info(f"Preloaded {npc_count} NPCs")
        return True
        
    except Exception as e:
        logger.error(f"Error preloading NPCs: {e}")
        return False

def initialize_game_system():
    """Initialize the game system with configuration from environment variables."""
    global game_system
    
    # Configuration from environment variables
    use_mockup = os.getenv('NEXUS_USE_MOCKUP', 'true').lower() == 'true'
    mockup_dir = os.getenv('NEXUS_MOCKUP_DIR', 'database')
    model_name = os.getenv('NEXUS_MODEL_NAME', 'google/gemma-2-9b-it:free')
    profile_analysis_model = os.getenv('NEXUS_PROFILE_MODEL_NAME')
    wise_guide_model = os.getenv('NEXUS_WISE_GUIDE_MODEL_NAME')
    debug_mode = os.getenv('NEXUS_DEBUG_MODE', 'false').lower() == 'true'
    
    logger.info(f"Initializing GameSystem with mockup={use_mockup}, model={model_name}")
    
    game_system = GameSystem(
        use_mockup=use_mockup,
        mockup_dir=mockup_dir,
        model_name=model_name,
        profile_analysis_model_name=profile_analysis_model,
        wise_guide_model_name=wise_guide_model,
        debug_mode=debug_mode
    )
    
    return game_system

@app.before_request
def setup_game_system():
    """Initialize game system before requests."""
    global game_system
    if game_system is None:
        initialize_game_system()

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'nexus-api',
        'version': '1.0.0'
    })

@app.route('/api/player/<player_id>/session', methods=['POST'])
def create_player_session(player_id: str):
    """Create or initialize a player session."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        # Get player system (creates if doesn't exist)
        player_system = game_system.get_player_system(player_id)
        
        # Get initial state
        initial_response = player_system.process_player_input("")
        
        return jsonify({
            'player_id': player_id,
            'session_created': True,
            'initial_state': initial_response
        })
    
    except Exception as e:
        logger.error(f"Error creating session for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/session', methods=['DELETE'])
def close_player_session(player_id: str):
    """Close a player session."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        game_system.close_player_session(player_id)
        
        return jsonify({
            'player_id': player_id,
            'session_closed': True
        })
    
    except Exception as e:
        logger.error(f"Error closing session for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/input', methods=['POST'])
def process_player_input(player_id: str):
    """Process player input and return game response."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        data = request.get_json()
        if not data or 'input' not in data:
            return jsonify({'error': 'Missing input field'}), 400
        
        player_input = data['input']
        
        # Get player system
        player_system = game_system.get_player_system(player_id)
        
        # Process input
        response = player_system.process_player_input(player_input)
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing input for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/state', methods=['GET'])
def get_player_state(player_id: str):
    """Get current player state."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        player_system = game_system.get_player_system(player_id)
        
        # Get current state by processing empty input
        state = player_system.process_player_input("")
        
        return jsonify(state)
    
    except Exception as e:
        logger.error(f"Error getting state for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/areas', methods=['GET'])
def get_areas():
    """Get all available game areas."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        # Get areas from database
        areas = game_system.db.get_areas()
        
        return jsonify({
            'areas': areas
        })
    
    except Exception as e:
        logger.error(f"Error getting areas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/npcs', methods=['GET'])
def get_npcs():
    """Get all NPCs, optionally filtered by area."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        area = request.args.get('area')
        
        # Get NPCs from database
        if area:
            npcs = game_system.db.get_npcs_by_area(area)
        else:
            npcs = game_system.db.get_all_npcs()
        
        return jsonify({
            'npcs': npcs,
            'area': area
        })
    
    except Exception as e:
        logger.error(f"Error getting NPCs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/storyboard', methods=['GET'])
def get_storyboard():
    """Get the game storyboard."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        storyboard = game_system.db.get_storyboard()
        
        return jsonify(storyboard)
    
    except Exception as e:
        logger.error(f"Error getting storyboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/profile', methods=['GET'])
def get_player_profile(player_id: str):
    """Get player psychological profile."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        profile = game_system.db.load_player_profile(player_id)
        
        return jsonify({
            'player_id': player_id,
            'profile': profile
        })
    
    except Exception as e:
        logger.error(f"Error getting profile for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/inventory', methods=['GET'])
def get_player_inventory(player_id: str):
    """Get player inventory."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        inventory = game_system.db.load_inventory(player_id)
        credits = game_system.db.get_player_credits(player_id)
        
        return jsonify({
            'player_id': player_id,
            'inventory': inventory,
            'credits': credits
        })
    
    except Exception as e:
        logger.error(f"Error getting inventory for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/conversation', methods=['GET'])
def get_conversation_history(player_id: str):
    """Get player conversation history."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        # Get conversation history from database
        history = game_system.db.get_conversation_history(player_id)
        
        return jsonify({
            'player_id': player_id,
            'conversation_history': history
        })
    
    except Exception as e:
        logger.error(f"Error getting conversation history for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_with_npc():
    """Direct chat endpoint for NPC interaction."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Missing message field'}), 400
        
        if 'player_name' not in data:
            return jsonify({'error': 'Missing player_name field'}), 400
        
        message = data['message']
        player_name = data['player_name']
        npc_name = data.get('npc_name')  # Optional NPC name parameter
        area = data.get('area')  # Optional area parameter
        
        # Validate player_name
        if not player_name or not isinstance(player_name, str) or len(player_name.strip()) == 0:
            return jsonify({'error': 'Invalid player_name: must be a non-empty string'}), 400
        
        player_name = player_name.strip()
        
        # Get player system
        player_system = game_system.get_player_system(player_name)
        
        # Ensure player_system is valid
        if not player_system:
            return jsonify({
                'error': f'Could not create or retrieve player system for: {player_name}'
            }), 500
        
        # If area is specified, go to that area first
        if area:
            go_command = f"/go {area}"
            try:
                area_response = player_system.process_player_input(go_command, skip_profile_update=True)
                if not area_response:
                    return jsonify({
                        'error': f'Invalid response when trying to go to area: {area}'
                    }), 500
            except Exception as e:
                return jsonify({
                    'error': f'Error going to area {area}: {str(e)}'
                }), 500
        
        # If NPC name is specified, try to switch to that NPC
        if npc_name:
            # Format as a /talk command to switch to the specific NPC
            talk_command = f"/talk {npc_name}"
            try:
                switch_response = player_system.process_player_input(talk_command, skip_profile_update=True)
            except Exception as e:
                return jsonify({
                    'error': f'Error switching to NPC {npc_name}: {str(e)}'
                }), 500
            
            # Ensure switch_response is not None
            if not switch_response:
                return jsonify({
                    'error': f'Invalid response when trying to switch to NPC: {npc_name}'
                }), 500
            
            # Check if the switch was successful
            if switch_response.get('current_npc_name', '').lower() != npc_name.lower():
                return jsonify({
                    'error': f'Could not find or switch to NPC: {npc_name}',
                    'available_npcs': switch_response.get('system_messages', [])
                }), 400
        
        # Process the actual chat message
        try:
            response = player_system.process_player_input(message)
        except Exception as e:
            return jsonify({
                'error': f'Error processing message: {str(e)}'
            }), 500
        
        # Ensure response is not None
        if not response:
            return jsonify({
                'error': 'Invalid response from game system'
            }), 500
        
        # Get LLM statistics with better formatting
        stats_tracker = get_global_stats_tracker()
        llm_stats = {}
        total_llm_time = 0
        
        # Get stats for each model type with clearer metrics (excluding async profile analysis)
        for model_type in ['dialogue', 'guide_selection', 'command_interpretation']:
            type_stats = stats_tracker.type_stats.get(model_type)
            if type_stats:
                last_call = type_stats.last_call_stats
                call_time = round(last_call.total_time, 3) if last_call else 0
                total_llm_time += call_time
                
                llm_stats[model_type] = {
                    'model': type_stats.current_model,
                    'last_call_time_ms': int(call_time * 1000),
                    'last_tokens_in': last_call.input_tokens if last_call else 0,
                    'last_tokens_out': last_call.output_tokens if last_call else 0,
                    'tokens_per_sec': round(last_call.output_tokens / last_call.total_time, 1) if last_call and last_call.total_time > 0 else 0,
                    'session_calls': type_stats.total_calls,
                    'session_time_ms': int(type_stats.total_time * 1000)
                }
        
        # Add performance summary (without async profile analysis)
        llm_stats['summary'] = {
            'total_llm_time_ms': int(total_llm_time * 1000),
            'active_calls': len([k for k in llm_stats.keys() if k != 'summary']),
            'performance_note': 'Response time optimized with async profile analysis'
        }
        
        return jsonify({
            'player_name': player_name,
            'player_message': message,
            'npc_name': npc_name,
            'npc_response': response.get('npc_response', ''),
            'system_messages': response.get('system_messages', []),
            'current_npc': response.get('current_npc_name'),
            'current_area': response.get('current_area'),
            'llm_stats': llm_stats
        })
    
    except Exception as e:
        player_name_for_log = locals().get('player_name', 'unknown_player')
        logger.error(f"Error in chat for {player_name_for_log}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands', methods=['GET'])
def get_available_commands():
    """Get list of available game commands."""
    try:
        commands = {
            'navigation': [
                '/go <area> - Move to a different area',
                '/talk <npc_name> - Start conversation with an NPC',
                '/exit - Exit current conversation'
            ],
            'information': [
                '/help - Show help text',
                '/who - List NPCs in current area',
                '/whereami - Show current location',
                '/inventory - Show your inventory',
                '/profile - Show your psychological profile'
            ],
            'interaction': [
                '/give <item> - Give an item to current NPC',
                '/hint - Get guidance from wise guide',
                '/endhint - End hint mode'
            ],
            'system': [
                '/reset - Reset your profile',
                '/reload - Reload game data'
            ]
        }
        
        return jsonify({
            'commands': commands
        })
    
    except Exception as e:
        logger.error(f"Error getting commands: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sense', methods=['POST'])
def sense_player():
    """Handle player arrival - NPC notices and greets the player."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Missing name field'}), 400
        
        player_name = data['name'].strip()
        if not player_name:
            return jsonify({'error': 'Player name cannot be empty'}), 400
        
        npc_name = data.get('npcname', '').strip()
        area = data.get('area', '').strip()
        
        # Get player system
        player_system = game_system.get_player_system(player_name)
        
        # Check if player has a current area, if not, set default starting area
        current_area = player_system.game_state.get('current_area')
        if not current_area:
            # Set default starting area to 'village' if no area specified, otherwise use specified area
            default_area = area if area else 'village'
            player_system.game_state['current_area'] = default_area
            logger.info(f"Set initial area for fresh player {player_name} to {default_area}")
        
        # Initialize other game state if missing
        if 'current_npc' not in player_system.game_state:
            player_system.game_state['current_npc'] = None
        if 'chat_session' not in player_system.game_state:
            player_system.game_state['chat_session'] = None
        
        # If area is specified, go to that area first (unless already there)
        if area:
            current_area = player_system.game_state.get('current_area')
            if current_area != area:
                go_command = f"/go {area}"
                try:
                    area_response = player_system.process_player_input(go_command, skip_profile_update=True)
                    if not area_response:
                        # For fresh player state after reset, this might be normal, continue anyway
                        logger.warning(f"Got None response when going to area {area} for fresh player {player_name}")
                except Exception as e:
                    return jsonify({
                        'error': f'Error going to area {area}: {str(e)}'
                    }), 500
            else:
                logger.info(f"Player {player_name} already in area {area}, skipping /go command")
        
        # If NPC name is specified, try to set that NPC directly
        if npc_name:
            try:
                # Get the current area for NPC lookup
                current_area = player_system.game_state.get('current_area', 'village')
                
                # Try to get the NPC data directly from database
                npc_data = game_system.db.get_npc(current_area, npc_name)
                
                if npc_data:
                    # Set the NPC directly in game state
                    player_system.game_state['current_npc'] = npc_data
                    
                    # Initialize a chat session for the NPC
                    from chat_manager import ChatSession
                    chat_session = ChatSession()
                    player_system.game_state['chat_session'] = chat_session
                    
                    logger.info(f"Directly set NPC {npc_name} for player {player_name} in area {current_area}")
                else:
                    return jsonify({
                        'error': f'Could not find NPC {npc_name} in area {current_area}'
                    }), 400
                    
            except Exception as e:
                return jsonify({
                    'error': f'Error setting NPC {npc_name}: {str(e)}'
                }), 500
        
        # Get current NPC info
        current_npc = player_system.game_state.get('current_npc')
        if not current_npc:
            return jsonify({
                'message': f"No NPC is currently present to notice {player_name}'s arrival.",
                'player_name': player_name
            })
        
        current_npc_name = current_npc.get('name', 'Unknown NPC')
        
        # Generate contextual greeting based on NPC's character and role
        npc_role = current_npc.get('role', 'resident')
        npc_area = current_npc.get('area', 'this place')
        
        # Create a more natural greeting prompt that fits the character  
        greeting_prompt = f"*{player_name} approaches you*"
        
        # Process as player input to generate NPC response
        response = player_system.process_player_input(greeting_prompt)
        
        npc_response = response.get('npc_response', f"*{current_npc_name} notices {player_name} has arrived*")
        
        return jsonify({
            'message': npc_response,
            'npc_name': current_npc_name,
            'player_name': player_name,
            'current_area': response.get('current_area'),
            'system_messages': response.get('system_messages', [])
        })
    
    except Exception as e:
        logger.error(f"Error in sense endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/leave', methods=['POST'])
def leave_player():
    """Handle player departure - save conversation and register player leaving."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Missing name field'}), 400
        
        player_name = data['name'].strip()
        if not player_name:
            return jsonify({'error': 'Player name cannot be empty'}), 400
        
        npc_name = data.get('npcname', '').strip()
        area = data.get('area', '').strip()
        
        # Get player system
        player_system = game_system.get_player_system(player_name)
        
        # If area is specified, go to that area first
        if area:
            go_command = f"/go {area}"
            try:
                area_response = player_system.process_player_input(go_command, skip_profile_update=True)
                if not area_response:
                    # For fresh player state after reset, this might be normal, continue anyway
                    logger.warning(f"Got None response when going to area {area} for fresh player {player_name}")
            except Exception as e:
                return jsonify({
                    'error': f'Error going to area {area}: {str(e)}'
                }), 500
        
        # If NPC name is specified, try to switch to that NPC
        if npc_name:
            talk_command = f"/talk {npc_name}"
            try:
                switch_response = player_system.process_player_input(talk_command, skip_profile_update=True)
                if not switch_response:
                    # For fresh player state after reset, this might be normal, continue anyway
                    logger.warning(f"Got None response when switching to NPC {npc_name} for fresh player {player_name}")
                else:
                    # Check if the switch was successful
                    if switch_response.get('current_npc_name', '').lower() != npc_name.lower():
                        return jsonify({
                            'error': f'Could not find or switch to NPC: {npc_name}',
                            'available_npcs': switch_response.get('system_messages', [])
                        }), 400
            except Exception as e:
                return jsonify({
                    'error': f'Error switching to NPC {npc_name}: {str(e)}'
                }), 500
        
        # Get current NPC and conversation info
        current_npc = player_system.game_state.get('current_npc')
        chat_session = player_system.game_state.get('chat_session')
        
        if current_npc and chat_session:
            # Save current conversation (like in goto area command)
            from session_utils import save_current_conversation
            from terminal_formatter import TerminalFormatter
            
            try:
                save_current_conversation(
                    game_system.db, 
                    player_name, 
                    current_npc, 
                    chat_session, 
                    TerminalFormatter, 
                    player_system.game_state
                )
                
                current_npc_name = current_npc.get('name', 'Unknown NPC')
                departure_message = f"*{current_npc_name} notices {player_name} is leaving*"
                
                # Clear current NPC and session
                player_system.game_state['current_npc'] = None
                player_system.game_state['chat_session'] = None
                
                return jsonify({
                    'message': departure_message,
                    'npc_name': current_npc_name,
                    'player_name': player_name,
                    'conversation_saved': True
                })
                
            except Exception as save_error:
                logger.error(f"Error saving conversation for {player_name}: {str(save_error)}")
                return jsonify({
                    'message': f"*{player_name} has left*",
                    'player_name': player_name, 
                    'npc_name': current_npc.get('name', 'Unknown NPC') if current_npc else None,
                    'conversation_saved': False,
                    'error': f"Could not save conversation: {str(save_error)}"
                })
        else:
            return jsonify({
                'message': f"*{player_name} has left*",
                'player_name': player_name,
                'npc_name': current_npc.get('name', 'Unknown NPC') if current_npc else None,
                'conversation_saved': False,
                'note': 'No active conversation to save'
            })
    
    except Exception as e:
        logger.error(f"Error in leave endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_database():
    """Reset the database by deleting all player data and reloading NPC/story data."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        data = request.get_json()
        if not data or 'key' not in data:
            return jsonify({'error': 'Missing key field'}), 400
        
        if data['key'] != '1234':
            return jsonify({'error': 'Invalid key'}), 403
        
        # Reset database (delete all player data)
        game_system.db.reset_database()
        
        # Reload NPC and story data
        game_system.db.reload_data()
        
        # Preload NPCs from text files
        npc_preload_success = preload_npcs()
        
        return jsonify({
            'success': True,
            'message': 'Database reset and game data reloaded successfully',
            'npcs_preloaded': npc_preload_success
        })
    
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reload', methods=['POST'])
def reload_game_data():
    """Reload game data from files (admin endpoint)."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        # Reload data
        game_system.db.reload_data()
        
        return jsonify({
            'success': True,
            'message': 'Game data reloaded successfully'
        })
    
    except Exception as e:
        logger.error(f"Error reloading data: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize game system
    initialize_game_system()
    
    # Run Flask app
    port = int(os.getenv('NEXUS_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Nexus Flask API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)