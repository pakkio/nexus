# Recommended Emotes for Each NPC

## Quick Reference: Which Emotes to Add to Each NPC Object

Based on personality, here are the recommended facial expressions for each NPC.

**Note:** You can either:
1. Add these `express_*` animations to inventory, OR
2. Use the built-in emote buttons in the EMOTES menu (no inventory needed)

---

## Happy/Friendly NPCs

### Jorin (Tavern Innkeeper)
**Personality**: Jovial, hospitable, storyteller
**Recommended emotes**:
- `express_smile` - Welcoming guests
- `express_laugh` - Enjoying tavern stories
- `express_toothsmile` - Big friendly smile

**Object Contents**:
- Body anims: TALK SIT 1, TALK SIT 2, STAND TALK 1, TALK 2
- Emotes: express_smile, express_laugh, express_toothsmile

---

### Meridia (Nexus Guide)
**Personality**: Wise, welcoming, ancient but warm
**Recommended emotes**:
- `express_smile` - Greeting travelers
- `express_open_mouth` - Sharing wisdom
- `express_worry` - Concern for seekers

**Object Contents**:
- Body anims: inchino, STAND TALK 1, TALK 2, TALK 6
- Emotes: express_smile, express_open_mouth, express_worry

---

### Mara (Village Healer)
**Personality**: Pragmatic, caring, worried about plants
**Recommended emotes**:
- `express_smile` - Compassionate healer
- `express_worry` - Concerned about disappearing plants
- `express_sad` - Remembering lost knowledge

**Object Contents**:
- Body anims: STAND TALK 1, TALK2, TALK4, TALK M 1
- Emotes: express_smile, express_worry, express_sad

---

## Serious/Scholarly NPCs

### Erasmus (Philosophical Guide)
**Personality**: Contemplative, transcendent, peaceful
**Recommended emotes**:
- `express_open_mouth` - Sharing cosmic wisdom
- `express_bored` - Eternally patient
- `express_smile` - Serene acceptance

**Object Contents**:
- Body anims: STAND TALK 1, TALK 5, TALK 6, read-standing
- Emotes: express_open_mouth, express_bored, express_smile

---

### Boros (Warrior Philosopher)
**Personality**: Balanced, strong, thoughtful
**Recommended emotes**:
- `express_anger` - Warrior intensity
- `express_frown` - Deep contemplation
- `express_smile` - Finding balance/peace

**Object Contents**:
- Body anims: STAND TALK 1, TALK M 1, read-standing, TALK2
- Emotes: express_anger, express_frown, express_smile

---

### Theron (Revolutionary Judge)
**Personality**: Intense, philosophical, haunted by loss
**Recommended emotes**:
- `express_disdain` - Rejecting old ways
- `express_anger` - Revolutionary passion
- `express_sad` - Missing his brother

**Object Contents**:
- Body anims: TALK SIT 1, TALK SIT 2, read-standing, STAND TALK 1
- Emotes: express_disdain, express_anger, express_sad

---

## Mystical/Sad NPCs

### Lyra (Memory Keeper)
**Personality**: Ancient, wise, sacrificial, burdened
**Recommended emotes**:
- `express_sad` - Burden of memories
- `express_worry` - Concerned about Veil
- `express_open_mouth` - Sharing ancient wisdom

**Object Contents**:
- Body anims: inchino, TALK SIT 1, read-standing, TALK 5
- Emotes: express_sad, express_worry, express_open_mouth

---

### Syra (Incomplete Weaver)
**Personality**: Tormented, ethereal, tragic
**Recommended emotes**:
- `express_sad` - Eternal sorrow
- `express_cry` - Failed transformation
- `express_afraid` - Trapped between worlds

**Object Contents**:
- Body anims: STAND TALK 1, TALK 6, TALK 5, read-standing
- Emotes: express_sad, express_cry, express_afraid

---

### Elira (Forest Guardian)
**Personality**: Empathic, nature-connected, gentle
**Recommended emotes**:
- `express_smile` - Compassionate nature
- `express_worry` - Concerned for forest
- `express_sad` - Witnessing decay

