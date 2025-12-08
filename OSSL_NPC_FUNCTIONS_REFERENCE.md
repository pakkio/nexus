# OSSL NPC Functions Reference

## Correct Function Names for OpenSim NPCs

### Creating and Removing NPCs

```lsl
// Create an NPC
key osNpcCreate(string firstname, string lastname, vector position, string notecard)
key osNpcCreate(string firstname, string lastname, vector position, string notecard, integer options)

// Remove an NPC
osNpcRemove(key npc)
```

### Movement and Positioning

```lsl
// Move NPC to a position
osNpcMoveTo(key npc, vector position)

// Move NPC to a target (with options)
osNpcMoveToTarget(key npc, vector target, integer options)

// Set NPC rotation
osNpcSetRot(key npc, rotation rot)

// Stop NPC movement
osNpcStopMoveToTarget(key npc)

// Make NPC sit
osNpcSit(key npc, key target, integer options)

// Make NPC stand
osNpcStand(key npc)
```

### Animations

```lsl
// Play animation - CORRECT FUNCTION NAME!
osNpcPlayAnimation(key npc, string animation)

// Stop animation
osNpcStopAnimation(key npc, string animation)
```

**NOTE:** It's `osNpcPlayAnimation()`, NOT `osNpcStartAnimation()`

### Communication

```lsl
// Make NPC say something in chat
osNpcSay(key npc, string message)
osNpcSay(key npc, integer channel, string message)

// Make NPC shout
osNpcShout(key npc, integer channel, string message)

// Make NPC whisper
osNpcWhisper(key npc, integer channel, string message)
```

### Information

```lsl
// Get NPC owner
key osNpcGetOwner(key npc)

// Check if key is an NPC
integer osIsNpc(key npc)
```

### Appearance

```lsl
// Save avatar appearance to notecard
string osAgentSaveAppearance(key avatar, string notecard)

// Load appearance onto NPC
osNpcLoadAppearance(key npc, string notecard)
```

## Common Usage Patterns

### Basic NPC Spawn
```lsl
key npcKey;
vector pos = <128, 128, 25>;
string appearance = osAgentSaveAppearance(llGetOwner(), "my_appearance");
npcKey = osNpcCreate("John", "Doe", pos, appearance, OS_NPC_SENSE_AS_AGENT);
```

### Animation Control
```lsl
// Start animation
osNpcPlayAnimation(npcKey, "sit");

// Stop animation
osNpcStopAnimation(npcKey, "sit");
```

### Movement
```lsl
// Move to position
vector target = <100, 100, 25>;
osNpcMoveTo(npcKey, target);

// Rotate NPC
rotation rot = llEuler2Rot(<0, 0, PI_BY_TWO>); // 90 degrees
osNpcSetRot(npcKey, rot);
```

### Cleanup
```lsl
// Always remove NPCs when done
osNpcRemove(npcKey);
npcKey = NULL_KEY;
```

## Options Constants

```lsl
OS_NPC_FLY             = 0x01  // NPC can fly
OS_NPC_NO_FLY          = 0x02  // NPC cannot fly
OS_NPC_LAND_AT_TARGET  = 0x04  // Land when reaching target
OS_NPC_RUNNING         = 0x08  // NPC runs instead of walks
OS_NPC_SENSE_AS_AGENT  = 0x10  // Sensors detect as avatar, not scripted agent
OS_NPC_NOT_OWNED       = 0x20  // NPC not owned by anyone
OS_NPC_CREATOR_OWNED   = 0x40  // NPC owned by script creator
OS_NPC_OBJECT_GROUP    = 0x80  // Use object's group
```

## Common Errors and Fixes

### ❌ WRONG
```lsl
osNpcStartAnimation(npcKey, "wave");  // Function doesn't exist!
```

### ✅ CORRECT
```lsl
osNpcPlayAnimation(npcKey, "wave");   // This is the right function
```

### ❌ WRONG
```lsl
// Animation name from inventory won't work if it has wrong permissions
osNpcPlayAnimation(npcKey, "MyAnimation");
```

### ✅ CORRECT
```lsl
// Make sure animation has COPY and TRANSFER permissions
// and is in the object's inventory
osNpcPlayAnimation(npcKey, "MyAnimation");
```

## Permission Requirements

For OSSL NPC functions to work:

1. **OpenSim.ini** must enable OSSL functions:
   ```ini
   [XEngine]
   AllowOSFunctions = true
   OSFunctionThreatLevel = VeryHigh
   ```

2. **Animations** must have proper permissions:
   - COPY permission
   - TRANSFER permission
   - Must be in object inventory

3. **Region permissions**:
   - Some regions restrict NPC creation
   - Check with `osNpcCreate()` return value (NULL_KEY = failed)

## Complete Example

```lsl
key npcKey;
string currentAnim;

default
{
    state_entry()
    {
        npcKey = NULL_KEY;
        currentAnim = "";
    }

    touch_start(integer num)
    {
        if (npcKey == NULL_KEY)
        {
            // Spawn NPC
            vector pos = llGetPos() + <2, 0, 0>;
            string appearance = osAgentSaveAppearance(llGetOwner(), "temp");
            npcKey = osNpcCreate("Guard", "Bot", pos, appearance, OS_NPC_SENSE_AS_AGENT);

            if (npcKey != NULL_KEY)
            {
                llOwnerSay("NPC spawned!");
                osNpcPlayAnimation(npcKey, "stand");
                currentAnim = "stand";
            }
        }
        else
        {
            // Stop old animation
            if (currentAnim != "")
            {
                osNpcStopAnimation(npcKey, currentAnim);
            }

            // Play new animation
            osNpcPlayAnimation(npcKey, "wave");
            currentAnim = "wave";
        }
    }

    on_rez(integer start)
    {
        if (npcKey != NULL_KEY)
        {
            osNpcRemove(npcKey);
            npcKey = NULL_KEY;
        }
    }
}
```

## References

- OpenSim Wiki: http://opensimulator.org/wiki/OSSL
- OSSL Functions: http://opensimulator.org/wiki/Category:OSSL_Functions
- NPC Functions: http://opensimulator.org/wiki/Category:OSSL_NPC_Functions
