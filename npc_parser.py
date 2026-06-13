"""
Canonical NPC file parser.

Consolidated from former duplicated implementations in load.py and app.py.
This module provides the authoritative parse_npc_file() function that supports
both legacy and new standardized NPC schema formats.
"""

import json
import traceback

try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    class TerminalFormatter:
        DIM = ""; RESET = ""; YELLOW = ""; RED = ""; GREEN = ""; BOLD = ""
        BRIGHT_CYAN = ""
        @staticmethod
        def format_terminal_text(text, width=80):
            import textwrap
            return "\n".join(textwrap.wrap(text, width=width))


def parse_npc_file(filepath):
    """Parse an NPC text file and return a dictionary of NPC attributes.

    Supports both legacy schema (Name:, Area:, Role:, etc.) and the new
    standardized schema (ID:, Personality_Traits:, SL_Commands:, etc.).
    Section headers (# CORE PERSONALITY, # QUEST MECHANICS, etc.) are handled.
    """
    data = {
        'name': '', 'area': '', 'role': '', 'motivation': '',
        'goal': '', 'needed_object': '', 'treasure': '',
        'playerhint': '', 'dialogue_hooks': '', 'veil_connection': '', 'code': '',
        'emotes': '', 'animations': '', 'lookup': '', 'llsettext': '', 'teleport': '',
        # New schema fields
        'id': '', 'personality_traits': '', 'relationship_status': '',
        'required_item': '', 'required_quantity': '', 'required_source': '',
        'reward_credits': '', 'prerequisites': '', 'success_conditions': '', 'failure_conditions': '',
        'ai_behavior_notes': '', 'conversation_state_tracking': '', 'conditional_responses': '',
        'relationships': '', 'default_greeting': '', 'repeat_greeting': '',
        'sl_commands': '', 'trading_rules': '', 'notecard_feature': '',
        'facial_expressions': '',
    }

    known_keys_map = {
        # Legacy schema
        'Name:': 'name', 'Area:': 'area', 'Role:': 'role',
        'Motivation:': 'motivation', 'Goal:': 'goal',
        'Needed Object:': 'needed_object', 'Treasure:': 'treasure',
        'PlayerHint:': 'playerhint', 'Veil Connection:': 'veil_connection',
        'Dialogue Hooks:': 'dialogue_hooks_header',
        'Dialogue_Hooks:': 'dialogue_hooks_header',
        'Emotes:': 'emotes', 'Animations:': 'animations',
        'FacialExpressions:': 'facial_expressions',
        'Lookup:': 'lookup', 'Llsettext:': 'llsettext', 'Teleport:': 'teleport',
        # New schema
        'ID:': 'id', 'Personality_Traits:': 'personality_traits',
        'Relationship_Status:': 'relationship_status',
        'Required_Item:': 'required_item', 'Required_Quantity:': 'required_quantity',
        'Required_Source:': 'required_source', 'Reward_Credits:': 'reward_credits',
        'Prerequisites:': 'prerequisites', 'Success_Conditions:': 'success_conditions',
        'Failure_Conditions:': 'failure_conditions', 'AI_Behavior_Notes:': 'ai_behavior_notes',
        'Conversation_State_Tracking:': 'conversation_state_tracking',
        'Conditional_Responses:': 'conditional_responses', 'Relationships:': 'relationships',
        'Default_Greeting:': 'default_greeting', 'Repeat_Greeting:': 'repeat_greeting',
        'SL_Commands:': 'sl_commands', 'Trading_Rules:': 'trading_rules',
        'NOTECARD_FEATURE:': 'notecard_feature', 'Notecard_Feature:': 'notecard_feature',
    }

    simple_multiline_fields = [
        'motivation', 'goal', 'playerhint', 'veil_connection', 'emotes', 'animations',
        'facial_expressions', 'lookup', 'llsettext', 'teleport', 'personality_traits',
        'relationship_status', 'prerequisites', 'success_conditions', 'failure_conditions',
        'ai_behavior_notes', 'conversation_state_tracking', 'conditional_responses',
        'relationships', 'default_greeting', 'repeat_greeting', 'sl_commands',
        'trading_rules', 'notecard_feature',
    ]

    current_field_being_parsed = None
    current_section = None
    dialogue_hooks_lines = []
    parsing_dialogue_hooks = False

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        for line_raw in lines:
            line_stripped = line_raw.strip()
            original_line_content_for_hooks = line_raw.rstrip('\n\r')

            # Handle section headers (lines starting with #)
            if line_stripped.startswith('#') and not line_stripped.startswith('##'):
                current_section = line_stripped[1:].strip()
                current_field_being_parsed = None
                parsing_dialogue_hooks = False
                continue

            # Skip sub-headers and empty lines in structured sections
            if line_stripped.startswith('##') or (not line_stripped and current_section):
                continue

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

            if matched_new_key:
                continue

            if parsing_dialogue_hooks:
                dialogue_hooks_lines.append(original_line_content_for_hooks)
            elif current_field_being_parsed in simple_multiline_fields:
                if line_stripped:
                    if data[current_field_being_parsed]:
                        data[current_field_being_parsed] += '\n' + line_stripped
                    else:
                        data[current_field_being_parsed] = line_stripped

        if dialogue_hooks_lines:
            data['dialogue_hooks'] = "\n".join(dialogue_hooks_lines).strip()
        else:
            data['dialogue_hooks'] = ""

        for key, value in data.items():
            if key != 'dialogue_hooks' and isinstance(value, str):
                data[key] = value.strip()

        # Extract Animations, FacialExpressions, Emotes, Lookup, Llsettext from sl_commands JSON
        if data.get('sl_commands'):
            try:
                sl_commands_str = data['sl_commands'].strip()

                # Find the first complete JSON object using brace counting
                brace_count = 0
                json_end = -1
                for i, char in enumerate(sl_commands_str):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end > 0:
                    first_json = sl_commands_str[:json_end]
                    sl_commands_data = json.loads(first_json)

                    if 'Animations' in sl_commands_data:
                        data['animations'] = ', '.join(sl_commands_data['Animations']) if isinstance(sl_commands_data['Animations'], list) else ''
                    if 'FacialExpressions' in sl_commands_data:
                        data['facial_expressions'] = ', '.join(sl_commands_data['FacialExpressions']) if isinstance(sl_commands_data['FacialExpressions'], list) else ''
                    if 'Emotes' in sl_commands_data:
                        data['emotes'] = ', '.join(sl_commands_data['Emotes']) if isinstance(sl_commands_data['Emotes'], list) else ''
                    if 'Lookup' in sl_commands_data:
                        data['lookup'] = ', '.join(sl_commands_data['Lookup']) if isinstance(sl_commands_data['Lookup'], list) else ''
                    if 'Llsettext' in sl_commands_data:
                        data['llsettext'] = sl_commands_data['Llsettext'] if isinstance(sl_commands_data['Llsettext'], str) else ''
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        if not data.get('name') or not data.get('area'):
            print(f"{TerminalFormatter.YELLOW}Warning: NPC file '{filepath}' missing Name or Area.{TerminalFormatter.RESET}")

        return data

    except FileNotFoundError:
        print(f"{TerminalFormatter.RED}Error: NPC file not found: '{filepath}'{TerminalFormatter.RESET}")
        raise
    except Exception as e:
        print(f"{TerminalFormatter.RED}Error parsing NPC file '{filepath}': {e}{TerminalFormatter.RESET}")
        traceback.print_exc()
        raise