**Object Contents**:
- Body anims: STAND TALK 1, TALK 5, TALK 6, read-standing
- Emotes: express_smile, express_worry, express_sad

---

## Warriors/Strong NPCs

### Garin (Blacksmith)
**Personality**: Passionate, strong, dedicated
**Recommended emotes**:
- `express_angry` - Forging intensity
- `express_toothsmile` - Pride in craft
- `express_frown` - Focused concentration

**Object Contents**:
- Body anims: STAND TALK 1, TALK M 1, TALK2, TALK4
- Emotes: express_angry, express_toothsmile, express_frown

---

### Cassian (Guard)
**Personality**: Opportunistic, cautious, pragmatic
**Recommended emotes**:
- `express_anger` - Guard authority
- `express_disdain` - Judging clients
- `express_smile` - When paid well

**Object Contents**:
- Body anims: STAND TALK 1, TALK M 1, TALK2, TALK4
- Emotes: express_anger, express_disdain, express_smile

---

## Artists/Creative NPCs

### Irenna (Puppeteer)
**Personality**: Artistic, expressive, emotional
**Recommended emotes**:
- `express_smile` - Artistic joy
- `express_surprise` - Creative inspiration
- `express_laugh` - Delighting children
- `express_sad` - Preserving lost memories

**Object Contents**:
- Body anims: STAND TALK 1, TALK 2, TALK 5, TALK 6
- Emotes: express_smile, express_surprise, express_laugh, express_sad

---

## Summary Table

| NPC | Main Emotion | Emotes to Add |
|-----|--------------|---------------|
| **Jorin** | Happy/Welcoming | smile, laugh, toothsmile |
| **Meridia** | Wise/Concerned | smile, open_mouth, worry |
| **Mara** | Caring/Worried | smile, worry, sad |
| **Erasmus** | Peaceful/Contemplative | open_mouth, bored, smile |
| **Boros** | Balanced/Strong | anger, frown, smile |
| **Theron** | Intense/Sad | disdain, anger, sad |
| **Lyra** | Burdened/Wise | sad, worry, open_mouth |
| **Syra** | Tormented/Tragic | sad, cry, afraid |
| **Elira** | Gentle/Concerned | smile, worry, sad |
| **Garin** | Passionate/Proud | angry, toothsmile, frown |
| **Cassian** | Authoritative | anger, disdain, smile |
| **Irenna** | Expressive/Artistic | smile, surprise, laugh, sad |

---

## Optional: No-Inventory Setup

**Don't want to add animations?**

Use the built-in emote buttons! Just install `npc_with_emotes.lsl` with NO emote animations in inventory.

The EMOTES menu will show:
- 😊 Smile → `express_smile`
- 😢 Sad → `express_sad`
- 😠 Angry → `express_anger`
- 😮 Surprise → `express_surprise`
- 😆 Laugh → `express_laugh`
- 😟 Worry → `express_worry`

These work with NO inventory additions - they're built into OpenSim!

---

## Example: Complete Boros Setup

**Object name**: `Boros.Mountains`

**Inventory**:
- `npc_with_emotes.lsl`
- `Boros` (appearance notecard)
- `STAND TALK 1` (body animation)
- `TALK M 1` (body animation)
- `read-standing` (body animation)
- `TALK2` (body animation)
- `express_anger` (emote - optional)
- `express_frown` (emote - optional)
- `express_smile` (emote - optional)

**Result**:
- Touch → Spawns Boros
- Touch → Main menu shows 4 body animations + EMOTES button
- Click EMOTES → Shows anger, frown, smile facial expressions
- Can combine: read-standing + angry face = angry philosopher reading!

---

## Pro Tip: Contextual Emotions

Make NPCs more realistic by changing expressions based on conversation:

**Example: Boros**
1. Greeting: smile
2. Discussing philosophy: frown (thinking)
3. Talking about war: anger (intensity)
4. Finding balance: smile (peace)

**Example: Syra**
1. First meeting: sad (tormented)
2. Ritual failure: cry (despair)
3. Ritual success: smile (finally at peace!)

This creates emotional narrative arc for each NPC! 🎭
