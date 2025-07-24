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
                area_response = player_system.process_player_input(go_command)
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
                switch_response = player_system.process_player_input(talk_command)
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
        
        # Get stats for each model type with clearer metrics
        for model_type in ['dialogue', 'profile', 'guide_selection', 'command_interpretation']:
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
        
        # Add performance summary
        llm_stats['summary'] = {
            'total_llm_time_ms': int(total_llm_time * 1000),
            'active_calls': len([k for k in llm_stats.keys() if k != 'summary']),
            'performance_note': 'Slow due to profile analysis + command interpretation + free tier models'
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