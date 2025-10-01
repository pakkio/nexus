#!/usr/bin/env python3
"""
Enhanced Context Builder for Nexus NPCs
Builds comprehensive world context to make NPC responses more specific and mission-oriented
"""

import os
import json
from typing import Dict, List, Any, Optional
from db_manager import DbManager

class EnhancedContextBuilder:
    """Builds comprehensive context documents for NPCs to reference"""

    def __init__(self, db: DbManager):
        self.db = db
        self._context_cache = {}
        self._cache_timestamp = 0

    def _load_location_files(self) -> Dict[str, Any]:
        """Load all Location.*.txt files"""
        locations = {}
        for filename in os.listdir('.'):
            if filename.startswith('Location.') and filename.endswith('.txt'):
                area_name = filename.replace('Location.', '').replace('.txt', '')
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()
                        locations[area_name] = self._parse_location_file(content, area_name)
                except Exception as e:
                    print(f"Warning: Error loading {filename}: {e}")
        return locations

    def _parse_location_file(self, content: str, area_name: str) -> Dict[str, Any]:
        """Parse location file content into structured data"""
        location_data = {'area_name': area_name}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('#') or not line:
                continue

            if ':' in line and not line.startswith(' '):
                # Save previous section
                if current_section and current_content:
                    location_data[current_section] = '\n'.join(current_content).strip()

                # Start new section
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                if value:
                    location_data[key] = value
                    current_section = None
                    current_content = []
                else:
                    current_section = key
                    current_content = []
            elif current_section:
                current_content.append(line)

        # Save final section
        if current_section and current_content:
            location_data[current_section] = '\n'.join(current_content).strip()

        return location_data

    def build_geographic_context(self) -> str:
        """Build comprehensive geographic information about all areas and NPC locations"""
        locations = self._load_location_files()
        all_npcs = self.db.list_npcs_by_area()

        geographic_info = ["=== GEOGRAPHIC CONTEXT ==="]
        geographic_info.append("Complete world geography with NPC locations:\n")

        # Group NPCs by area
        npcs_by_area = {}
        for npc in all_npcs:
            area = npc.get('area', 'Unknown')
            if area not in npcs_by_area:
                npcs_by_area[area] = []
            npcs_by_area[area].append(npc.get('name', 'Unknown'))

        # Build area descriptions with NPCs
        for area_name, npc_list in npcs_by_area.items():
            # Get location details if available
            location_data = locations.get(area_name, {})
            description = location_data.get('Setting_Description', 'Area information not available')

            geographic_info.append(f"**{area_name.upper()}**")
            geographic_info.append(f"Description: {description}")
            geographic_info.append(f"NPCs here: {', '.join(npc_list)}")

            # Add special properties if available
            special_props = location_data.get('Special_Properties', '')
            if special_props:
                geographic_info.append(f"Special: {special_props}")

            # Add connections if available
            connections = location_data.get('Connected_Locations', '')
            if connections:
                geographic_info.append(f"Connected to: {connections}")

            geographic_info.append("")  # Blank line between areas

        return '\n'.join(geographic_info)

    def build_quest_chain_context(self) -> str:
        """Build quest progression information showing mission dependencies"""
        all_npcs = self.db.list_npcs_by_area()

        quest_info = ["=== MISSION PROGRESSION GUIDE ==="]
        quest_info.append("Exact quest information - use this to give ACCURATE answers:\n")

        # Parse quest chains from NPC data
        quest_chains = {}
        for npc in all_npcs:
            npc_name = npc.get('name', 'Unknown')
            area = npc.get('area', 'Unknown')

            # Extract quest info from NPC data with both old and new field names
            required_item = npc.get('required_item') or npc.get('needed_object') or npc.get('Required_Item', '')
            treasure = npc.get('treasure') or npc.get('Treasure', '')
            goal = npc.get('goal', '')
            required_source = npc.get('required_source') or npc.get('Required_Source', '')

            if required_item or treasure:
                quest_info.append(f"**{npc_name} (area: {area})**")
                if goal:
                    quest_info.append(f"  Mission: {goal}")
                if required_item:
                    quest_info.append(f"  ✓ Needs item: '{required_item}'")
                    if required_source:
                        # Parse source to make it clearer
                        source_parts = required_source.split('_')
                        if len(source_parts) >= 2:
                            source_npc = source_parts[0].capitalize()
                            source_area = ' '.join(source_parts[1:]).replace('_', ' ').title()
                            quest_info.append(f"  ✓ Get '{required_item}' from: {source_npc} in {source_area}")
                        else:
                            quest_info.append(f"  ✓ Source: {required_source}")
                if treasure:
                    quest_info.append(f"  ✓ Gives item: '{treasure}'")
                quest_info.append("")

        quest_info.append("\n" + "!"*60)
        quest_info.append("CRITICAL RULES - NEVER VIOLATE THESE:")
        quest_info.append("!"*60)
        quest_info.append("1. When player asks 'where can I find X item':")
        quest_info.append("   → Look for who GIVES that item in the list above")
        quest_info.append("   → Tell them the EXACT NPC name and area listed")
        quest_info.append("")
        quest_info.append("2. When player asks 'what does X NPC need':")
        quest_info.append("   → Look for that NPC's 'Needs item' field")
        quest_info.append("   → Tell them the EXACT item name listed")
        quest_info.append("")
        quest_info.append("3. NEVER GUESS OR INVENT quest info:")
        quest_info.append("   → Use ONLY information from the list above")
        quest_info.append("   → If not listed, say 'Non lo so con certezza'")
        quest_info.append("")
        quest_info.append("4. Example: 'minerale_ferro_antico'")
        quest_info.append("   → Check list: Garin NEEDS it, Boros in Mountain GIVES it")
        quest_info.append("   → Answer: 'Boros sulla Montagna ha il minerale'")
        quest_info.append("!"*60)

        return '\n'.join(quest_info)

    def build_object_location_context(self) -> str:
        """Build comprehensive object and item location mapping"""
        all_npcs = self.db.list_npcs_by_area()

        object_info = ["=== OBJECT & ITEM LOCATIONS ==="]
        object_info.append("Where to find important quest items and objects:\n")

        # Map items to their sources
        item_sources = {}
        item_receivers = {}

        for npc in all_npcs:
            npc_name = npc.get('name', 'Unknown')
            area = npc.get('area', 'Unknown')

            # Items this NPC gives
            treasure = npc.get('treasure') or npc.get('Treasure', '')
            if treasure:
                item_sources[treasure] = f"{npc_name} in {area}"

            # Items this NPC needs
            required_item = npc.get('needed_object') or npc.get('Required_Item', '')
            if required_item:
                item_receivers[required_item] = f"{npc_name} in {area}"

        # Build comprehensive item list
        all_items = set(list(item_sources.keys()) + list(item_receivers.keys()))

        for item in sorted(all_items):
            object_info.append(f"**{item}**")
            if item in item_sources:
                object_info.append(f"  Source: {item_sources[item]}")
            if item in item_receivers:
                object_info.append(f"  Needed by: {item_receivers[item]}")
            object_info.append("")

        # Add location-specific objects
        locations = self._load_location_files()
        object_info.append("\n**AREA OBJECTS & FEATURES:**")
        for area_name, location_data in locations.items():
            interactive_objects = location_data.get('Interactive_Objects', '')
            if interactive_objects:
                object_info.append(f"{area_name}: {interactive_objects}")

        return '\n'.join(object_info)

    def build_comprehensive_context(self, max_length: int = 2000) -> str:
        """Build complete enhanced context for NPC system prompts"""
        context_parts = [
            self.build_geographic_context(),
            self.build_quest_chain_context(),
            self.build_object_location_context()
        ]

        full_context = '\n\n'.join(context_parts)

        # Truncate if too long but preserve structure
        if len(full_context) > max_length:
            lines = full_context.split('\n')
            truncated_lines = []
            current_length = 0

            for line in lines:
                if current_length + len(line) + 1 <= max_length - 100:  # Leave room for ending
                    truncated_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break

            full_context = '\n'.join(truncated_lines) + '\n\n[Context truncated for length - refer to specific areas/NPCs as needed]'

        return full_context

