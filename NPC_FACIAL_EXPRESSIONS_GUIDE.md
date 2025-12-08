# NPC Facial Expressions in OSSL

## Overview

Yes! You can control NPC facial expressions (emotes) in OpenSim using `osNpcPlayAnimation()` with **built-in facial animation names**.

Facial expressions are special animations that affect only the face.

---

## Built-In Facial Expressions

### Available Facial Animations (Standard in SL/OpenSim)

```lsl
// Happy/Positive
"express_smile"          // Smile
"express_laugh"          // Laughing
"express_toothsmile"     // Big toothy smile
"express_grin"           // Grin

// Sad/Negative
"express_sad"            // Sad face
"express_cry"            // Crying
"express_frown"          // Frown

// Other Emotions
"express_anger"          // Angry face
"express_angry"          // Another angry variant
"express_surprise"       // Surprised/shocked
"express_afraid"         // Afraid/scared
"express_worry"          // Worried expression
"express_shrug"          // Shrug (shoulders + face)

// Playful
"express_wink"           // Wink
"express_kiss"           // Blowing a kiss
"express_tongue_out"     // Sticking tongue out
"express_disdain"        // Disdainful look
"express_repulsed"       // Disgusted

// Neutral
"express_open_mouth"     // Open mouth
"express_bored"          // Bored expression
```

---

## How to Use with NPCs

### Basic Example

```lsl
key npcKey;

default
{
    touch_start(integer num)
    {
        // Spawn NPC first...

        // Make NPC smile
        osNpcPlayAnimation(npcKey, "express_smile");

        // Wait 3 seconds
        llSleep(3.0);

        // Make NPC sad
        osNpcStopAnimation(npcKey, "express_smile");
        osNpcPlayAnimation(npcKey, "express_sad");
    }
}
```

### Combining Face + Body Animations

You can play BOTH a facial expression AND a body animation simultaneously:

```lsl
// Play talking animation
osNpcPlayAnimation(npcKey, "STAND TALK 1");

// Add smile while talking
osNpcPlayAnimation(npcKey, "express_smile");

// NPC will talk AND smile at the same time!
```

---

## Updated npc.lsl with Facial Expressions

Here's how to add facial expression support to the NPC manager:

```lsl
// Add to global variables
list availableFaces;
string currentFace;

// In state_entry(), load facial expressions
loadFacialExpressions()
{
    availableFaces = [];

    // Check which facial animations exist in inventory
    integer i;
    for (i = 0; i < llGetInventoryNumber(INVENTORY_ANIMATION); i++)
    {
        string anim = llGetInventoryName(INVENTORY_ANIMATION, i);

        // Check if it's a facial expression
        if (llSubStringIndex(anim, "express_") == 0)
        {
            availableFaces += [anim];
        }
    }
}

// Play facial expression
playFace(string faceName)
{
    if (npcKey == NULL_KEY) return;

    // Stop previous facial expression
    if (currentFace != "")
    {
        osNpcStopAnimation(npcKey, currentFace);
    }

    // Play new facial expression
    osNpcPlayAnimation(npcKey, faceName);
    currentFace = faceName;
}
```

---

## Suggested Facial Expressions by NPC

Based on personality:

### Happy/Friendly NPCs
**Jorin (Innkeeper)**: `express_smile`, `express_laugh`
**Mara (Healer)**: `express_smile`, `express_worry`
**Meridia (Guide)**: `express_smile`, `express_open_mouth`

### Serious/Scholarly NPCs
**Erasmus (Philosopher)**: `express_open_mouth`, `express_bored`
**Boros (Warrior)**: `express_angry`, `express_frown`
**Theron (Judge)**: `express_disdain`, `express_anger`

### Mystical/Sad NPCs
**Lyra (Memory Keeper)**: `express_sad`, `express_worry`
**Syra (Incomplete)**: `express_sad`, `express_cry`, `express_afraid`
**Elira (Nature)**: `express_smile`, `express_worry`

### Warriors
**Cassian (Guard)**: `express_anger`, `express_disdain`
**Garin (Blacksmith)**: `express_angry`, `express_toothsmile`

### Artists
**Irenna (Puppeteer)**: `express_smile`, `express_surprise`, `express_laugh`

---

## Complete Example: NPC with Emotions

