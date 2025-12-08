# NPC Manager Setup Guide

## Overview
This script allows you to rez and manage an NPC from a notecard with touch-based dialog controls for animations.

## Features
✅ **First touch**: Reads notecard and spawns NPC
✅ **Subsequent touches**: Shows dialog to destroy NPC or play animations
✅ **Auto-stops previous animation** before starting a new one
✅ **Clean NPC lifecycle management**

---

## Setup Instructions

### 1. Prepare Your Object

Create or select an object in Second Life that will be your NPC spawner.

### 2. Add Script and Notecard

**Add to object's Content tab:**
- `npc_manager.lsl` (the main script)
- `boros_notecard` (configuration notecard - see format below)
- All animation scripts that you want to use (already in your object):
  - `read-standing`
  - `STAND TALK 1`
  - `TALK2`
  - `TALK4`
  - `TALK 5`
  - `TALK 6`

### 3. Configure the Notecard

Create a notecard named `boros_notecard` with this format:

```
# Boros NPC Configuration
name=Boros
position=<1.0, 0.0, 0.0>
rotation=<0.0, 0.0, 0.0, 1.0>
```

**Configuration Options:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `name` | NPC display name | `Boros` |
| `position` | Spawn position relative to object (meters) | `<1.0, 0.0, 0.0>` (1m forward) |
| `rotation` | Spawn rotation (quaternion) | `<0, 0, 0, 1>` (forward) |
| `appearance` | Optional: saved appearance notecard | `boros_appearance` |

**Common Rotation Values:**
- `<0.0, 0.0, 0.0, 1.0>` - Facing same direction as object
- `<0.0, 0.0, 1.0, 0.0>` - Facing opposite direction (180°)
- `<0.0, 0.0, 0.707, 0.707>` - Facing left (90°)
- `<0.0, 0.0, -0.707, 0.707>` - Facing right (-90°)

### 4. Save and Reset Script

After adding all items, the script will auto-reset. You should see:
```
Touch to spawn NPC
```
displayed as floating text above the object.

---

## Usage

### Spawning the NPC

**Touch the object** → Script reads the notecard and spawns the NPC at the configured position.

You'll see:
```
Reading boros_notecard...
Notecard read complete. Spawning NPC...
NPC spawned successfully: <uuid>
```

Floating text changes to: `NPC Active - Touch for options`

### Managing the NPC

**Touch the object again** → Dialog appears with options:

**Dialog Buttons:**
- `DESTROY` - Remove the NPC completely
- `STOP` - Stop current animation
- `read-standing` - Play "read-standing" animation
- `STAND TALK 1` - Play "STAND TALK 1" animation
- `TALK2` - Play "TALK2" animation
- `TALK4` - Play "TALK4" animation
- `TALK 5` - Play "TALK 5" animation
- `TALK 6` - Play "TALK 6" animation

**Animation Behavior:**
- When you select an animation, any previously playing animation **automatically stops** first
- The new animation starts immediately
- Current animation name is displayed in the dialog message

### Destroying the NPC

Click `DESTROY` in the dialog → NPC is removed, object resets to "Touch to spawn NPC" mode.

---

## Customization

### Changing Available Animations

Edit the `availableAnims` list in the script:

```lsl
list availableAnims = [
    "read-standing",
    "STAND TALK 1",
    "TALK2",
    "TALK4",
    "TALK 5",
    "TALK 6"
];
```

**Important:** Animation names must **exactly match** the inventory item names in the object.

### Changing Notecard Name

Change the `notecardName` variable:

```lsl
string notecardName = "boros_notecard";
```

### Adjusting Spawn Position

Edit the notecard's `position` parameter:

```
# Spawn 2 meters in front, 1 meter to the right
position=<2.0, 1.0, 0.0>

# Spawn 3 meters behind
position=<-3.0, 0.0, 0.0>

# Spawn 1 meter above
position=<0.0, 0.0, 1.0>
```

**Coordinate system:**
- **X**: Forward (+) / Backward (-)
- **Y**: Left (-) / Right (+)
- **Z**: Up (+) / Down (-)

---

## Troubleshooting

### "Missing notecard!" error
**Problem:** The script can't find `boros_notecard`
**Solution:** Make sure the notecard is named exactly `boros_notecard` (case-sensitive) and is in the object's inventory

### "ERROR: Failed to spawn NPC!"
**Problem:** NPC creation failed
**Solutions:**
- Ensure you have permission to create NPCs in the region
- Check that the spawn position is valid (not inside walls/ground)
- Verify OpenSim OSSL functions are enabled

### NPC spawns underground/in the air
**Problem:** Position offset is incorrect
**Solution:** Adjust the `position` parameter in the notecard. Test with small values like `<1.0, 0.0, 0.0>` first

### Animation doesn't play
**Problem:** Animation name mismatch
**Solutions:**
- Verify animation name in `availableAnims` list matches inventory item exactly
- Check that the animation has full permissions
- Ensure animation is in the object's inventory

### "Only the owner can control this NPC"
**Problem:** Non-owner trying to use the object
**Solution:** This is by design for security. Only the object owner can spawn/control the NPC.

---

## Advanced: Using Custom Appearance

To make the NPC look like a specific avatar:

### Method 1: Save Appearance to Notecard

1. Have the avatar whose appearance you want to copy stand near the object
2. Get their UUID (avatar key)
3. Add this line to your script in `state_entry()`:
   ```lsl
   osAgentSaveAppearance(<avatar_uuid>, "boros_appearance");
   ```
4. Touch the object once (this creates the appearance notecard)
5. Remove the osAgentSaveAppearance line
6. Add to your `boros_notecard`:
   ```
   appearance=boros_appearance
   ```

### Method 2: Use Owner's Appearance (Default)

If no `appearance` parameter is specified, the NPC will use the object owner's current appearance.

---

## Example Configurations

### Standing Guard NPC
```
name=Guard Boros
position=<2.0, 0.0, 0.0>
rotation=<0.0, 0.0, 1.0, 0.0>
```
Spawns 2m in front, facing backward (toward object)

### Sitting Reader NPC
```
name=Scholar Boros
position=<0.5, 0.0, -0.5>
rotation=<0.0, 0.0, 0.0, 1.0>
```
Spawns 0.5m forward, 0.5m down (for sitting), facing forward

### Greeter NPC
```
name=Welcome Guide
position=<1.5, 0.0, 0.0>
rotation=<0.0, 0.0, 0.707, 0.707>
```
Spawns 1.5m in front, rotated 90° left

---

## Script Features Summary

| Feature | Description |
|---------|-------------|
| **Notecard-based config** | All spawn settings in external notecard |
| **Dynamic NPC creation** | Creates NPC on first touch |
| **Dialog interface** | Easy touch-based control |
| **Animation management** | Auto-stops previous animation |
| **Clean destruction** | Properly removes NPC and cleans up |
| **Owner-only control** | Security built-in |
| **Auto-reset on region change** | Handles region crossings gracefully |

---

## Credits

Script created for Eldoria NPC system integration with Second Life/OpenSim.