def add_enhanced_context_to_prompt(original_prompt: str, db: DbManager) -> str:
    """Add enhanced context to existing NPC system prompt"""
    context_builder = EnhancedContextBuilder(db)
    enhanced_context = context_builder.build_comprehensive_context()

    # Insert enhanced context before the final game rules
    prompt_lines = original_prompt.split('\n')

    # Find insertion point (before behavior instructions)
    insertion_point = -1
    for i, line in enumerate(prompt_lines):
        if 'COMPORTAMENTO IMPORTANTE' in line or 'LINGUA' in line:
            insertion_point = i
            break

    if insertion_point == -1:
        # Fallback: add before last few lines
        insertion_point = len(prompt_lines) - 5

    # Insert enhanced context
    enhanced_lines = prompt_lines[:insertion_point] + \
                    ['', enhanced_context, ''] + \
                    prompt_lines[insertion_point:]

    return '\n'.join(enhanced_lines)

if __name__ == '__main__':
    # Test the context builder
    from db_manager import DbManager

    db = DbManager(use_mockup=True, mockup_dir='database')
    builder = EnhancedContextBuilder(db)

    print("=== TESTING ENHANCED CONTEXT BUILDER ===\n")

    print("1. Geographic Context:")
    print(builder.build_geographic_context()[:500] + "...\n")

    print("2. Quest Chain Context:")
    print(builder.build_quest_chain_context()[:500] + "...\n")

    print("3. Object Location Context:")
    print(builder.build_object_location_context()[:500] + "...\n")

    print("4. Full Context (truncated):")
    full_context = builder.build_comprehensive_context()
    print(f"Full context length: {len(full_context)} characters")
    print(full_context[:800] + "...")