```lsl
key npcKey;
string currentAnim;
string currentFace;

playEmotionalAnimation(string bodyAnim, string faceAnim)
{
    // Stop previous animations
    if (currentAnim != "")
    {
        osNpcStopAnimation(npcKey, currentAnim);
    }
    if (currentFace != "")
    {
        osNpcStopAnimation(npcKey, currentFace);
    }

    // Play new animations
    osNpcPlayAnimation(npcKey, bodyAnim);
    osNpcPlayAnimation(npcKey, faceAnim);

    currentAnim = bodyAnim;
    currentFace = faceAnim;

    llOwnerSay("NPC: " + bodyAnim + " + " + faceAnim);
}

default
{
    touch_start(integer num)
    {
        if (npcKey == NULL_KEY)
        {
            // Spawn NPC...
            return;
        }

        // Example: NPC is happy and talking
        playEmotionalAnimation("STAND TALK 1", "express_smile");

        // Or: NPC is sad and reading
        // playEmotionalAnimation("read-standing", "express_sad");

        // Or: NPC is angry and gesturing
        // playEmotionalAnimation("TALK M 1", "express_anger");
    }
}
```

---

## Dialog Menu with Emotions

You could extend the dialog to include facial expressions:

```lsl
showNPCDialog(key toucher)
{
    list buttons;

    // Body animations
    buttons += ["DESTROY", "STOP"];
    buttons += availableAnims;

    // Add emotion section
    buttons += ["😊 Happy", "😢 Sad", "😠 Angry"];

    llDialog(toucher, "Choose animation or emotion:", buttons, dialogChannel);
}

listen(integer channel, string name, key id, string message)
{
    if (message == "😊 Happy")
    {
        playFace("express_smile");
    }
    else if (message == "😢 Sad")
    {
        playFace("express_sad");
    }
    else if (message == "😠 Angry")
    {
        playFace("express_anger");
    }
    // ... handle other animations
}
```

---

## Important Notes

### 1. Built-In vs Custom
- Facial expression animations starting with `express_` are **built-in** to SL/OpenSim
- You DON'T need to add them to inventory - they're always available
- Custom facial animations can also be used if you have them

### 2. Stopping Facial Expressions
```lsl
// Stop specific face
osNpcStopAnimation(npcKey, "express_smile");

// Or stop all animations (including face)
osNpcRemove(npcKey);  // Removes NPC entirely
```

### 3. Combining Expressions
You can only play ONE facial expression at a time (they override each other).

But you can combine:
- 1 facial expression
- Multiple body animations
- Multiple emotes

```lsl
osNpcPlayAnimation(npcKey, "STAND TALK 1");    // Body
osNpcPlayAnimation(npcKey, "express_smile");   // Face
osNpcPlayAnimation(npcKey, "hand_wave");       // Gesture
// All three play simultaneously!
```

---

## Testing Facial Expressions

Quick test script:

```lsl
key npcKey;
integer faceIndex;
list faces = [
    "express_smile",
    "express_sad",
    "express_anger",
    "express_surprise",
    "express_laugh",
    "express_cry"
];

default
{
    state_entry()
    {
        // Spawn your NPC first
        vector pos = llGetPos() + <1,0,0>;
        string appearance = osAgentSaveAppearance(llGetOwner(), "temp");
        npcKey = osNpcCreate("Test", "NPC", pos, appearance, OS_NPC_SENSE_AS_AGENT);
    }

    touch_start(integer num)
    {
        // Cycle through facial expressions
        string face = llList2String(faces, faceIndex);

        llOwnerSay("Testing: " + face);
        osNpcPlayAnimation(npcKey, face);

        faceIndex = (faceIndex + 1) % llGetListLength(faces);
    }

    on_rez(integer start)
    {
        if (npcKey != NULL_KEY)
        {
            osNpcRemove(npcKey);
        }
        llResetScript();
    }
}
```

---

## Summary

✅ **YES** - You can control NPC facial expressions!
✅ Use `osNpcPlayAnimation(npcKey, "express_smile")` etc.
✅ Built-in expressions are always available (no inventory needed)
✅ Can combine facial + body animations simultaneously
✅ Each NPC can have personality-appropriate expressions

The `express_*` animations are standard in Second Life/OpenSim and work without needing to add them to inventory!
