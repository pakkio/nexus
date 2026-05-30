# Nexus RPG Dialog Example via curl

This document shows a complete dialog session with the Nexus RPG API using curl commands.

## Server Information

**Base URL:** http://localhost:5000
**Server Status:** Running (PID: 1833622)
**Version:** 2.0.0

---

## Step 1: Check Server Health

```bash
curl -X GET http://localhost:5000/health
```

**Response:**
```json
{
  "app_last_modified": "2025-12-07 12:18:37",
  "last_change": "Major update: version bump, see release notes.",
  "process_id": 1833622,
  "server_time": "2025-12-17 21:46:23",
  "service": "nexus-api",
  "status": "healthy",
  "uptime": "n/a",
  "version": "2.0.0"
}
```

---

## Step 2: List Available NPCs

```bash
curl -s -X GET "http://localhost:5000/api/game/npcs" | python3 -m json.tool
```

**Response (partial):**
```json
{
  "area": null,
  "npcs": [
    {
      "area": "Ancient Ruins",
      "code": "ancientruins.syra",
      "name": "Syra",
      "role": "Eco Residuo, Tessitrice Incompleta"
    },
    {
      "area": "Forest",
      "code": "forest.elira",
      "name": "Elira",
      "role": "Guardiana del Nodo Naturale, Interprete dei Sussurri"
    },
    {
      "area": "Mountain",
      "code": "mountain.boros",
      "name": "Boros",
      "role": "Primo Monaco dell'Equilibrio, Testimone delle Ere"
    }
  ]
}
```

---

## Step 3: Arrive at NPC (Sense Endpoint)

The `/sense` endpoint simulates arriving at an NPC location and receiving an initial greeting.

```bash
curl -s -X POST http://localhost:5000/sense \
  -H "Content-Type: application/json" \
  -d '{
    "player_id": "TestPlayer",
    "display_name": "Alice",
    "npcname": "Elira",
    "area": "Forest"
  }'
```

**Response:**
```json
{
  "current_area": "Forest",
  "display_name": "Alice",
  "npc_name": "Elira",
  "npc_response": "*Elira nota Alice* Salve, viandante.",
  "player_id": "TestPlayer",
  "sl_commands": "[lookup=healing_herbs;llSetText=Elira nota Alice Salve, viandante.;anim=STAND TALK 1]",
  "system_messages": []
}
```

---

## Step 4: First Chat Message

```bash
curl -s -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "player_id": "TestPlayer",
    "display_name": "Alice",
    "message": "Ciao Elira, puoi parlarmi della foresta?",
    "npc_name": "Elira",
    "area": "Forest"
  }'
```

**Response:**
```json
{
  "current_area": "Forest",
  "current_npc": "Elira",
  "display_name": "Alice",
  "llm_stats": {
    "command_interpretation": {
      "last_call_time_ms": 861,
      "last_tokens_in": 2626,
      "last_tokens_out": 110,
      "model": "google/gemini-2.5-flash",
      "session_calls": 43,
      "session_time_ms": 52079,
      "tokens_per_sec": 127.8
    },
    "dialogue": {
      "last_call_time_ms": 1461,
      "last_tokens_in": 5164,
      "last_tokens_out": 57,
      "model": "google/gemini-2.5-flash",
      "session_calls": 2,
      "session_time_ms": 3576,
      "tokens_per_sec": 39.0
    },
    "summary": {
      "active_calls": 2,
      "performance_note": "Response time optimized with async profile analysis",
      "total_llm_time_ms": 2322
    }
  },
  "npc_name": "Elira",
  "npc_response": "[CONVERSATION_RESUMED: Player returned to the conversation with Elira.]\nLa foresta e' un respiro, Cercastorie. Ogni albero qui ricorda il momento in cui un Tessitore scelse di non esistere piu'. Riesci a sentire quell'eco di pace?\n\n[Hint: Posso essere convinta con parole sincere di compassione, oppure portandomi una Pozione di Guarigione da Mara]",
  "player_id": "TestPlayer",
  "player_message": "Ciao Elira, puoi parlarmi della foresta?",
  "sl_commands": "[lookup=ancient_tree;llSetText=La foresta e' un respiro. Senti leco di pace?;anim=TALK 6]",
  "system_messages": [
    "Elira > [CONVERSATION_RESUMED: Player returned to the conversation with Elira.]\nLa foresta è un respiro, Cercastorie. Ogni albero qui ricorda il momento in cui un Tessitore scelse di non esistere più. Riesci a sentire quell'eco di pace?\n\n[Hint: Posso essere convinta con parole sincere di compassione, oppure portandomi una Pozione di Guarigione da Mara]"
  ]
}
```

**NPC Says:** "La foresta è un respiro, Cercastorie. Ogni albero qui ricorda il momento in cui un Tessitore scelse di non esistere più. Riesci a sentire quell'eco di pace?"

