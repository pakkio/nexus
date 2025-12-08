# Simple NPC Setup Guide

## Quick Start

This is a completely **generic** NPC spawner. Just drop the script in any object and rename it!

## Setup (3 steps)

### 1. Rename Your Object
Format: `<NPCName>.<Location>`

Examples:
- `Boros.Mountains`
- `Elira.Forest`
- `Lyra.Sanctum`

### 2. Add to Object Inventory
- `npc.lsl` - the script
- `Boros` - appearance notecard (same name as first part of object name)
- Any animation files you want to use

### 3. Done!
Touch to spawn the NPC, touch again for animation menu.

---

## How It Works

**Object Name**: `Boros.Mountains`

The script:
1. Reads object name → `"Boros.Mountains"`
2. Extracts first part → `"Boros"`
3. Looks for notecard → `"Boros"`
4. Creates NPC named → `"Boros"`
5. Loads all animations from inventory automatically

---

## Example Setup: Boros in Mountains

**Object Contents:**
```
npc.lsl
Boros                    (appearance notecard - LLSD format)
read-standing           (animation)
STAND TALK 1            (animation)
TALK2                   (animation)
TALK4                   (animation)
TALK 5                  (animation)
TALK 6                  (animation)
```

**Object Name:** `Boros.Mountains`

**Result:** NPC named "Boros" spawns using the "Boros" appearance notecard

---

## Multiple NPCs

Want multiple NPCs? Just duplicate the object and rename it!

**Example:**

| Object Name | Notecard Needed | NPC Name |
|------------|-----------------|----------|
| `Boros.Mountains` | `Boros` | Boros |
| `Elira.Forest` | `Elira` | Elira |
| `Lyra.Sanctum` | `Lyra` | Lyra |

Each object is independent. Same script works for all!

---

## Creating Appearance Notecards

### Method 1: Save Avatar Appearance
```lsl
// Temporary script to save appearance
default {
    touch_start(integer num) {
        string name = osAgentSaveAppearance(llDetectedKey(0), "Boros");
        llOwnerSay("Saved as: " + name);
    }
}
```

1. Put this script in an object
2. Touch it
3. A notecard "Boros" will be created with your appearance
4. Remove the script, keep the notecard
5. Copy the notecard to your NPC object

### Method 2: Use Existing Notecard
If you already have an appearance notecard (LLSD format), just copy it to the object and make sure the name matches!

---

## Dialog Options

When you touch a spawned NPC, you get buttons for:

- **DESTROY** - Remove the NPC
- **STOP** - Stop current animation
- **Animation names** - All animations from inventory (auto-detected)

---

## Customization

Want to change spawn position or rotation? Edit these lines in `state_entry()`:

```lsl
npcSpawnOffset = <1.0, 0.0, 0.0>;  // 1m in front of object
npcSpawnRot = ZERO_ROTATION;        // Same rotation as object
```

Common spawn offsets:
- `<1.0, 0.0, 0.0>` - 1m forward
- `<2.0, 1.0, 0.0>` - 2m forward, 1m right
- `<0.0, 0.0, 0.5>` - 0.5m up

---

## Troubleshooting

### "ERROR: Notecard 'Boros' not found"
- Make sure notecard name matches object name (before the dot)
- Object: `Boros.Mountains` needs notecard: `Boros`
- Check spelling and case sensitivity

### "Warning: No animations found in inventory"
- Add animation files to the object's inventory
- They will automatically appear in the dialog menu

### NPC doesn't spawn / returns NULL_KEY
- Check OSSL permissions on your region
- Make sure spawn position is valid (not underground)
- Try moving the object to a different location

### Animation doesn't play
- Animation must have COPY and TRANSFER permissions
- Animation must be in the object's inventory
- Make sure animation name is correct

---

## Advanced: No Dot in Object Name

If object name is just `Boros` (no dot), script will:
- Use `"Boros"` as NPC name
- Look for notecard `"Boros"`

This works fine too!

---

## Features

✅ Automatic notecard detection from object name
✅ Automatic animation loading from inventory
✅ Touch to spawn, touch again for menu
✅ Animation management with auto-stop
✅ Clean NPC lifecycle (destroy, region crossing)
✅ Owner-only control
✅ Reusable for any NPC - just rename!

---

## Complete Example

1. Create cube in SL
2. Name it: `Boros.Mountains`
3. Add to inventory:
   - `npc.lsl`
   - `Boros` (appearance notecard)
   - `read-standing` (animation)
   - `wave` (animation)
4. Touch cube
5. Boros spawns!
6. Touch again → Get menu with DESTROY, STOP, read-standing, wave

Done! 🎉
