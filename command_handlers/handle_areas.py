from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action

def handle_areas(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    _add_profile_action(state, "Used /areas command")
    
    # Get areas from NPCs (legacy support)
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TF)
    known_areas_from_npcs = session_utils.get_known_areas_from_list(all_known_npcs)
    
    # Get locations from new system
    locations = db.list_locations()
    
    # Combine and show both NPC areas and Location data
    all_areas = set()
    if known_areas_from_npcs:
        all_areas.update([area.lower() for area in known_areas_from_npcs])
    
    location_map = {}
    for location in locations:
        location_name = location.get('name', '').strip()
        location_id = location.get('id', '').strip()
        if location_name:
            all_areas.add(location_name.lower())
            location_map[location_name.lower()] = location
    
    if not all_areas:
        print(f"{TF.YELLOW}No known areas found.{TF.RESET}")
    else:
        print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}Available Areas:{TF.RESET}")
        
        # Show areas from NPCs first
        if known_areas_from_npcs:
            for area_name in sorted(known_areas_from_npcs):
                area_lower = area_name.lower()
                if area_lower in location_map:
                    location = location_map[area_lower]
                    access_info = f" ({location.get('access_level', 'Unknown Access')})" if location.get('access_level') else ""
                    print(f" {TF.CYAN}➢ {area_name}{TF.RESET}{TF.DIM}{access_info}{TF.RESET}")
                else:
                    print(f" {TF.CYAN}➢ {area_name}{TF.RESET}")
        
        # Show any additional locations not covered by NPC areas
        for location in sorted(locations, key=lambda x: x.get('name', '').lower()):
            location_name = location.get('name', '').strip()
            if location_name and location_name.lower() not in [area.lower() for area in (known_areas_from_npcs or [])]:
                access_info = f" ({location.get('access_level', 'Unknown Access')})" if location.get('access_level') else ""
                print(f" {TF.CYAN}➢ {location_name}{TF.RESET}{TF.DIM}{access_info}{TF.RESET}")
                
        print(f"\n{TF.DIM}Use '/describe <area>' for detailed area information.{TF.RESET}")
        
    return {**state, 'status': 'ok', 'continue_loop': True}