---

## Step 5: Continue Conversation

```bash
curl -s -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "player_id": "TestPlayer",
    "display_name": "Alice",
    "message": "Si, sento qualcosa di speciale. Cosa sono i Tessitori di cui parli?"
  }'
```

**Response:**
```json
{
  "current_area": "Forest",
  "current_npc": "Elira",
  "display_name": "Alice",
  "llm_stats": {
    "command_interpretation": {
      "last_call_time_ms": 926,
      "last_tokens_in": 2631,
      "last_tokens_out": 85,
      "model": "google/gemini-2.5-flash",
      "session_calls": 44,
      "session_time_ms": 53006,
      "tokens_per_sec": 91.8
    },
    "dialogue": {
      "last_call_time_ms": 1461,
      "last_tokens_in": 5164,
      "last_tokens_out": 57,
      "model": "google/gemini-2.5-flash",
      "session_calls": 2,
      "session_time_ms": 3576,
      "tokens_per_sec": 39.0
    },
    "summary": {
      "active_calls": 2,
      "performance_note": "Response time optimized with async profile analysis",
      "total_llm_time_ms": 2387
    }
  },
  "npc_name": null,
  "npc_response": "[CONVERSATION_RESUMED: Player returned to the conversation with Elira.]\nI Tessitori... erano coloro che intrecciavano la trama stessa dell'esistenza. Qui, in questa foresta, alcuni di loro scelsero di dissolversi nel Velo, per proteggere cio' che amavano. La loro memoria e' la linfa di questi alberi.\n\n[Hint: Posso essere convinta con parole sincere di compassione, oppure portandomi una Pozione di Guarigione da Mara]",
  "player_id": "TestPlayer",
  "player_message": "Si, sento qualcosa di speciale. Cosa sono i Tessitori di cui parli?",
  "sl_commands": "[lookup=sacred_grove;llSetText=I Tessitori si fusero nel Velo qui. La loro memoria e' la linfa degli alberi.;anim=TALK 6]",
  "system_messages": [
    "Elira > [CONVERSATION_RESUMED: Player returned to the conversation with Elira.]\nI Tessitori... erano coloro che intrecciavano la trama stessa dell'esistenza. Qui, in questa foresta, alcuni di loro scelsero di dissolversi nel Velo, per proteggere ciò che amavano. La loro memoria è la linfa di questi alberi.\n\n[Hint: Posso essere convinta con parole sincere di compassione, oppure portandomi una Pozione di Guarigione da Mara]"
  ]
}
```

**NPC Says:** "I Tessitori... erano coloro che intrecciavano la trama stessa dell'esistenza. Qui, in questa foresta, alcuni di loro scelsero di dissolversi nel Velo, per proteggere ciò che amavano. La loro memoria è la linfa di questi alberi."

---

## Key API Endpoints

### Chat Endpoints
- **POST /sense** - Arrive at NPC and get initial greeting
- **POST /api/chat** - Send message and receive NPC response
- **POST /leave** - Leave conversation and save state

### Information Endpoints
- **GET /api/game/npcs** - List all NPCs
- **GET /api/player/{player_id}/inventory** - Check inventory
- **GET /api/player/{player_id}/profile** - View player profile
- **GET /api/player/{player_id}/conversation** - Get conversation history

### Admin Endpoints
- **POST /reset** - Reset database (requires key: "1234")
- **GET /health** - Server health check

---

## Understanding the Response

Each chat response includes:

1. **npc_response** - The actual dialog text from the NPC (normalized for LSL)
2. **sl_commands** - Second Life commands for animations/effects
3. **llm_stats** - Performance metrics showing AI response times
4. **system_messages** - Game system notifications
5. **current_area** - Player's current location
6. **current_npc** - NPC currently talking to

---

## Dialog Flow Summary

**Player (Alice):** Arrives at Forest to meet Elira
**Elira:** *Salve, viandante.*

**Alice:** "Ciao Elira, puoi parlarmi della foresta?"
**Elira:** "La foresta è un respiro, Cercastorie. Ogni albero qui ricorda il momento in cui un Tessitore scelse di non esistere più. Riesci a sentire quell'eco di pace?"

**Alice:** "Si, sento qualcosa di speciale. Cosa sono i Tessitori di cui parli?"
**Elira:** "I Tessitori... erano coloro che intrecciavano la trama stessa dell'esistenza. Qui, in questa foresta, alcuni di loro scelsero di dissolversi nel Velo, per proteggere ciò che amavano. La loro memoria è la linfa di questi alberi."

---

## Notes

- The system uses **async profile analysis** to optimize response times
- All text is **normalized for LSL** (Second Life scripting language) with accented characters converted
- The AI uses **Google Gemini 2.5 Flash** model for dialogue generation
- Conversation history is automatically saved and can be resumed
- Response times average 1-2 seconds including LLM processing
