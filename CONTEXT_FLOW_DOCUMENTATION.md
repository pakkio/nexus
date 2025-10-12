# Complete NPC Context Flow Documentation

## YES - System is Using All Three Context Sources! ✅

When an NPC conversation starts, the system builds context from **THREE sources**:

### 1. NPC Personalized Prefix (NEW) ✅
**File**: `NPC_PREFIX.<area>.<name>.txt`
**Loaded by**: `_load_npc_narrative_prefix()` in `session_utils.py:88-112`
**When**: At system prompt build time
**Size**: 264-608 words (~350-810 tokens)
**Content**: Personalized narrative context for that specific NPC

### 2. Previous Conversation History (EXISTING) ✅
**Loaded by**: `load_and_prepare_conversation()` in `session_utils.py:149-214`
**Storage**: Database via `db.load_conversation(player_id, npc_code)` at line 191
**When**: When conversation starts/resumes
**Content**: All previous messages between player and this NPC

### 3. Current Dialog (EXISTING) ✅
**Handled by**: `ChatSession.add_message()` and `ChatSession.ask()`
**When**: During active conversation
**Content**: New messages exchanged in current session

---

## Complete Data Flow Trace

### Phase 1: Conversation Initialization

```
start_conversation_with_specific_npc()  [session_utils.py:347]
    ↓
load_and_prepare_conversation()  [session_utils.py:149]
    ↓
    ├─> Get NPC data from database
    ├─> build_system_prompt()  [session_utils.py:114]
    │     ↓
    │     ├─> _load_npc_narrative_prefix(area, name)  [session_utils.py:88]
    │     │     ↓
    │     │     └─> Loads NPC_PREFIX.<area>.<name>.txt  ✅ SOURCE 1
    │     │
    │     ├─> Build full system prompt with:
    │     │     • Personalized narrative prefix (if exists)
    │     │     • Character info from NPC.txt file
    │     │     • Game rules and instructions
    │     │     • Player profile insights (optional)
    │     │     • Brief mode rules (if enabled)
    │     │
    │     └─> Returns complete system prompt string
    │
    ├─> Create ChatSession with system prompt
    │
    └─> db.load_conversation(player_id, npc_code)  [line 191]
          ↓
          └─> Loads previous messages from database  ✅ SOURCE 2
                ↓
                └─> chat_session.add_message(role, content) for each
```

### Phase 2: Conversation Execution

```
Player sends message
    ↓
chat_session.add_message("user", player_message)  ✅ SOURCE 3
    ↓
chat_session.ask(player_message, ...)
    ↓
    ├─> chat_session.get_history()
    │     ↓
    │     ├─> [system: Full system prompt with NPC_PREFIX]  ← SOURCE 1
    │     ├─> [previous messages from database...]          ← SOURCE 2
    │     └─> [current user message]                        ← SOURCE 3
    │
    ├─> Send to LLM via llm_wrapper()
    │
    └─> LLM generates response using ALL context
          ↓
          chat_session.add_message("assistant", response)
```

### Phase 3: Conversation Save

```
save_current_conversation()  [session_utils.py:217]
    ↓
    ├─> Add [CONVERSATION_BREAK] marker
    │
    └─> db.save_conversation(player_id, npc_code, messages)
          ↓
          └─> Saves to database for next session  → Becomes SOURCE 2 next time
```

---

## System Prompt Structure (What LLM Sees)

```
================================================================================
CONTESTO NARRATIVO PERSONALIZZATO PER TE         ← SOURCE 1: NPC PREFIX
================================================================================
[Personalized narrative context from NPC_PREFIX.<area>.<name>.txt]
- Role in story
- Mission details
- Connected NPCs
- Directions to give
- Philosophy/themes
- Final realities
================================================================================

Sei [NAME], un/una [ROLE]...                    ← NPC character file
Motivazione: ...
Obiettivo: ...
V.O. (player hint): ...

[Dialogue hooks, greetings, AI behavior notes]
[Brief mode rules if enabled]
[Player profile insights if available]
[Game rules and instructions]
[Item giving mechanics]
[All standard NPC instructions]
```

---

## Message History Structure (What LLM Sees)

```json
[
  {
    "role": "system",
    "content": "[Complete system prompt with NPC_PREFIX above]"
  },
  {
    "role": "user",                              ← SOURCE 2: Previous history
    "content": "Ciao Irenna, what do you do?"
  },
  {
    "role": "assistant",                         ← SOURCE 2: Previous history
    "content": "Benvenuto! I create puppet shows..."
  },
  {
    "role": "user",
    "content": "[CONVERSATION_BREAK: Player left]"
  },
  {
    "role": "user",
    "content": "[CONVERSATION_RESUMED: Player returned]"
  },
  {
    "role": "user",                              ← SOURCE 3: Current dialog
    "content": "Tell me about the Veil"
  }
]
```

---

## Storage Locations

### During Conversation (In Memory)
- **System Prompt**: `chat_session.system_prompt` (includes NPC_PREFIX)
- **Message History**: `chat_session.messages[]` (previous + current)
- **Game State**: `game_session_state{}` (includes all loaded prefixes)

