# NPC Spawn Failure Debugging Guide

## Current Status

After implementing 3 critical bug fixes in `brain.lsl`, the NPC spawn is failing with `osNpcCreate()` returning `NULL_KEY`.

## What Was Fixed

1. **Global variable corruption** - Eliminated all shared temp variables
2. **Notecard reset bug** - Added `givingNotecard` flag to prevent script reset
3. **Spawn after reset** - Added explicit state variable resets in `state_entry()`

## Current Problem

**Symptom:** NPC won't spawn when touched  
**Error:** `osNpcCreate()` returns `NULL_KEY`  
**Timeline:** 
- 16:19 - Script was working
- 16:28 - After fixes, spawn started failing

## Changes Made for Diagnosis

### Added Notecard Validation (brain.lsl lines 87-95)
```lsl
// Validate appearance notecard exists
if (llGetInventoryType(appearanceNotecard) != INVENTORY_NOTECARD)
{
    llOwnerSay("ERROR: Notecard '" + appearanceNotecard + "' not found in inventory!");
    llSetText("Missing notecard:\n" + appearanceNotecard, RED, 1.0);
    return;
}

llOwnerSay("✓ Notecard '" + appearanceNotecard + "' found in inventory");
```

### Enhanced Debug Logging (brain.lsl lines 127-156)
```lsl
spawnNPC()
{
    if (npcSpawned) 
    {
        llOwnerSay("DEBUG: NPC already spawned, returning");
        return;
    }

    llOwnerSay("DEBUG: Spawning NPC...");
    llOwnerSay("  NPC_NAME = '" + NPC_NAME + "'");
    llOwnerSay("  appearanceNotecard = '" + appearanceNotecard + "'");
    llOwnerSay("  Notecard type = " + (string)llGetInventoryType(appearanceNotecard));
    
    vector spawnPos = llGetPos() + <1.0, 0.0, 0.0> * llGetRot();
    llOwnerSay("  Spawn position = " + (string)spawnPos);
    
    npcKey = osNpcCreate(NPC_NAME, "NPC", spawnPos, appearanceNotecard, OS_NPC_SENSE_AS_AGENT);
    llOwnerSay("  osNpcCreate returned: " + (string)npcKey);

    if (npcKey != NULL_KEY)
    {
        // Success handling
    }
    else
    {
        llOwnerSay("✗ Failed to spawn NPC - osNpcCreate returned NULL_KEY");
        llOwnerSay("  Check: Notecard '" + appearanceNotecard + "' format (must be LLSD appearance data)");
        llOwnerSay("  Check: NPC permissions enabled on this sim");
        llSetText("✗ Spawn failed", RED, 1.0);
    }
}
```

## What to Check When Testing

### 1. During Initialization (after script reset/start)
Look for these messages in chat:
```
✓ NPC: Boros | Area: Mountain
✓ Server: http://212.227.64.143:5000
Loaded 11 anims, X emotes
✓ Notecard 'Boros' found in inventory  <-- KEY MESSAGE
```

**If you see:**
- `ERROR: Notecard 'Boros' not found in inventory!` → Notecard is missing or has wrong name
- No message about notecard at all → Init failed early (check URL/object name)

### 2. When Touching to Spawn
Look for these debug messages:
```
DEBUG: Spawning NPC...
  NPC_NAME = 'Boros'
  appearanceNotecard = 'Boros'
  Notecard type = 7                    <-- Should be 7 (INVENTORY_NOTECARD)
  Spawn position = <X, Y, Z>
  osNpcCreate returned: <uuid>         <-- Should be a UUID, not 00000000-0000-0000-0000-000000000000
```

### 3. Diagnostic Interpretation

| Notecard Type | Meaning | Action |
|---------------|---------|--------|
| 7 | INVENTORY_NOTECARD - Correct | Notecard exists and is valid type |
| -1 | INVENTORY_NONE | Notecard not in inventory - check name spelling |
| Other | Wrong inventory type | Item exists but isn't a notecard |

| osNpcCreate Return | Meaning | Possible Causes |
|--------------------|---------|-----------------|
| Valid UUID (not all zeros) | Success | NPC spawned correctly |
| NULL_KEY (00000000-...) | Failure | 1. Notecard wrong format<br>2. NPC permissions disabled<br>3. Name conflict<br>4. Position invalid |

## Common Causes of osNpcCreate() Failure

