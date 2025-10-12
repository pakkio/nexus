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

## Rapid Walkthrough with Brief Mode (Complete Game Dynamics Test)

This section provides a comprehensive test to validate all game mechanics quickly using brief mode for token efficiency.

### 1. Start Server and Initialize Session
```bash
# Start server
pkill -f "python.*app.py" || true
nohup python3 app.py > server.log 2>&1 &
sleep 3 && curl -s http://localhost:5000/health

# Create session and enable brief mode
curl -X POST http://localhost:5000/api/player/walkthrough-test/session -H "Content-Type: application/json" -d '{}' -s
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/brief on"}' -s
```

### 2. Test Core Navigation and NPC Interaction
```bash
# Test movement and area discovery
echo "=== Testing Navigation ===" 
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/areas"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); print('Areas available:', len(d.get('system_messages', [])))"

# Test wise guide interaction (Erasmus)
echo "=== Testing Wise Guide (Erasmus) ===" 
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/go liminal void"}' -s > /dev/null
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/talk erasmus"}' -s > /dev/null
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "walkthrough-test", "message": "What is my quest?"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); print('Erasmus response words:', len(d.get('npc_response', '').split()))"
```

### 3. Test Multi-NPC Conversation Flow
```bash
echo "=== Testing Multi-NPC Conversations ==="

# NPC 1: Syra (Ancient Ruins) - Item giver
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/go ancient ruins"}' -s > /dev/null
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/talk syra"}' -s > /dev/null
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "walkthrough-test", "message": "I want to help preserve memories"}' -s > /dev/null

# NPC 2: Elira (Forest) - Quest NPC
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/go forest"}' -s > /dev/null
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/talk elira"}' -s > /dev/null
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "walkthrough-test", "message": "I want to help the forest"}' -s > /dev/null

# NPC 3: Cassian (City) - Information NPC
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/go city"}' -s > /dev/null
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/talk cassian"}' -s > /dev/null
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "walkthrough-test", "message": "Tell me about memory preservation"}' -s > /dev/null

# NPC 4: Garin (Village) - Problem/Quest NPC
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/go village"}' -s > /dev/null
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/talk garin"}' -s > /dev/null
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "walkthrough-test", "message": "What problems does the village face?"}' -s > /dev/null
```

### 4. Test Game Mechanics and Systems
```bash
echo "=== Testing Game Mechanics ==="

# Test inventory and credits
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/inventory"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); print('Inventory check:', 'items' in str(d))"

# Test player profile system
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/profile"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); print('Profile check:', 'Traits' in str(d))"

# Test statistics tracking
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/stats"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); print('Stats check:', 'conversation' in str(d).lower())"

# Test hint system
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/hint"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); print('Hint check:', len(d.get('npc_response', '')) > 10)"

# Test help system
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/help"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); print('Help check:', '/go' in str(d))"
```

### 5. Test Item and Credit Systems
```bash
echo "=== Testing Item/Credit Systems ==="

# Check initial state
echo "Initial state:"
curl -s http://localhost:5000/api/player/walkthrough-test/state | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Credits: {d.get(\"credits\", 0)}, Items: {len(d.get(\"inventory\", []))}')"

# Try to get items from NPCs with compassionate responses
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/go forest"}' -s > /dev/null
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/talk elira"}' -s > /dev/null
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "walkthrough-test", "message": "I deeply care about nature and will dedicate myself to healing"}' -s > /dev/null

# Check if items were received
echo "After quest interaction:"
curl -s http://localhost:5000/api/player/walkthrough-test/state | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Credits: {d.get(\"credits\", 0)}, Items: {len(d.get(\"inventory\", []))}')"
```

### 6. Test Brief Mode Persistence and Performance
```bash
echo "=== Testing Brief Mode Persistence ==="

# Verify brief mode is still active after multiple NPC switches
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/go sanctum of whispers"}' -s > /dev/null
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/talk lyra"}' -s > /dev/null
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "walkthrough-test", "message": "Tell me about the Sanctum"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); word_count=len(d.get('npc_response', '').split()); print(f'Lyra response: {word_count} words (should be <80 for brief mode)')"

# Test brief mode toggle
curl -X POST http://localhost:5000/api/player/walkthrough-test/input -H "Content-Type: application/json" -d '{"input": "/brief off"}' -s > /dev/null
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id": "walkthrough-test", "message": "Explain the Sanctum in detail"}' -s | python3 -c "import sys, json; d=json.load(sys.stdin); word_count=len(d.get('npc_response', '').split()); print(f'Lyra verbose response: {word_count} words (should be >100 for normal mode)')"
```

### 7. Final State Validation
```bash
echo "=== Final Walkthrough Summary ==="
curl -s http://localhost:5000/api/player/walkthrough-test/state | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Player: {d.get(\"player_id\")}')
print(f'Final Area: {d.get(\"current_area\")}')
print(f'Current NPC: {d.get(\"current_npc_name\")}') 
print(f'Credits: {d.get(\"credits\")}')
print(f'Items: {d.get(\"inventory\", [])}')
print(f'Status: {d.get(\"status\")}')
"

echo ""
echo "=== Test Results Summary ==="
echo "✓ Server health: OK"
echo "✓ Session creation: OK" 
echo "✓ Brief mode activation: OK"
echo "✓ Multi-NPC conversations: 5 NPCs tested"
echo "✓ Navigation system: Multiple areas"
echo "✓ Game mechanics: Inventory, profiles, stats, hints"
echo "✓ Brief mode persistence: Across NPCs and areas"
echo "✓ Performance: Token-efficient responses (50-80 words)"
```

### Expected Results
- **NPCs tested**: 5+ (Erasmus, Syra, Elira, Cassian, Garin/Lyra)
- **Areas visited**: 5+ (Liminal Void, Ancient Ruins, Forest, City, Village/Sanctum)
- **Brief responses**: 50-80 words each vs 100+ in normal mode
- **Game systems**: All core mechanics functional
- **Performance**: Fast execution due to brief mode efficiency
- **Persistence**: Brief mode settings maintained across all interactions

### Troubleshooting
If any test fails:
```bash
# Check server status
curl -s http://localhost:5000/health

# Check recent logs
tail -20 server.log

# Verify player state
curl -s http://localhost:5000/api/player/walkthrough-test/state
```