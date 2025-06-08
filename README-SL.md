# Second Life/LSL Integration

The Eldoria AI-RPG engine includes comprehensive **Second Life/LSL integration** for in-world deployment and immersive VR experiences.

## LSL Interface Modules

*   **`lsl_main_gradio.py`** - Web interface with LSL HTTP header simulation
*   **`lsl_main_simulator.py`** - Command-line LSL simulator with SL context headers
*   **`game_system_api.py`** - Core API with LSL-compatible text formatting

## Second Life Command Generation

NPCs can generate contextual Second Life commands based on dialogue:

*   **Emotes:** `[emote=greet]` → Triggers gesture animations in SL
*   **Animations:** `[anim=sit]` → Controls avatar animations
*   **Object Lookups:** `[lookup=crystal]` → References in-world objects
*   **Text Display:** `[llSetText=Welcome!]` → Updates floating text

## LSL-Compatible Features

*   **Message Length Limits:** Automatic truncation for LSL string constraints (1000 chars)
*   **Header Processing:** Handles `X-SecondLife-Owner-Key`, `X-SecondLife-Region`, etc.
*   **Text Formatting:** Converts markdown to SL-compatible format:
    *   `**bold**` → `BOLD TEXT` (uppercase)
    *   `*italic*` → `[italic text]` (brackets)
*   **ANSI Code Removal:** Clean output for LSL HTTP responses

## Running LSL Interfaces

```bash
# Web interface with SL header simulation
python lsl_main_gradio.py

# Command-line LSL simulator
python lsl_main_simulator.py --mockup --player SL_Avatar_Name

# Test SL integration
python test_sl_integration.py
```

## Virtual World Deployment

Experience Eldoria directly in virtual worlds through **LSL integration**:

**🌐 Virtual World Deployment:**
* Deploy NPCs as interactive objects in Second Life
* Real-time conversations with AI-powered characters
* Contextual animations and gestures during dialogue
* In-world object interactions and references

**🎮 Enhanced Immersion Features:**
* **Avatar Context:** NPCs recognize your SL avatar name and region
* **Visual Commands:** NPCs trigger emotes, animations, and object interactions
* **Spatial Awareness:** References to nearby objects and locations
* **Dynamic Text:** Floating text updates based on story progression

**🎭 Example SL Experience:**
When talking to Lyra in the Sanctum, she might respond:
> *"The Veil remembers all who seek wisdom..."* 
> `[emote=bow][llSetText=Wisdom Seeker Welcomed][lookup=ancient_tome]`

This triggers: a bowing gesture, updates floating text, and highlights the ancient tome object in your virtual environment.

## Technical Implementation

### LSL HTTP Headers

The system recognizes and processes standard Second Life HTTP headers:

* `X-SecondLife-Owner-Key` - Avatar UUID of the object owner
* `X-SecondLife-Region` - Region name where the object is located
* `X-SecondLife-Object-Name` - Name of the requesting object
* `X-SecondLife-Object-Key` - UUID of the requesting object

### Message Format

LSL responses are automatically formatted for Second Life compatibility:

1. **Length Constraints:** Messages truncated to 1000 characters maximum
2. **Encoding:** UTF-8 encoding with LSL-safe character handling
3. **Command Parsing:** Special commands extracted and formatted for LSL processing

### Example LSL Script Integration

```lsl
// Example LSL script for Eldoria NPC integration
default {
    state_entry() {
        llSetText("Eldoria NPC - Click to interact", <1,1,1>, 1.0);
    }
    
    touch_start(integer total_number) {
        key avatar = llDetectedKey(0);
        string message = "Hello, " + llDetectedName(0) + "!";
        
        // Send request to Eldoria server
        llHTTPRequest("http://your-server.com/eldoria", [
            HTTP_METHOD, "POST",
            HTTP_MIMETYPE, "application/json"
        ], llList2Json(JSON_OBJECT, [
            "player", llDetectedName(0),
            "message", message,
            "avatar_key", avatar
        ]));
    }
    
    http_response(key request_id, integer status, list metadata, string body) {
        // Process Eldoria response
        list response = llJson2List(body);
        string npc_message = llList2String(response, 0);
        string commands = llList2String(response, 1);
        
        // Display NPC response
        llSay(0, npc_message);
        
        // Process any SL commands
        if (llSubStringIndex(commands, "[emote=") != -1) {
            // Trigger appropriate gesture/animation
        }
        if (llSubStringIndex(commands, "[llSetText=") != -1) {
            // Update floating text
        }
    }
}
```

## Development and Testing

### Local Testing

Use the LSL simulator for local development:

```bash
# Start with SL context simulation
python lsl_main_simulator.py --mockup --player TestAvatar

# Test with simulated headers
curl -X POST http://localhost:7860/chat \
  -H "X-SecondLife-Owner-Key: 12345678-1234-1234-1234-123456789abc" \
  -H "X-SecondLife-Region: Eldoria Realm" \
  -d '{"message": "Hello Lyra", "player": "TestAvatar"}'
```

### Integration Testing

Run the comprehensive SL integration test suite:

```bash
python test_sl_integration.py
```

This tests:
- LSL header processing
- Command generation
- Message formatting
- Response truncation
- Error handling

## Future Enhancements

* **Advanced Object Interactions:** Enhanced physics and object manipulation
* **Multi-Avatar Support:** Group conversations and shared experiences
* **Region-Specific Content:** Location-aware NPCs and storylines
* **Gesture Libraries:** Expanded animation and emote systems
* **HUD Integration:** In-world interface panels and status displays