### 1. Notecard Format Wrong
**Problem:** Notecard contains config data instead of LLSD appearance data  
**Solution:** 
- Notecard must contain LLSD-formatted appearance data from `osAgentSaveAppearance()`
- Should look like: `<?xml version="1.0" encoding="utf-8"?><llsd>...`
- NOT like: `name=Boros` or `position=<1,0,0>`

**How to create correct notecard:**
1. Wear the desired avatar appearance
2. Run: `osAgentSaveAppearance(llGetOwner(), "Boros");`
3. This creates the notecard with proper LLSD format

### 2. OpenSim NPC Permissions
**Problem:** Server doesn't allow NPC creation  
**Check:** OpenSim.ini settings:
```ini
[NPC]
Enabled = true
AllowNotOwned = false
AllowSenseAsAvatar = true
```

### 3. Name Conflict
**Problem:** NPC with same name already exists in region  
**Solution:** 
- Check for existing NPCs: look for avatar named "Boros"
- Remove old NPC before spawning new one
- Or use unique names

### 4. Position Invalid
**Problem:** Spawn position is inside terrain/objects  
**Current code:** `spawnPos = llGetPos() + <1.0, 0.0, 0.0> * llGetRot();`
**Solution:** Ensure object is placed where +1m in front is valid ground

## Comparison with Working Version

### boros_balanced.lsl (WORKING)
```lsl
state_entry() {
    npcKey = NULL_KEY;
    // ... setup ...
    extractNPCName();  // Sets appearanceNotecard = npcName
    loadAnimationsFromInventory();
    
    if (llGetInventoryType(appearanceNotecard) != INVENTORY_NOTECARD)
    {
        llOwnerSay("ERROR: Notecard '" + appearanceNotecard + "' not found!");
    }
}

touch_start(integer input_num) {
    if (npcKey == NULL_KEY)  // Uses npcKey check, not npcSpawned flag
    {
        spawnNPC();
    }
}

spawnNPC() {
    npcKey = osNpcCreate(npcName, "NPC", spawnPos, appearanceNotecard, OS_NPC_SENSE_AS_AGENT);
    // Exact same call as brain.lsl
}
```

### brain.lsl (CURRENT)
```lsl
state_entry() {
    npcKey = NULL_KEY;
    npcSpawned = FALSE;  // Additional flag
    // ...
    init();  // Separate function
}

init() {
    // ... parse name ...
    appearanceNotecard = NPC_NAME;
    loadAnimations();
    
    if (llGetInventoryType(appearanceNotecard) != INVENTORY_NOTECARD)
    {
        llOwnerSay("ERROR: Notecard '" + appearanceNotecard + "' not found!");
        return;  // Early return
    }
}

touch_start(integer n) {
    if (!npcSpawned)  // Uses npcSpawned flag
    {
        spawnNPC();
    }
}

spawnNPC() {
    if (npcSpawned) return;  // Double-check with flag
    
    npcKey = osNpcCreate(NPC_NAME, "NPC", spawnPos, appearanceNotecard, OS_NPC_SENSE_AS_AGENT);
    // Same call as boros_balanced.lsl
}
```

**Key Differences:**
1. brain.lsl uses `npcSpawned` flag, boros uses `npcKey == NULL_KEY` check
2. brain.lsl has separate `init()` function
3. brain.lsl has early return in init() if notecard missing

## Next Steps

1. **Test with current debug version** - Check all debug output
2. **If notecard type = -1**: Notecard isn't in inventory (name mismatch?)
3. **If notecard type = 7 but spawn fails**: Check notecard format (must be LLSD, not config)
4. **If spawn position looks wrong**: Adjust spawn offset
5. **If all looks correct**: Check OpenSim NPC permissions

## Quick Test: Minimal Spawn Script

If all else fails, test with this minimal script in a new object:

```lsl
key npcKey;

default
{
    state_entry()
    {
        llOwnerSay("Ready to test spawn");
    }
    
    touch_start(integer n)
    {
        vector pos = llGetPos() + <1, 0, 0>;
        npcKey = osNpcCreate("TestNPC", "Test", pos, "Boros", OS_NPC_SENSE_AS_AGENT);
        
        if (npcKey != NULL_KEY)
            llOwnerSay("SUCCESS: " + (string)npcKey);
        else
            llOwnerSay("FAILED: NULL_KEY returned");
    }
}
```

If this minimal version fails, the problem is NOT with brain.lsl logic, but with:
- Notecard format
- OpenSim permissions
- Server configuration

## Files Modified This Session
- `/root/nexus/brain.lsl` - Added notecard validation + enhanced debug logging
- `/root/nexus/NPC_SPAWN_DEBUG_GUIDE.md` - This debugging guide
