# Testing Server Instructions

## Quick Brief Mode Test (Recommended for Token Efficiency)

For fast testing with minimal token usage:

```bash
# 1. Start server
pkill -f "python.*app.py" || true
nohup python app.py > server.log 2>&1 &
sleep 3 && curl -s http://localhost:5000/health

# 2. Create session and enable brief mode
curl -X POST http://localhost:5000/api/player/test-player/session -H "Content-Type: application/json" -d '{}' -s
curl -X POST http://localhost:5000/api/player/test-player/input -H "Content-Type: application/json" -d '{"input": "/brief on"}' -s

# 3. Test brief conversations (short responses)
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "test-player", "message": "What is this place?"}' -s

# 4. Test different NPC in brief mode
curl -X POST http://localhost:5000/api/player/test-player/input -H "Content-Type: application/json" -d '{"input": "/go ancient ruins"}' -s
curl -X POST http://localhost:5000/api/player/test-player/input -H "Content-Type: application/json" -d '{"input": "/talk Syra"}' -s
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "test-player", "message": "Tell me about your work"}' -s
```

## Starting the Server

1. **Kill any existing processes:**
   ```bash
   pkill -f "python.*app.py" || true
   ```

2. **Start Flask server in background:**
   ```bash
   nohup python app.py > server.log 2>&1 &
   ```

3. **Verify server is running:**
   ```bash
   ps aux | grep "python.*app.py" | grep -v grep
   curl -s http://localhost:5000/health
   ```

## Testing NPC Dialog

### 1. Create Player Session
```bash
curl -X POST http://localhost:5000/api/player/test-player/session \
  -H "Content-Type: application/json" \
  -d '{}' \
  -s
```

**Expected Response:**
```json
{
  "initial_state": {
    "credits": 220,
    "current_area": "Liminal Void",
    "current_npc_name": "Erasmus",
    "inventory": [],
    "player_id": "test-player",
    "status": "ok"
  },
  "session_created": true
}
```

### 2. Talk to Wise Guide (Erasmus)
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test-player", "message": "Hello Erasmus, what is this place?"}' \
  -s
```

### 3. Move to Different Area and Talk to Regular NPC

**Move to Ancient Ruins:**
```bash
curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/go ancient ruins"}' \
  -s
```

**Talk to Syra:**
```bash
curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/talk Syra"}' \
  -s
```

**Send message to Syra:**
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test-player", "message": "Hello Syra, tell me about your weaving work"}' \
  -s
```

## Available NPCs and Locations

### NPC List
- **Erasmus** (Liminal Void) - Wise Guide
- **Syra** (Ancient Ruins) - Regular NPC  
- **Lyra** (Sanctum of Whispers) - Regular NPC
- **Theron** (City) - Regular NPC
- **Cassian** (City) - Regular NPC
- **Irenna** (City) - Regular NPC
- **Elira** (Forest) - Regular NPC
- **Boros** (Mountain) - Regular NPC
- **Meridia** (Nexus of Paths) - Regular NPC
- **Jorin** (Tavern) - Regular NPC
- **Garin** (Village) - Regular NPC
- **Mara** (Village) - Regular NPC

### Get All NPCs
```bash
curl -s http://localhost:5000/api/game/npcs
```

## Useful Endpoints

### Health Check
```bash
curl -s http://localhost:5000/health
```

### Player State
```bash
curl -s http://localhost:5000/api/player/test-player/state
```

### Player Profile
```bash
curl -s http://localhost:5000/api/player/test-player/profile
```

### Player Inventory
```bash
curl -s http://localhost:5000/api/player/test-player/inventory
```

## Debugging

### Check Server Logs
```bash
tail -50 server.log
```

### Check for Debug Output
```bash
grep -A 10 "LLM PROMPT DEBUG" server.log
```

### Monitor Real-time Logs
```bash
tail -f server.log
```

## Testing Brief Mode (Token-Efficient Testing)

Brief mode reduces NPC verbosity for faster testing and lower token usage.

### 1. Enable Brief Mode
```bash
curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/brief on"}' \
  -s
```

**Expected Response:**
```json
{
  "system_messages": ["✓ Modalità Brief ATTIVATA - Gli NPC risponderanno in modo conciso ed essenziale."]
}
```

### 2. Test Brief Mode Conversations

**Test with Erasmus (Wise Guide):**
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test-player", "message": "What is this place?"}' \
  -s
```

**Expected:** Concise 2-3 sentence response instead of verbose explanation.

**Test with Syra (Regular NPC):**
```bash
# First move to Ancient Ruins and talk to Syra
curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/go ancient ruins"}' \
  -s

curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/talk Syra"}' \
  -s

# Test brief conversation
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test-player", "message": "Tell me about your work"}' \
  -s
```

**Expected:** Short, direct response about weaving work (3-4 sentences max).

### 3. Test Brief Mode Toggle

**Disable Brief Mode:**
```bash
curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/brief off"}' \
  -s
```

**Test Verbose Response:**
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test-player", "message": "Can you explain more about memory patterns?"}' \
  -s
```

**Expected:** Detailed, multi-paragraph response with extensive explanations.

### 4. Brief Mode Persistence Test

Brief mode should persist across different NPCs:

```bash
# Enable brief mode
curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/brief on"}' \
  -s

# Test with first NPC (Syra)
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test-player", "message": "Quick question about weaving"}' \
  -s

# Switch to different NPC and test persistence
curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/go city"}' \
  -s

curl -X POST http://localhost:5000/api/player/test-player/input \
  -H "Content-Type: application/json" \
  -d '{"input": "/talk Cassian"}' \
  -s

curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test-player", "message": "Hello, what do you do here?"}' \
  -s
```

**Expected:** Both NPCs should respond concisely without needing to re-enable brief mode.

## Expected NPC Response Format

Successful chat responses include:
- `npc_response`: The NPC's dialog response
- `current_npc`: Current NPC name
- `current_area`: Current area name
- `sl_commands`: Second Life commands generated
- `llm_stats`: Performance statistics
- `system_messages`: Any system notifications

### Brief Mode Response Characteristics
- **Brief ON**: 1-4 sentences, direct answers, minimal narrative flourish
- **Brief OFF**: Full narrative responses with detailed explanations, examples, and atmospheric descriptions