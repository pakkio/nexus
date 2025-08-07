from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_describe(args_str: str, state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    
    if not args_str.strip():
        print(f"{TF.YELLOW}Usage: /describe <area_name>{TF.RESET}")
        print(f"{TF.DIM}Use /areas to see available areas.{TF.RESET}")
        return {**state, 'status': 'error', 'continue_loop': True}
    
    area_query = args_str.strip()
    _add_profile_action(state, f"Used /describe command for '{area_query}'")
    
    # Try to find location by name first
    location = db.get_location_by_name(area_query)
    
    if not location:
        # Try to find location by ID as fallback
        location = db.get_location(area_query)
    
    if not location:
        print(f"{TF.RED}Location '{area_query}' not found.{TF.RESET}")
        print(f"{TF.DIM}Use /areas to see available areas.{TF.RESET}")
        return {**state, 'status': 'error', 'continue_loop': True}
    
    # Display location information
    location_name = location.get('name', 'Unknown Location')
    print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}=== {location_name} ==={TF.RESET}")
    
    # Basic info
    area_type = location.get('area_type', '')
    access_level = location.get('access_level', '')
    if area_type or access_level:
        info_parts = []
        if area_type: info_parts.append(f"Type: {area_type}")
        if access_level: info_parts.append(f"Access: {access_level}")
        print(f"{TF.DIM}{' | '.join(info_parts)}{TF.RESET}")
    
    # Main description
    setting_description = location.get('setting_description', '').strip()
    if setting_description:
        print(f"\n{TF.GREEN}Description:{TF.RESET}")
        # Format description with proper line wrapping
        formatted_desc = TF.format_terminal_text(setting_description, width=70)
        for line in formatted_desc.split('\n'):
            print(f"  {line}")
    
    # Veil connection (lore)
    veil_connection = location.get('veil_connection', '').strip()
    if veil_connection:
        print(f"\n{TF.MAGENTA}Veil Connection:{TF.RESET}")
        formatted_veil = TF.format_terminal_text(veil_connection, width=70)
        for line in formatted_veil.split('\n'):
            print(f"  {line}")
    
    # NPCs present
    primary_npcs = location.get('primary_npcs', '').strip()
    secondary_npcs = location.get('secondary_npcs', '').strip()
    if primary_npcs or secondary_npcs:
        print(f"\n{TF.YELLOW}NPCs Present:{TF.RESET}")
        if primary_npcs:
            print(f"  {TF.BOLD}Primary:{TF.RESET} {primary_npcs}")
        if secondary_npcs:
            # Parse secondary NPCs if it's a JSON-like list
            if secondary_npcs.startswith('[') and secondary_npcs.endswith(']'):
                try:
                    import json
                    npc_list = json.loads(secondary_npcs.replace("'", '"'))
                    print(f"  {TF.DIM}Secondary:{TF.RESET} {', '.join(npc_list)}")
                except:
                    print(f"  {TF.DIM}Secondary:{TF.RESET} {secondary_npcs}")
            else:
                print(f"  {TF.DIM}Secondary:{TF.RESET} {secondary_npcs}")
    
    # Interactive elements
    interactive_objects = location.get('interactive_objects', '').strip()
    if interactive_objects:
        print(f"\n{TF.CYAN}Interactive Objects:{TF.RESET}")
        # Parse if it's a list format
        if interactive_objects.startswith('[') and interactive_objects.endswith(']'):
            try:
                import json
                obj_list = json.loads(interactive_objects.replace("'", '"'))
                for obj in obj_list:
                    print(f"  • {obj}")
            except:
                print(f"  {interactive_objects}")
        else:
            print(f"  {interactive_objects}")
    
    # Special properties
    special_properties = location.get('special_properties', '').strip()
    if special_properties:
        print(f"\n{TF.BRIGHT_YELLOW}Special Properties:{TF.RESET}")
        formatted_props = TF.format_terminal_text(special_properties, width=70)
        for line in formatted_props.split('\n'):
            print(f"  {line}")
    
    # Connected locations
    connected_locations = location.get('connected_locations', '').strip()
    if connected_locations:
        print(f"\n{TF.BRIGHT_CYAN}Connected Areas:{TF.RESET}")
        if connected_locations.startswith('[') and connected_locations.endswith(']'):
            try:
                import json
                loc_list = json.loads(connected_locations.replace("'", '"'))
                for loc in loc_list:
                    print(f"  → {loc}")
            except:
                print(f"  {connected_locations}")
        else:
            print(f"  {connected_locations}")
    
    print() # Empty line for spacing
    
    return {**state, 'status': 'ok', 'continue_loop': True}