### Between Sessions (On Disk)
- **NPC PREFIX**: `NPC_PREFIX.<area>.<name>.txt` (read-only, loaded on demand)
- **Conversation History**: Database (via `db_manager.py`)
  - Mockup: `database/conversations_<player_id>_<npc_code>.json`
  - MySQL: `conversations` table
- **Player State**: Database (inventory, credits, profile, plot flags)

---

## Code References

### Loading NPC Prefix
**File**: `session_utils.py`
- **Function**: `_load_npc_narrative_prefix(area, name)` (lines 88-112)
- **Called by**: `build_system_prompt()` (line 155)
- **Integration**: Lines 154-166 (loads and inserts at top of prompt)

### Loading Previous Conversations
**File**: `session_utils.py`
- **Function**: `load_and_prepare_conversation()` (lines 149-214)
- **Database call**: `db.load_conversation(player_id, npc_code)` (line 191)
- **Adds to session**: Lines 194-197 (loops through messages)
- **Resume handling**: Lines 200-206 (adds CONVERSATION_RESUMED marker)

### Saving Conversations
**File**: `session_utils.py`
- **Function**: `save_current_conversation()` (lines 217-253)
- **Break marker**: Line 240-243 (adds CONVERSATION_BREAK)
- **Database call**: `db.save_conversation()` (line 248)

### Current Dialog Handling
**File**: `chat_manager.py`
- **Add message**: `ChatSession.add_message(role, content)` (line 45)
- **Send to LLM**: `ChatSession.ask()` (line 70)
- **Get full history**: `ChatSession.get_history()` (line 160)

---

## Token Usage Summary

### Per Regular NPC Conversation

| Component | Source | Tokens | When |
|-----------|--------|--------|------|
| **NPC Prefix** | File | ~545 | Every conversation (system prompt) |
| **Character File** | NPC.txt | ~1000 | Every conversation (system prompt) |
| **Game Rules** | Hardcoded | ~800 | Every conversation (system prompt) |
| **Previous History** | Database | Variable | Loaded once at start |
| **Current Dialog** | In-memory | Variable | Grows during session |

**System Prompt Total**: ~2,345 tokens (before history)
**With History (10 messages)**: ~3,500-4,000 tokens
**With History (50 messages)**: ~7,000-10,000 tokens

### Per Wise Guide Consultation (`/hint`)

| Component | Tokens |
|-----------|--------|
| NPC character file | ~1000 |
| Condensed narrative | ~1000 |
| Character/location map | ~200 |
| Player profile summary | ~200 |
| Conversation summary | ~300 |
| Game rules | ~800 |
| **Total System Prompt** | **~3,500** |

---

## Example: Full Context for Irenna

### When player talks to Irenna in City:

```
SYSTEM PROMPT (~2,345 tokens):
├─ NPC_PREFIX.city.irenna.txt (~536 words = 715 tokens)
│    • Your role: Marionettista della Resistenza
│    • Living marionettes animated by lost memories
│    • Need Filo della Memoria from Lyra
│    • Philosophy vs Theron about forgetting pain
│    • Final show at Nesso dei Sentieri
│
├─ NPC.city.irenna.txt character file (~1000 tokens)
│    • Personality traits
│    • Trading rules
│    • Conditional responses
│    • AI behavior notes
│    • SL integration commands
│
└─ Game rules and instructions (~800 tokens)
     • Italian language requirement
     • Item giving mechanics
     • Trading rules
     • System command warnings

PREVIOUS HISTORY (from database, variable):
├─ User: "Ciao Irenna"
├─ Assistant: "Benvenuto al mio piccolo teatro!..."
├─ User: "What's your story?"
├─ Assistant: "Le mie marionette si muovono da sole..."
└─ [CONVERSATION_BREAK / CONVERSATION_RESUMED markers]

CURRENT DIALOG (this session):
├─ User: "Tell me about the Veil crisis"
└─ Assistant: [Response generated using ALL above context]
```

---

## Verification Commands

### Test NPC Context Loading
```bash
# Test regular NPC with prefix
python3 main.py --mockup --area City --npc Irenna --model "openai/gpt-4o-mini"

# Ask: "What's your role in the story?"
# Irenna should mention: puppet theater, resistance, memory preservation

# Ask: "Who do you know?"
# Should mention: Theron (philosophical opposition), Cassian (propaganda target)

# Ask: "What happens at the final gathering?"
# Should mention: Nesso dei Sentieri, theater tent, all characters present
```

### Test Conversation Persistence
```bash
# Session 1: Talk to Irenna
python3 main.py --mockup --area City --npc Irenna
> Tell me about your puppets
> /exit

# Session 2: Resume with Irenna
python3 main.py --mockup --area City --npc Irenna
# Should remember previous conversation about puppets
```

---

## Conclusion

✅ **YES - All three context sources are active:**

1. **NPC_PREFIX files** - Loaded automatically via `_load_npc_narrative_prefix()`
2. **Previous conversations** - Loaded from database via `db.load_conversation()`
3. **Current dialog** - Managed by `ChatSession` in memory

The system is **fully functional** and NPCs have access to:
- Their personalized narrative context (~545 tokens)
- Complete conversation history with the player
- Real-time dialog in the current session

**Total context per NPC**: 2,345 tokens (system) + history (variable) + current (variable)
