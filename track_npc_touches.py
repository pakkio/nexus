#!/usr/bin/env python3
"""
Module to track NPC touches and handle timeout functionality.
This file maintains a record of when NPCs were last touched for 
implementing timeout behavior after 5 minutes of inactivity.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

class NPCTouchTracker:
    """Tracks when NPCs were last touched for timeout functionality."""
    
    def __init__(self, data_file: str = "npc_touch_data.json"):
        self.data_file = data_file
        self.touch_data = self._load_touch_data()
    
    def _load_touch_data(self) -> Dict[str, str]:
        """Load touch data from file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_touch_data(self):
        """Save touch data to file."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.touch_data, f, indent=2)
        except IOError as e:
            print(f"Error saving touch data: {e}")
    
    def record_touch(self, npc_name: str, area: str, avatar_key: str, avatar_name: str):
        """Record a touch event for an NPC."""
        timestamp = datetime.now().isoformat()
        key = f"{npc_name}:{area}"
        
        self.touch_data[key] = {
            "npc_name": npc_name,
            "area": area,
            "avatar_key": avatar_key,
            "avatar_name": avatar_name,
            "timestamp": timestamp,
            "status": "active"
        }
        
        self._save_touch_data()
        print(f"[NPCTouchTracker] Recorded touch for {npc_name} in {area} by {avatar_name}")
    
    def get_latest_touch(self, npc_name: str, area: str) -> Optional[Dict[str, Any]]:
        """Get the latest touch record for an NPC."""
        key = f"{npc_name}:{area}"
        return self.touch_data.get(key)
    
    def is_timeout_expired(self, npc_name: str, area: str, timeout_minutes: int = 5) -> bool:
        """Check if the timeout has expired for an NPC."""
        touch_record = self.get_latest_touch(npc_name, area)
        if not touch_record:
            return True  # If no record exists, consider it expired
        
        timestamp_str = touch_record.get("timestamp")
        if not timestamp_str:
            return True
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            timeout_duration = timedelta(minutes=timeout_minutes)
            current_time = datetime.now()
            
            return (current_time - timestamp) > timeout_duration
        except ValueError:
            return True  # If timestamp format is invalid, consider expired
    
    def reset_npc(self, npc_name: str, area: str):
        """Reset the touch record for an NPC."""
        key = f"{npc_name}:{area}"
        if key in self.touch_data:
            del self.touch_data[key]
            self._save_touch_data()
            print(f"[NPCTouchTracker] Reset touch data for {npc_name} in {area}")
    
    def get_active_npcs(self, timeout_minutes: int = 5) -> Dict[str, Dict[str, Any]]:
        """Get all NPCs that have been active within the timeout period."""
        active_npcs = {}
        current_time = datetime.now()
        
        for key, record in self.touch_data.items():
            timestamp_str = record.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if (current_time - timestamp).total_seconds() <= timeout_minutes * 60:
                        # Check if the status is still active
                        if record.get("status") == "active":
                            active_npcs[key] = record
                except ValueError:
                    continue
        
        return active_npcs

# Example usage
if __name__ == "__main__":
    # Demo usage
    tracker = NPCTouchTracker()
    
    # Record a touch (using object name as NPC name)
    tracker.record_touch("ObjectNameNPC", "DefaultArea", "avatar_key_123", "TestAvatar")
    
    # Check latest touch
    latest = tracker.get_latest_touch("ObjectNameNPC", "DefaultArea")
    print(f"Latest touch: {latest}")

    # Check if timeout expired (should be False immediately after recording)
    is_expired = tracker.is_timeout_expired("ObjectNameNPC", "DefaultArea")
    print(f"Is timeout expired: {is_expired}")
    
    # Get active NPCs
    active = tracker.get_active_npcs()
    print(f"Active NPCs: {active}")