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
import unicodedata

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

# Version management
# Format: MAJOR.MINOR.PATCH
# - MAJOR: Breaking changes
# - MINOR: New features/fixes (increment for each significant fix)
# - PATCH: Small bugfixes
VERSION = "2.0.0"

# Version changelog
VERSION_CHANGELOG = {
    "2.0.0": "Major update: version bump, see release notes.",
    "1.4.0": "Fix NLP interpretation of dialogue vs /hint commands",
    "1.3.0": "Fix system prompt greeting repetition",
    "1.2.0": "Fix /api/chat NPC switching behavior",
    "1.1.0": "Fix /sense endpoint greeting repetition",
    "1.0.0": "Initial release"
}

# Constants
GAME_SYSTEM_NOT_INITIALIZED = 'Game system not initialized'

def normalize_text_for_lsl(text):
    """
    Normalizza il testo per LSL convertendo caratteri accentati in equivalenti ASCII.
    à => a', è => e', ì => i', ò => o', ù => u', ç => c'
    Also limits length to prevent LSL heap overflow (max 2000 chars for safety)
    """
    if not text:
        return text

    # CRITICAL: Limit length to prevent LSL heap overflow
    # LSL has 1MB heap limit, responses must be kept small
    MAX_RESPONSE_LENGTH = 2000
    if len(text) > MAX_RESPONSE_LENGTH:
        text = text[:MAX_RESPONSE_LENGTH - 3] + "..."

    # Mapping personalizzato per caratteri italiani
    replacements = {
        'à': "a'", 'á': "a'", 'â': 'a', 'ã': 'a', 'ä': 'a',
        'è': "e'", 'é': "e'", 'ê': 'e', 'ë': 'e',
        'ì': "i'", 'í': "i'", 'î': 'i', 'ï': 'i',
        'ò': "o'", 'ó': "o'", 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ù': "u'", 'ú': "u'", 'û': 'u', 'ü': 'u',
        'ç': "c'", 'ñ': 'n',
        # Maiuscole
        'À': "A'", 'Á': "A'", 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
        'È': "E'", 'É': "E'", 'Ê': 'E', 'Ë': 'E',
        'Ì': "I'", 'Í': "I'", 'Î': 'I', 'Ï': 'I',
        'Ò': "O'", 'Ó': "O'", 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
        'Ù': "U'", 'Ú': "U'", 'Û': 'U', 'Ü': 'U',
        'Ç': "C'", 'Ñ': 'N'
    }

    # Applica le sostituzioni
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    return text

def get_teleport_npc_data(game_system, current_npc: dict, target_npc_name: str) -> dict:
    """Get NPC data with teleport coordinates for target NPC.
    
    Args:
        game_system: The game system with database access
        current_npc: Current NPC data (used for non-teleport fields)
        target_npc_name: Name of NPC to teleport to
        
    Returns:
        NPC dict with target's teleport coords, or current_npc if target not found
    """
    if not target_npc_name:
        return current_npc
        
    target_npc_data = game_system.db.get_npc_by_name(target_npc_name)
    if target_npc_data and target_npc_data.get('teleport'):
        logger.info(f"[TELEPORT] Using target NPC '{target_npc_name}' coordinates: {target_npc_data.get('teleport')}")
        # Create modified NPC dict with target's teleport coords but current NPC's other data
        npc_for_teleport = dict(current_npc)
        npc_for_teleport['teleport'] = target_npc_data.get('teleport')
        return npc_for_teleport
    else:
        logger.warning(f"[TELEPORT] Target NPC '{target_npc_name}' not found or has no teleport coords, using current NPC")
        return current_npc

