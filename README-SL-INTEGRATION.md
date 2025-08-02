# Second Life/OpenSim Integration Guide

## Overview

The Nexus/Eldoria RPG system provides comprehensive integration with Second Life and OpenSim virtual worlds through LSL (Linden Scripting Language) scripts and optimized API endpoints. This integration enables real-time AI-powered NPC interactions within virtual environments.

## Features

- **Real-time NPC Conversations**: Chat directly with AI NPCs in Second Life/OpenSim
- **Automatic Avatar Detection**: NPCs detect and greet approaching avatars
- **Memory Persistence**: Conversations are saved and remembered across sessions
- **UTF-8 Text Normalization**: Proper display of accented characters in SL/OpenSim
- **SL Commands Integration**: NPCs can trigger animations, emotes, and object interactions
- **Performance Optimized**: Sub-3 second response times for smooth gameplay

## Quick Start

### 1. Server Setup

Start the Nexus server:
```bash
python app.py
# Server runs on http://localhost:5000 by default
```

### 2. LSL Script Deployment

1. Rez a prim in Second Life/OpenSim
2. Copy the contents of `nexus_eldoria_tester.lsl` into the prim's script
3. Configure the server URL in the script:
   ```lsl
   string NEXUS_SERVER_URL = "http://your-server:5000";
   ```
4. Save and run the script

### 3. Basic Interaction

- **Touch the object** to simulate arrival (NPC will greet you)
- **Chat in public channel** to talk with the NPC
- **Touch again** to simulate departure
- Use **`/leave`** command for manual departure

## API Endpoints

### `/sense` - Avatar Arrival
Handles avatar detection and initial NPC greetings.

**Request:**
```json
{
  "name": "AvatarName",
  "npcname": "mara",
  "area": "Village"
}
```

**Response:**
```json
{
  "npc_response": "Greeting message from NPC",
  "npc_name": "Mara",
  "player_name": "AvatarName",
  "current_area": "Village",
  "sl_commands": "[lookup=item;llSetText=message;emote=gesture;anim=action]"
}
```

### `/api/chat` - NPC Conversation
Processes chat messages and generates NPC responses.

**Request:**
```json
{
  "player_name": "AvatarName",
  "message": "Hello!",
  "npc_name": "mara",
  "area": "Village"
}
```

**Response:**
```json
{
  "npc_response": "NPC reply with normalized text",
  "sl_commands": "[lookup=item;llSetText=message;emote=gesture;anim=action]",
  "player_name": "AvatarName",
  "npc_name": "mara",
  "current_area": "Village",
  "llm_stats": { /* Performance statistics */ }
}
```

### `/leave` - Avatar Departure
Handles avatar departure and conversation cleanup.

**Request:**
```json
{
  "name": "AvatarName",
  "npcname": "mara",
  "area": "Village"
}
```

## LSL Script Configuration

### Key Parameters

```lsl
string NEXUS_SERVER_URL = "http://localhost:5000";  // Your server URL
string NPC_NAME = "mara";                           // NPC to interact with
string AREA_NAME = "Village";                       // Game area
float SENSOR_RANGE = 5.0;                          // Detection range (meters)
float SENSOR_REPEAT = 3.0;                         // Scan frequency (seconds)
integer MAX_RESPONSE_LENGTH = 0;                   // Text limit (0 = unlimited)
```

### Avatar Session Management

The script automatically tracks:
- Avatar arrivals/departures via sensor detection
- Touch-based manual control
- Chat session states (active/inactive)
- Performance statistics

### Commands

- **`/stats`**: Display performance statistics
- **`/leave`**: Manual departure command
- **`/profile`**: View player psychological profile
- **Any other `/command`**: Sent to NPC for processing

## Text Normalization

The system automatically converts UTF-8 characters for LSL compatibility:

| Input | Output | Input | Output |
|-------|--------|-------|--------|
| à     | a'     | À     | A'     |
| è     | e'     | È     | E'     |
| ì     | i'     | Ì     | I'     |
| ò     | o'     | Ò     | O'     |
| ù     | u'     | Ù     | U'     |
| ç     | c'     | Ç     | C'     |

## SL Commands Format

NPCs can generate Second Life-specific commands:

```
[lookup=object_name;llSetText=hover_text;emote=gesture_name;anim=animation_name]
```

### Command Types

- **`lookup`**: Reference to in-world objects NPCs can interact with
- **`llSetText`**: Floating text to display above the object
- **`emote`**: Gesture animations for NPCs
- **`anim`**: Character animations and actions

## Performance Metrics

Expected performance benchmarks:
- **Arrival responses**: ~2.9 seconds average
- **Chat responses**: ~0.88 seconds average  
- **Departure responses**: ~0.012 seconds average
- **HTTP timeout**: 2 minutes maximum

## NPC Configuration

NPCs are defined in `NPC.<area>.<name>.txt` files with SL-specific fields:

```
Name: Mara
Area: Village
Role: Erborista della Memoria
Motivation: Preservare la conoscenza delle erbe prima che svanisca
Goal: Creare elisir contro i Sussurri dell'Oblio
Emotes: sorriso_compassionevole, cipiglio_preoccupato, gesto_protettivo
Animations: curare_giardino, preparare_pozioni, esaminare_piante
Lookup: giardino_erbe, mortaio_pestello, collezione_semi
Llsettext: Può mostrare ricette erboristiche, guide medicinali
```

## Error Handling

### Common Issues

1. **HTTP 500 Errors**: Check server logs for specific error details
2. **Connection Timeouts**: Verify server URL and network connectivity
3. **UTF-8 Display Issues**: Ensure text normalization is enabled
4. **Infinite Loops**: Update to latest LSL script version

### Debugging

Enable verbose logging in the LSL script:
```lsl
llOwnerSay("Debug: " + message);  // Add debug output
```

Check server logs for detailed error information:
```bash
tail -f server.log  # Monitor real-time logs
```

## Advanced Configuration

### Custom NPCs

1. Create new NPC file: `NPC.<area>.<npc_name>.txt`
2. Define SL-specific fields (Emotes, Animations, Lookup, Llsettext)
3. Update LSL script NPC_NAME parameter
4. Restart server to load new NPC

### Multiple Areas

Configure different areas by changing:
```lsl
string AREA_NAME = "YourArea";
```

Ensure corresponding NPC files exist for the target area.

### Performance Tuning

Adjust sensor parameters for optimal performance:
```lsl
float SENSOR_RANGE = 10.0;     // Larger detection area
float SENSOR_REPEAT = 1.0;     // More frequent scanning
```

## Troubleshooting

### Script Won't Start
- Check syntax errors in LSL editor
- Verify all required functions are present
- Ensure proper URL format (include http://)

### NPC Doesn't Respond
- Verify server is running on specified port
- Check NPC name matches exactly (case-sensitive)
- Confirm area configuration is correct

### Text Corruption
- Update to latest server version with text normalization
- Verify UTF-8 encoding in NPC files
- Check for special characters in responses

### Memory Issues
- Monitor script memory usage in LSL
- Reduce MAX_RESPONSE_LENGTH if needed
- Clear old conversation data periodically

## API Integration Examples

### Sense Endpoint Test
```bash
curl -X POST http://localhost:5000/sense \
  -H "Content-Type: application/json" \
  -d '{"name":"TestUser","npcname":"mara","area":"Village"}'
```

### Chat Endpoint Test
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"player_name":"TestUser","message":"Hello","npc_name":"mara","area":"Village"}'
```

## Contributing

When modifying the integration:

1. Test thoroughly in both Second Life and OpenSim
2. Verify UTF-8 character handling
3. Check performance impact
4. Update documentation
5. Test error conditions and recovery

## License

This integration is part of the Nexus/Eldoria RPG system. See main project license for details.