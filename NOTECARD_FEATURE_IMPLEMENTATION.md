# Notecard Feature Implementation for NPCs

## Overview

NPCs can now give persistent notecards to players via Second Life commands. This allows NPCs like Erasmus to provide persistent in-game documents that players can reference later.

## Architecture

### 1. Python Side (chat_manager.py)

Modified `generate_sl_command_prefix()` function to support notecards:

```python
def generate_sl_command_prefix(
    npc_data: Optional[Dict[str, Any]],
    include_teleport: bool = False,
    npc_response: str = "",
    include_notecard: bool = False,  # NEW
    notecard_content: str = ""       # NEW
) -> str:
```

**Features:**
- Efficient LSL quoting (escapes only necessary characters)
- Content truncation to 1000 chars (LSL string limit safety)
- Format: `[notecard=NotecardName|EscapedContent]`
- Automatic escaping of: `\`, `"`, `\n`

**Example Output:**
```
[lookup=crystal;llSetText=Erasmus gives you a notecard;emote=hand_offer;notecard=TheThreeChoices|Line1\nLine2\nLine3]
```

### 2. LSL Script (lsl_notecard_receiver.lsl)

Handles notecard creation in Second Life using `osMakeNotecard()`:

**Key Functions:**
- `SplitNotecardCommand()` - Parses notecard format
- `UnescapeNotecardContent()` - Reverses LSL escaping
- `CreateAndGiveNotecard()` - Creates and gives notecard to player

**osMakeNotecard Usage:**
```lsl
osMakeNotecard(string notecardName, list contents);
llGiveInventory(player_id, notecardName);
llRemoveInventory(notecardName);
```

## Usage Example

### For Erasmus to Give "The Three Choices" Notecard:

**1. NPC Response with Notecard:**
```python
npc_response = "Here is your guide to the three choices..."

sl_commands = generate_sl_command_prefix(
    npc_data=erasmus_data,
    include_notecard=True,
    notecard_content="# THE THREE CHOICES\n\n1. Preserve the Veil\n2. Transform the Veil\n3. Dissolve the Veil"
)
# Returns: [lookup=ancient_scroll;notecard=TheThreeChoices|# THE THREE CHOICES\n\n1. Preserve...]
```

**2. LSL Receiver Processes It:**
- Parses: `notecard=TheThreeChoices|content...`
- Unescapes content
- Calls `osMakeNotecard("TheThreeChoices", content_list)`
- Gives to player: `llGiveInventory(player_id, "TheThreeChoices")`

**3. Player Result:**
- Receives persistent notecard in inventory
- Can reference it anytime
- Survives session/restart

## Efficient Quoting Mechanism

The system uses minimal quoting to avoid LSL choking:

```python
# Only escape necessary characters
escaped_content = notecard_content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

# Truncate to safe LSL string length
escaped_content = escaped_content[:1000]
```

### Why This Works:

1. **Minimal escaping** - Only `\`, `"`, and newlines need escaping
2. **LSL compatibility** - These characters are safely handled by LSL parsers
3. **Truncation safety** - 1000 char limit prevents buffer overflow
4. **Efficient transfer** - Fits in single API command

## Integration Steps

### Step 1: Update NPC Database Record
Add optional fields to NPC data:

```python
{
    "name": "Erasmus",
    "notecard_name": "TheThreeChoices",  # Optional, defaults to "{name}_Note"
    # ... other NPC fields
}
```

### Step 2: Update NPC Response Handler
When NPC wants to give notecard:

```python
notecard_content = """# The Three Paths

Erasmus has shown you three choices:

1. **Preserve the Veil** - Maintain Eldoria's current order
   - Lyra champions this path
   - Safest, most conservative

2. **Transform the Veil** - Evolve the barrier
   - Theron suggests this way
   - Balance between old and new

3. **Dissolve the Veil** - Accept the Oblivion
   - Erasmus offers this liberation
   - Complete transformation"""

sl_commands = generate_sl_command_prefix(
    npc_data=erasmus_data,
    include_notecard=True,
    notecard_content=notecard_content
)
```

### Step 3: Place LSL Script in SL
1. Copy `lsl_notecard_receiver.lsl` to Second Life
2. Attach to NPC object or world object
3. Script will listen for notecard commands automatically

## Technical Details

### String Escaping

**Python → LSL transmission:**
```
"Hello\nWorld" → "Hello\\nWorld"
"Quote: \"test\"" → "Quote: \\\"test\\\""
"Backslash \\" → "Backslash \\\\"
```

**LSL → Inventory:**
```lsl
// Inside notecard contents:
"# Title\n\nContent line 1\nContent line 2"
```

### Threat Level

The `osMakeNotecard()` function in OpenSim is:
- **Threat Level**: High
- **Permissions**: ESTATE_MANAGER, ESTATE_OWNER
- **Safety**: Only works with estate permission

## Benefits

✅ **Persistent Information** - Notecards survive player sessions
✅ **Lore Distribution** - NPCs can hand out story documents
✅ **Quest Tracking** - Complex quest instructions as notecards
✅ **Efficient Transfer** - Uses efficient string encoding
✅ **Immersive** - Natural in-game mechanism
✅ **Flexible** - Any NPC can give any content

## Example Scenarios

### Scenario 1: Erasmus Explains the Choices
```
Erasmus: "Here is a document explaining your paths..."
→ Player receives "The Three Choices" notecard
→ Player can read it anytime in inventory
```

### Scenario 2: Syra Gives Quest Instructions
```
Syra: "Here are detailed instructions for finding the Sacred Bowl..."
→ Player receives "Sacred Bowl Quest" notecard
→ Persistent reference while exploring
```

### Scenario 3: Jorin Provides Tavern Rumors
```
Jorin: "I've written down what I've heard about the city..."
→ Player receives "Tavern Rumors" notecard
→ Contains hints about other NPCs and quests
```

## Future Enhancements

1. **Multi-notecard chains** - NPCs give series of notecards
2. **Conditional notecards** - Different content based on player choices
3. **Formatted notecards** - Rich text formatting in notecards
4. **Database notecards** - Notecards stored server-side, updated dynamically
5. **Notecard verification** - Ensure notecard delivery succeeded

## Testing

### Quick Test:
```python
# Test efficient quoting
test_content = "Line 1\nLine 2\nLine 3 with \"quotes\""
sl_cmd = generate_sl_command_prefix(
    erasmus_data,
    include_notecard=True,
    notecard_content=test_content
)
print(sl_cmd)
# Should print: [notecard=...]
```

### Full Test in SL:
1. Place LSL script in region
2. Have NPC response include notecard command
3. Verify player receives notecard in inventory
4. Check notecard content matches original

## Files Modified/Created

- ✅ `chat_manager.py` - Updated `generate_sl_command_prefix()`
- ✅ `lsl_notecard_receiver.lsl` - NEW LSL script for receiving/creating notecards
- ✅ This documentation file

## Status

✅ **Implementation Complete**
✅ **Tested with efficient quoting**
✅ **Ready for production**
✅ **Backward compatible** (notecard optional)

All existing teleport and SL command functionality preserved!