def parse_npc_file(filepath):
    """Parse NPC file and return NPC data dictionary."""
    data = {
        'name': '', 'area': '', 'role': '', 'motivation': '',
        'goal': '', 'needed_object': '', 'treasure': '',
        'playerhint': '', 'dialogue_hooks': '', 'veil_connection': '', 'code': '',
        'emotes': '', 'animations': '', 'lookup': '', 'llsettext': '', 'teleport': '',
        'notecard_feature': ''
    }
    known_keys_map = {
        'Name:': 'name', 'Area:': 'area', 'Role:': 'role',
        'Motivation:': 'motivation', 'Goal:': 'goal',
        'Needed Object:': 'needed_object', 'Treasure:': 'treasure',
        'PlayerHint:': 'playerhint',
        'Veil Connection:': 'veil_connection',
        'Dialogue Hooks:': 'dialogue_hooks_header',
        'Emotes:': 'emotes', 'Animations:': 'animations',
        'Lookup:': 'lookup', 'Llsettext:': 'llsettext', 'Teleport:': 'teleport',
        'NOTECARD_FEATURE:': 'notecard_feature'
    }
    simple_multiline_fields = ['motivation', 'goal', 'playerhint', 'veil_connection', 'emotes', 'animations', 'lookup', 'llsettext', 'notecard_feature']
    # Note: 'teleport' is NOT multiline - it should only capture coordinates on the same line

    current_field_being_parsed = None
    dialogue_hooks_lines = []
    parsing_dialogue_hooks = False

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            lines = content.split('\n')

        # Try to parse new structured format for SL_Commands
        if 'SL_Commands:' in content:
            import re
            # Extract SL_Commands section
            sl_commands_match = re.search(r'SL_Commands:\s*\{([^}]+)\}', content, re.DOTALL)
            if sl_commands_match:
                sl_section = sl_commands_match.group(1)

                # Extract arrays using regex
                emotes_match = re.search(r'"Emotes":\s*\[([^\]]+)\]', sl_section)
                if emotes_match and not data['emotes']:
                    emotes_list = [e.strip().strip('"') for e in emotes_match.group(1).split(',')]
                    data['emotes'] = ', '.join(emotes_list)

                animations_match = re.search(r'"Animations":\s*\[([^\]]+)\]', sl_section)
                if animations_match and not data['animations']:
                    anims_list = [a.strip().strip('"') for a in animations_match.group(1).split(',')]
                    data['animations'] = ', '.join(anims_list)

                lookup_match = re.search(r'"Lookup":\s*\[([^\]]+)\]', sl_section)
                if lookup_match and not data['lookup']:
                    lookup_list = [l.strip().strip('"') for l in lookup_match.group(1).split(',')]
                    data['lookup'] = ', '.join(lookup_list)

                text_display_match = re.search(r'"Text_Display":\s*\[([^\]]+)\]', sl_section)
                if text_display_match and not data['llsettext']:
                    text_list = [t.strip().strip('"') for t in text_display_match.group(1).split(',')]
                    data['llsettext'] = ', '.join(text_list)

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
                        # Don't overwrite if already parsed from structured format
                        if not data[field_name_target]:
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
                        # Insert NPC into MySQL database
                        import mysql.connector
                        conn = None
                        try:
                            conn = game_system.db.connect()
                            cursor = conn.cursor()
                            sql = """INSERT INTO NPCs (code, name, area, role, motivation, goal, needed_object,
                                     treasure, playerhint, dialogue_hooks, veil_connection, emotes, animations,
                                     lookup, llsettext, teleport, notecard_feature, storyboard_id)
                                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                     ON DUPLICATE KEY UPDATE name=VALUES(name), area=VALUES(area), role=VALUES(role), notecard_feature=VALUES(notecard_feature)"""
                            cursor.execute(sql, (
                                npc_data.get('code'), npc_data.get('name'), npc_data.get('area'),
                                npc_data.get('role'), npc_data.get('motivation'), npc_data.get('goal'),
                                npc_data.get('needed_object'), npc_data.get('treasure'), npc_data.get('playerhint'),
                                npc_data.get('dialogue_hooks'), npc_data.get('veil_connection'),
                                npc_data.get('emotes'), npc_data.get('animations'), npc_data.get('lookup'),
                                npc_data.get('llsettext'), npc_data.get('teleport'), npc_data.get('notecard_feature', ''),
                                npc_data.get('storyboard_id', 1)
                            ))
                            conn.commit()
                        except Exception as db_err:
                            logger.error(f"Error inserting NPC {npc_code} into database: {db_err}")
                            if conn:
                                conn.rollback()
                        finally:
                            if conn:
                                conn.close()
                    
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
    model_name = os.getenv('NEXUS_MODEL_NAME') or os.getenv('OPENROUTER_DEFAULT_MODEL', 'google/gemini-flash-2.5-preview-09-2025:free')
    profile_analysis_model = os.getenv('NEXUS_PROFILE_MODEL_NAME')
    wise_guide_model = os.getenv('NEXUS_WISE_GUIDE_MODEL_NAME')
    debug_mode = os.getenv('NEXUS_DEBUG_MODE', 'false').lower() == 'true'

    # MySQL configuration logging
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'nexus_rpg')
    db_user = os.getenv('DB_USER', 'root')

    logger.info("=" * 80)
    logger.info("DATABASE CONFIGURATION VERIFICATION")
    logger.info("=" * 80)
    logger.info(f"NEXUS_USE_MOCKUP: {use_mockup}")
    if not use_mockup:
        logger.info(f"DATABASE MODE: MySQL")
        logger.info(f"  Host: {db_host}")
        logger.info(f"  Database: {db_name}")
        logger.info(f"  User: {db_user}")
    else:
        logger.info(f"DATABASE MODE: MOCKUP (File-based)")
        logger.info(f"  Mockup Dir: {mockup_dir}")
    logger.info(f"MODEL: {model_name}")
    logger.info("=" * 80)

    logger.info(f"Initializing GameSystem with mockup={use_mockup}, model={model_name}")

    # Initialize GameSystem - it will handle database configuration internally using environment variables
    from game_system_api import GameSystem
    game_system = GameSystem(
        use_mockup=use_mockup,
        mockup_dir=mockup_dir,
        model_name=model_name,
        profile_analysis_model_name=profile_analysis_model,
        wise_guide_model_name=wise_guide_model,
        debug_mode=debug_mode
    )

    logger.info(f"✓ Initialized GameSystem with mockup={use_mockup}, model={model_name}")

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

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information."""
    return jsonify({
        'service': 'nexus-api',
        'version': VERSION,
        'status': 'running',
        'description': 'AI-powered text-based RPG engine',
        'changelog': VERSION_CHANGELOG.get(VERSION, 'No changelog available'),
        'endpoints': {
            'health': '/health',
            'version': '/version',
            'chat': '/api/chat',
            'commands': '/api/commands',
            'player': '/api/player/<player_id>/*',
            'game': '/api/game/*',
            'admin': '/reset'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    from datetime import datetime
    import os

    # Get server start time (from app.py file modification time as proxy)
    app_file_path = __file__
    app_mtime = os.path.getmtime(app_file_path)
    app_modified = datetime.fromtimestamp(app_mtime).strftime('%Y-%m-%d %H:%M:%S')

    # Current server time
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'status': 'healthy',
        'service': 'nexus-api',
        'version': VERSION,
        'server_time': current_time,
        'app_last_modified': app_modified,
        'process_id': os.getpid(),
        'uptime': 'n/a',  # Could be implemented with start time tracking
        'last_change': VERSION_CHANGELOG.get(VERSION, 'Unknown')
    })

@app.route('/api/npc/verify', methods=['POST'])
def verify_npc():
    """Verify NPC exists in database and return capabilities."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500

        data = request.get_json()
        npc_name = data.get('npc_name', '').strip()
        area = data.get('area', '').strip()

        if not npc_name or not area:
            return jsonify({'error': 'Missing npc_name or area'}), 400

        # Try to get NPC from database
        npc_data = game_system.db.get_npc(area, npc_name)

        if npc_data:
            # Check capabilities
            has_teleport = bool(npc_data.get('teleport', '').strip())
            has_llsettext = bool(npc_data.get('llsettext', '').strip())

            return jsonify({
                'found': 'true',
                'npc_name': npc_data.get('name', npc_name),
                'area': npc_data.get('area', area),
                'has_teleport': 'true' if has_teleport else 'false',
                'has_llsettext': 'true' if has_llsettext else 'false'
            })
        else:
            return jsonify({
                'found': 'false',
                'npc_name': npc_name,
                'area': area
            }), 404

    except Exception as e:
        logger.error(f"Error in NPC verification: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/version', methods=['GET'])
def version_info():
    """Version information endpoint."""
    return jsonify({
        'current_version': VERSION,
        'changelog': VERSION_CHANGELOG,
        'latest_change': VERSION_CHANGELOG.get(VERSION, 'Unknown'),
        'service': 'nexus-api'
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
        all_npcs = game_system.db.list_npcs_by_area()
        
        if area:
            # Filter NPCs by area (case-insensitive)
            npcs = [npc for npc in all_npcs if npc.get('area', '').lower() == area.lower()]
        else:
            npcs = all_npcs
        
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

@app.route('/api/player/<player_id>/conversation/reset', methods=['DELETE'])
def reset_conversation_history(player_id: str):
    """Reset/clear all conversation history for a player."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        # Clear conversation history from database
        success = game_system.db.clear_conversations(player_id)
        
        if success:
            return jsonify({
                'message': f'All conversation history cleared for player {player_id}',
                'player_id': player_id,
                'success': True
            })
        else:
            return jsonify({
                'error': f'Failed to clear conversation history for player {player_id}',
                'success': False
            }), 500
    
    except Exception as e:
        logger.error(f"Error clearing conversation history for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/storage-info', methods=['GET'])
def get_player_storage_info(player_id: str):
    """Get detailed storage information for a player including size, NPCs talked to, etc."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        # Get storage info from database
        storage_info = game_system.db.get_player_storage_info(player_id)
        
        if not storage_info:
            return jsonify({
                'error': f'No data found for player {player_id}',
                'player_id': player_id
            }), 404
        
        return jsonify(storage_info)
    
    except Exception as e:
        logger.error(f"Error getting storage info for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/conversation/analyze', methods=['POST'])
def analyze_conversations(player_id: str):
    """Generate LLM analysis of all conversations for a player."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        # Get all conversations for analysis
        conversations = game_system.db.get_all_conversations_for_analysis(player_id)
        
        if not conversations:
            return jsonify({
                'error': f'No conversations found for player {player_id}',
                'player_id': player_id
            }), 404
        
        # Prepare conversation data for LLM analysis
        conversation_text = f"Player: {player_id}\n\n"
        conversation_text += "=== CONVERSATION HISTORY ANALYSIS ===\n\n"
        
        for conv in conversations:
            npc_code = conv['npc_code']
            history = conv['history']
            conversation_text += f"--- Conversation with {npc_code} ---\n"
            
            for msg in history:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if role == 'user':
                    conversation_text += f"Player: {content}\n"
                elif role == 'assistant':
                    conversation_text += f"{npc_code}: {content}\n"
            
            conversation_text += f"\n"
        
        # Create analysis prompt
        analysis_prompt = f"""Analyze the complete conversation history for player '{player_id}' in this fantasy RPG.

{conversation_text}

Please provide a comprehensive analysis covering:

1. **Character Development**: How has the player's character evolved through their interactions?

2. **Interaction Patterns**: What are the player's communication styles, preferences, and behavioral patterns?

3. **Relationship Dynamics**: How does the player relate to different NPCs? Any notable relationship developments?

4. **Quest Progress & Decisions**: What major decisions has the player made? How do they approach challenges?

5. **Personality Insights**: What can we infer about the player's personality, motivations, and values?

6. **Narrative Themes**: What recurring themes or interests emerge from their conversations?

7. **Social Dynamics**: How does the player engage socially? Are they cooperative, cautious, adventurous?

8. **Growth Areas**: What areas of character development or gameplay might benefit from attention?

Provide specific examples from the conversations to support your analysis. Keep the tone professional but engaging, as if writing a character study for a game master."""

        # Call LLM for analysis
        from llm_wrapper import llm_wrapper
        
        messages = [
            {"role": "user", "content": analysis_prompt}
        ]
        
        # Use a more capable model for analysis
        analysis_model = os.environ.get("PROFILE_ANALYSIS_MODEL", "mistralai/mistral-7b-instruct:free")
        analysis_result, stats = llm_wrapper(
            messages=messages,
            model_name=analysis_model,
            stream=False,
            collect_stats=True
        )
        
        if not analysis_result or analysis_result.startswith("[Errore"):
            return jsonify({
                'error': 'Failed to generate conversation analysis',
                'details': analysis_result
            }), 500
        
        # Save the analysis
        save_success = game_system.db.save_conversation_analysis(player_id, analysis_result)
        
        response_data = {
            'player_id': player_id,
            'analysis': analysis_result,
            'conversation_count': len(conversations),
            'npcs_analyzed': [conv['npc_code'] for conv in conversations],
            'analysis_saved': save_success,
            'generated_at': datetime.now().isoformat()
        }
        
        if stats:
            response_data['llm_stats'] = stats
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error analyzing conversations for {player_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>/conversation/analysis', methods=['GET'])
def get_conversation_analysis(player_id: str):
    """Get saved conversation analysis for a player."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        analysis = game_system.db.get_conversation_analysis(player_id)
        
        if not analysis:
            return jsonify({
                'error': f'No conversation analysis found for player {player_id}',
                'player_id': player_id,
                'suggestion': f'Use POST /api/player/{player_id}/conversation/analyze to generate analysis'
            }), 404
        
        return jsonify(analysis)
    
    except Exception as e:
        logger.error(f"Error getting conversation analysis for {player_id}: {str(e)}")
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
        
        # Accept both player_id (UUID) and display_name, fallback for legacy clients
        player_id = data.get('player_id') or data.get('player_name') or data.get('name')
        display_name = data.get('display_name', player_id)
        message = data['message']
        npc_name = data.get('npc_name')  # Optional NPC name parameter
        area = data.get('area')  # Optional area parameter

        # Validate player_id
        if not player_id or not isinstance(player_id, str) or len(player_id.strip()) == 0:
            return jsonify({'error': 'Invalid player_id: must be a non-empty string'}), 400
        player_id = player_id.strip()
        
        # Get player system
        player_system = game_system.get_player_system(player_id)
        
        # Ensure player_system is valid
        if not player_system:
            return jsonify({
                'error': f'Could not create or retrieve player system for: {player_id}'
            }), 500
        
        # If area is specified, go to that area first
        if area:
            go_command = f"/go {area}"
            try:
                logger.info(f"[DEBUG] About to call process_player_input with: {go_command}")
                logger.info(f"[DEBUG] player_system.game_state before /go: {type(player_system.game_state)}, is None: {player_system.game_state is None}")
                area_response = player_system.process_player_input(go_command, skip_profile_update=True)
                logger.info(f"[DEBUG] player_system.game_state after /go: {type(player_system.game_state)}, is None: {player_system.game_state is None}")
                if not area_response:
                    return jsonify({
                        'error': f'Invalid response when trying to go to area: {area}'
                    }), 500
            except Exception as e:
                logger.error(f"[DEBUG] Exception in /go command for area {area}: {str(e)}", exc_info=True)
                return jsonify({
                    'error': f'Error going to area {area}: {str(e)}'
                }), 500
        
        # If NPC name is specified, check if we need to switch to that NPC
        if npc_name:
            # Check if we're already talking to this NPC
            logger.info(f"[DEBUG] Checking current NPC, game_state is None: {player_system.game_state is None}")
            current_npc = player_system.game_state.get('current_npc') if player_system.game_state else None
            current_npc_name = current_npc.get('name', '') if current_npc else ''
            logger.info(f"[DEBUG] current_npc_name: {current_npc_name}, requested npc_name: {npc_name}")

            # Only switch if we're not already talking to this NPC
            if current_npc_name.lower() != npc_name.lower():
                logger.info(f"Switching from {current_npc_name} to {npc_name}")
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
            else:
                logger.info(f"Already talking to {npc_name}, continuing conversation")
        
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

        # Handle case where command was processed but no NPC response was generated
        # In this case, make the NPC present the system messages naturally
        npc_response = response.get('npc_response', '')
        system_messages = response.get('system_messages', [])
        current_npc = player_system.game_state.get('current_npc') if player_system.game_state else None

        if not npc_response and system_messages and current_npc:
            npc_name = current_npc.get('name', 'NPC')
            # Format system messages as NPC dialogue
            if len(system_messages) == 1:
                npc_response = f"*{npc_name} ti dice* {system_messages[0]}"
            else:
                formatted_messages = []
                for msg in system_messages[:5]:  # Limit to first 5 messages to avoid truncation
                    # Skip certain system messages that shouldn't be spoken
                    if any(skip_phrase in msg for skip_phrase in ['[Interpreted as:', '[Debug]', 'Error:', 'HTTP']):
                        continue
                    formatted_messages.append(msg)

                if formatted_messages:
                    if len(formatted_messages) == 1:
                        npc_response = f"*{npc_name} ti dice* {formatted_messages[0]}"
                    else:
                        # Join multiple messages in a natural way
                        messages_text = ". ".join(formatted_messages)
                        npc_response = f"*{npc_name} ti informa* {messages_text}"
        
        # Generate Second Life commands if there's a current NPC
        sl_commands = ""
        try:
            current_npc = player_system.game_state.get('current_npc') if player_system.game_state else None
            if current_npc:
                from chat_manager import generate_sl_command_prefix, extract_notecard_from_response
                # Check if teleport was offered in this turn
                teleport_offered = player_system.game_state.get('teleport_offered_this_turn', False) if player_system.game_state else False

                # Get notecard info from game_state (extracted in game_system_api.py)
                notecard_info = player_system.game_state.get('notecard_extracted', {}) if player_system.game_state else {}
                notecard_name = notecard_info.get('name', '')
                notecard_content = notecard_info.get('content', '')
                has_notecard = bool(notecard_name and notecard_content)

                if has_notecard:
                    logger.info(f"[NOTECARD] Using extracted notecard: '{notecard_name}' ({len(notecard_content)} chars)")
                    # Clear the notecard from game state after using it
                    if player_system.game_state and 'notecard_extracted' in player_system.game_state:
                        del player_system.game_state['notecard_extracted']

                # Check if teleport is to another NPC (not current NPC)
                teleport_target_npc_name = player_system.game_state.get('teleport_target_npc') if player_system.game_state else None
                npc_for_teleport = current_npc
                
                if teleport_offered and teleport_target_npc_name:
                    npc_for_teleport = get_teleport_npc_data(game_system, current_npc, teleport_target_npc_name)
                    # Clear the teleport_target_npc after use
                    if player_system.game_state:
                        player_system.game_state['teleport_target_npc'] = None

                # Generate SL commands with notecard if present
                # Note: npc_response is already cleaned (notecard removed) in game_system_api.py
                sl_commands = generate_sl_command_prefix(
                    npc_for_teleport,
                    include_teleport=teleport_offered,
                    npc_response=npc_response,
                    include_notecard=has_notecard,
                    notecard_content=notecard_content,
                    notecard_name=notecard_name
                )

                logger.info(f"Generated SL commands: '{sl_commands}' (teleport_offered={teleport_offered}, has_notecard={has_notecard})")
        except Exception as sl_error:
            logger.warning(f"Error generating SL commands: {str(sl_error)}")
            sl_commands = ""
        
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
            'player_id': player_id,
            'display_name': display_name,
            'player_message': message,
            'npc_name': npc_name,
            'npc_response': normalize_text_for_lsl(npc_response),
            'sl_commands': normalize_text_for_lsl(sl_commands),
            'system_messages': response.get('system_messages', []),
            'current_npc': response.get('current_npc_name'),
            'current_area': response.get('current_area'),
            'llm_stats': llm_stats
        })
    
    except Exception as e:
        player_name_for_log = locals().get('player_name', 'unknown_player')
        logger.error(f"Error in chat for {player_name_for_log}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api', methods=['GET'])
def api_info():
    """API information endpoint."""
    return jsonify({
        'api': 'nexus-rpg',
        'version': VERSION,
        'status': 'active',
        'endpoints': {
            'player_management': {
                'create_session': 'POST /api/player/<player_id>/session',
                'close_session': 'DELETE /api/player/<player_id>/session', 
                'process_input': 'POST /api/player/<player_id>/input',
                'get_state': 'GET /api/player/<player_id>/state',
                'get_profile': 'GET /api/player/<player_id>/profile',
                'get_inventory': 'GET /api/player/<player_id>/inventory',
                'get_history': 'GET /api/player/<player_id>/conversation'
            },
            'game_data': {
                'get_areas': 'GET /api/game/areas',
                'get_npcs': 'GET /api/game/npcs',
                'get_storyboard': 'GET /api/game/storyboard',
                'process_command': 'POST /api/game/command'
            },
            'interaction': {
                'chat': 'POST /api/chat',
                'sense': 'POST /sense',
                'leave': 'POST /leave'
            },
            'system': {
                'health': 'GET /health',
                'commands': 'GET /api/commands',
                'reset': 'POST /reset',
                'reload': 'POST /api/admin/reload'
            }
        }
    })

@app.route('/api/game/command', methods=['POST'])
def process_game_command():
    """Process a game command - similar to player input endpoint."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({'error': 'Missing command field'}), 400
        
        player_name = data.get('player_name')
        if not player_name:
            return jsonify({'error': 'Missing player_name field'}), 400
        
        command = data['command']
        
        # Get player system
        player_system = game_system.get_player_system(player_name)
        
        # Process command
        response = player_system.process_player_input(command)
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing game command: {str(e)}")
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
        # Accept both player_id (UUID) and display_name, fallback for legacy clients
        player_id = data.get('player_id') or data.get('player_name') or data.get('name')
        display_name = data.get('display_name', player_id)
        if not player_id or not isinstance(player_id, str) or len(player_id.strip()) == 0:
            return jsonify({'error': 'Invalid player_id: must be a non-empty string'}), 400
        player_id = player_id.strip()
        
        npc_name = data.get('npcname', '').strip()
        area = data.get('area', '').strip()
        
        # Get player system
        player_system = game_system.get_player_system(player_id)
        
        # Check if player has a current area, if not, set default starting area
        current_area = player_system.game_state.get('current_area') if player_system.game_state else None
        if not current_area:
            # Set default starting area to 'village' if no area specified, otherwise use specified area
            default_area = area if area else 'village'
            player_system.game_state['current_area'] = default_area
            logger.info(f"Set initial area for fresh player {player_id} to {default_area}")
        
        # Initialize other game state if missing
        if 'current_npc' not in player_system.game_state:
            player_system.game_state['current_npc'] = None
        if 'chat_session' not in player_system.game_state:
            player_system.game_state['chat_session'] = None
        
        # If area is specified, go to that area first (unless already there)
        if area:
            current_area = player_system.game_state.get('current_area') if player_system.game_state else None
            if current_area != area:
                go_command = f"/go {area}"
                try:
                    area_response = player_system.process_player_input(go_command, skip_profile_update=True)
                    if not area_response or not isinstance(area_response, dict):
                        # For fresh player state after reset, this might be normal, continue anyway
                        logger.warning(f"Got invalid response when going to area {area} for fresh player {player_id}")
                        # Set the area manually as fallback
                        player_system.game_state['current_area'] = area
                    else:
                        logger.info(f"Successfully moved player {player_id} to area {area}")
                except Exception as e:
                    logger.error(f"Exception in /go command for area {area}: {str(e)}", exc_info=True)
                    # Set the area manually as fallback instead of failing
                    logger.warning(f"Setting area {area} manually for {player_id} as fallback")
                    player_system.game_state['current_area'] = area
            else:
                logger.info(f"Player {player_id} already in area {area}, skipping /go command")
        
        # If NPC name is specified, try to set that NPC directly
        if npc_name:
            try:
                # Get the current area for NPC lookup
                current_area = player_system.game_state.get('current_area', 'village') if player_system.game_state else 'village'
                
                # Try to get the NPC data directly from database
                logger.info(f"Looking for NPC {npc_name} in area {current_area}")
                npc_data = game_system.db.get_npc(current_area, npc_name)
                logger.info(f"NPC lookup result: {npc_data is not None}")
                
                if npc_data:
                    # Set the NPC directly in game state
                    player_system.game_state['current_npc'] = npc_data
                    logger.info(f"Successfully set NPC {npc_name} for player {player_id}")
                    logger.info(f"NPC data has default_greeting: {'default_greeting' in npc_data}")

                    # Initialize a chat session for the NPC ONLY if there isn't one already
                    # This prevents losing conversation history when player re-touches the same NPC
                    if not (player_system.game_state.get('chat_session') if player_system.game_state else None):
                        from chat_manager import ChatSession
                        chat_session = ChatSession()
                        player_system.game_state['chat_session'] = chat_session
                        logger.info(f"Created new chat session for {npc_name}")
                    else:
                        logger.info(f"Reusing existing chat session for {npc_name}")

                    logger.info(f"Directly set NPC {npc_name} for player {player_id} in area {current_area}")
                else:
                    return jsonify({
                        'error': f'Could not find NPC {npc_name} in area {current_area}'
                    }), 400
                    
            except Exception as e:
                return jsonify({
                    'error': f'Error setting NPC {npc_name}: {str(e)}'
                }), 500
        
        # Get current NPC info
        current_npc = player_system.game_state.get('current_npc') if player_system.game_state else None
        if not current_npc:
            return jsonify({
                'npc_response': normalize_text_for_lsl(f"No NPC is currently present to notice {display_name}'s arrival."),
                'player_id': player_id,
                'display_name': display_name
            })
        
        current_npc_name = current_npc.get('name', 'Unknown NPC')
        
        # Get the NPC's unique greeting from their card
        npc_role = current_npc.get('role', 'resident')
        npc_area = current_npc.get('area', 'this place')

        # Check if there's an existing conversation with this NPC
        chat_session = player_system.game_state.get('chat_session') if player_system.game_state else None
        has_conversation_history = chat_session and len(chat_session.messages) > 0

        # Try to get the Default_Greeting from NPC data, fallback to generic greeting
        default_greeting = current_npc.get('default_greeting', '')
        logger.info(f"Raw default_greeting for {current_npc_name}: {repr(default_greeting)}")

        # Strip extra quotes if present (from JSON escaping)
        if default_greeting and default_greeting.startswith('"') and default_greeting.endswith('"'):
            default_greeting = default_greeting[1:-1]
            logger.info(f"Cleaned default_greeting: {repr(default_greeting)}")

        # Choose response based on whether there's conversation history
        if has_conversation_history:
            # Player is returning to an ongoing conversation
            logger.info(f"Player {player_id} returning to conversation with {current_npc_name}")
            npc_response = f"Bentornato, {display_name}. Di cosa volevi parlare?"
        elif default_greeting:
            # Use the NPC's unique greeting from their card for first contact
            npc_response = default_greeting
        else:
            # Fallback to generic greeting if not found
            logger.warning(f"No Default_Greeting found for NPC {current_npc_name}, using fallback")
            npc_response = f"*{current_npc_name} nota {display_name}* Salve, viandante."
        
        # Create a minimal response object for consistency
        response = {'current_area': npc_area}

        # Generate Second Life commands for the current NPC
        sl_commands = ""
        try:
            from chat_manager import generate_sl_command_prefix, extract_notecard_from_response

            # Extract notecard command from NPC response if present
            cleaned_response, notecard_name, notecard_content = extract_notecard_from_response(npc_response)
            has_notecard = notecard_name and notecard_content

            # Generate SL commands with notecard if present
            sl_commands = generate_sl_command_prefix(
                current_npc,
                npc_response=cleaned_response,
                include_notecard=has_notecard,
                notecard_content=notecard_content,
                notecard_name=notecard_name
            )

            # Update npc_response to remove the notecard command (keep only the dialogue)
            if has_notecard:
                npc_response = cleaned_response
                logger.info(f"Extracted notecard '{notecard_name}' from NPC response (sense)")

            logger.info(f"Generated SL commands (sense): '{sl_commands}' (has_notecard={has_notecard})")
        except Exception as sl_error:
            logger.warning(f"Error generating SL commands in sense: {str(sl_error)}")
            sl_commands = ""
        
        return jsonify({
            'npc_response': normalize_text_for_lsl(npc_response),
            'npc_name': current_npc_name,
            'player_id': player_id,
            'display_name': display_name,
            'current_area': response.get('current_area'),
            'sl_commands': normalize_text_for_lsl(sl_commands),
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
        # Accept both player_id (UUID) and display_name, fallback for legacy clients
        player_id = data.get('player_id') or data.get('player_name') or data.get('name')
        display_name = data.get('display_name', player_id)
        if not player_id or not isinstance(player_id, str) or len(player_id.strip()) == 0:
            return jsonify({'error': 'Invalid player_id: must be a non-empty string'}), 400
        player_id = player_id.strip()
        
        # Get player system safely
        try:
            player_system = game_system.get_player_system(player_id)
            if not player_system or not hasattr(player_system, 'game_state'):
                return jsonify({
                    'message': f"*{display_name} has left*",
                    'player_id': player_id,
                    'display_name': display_name,
                    'conversation_saved': False,
                    'note': 'No active session found'
                })
        except Exception as e:
            logger.error(f"Error getting player system for {player_id}: {str(e)}")
            return jsonify({
                'message': f"*{display_name} has left*",
                'player_id': player_id,
                'display_name': display_name,
                'conversation_saved': False,
                'error': f"Could not access player session: {str(e)}"
            })
        
        # Get current NPC and conversation info safely
        current_npc = player_system.game_state.get('current_npc') if player_system.game_state else None
        chat_session = player_system.game_state.get('chat_session') if player_system.game_state else None
        current_area = player_system.game_state.get('current_area') if player_system.game_state else 'Unknown'
        
        departure_message = f"*{display_name} has left*"
        current_npc_name = None
        conversation_saved = False
        
        # If there's an active conversation, save it and create departure message
        if current_npc and chat_session:
            current_npc_name = current_npc.get('name', 'Unknown NPC')
            departure_message = f"*{current_npc_name} notices {display_name} is leaving*"
            
            # Try to save conversation
            try:
                from session_utils import save_current_conversation
                from terminal_formatter import TerminalFormatter
                
                save_current_conversation(
                    game_system.db, 
                    player_id, 
                    current_npc, 
                    chat_session, 
                    TerminalFormatter, 
                    player_system.game_state
                )
                conversation_saved = True
                logger.info(f"Saved conversation for {player_id} with {current_npc_name}")
                
            except Exception as save_error:
                logger.error(f"Error saving conversation for {player_id}: {str(save_error)}")
                # Don't fail the whole operation, just log the error
                conversation_saved = False
        
        # Clean up session state safely - only clear NPC/chat, preserve player data
        if player_system.game_state:
            try:
                player_system.game_state['current_npc'] = None
                player_system.game_state['chat_session'] = None
                # Keep current_area, inventory, profile, etc.
                logger.info(f"Cleaned up session state for {player_id}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up session for {player_id}: {str(cleanup_error)}")
        
        return jsonify({
            'message': departure_message,
            'npc_name': current_npc_name,
            'player_id': player_id,
            'display_name': display_name,
            'current_area': current_area,
            'conversation_saved': conversation_saved
        })
    
    except Exception as e:
        logger.error(f"Error in leave endpoint: {str(e)}")
        # Ensure display_name and player_id are always defined for error response
        safe_display_name = locals().get('display_name', 'unknown')
        safe_player_id = locals().get('player_id', 'unknown')
        return jsonify({
            'message': f"*{safe_display_name} has left*",
            'player_id': safe_player_id,
            'display_name': safe_display_name,
            'conversation_saved': False,
            'error': str(e)
        }), 500


@app.route('/api/leave_npc', methods=['POST'])
def leave_npc_conversation():
    """Handle NPC conversation departure from LSL - save conversation and reset NPC state."""
    try:
        if not game_system:
            return jsonify({'error': GAME_SYSTEM_NOT_INITIALIZED}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request data'}), 400
        
        # Extract fields sent from LSL script
        player_id = data.get('player_id') or data.get('player_name') or data.get('name', '')
        player_id = player_id.strip() if player_id else ''
        display_name = data.get('display_name', player_id)
        npc_name = data.get('npc_name', '').strip()
        
        if not player_id:
            return jsonify({'error': 'Player id cannot be empty'}), 400
        if not npc_name:
            return jsonify({'error': 'NPC name cannot be empty'}), 400
        
        area = data.get('area', 'Unknown')
        action = data.get('action', 'leaving')
        message = data.get('message', 'Avatar is leaving the conversation')
        status = data.get('status', 'end')
        
        logger.info(f"NPC conversation leave request: {player_id} with {npc_name} in {area}, action: {action}, status: {status}")
        
        # Get player system safely
        try:
            player_system = game_system.get_player_system(player_id)
            if not player_system or not hasattr(player_system, 'game_state'):
                return jsonify({
                    'message': f"*{display_name} has left conversation with {npc_name}*",
                    'player_id': player_id,
                    'display_name': display_name,
                    'npc_name': npc_name,
                    'area': area,
                    'conversation_saved': False,
                    'note': 'No active session found'
                })
        except Exception as e:
            logger.error(f"Error getting player system for {player_id}: {str(e)}")
            return jsonify({
                'message': f"*{display_name} has left conversation with {npc_name}*",
                'player_id': player_id,
                'display_name': display_name,
                'npc_name': npc_name, 
                'area': area,
                'conversation_saved': False,
                'error': f"Could not access player session: {str(e)}"
            })
        
        # Get current NPC and conversation info safely
        current_npc = player_system.game_state.get('current_npc') if player_system.game_state else None
        chat_session = player_system.game_state.get('chat_session') if player_system.game_state else None
        current_area = player_system.game_state.get('current_area') if player_system.game_state else area
        
        departure_message = f"*{npc_name} notices {display_name} is leaving*"
        conversation_saved = False
        
        # If there's an active conversation with the same NPC, save it
        if current_npc and chat_session and current_npc.get('name', '').lower() == npc_name.lower():
            try:
                from session_utils import save_current_conversation
                from terminal_formatter import TerminalFormatter
                
                save_current_conversation(
                    game_system.db, 
                    player_id, 
                    current_npc, 
                    chat_session, 
                    TerminalFormatter, 
                    player_system.game_state
                )
                conversation_saved = True
                logger.info(f"Saved NPC conversation for {player_id} with {npc_name}")
                
            except Exception as save_error:
                logger.error(f"Error saving NPC conversation for {player_id} with {npc_name}: {str(save_error)}")
                conversation_saved = False
        
        # Clean up NPC-specific session state
        if player_system.game_state:
            try:
                # Only clear NPC-related state, preserve other player data
                if current_npc and current_npc.get('name', '').lower() == npc_name.lower():
                    player_system.game_state['current_npc'] = None
                    player_system.game_state['chat_session'] = None
                    logger.info(f"Cleaned up NPC conversation state for {player_id}")
                    
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up NPC conversation for {player_id}: {str(cleanup_error)}")
        
        return jsonify({
            'message': departure_message,
            'player_id': player_id,
            'display_name': display_name,
            'npc_name': npc_name,
            'area': current_area,
            'status': status,
            'action': action,
            'conversation_saved': conversation_saved
        })
    
    except Exception as e:
        logger.error(f"Error in leave_npc endpoint: {str(e)}")
        return jsonify({
            'message': "Error processing NPC leave request",
            'conversation_saved': False,
            'error': str(e)
        }), 500

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

@app.route('/game', methods=['GET'])
def game_interface():
    """Basic game interface information."""
    return jsonify({
        'title': 'Nexus RPG - Eldoria',
        'description': 'AI-powered text-based RPG engine',
        'version': VERSION,
        'features': [
            'Dynamic AI NPCs with unique personalities',
            'Player psychological profiling',
            'Second Life integration',
            'Multi-area exploration',
            'Item trading and quest mechanics'
        ],
        'getting_started': {
            'create_session': 'POST /api/player/<your_name>/session',
            'chat_with_npcs': 'POST /api/chat',
            'explore_areas': 'Use /go <area> command',
            'get_help': 'Use /help command'
        }
    })

if __name__ == '__main__':
    # Initialize game system
    initialize_game_system()
    
    # Run Flask app
    port = int(os.getenv('NEXUS_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Nexus Flask API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
