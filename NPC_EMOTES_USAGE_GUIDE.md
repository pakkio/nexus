# NPC Script with Emotes - Usage Guide

## What's New

The updated `npc_with_emotes.lsl` script now supports **facial expressions (emotes)** in addition to body animations!

---

## Features

✅ **Separate body animations and facial expressions**
✅ **Auto-detects emotes** from inventory (animations starting with `express_`)
✅ **Built-in emote buttons** if no emotes in inventory
✅ **Independent control** - play body animation + facial expression simultaneously
✅ **Dedicated EMOTES menu** for facial expressions

---

## How It Works

### Main Dialog
When you touch a spawned NPC, you get:
- **DESTROY** - Remove NPC
- **STOP** - Stop body animation
- **EMOTES** - Open facial expression menu
- All body animations from inventory

### Emotes Dialog
Click "EMOTES" to see:
- **BACK** - Return to main menu
- **STOP EMOTE** - Stop facial expression
- All `express_*` animations from inventory
- Built-in emote buttons (if no emotes in inventory):
  - 😊 Smile
  - 😢 Sad
  - 😠 Angry
  - 😮 Surprise
  - 😆 Laugh
  - 😟 Worry

---

## Setup Instructions

### Option 1: Using Inventory Emotes

**Object Contents:**
```
npc_with_emotes.lsl
Boros (appearance notecard)
STAND TALK 1 (body animation)
TALK M 1 (body animation)
read-standing (body animation)
TALK2 (body animation)
express_smile (facial expression)
express_sad (facial expression)
express_anger (facial expression)
```

The script will:
- Load body animations: `STAND TALK 1`, `TALK M 1`, `read-standing`, `TALK2`
- Load emotes: `express_smile`, `express_sad`, `express_anger`
- Show them in separate menus

### Option 2: Using Built-In Emotes

**Object Contents:**
```
npc_with_emotes.lsl
Boros (appearance notecard)
STAND TALK 1 (body animation)
TALK M 1 (body animation)
read-standing (body animation)
TALK2 (body animation)
```

The script will:
- Load body animations from inventory
- Show built-in emote buttons (😊 Smile, 😢 Sad, etc.)
- Use OpenSim's built-in facial expressions

---

## Example Usage

### 1. Spawn NPC
Touch object → NPC spawns

### 2. Play Body Animation
Touch object → Select "STAND TALK 1" → NPC talks

### 3. Add Facial Expression
Touch object → Click "EMOTES" → Select "😊 Smile" → NPC talks AND smiles!

### 4. Change Expression
Touch object → Click "EMOTES" → Select "😢 Sad" → NPC talks AND looks sad

### 5. Stop Expression
Touch object → Click "EMOTES" → Click "STOP EMOTE" → NPC talks with neutral face

---

## Status Display

The main dialog now shows:
```
NPC: Boros
Anim: STAND TALK 1
Emote: express_smile

Select option:
```

Shows both current body animation AND facial expression!

---

## Key Differences from Original

| Feature | Original npc.lsl | New npc_with_emotes.lsl |
|---------|------------------|-------------------------|
| Emote support | ❌ No | ✅ Yes |
| Separate menus | ❌ No | ✅ Yes (main + emotes) |
| Built-in emotes | ❌ No | ✅ Yes (if no inventory) |
| Status display | Shows animation only | Shows animation + emote |
| Independent control | ❌ No | ✅ Yes (body + face separate) |

---

## Advanced: Adding Custom Emotes

You can create facial expression animations and add them to inventory:

1. Name them starting with `express_` (e.g., `express_custom_wink`)
2. Add to object inventory
3. Script auto-detects and adds to emote menu

---

## Built-In Emotes Reference

If you DON'T add emote animations to inventory, these built-in buttons appear:

| Button | Expression | LSL Name |
|--------|------------|----------|
| 😊 Smile | Happy smile | `express_smile` |
| 😢 Sad | Sad face | `express_sad` |
| 😠 Angry | Angry face | `express_anger` |
| 😮 Surprise | Surprised | `express_surprise` |
| 😆 Laugh | Laughing | `express_laugh` |
| 😟 Worry | Worried | `express_worry` |

These are **built-in to OpenSim** - no inventory needed!

---

## Example Scenario

**Boros the Warrior Philosopher**

1. Touch object → Boros spawns
2. Touch → Select "read-standing" → Boros reads a book
3. Touch → Click "EMOTES" → Select "😟 Worry" → Boros reads with worried expression (contemplating philosophy!)
4. Touch → Select "TALK M 1" → Boros does masculine warrior talk
5. Touch → Click "EMOTES" → Select "😠 Angry" → Boros talks angrily (warrior mode!)
6. Touch → Click "EMOTES" → Select "😊 Smile" → Boros talks with smile (at peace)

Each NPC can express emotions while doing their signature animations!

---

## Troubleshooting

### "No emote buttons appear"
- Add at least one `express_*` animation to inventory, OR
- Use the built-in emote buttons (😊 😢 etc.)

### "Emote doesn't play"
- Built-in emotes (`express_*`) work without inventory
- Custom emotes must be in inventory and start with `express_`

### "Both animation and emote stop together"
- Click "STOP" only stops body animation
- Click "STOP EMOTE" only stops facial expression
- Use them independently!

---

## Migration from Original Script

Replace `npc.lsl` with `npc_with_emotes.lsl`:

**No changes needed to inventory!**
- Keep all your body animations as-is
- Optionally add `express_*` animations for custom emotes
- Script auto-adapts to what's in inventory

---

## Summary

✅ **Two-tier menu system**: Main (animations) + Emotes (facial expressions)
✅ **Auto-detection**: Separates body animations from facial expressions
✅ **Built-in fallback**: Uses OpenSim built-in emotes if none in inventory
✅ **Independent control**: Body and face animations work simultaneously
✅ **Status tracking**: Shows both current animation and current emote

Perfect for creating NPCs with personality and emotional expression! 🎭
