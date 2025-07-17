# Nexus Flask API

RESTful API for the Nexus AI-powered text-based RPG engine.

## Quick Start

1. Install dependencies:
```bash
poetry install
```

2. Set up environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the Flask API:
```bash
python app.py
```

4. Test the API:
```bash
python test_api.py
```

## Configuration

Environment variables for customization:

- `NEXUS_USE_MOCKUP`: Use local database files (default: true)
- `NEXUS_MOCKUP_DIR`: Directory for local database files (default: database)
- `NEXUS_MODEL_NAME`: LLM model name (default: google/gemma-2-9b-it:free)
- `NEXUS_PROFILE_MODEL_NAME`: Model for profile analysis (optional)
- `NEXUS_WISE_GUIDE_MODEL_NAME`: Model for wise guide selection (optional)
- `NEXUS_DEBUG_MODE`: Enable debug mode (default: false)
- `NEXUS_PORT`: API port (default: 5000)
- `FLASK_DEBUG`: Enable Flask debug mode (default: false)

## API Endpoints

### Health Check
- `GET /health` - Check API health

### Player Session Management
- `POST /api/player/{player_id}/session` - Create/initialize player session
- `DELETE /api/player/{player_id}/session` - Close player session

### Game Interaction
- `POST /api/player/{player_id}/input` - Process player input
  ```json
  {"input": "/help"}
  ```
- `POST /api/chat/{player_id}` - Direct chat with NPC
  ```json
  {"message": "Hello there!"}
  ```

### Player Data
- `GET /api/player/{player_id}/state` - Get current player state
- `GET /api/player/{player_id}/profile` - Get psychological profile
- `GET /api/player/{player_id}/inventory` - Get inventory and credits
- `GET /api/player/{player_id}/conversation` - Get conversation history

### Game Data
- `GET /api/game/storyboard` - Get game storyboard
- `GET /api/game/areas` - Get all areas
- `GET /api/game/npcs` - Get all NPCs (optional ?area=name filter)

### System
- `GET /api/commands` - Get available commands
- `POST /api/admin/reload` - Reload game data (admin)

## Game Commands

### Navigation
- `/go <area>` - Move to a different area
- `/talk <npc_name>` - Start conversation with an NPC
- `/exit` - Exit current conversation

### Information
- `/help` - Show help text
- `/who` - List NPCs in current area
- `/whereami` - Show current location
- `/inventory` - Show your inventory
- `/profile` - Show your psychological profile

### Interaction
- `/give <item>` - Give an item to current NPC
- `/hint` - Get guidance from wise guide
- `/endhint` - End hint mode

### System
- `/reset` - Reset your profile
- `/reload` - Reload game data

## Response Format

All API responses include:

```json
{
  "player_id": "player_name",
  "npc_response": "NPC dialogue text",
  "system_messages": ["Status messages"],
  "current_area": "area_name",
  "current_npc_name": "npc_name",
  "inventory": ["item1", "item2"],
  "credits": 100,
  "profile_summary": "Player traits and analysis",
  "status": "ok"
}
```

## Usage Examples

### Python Client
```python
import requests

# Create session
response = requests.post("http://localhost:5000/api/player/alice/session")

# Send command
response = requests.post("http://localhost:5000/api/player/alice/input", 
                        json={"input": "/help"})

# Chat with NPC
response = requests.post("http://localhost:5000/api/chat/alice", 
                        json={"message": "Tell me about this place"})
```

### JavaScript Client
```javascript
// Create session
fetch('http://localhost:5000/api/player/alice/session', {
  method: 'POST'
})

// Send command
fetch('http://localhost:5000/api/player/alice/input', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({input: '/help'})
})

// Chat with NPC
fetch('http://localhost:5000/api/chat/alice', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({message: 'Hello!'})
})
```

### cURL Examples
```bash
# Health check
curl http://localhost:5000/health

# Create session
curl -X POST http://localhost:5000/api/player/test/session

# Send command
curl -X POST http://localhost:5000/api/player/test/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/help"}'

# Chat
curl -X POST http://localhost:5000/api/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello there!"}'
```

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Success
- 400: Bad Request (missing/invalid parameters)
- 500: Internal Server Error

Error responses include:
```json
{
  "error": "Error description",
  "message": "Detailed error message"
}
```

## Features

- **Multi-player support**: Each player has their own session
- **AI-powered NPCs**: Conversations with LLM-generated responses
- **Psychological profiling**: Dynamic player trait analysis
- **Persistent state**: Game state saved between sessions
- **Rich inventory system**: Items and credits tracking
- **Hint system**: AI-powered guidance
- **CORS enabled**: Cross-origin requests supported
- **Comprehensive logging**: Full request/response logging

## Architecture

The API is built on top of the existing Nexus game system:
- `GameSystem`: Multi-player session manager
- `_SinglePlayerGameSystem`: Individual player logic
- `DbManager`: Database abstraction layer
- `ChatSession`: Conversation management
- `PlayerProfile`: Psychological analysis

## Development

Run tests:
```bash
python test_api.py
```

Enable debug mode:
```bash
export FLASK_DEBUG=true
export NEXUS_DEBUG_MODE=true
python app.py
```