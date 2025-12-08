# NPC Animation Assignments

## Available Animations
- inchino (bow/greeting)
- read-standing
- STAND TALK 1
- TALK 2
- TALK 5
- TALK 6
- TALK M 1
- TALK SIT 1
- TALK SIT 2
- TALK2
- TALK4

---

## Suggested Assignments by NPC

### 1. **Erasmus** (Liminal Void) - Philosophical Guide
**Character**: Ethereal, wise, contemplative, bridge consciousness
**Animations**:
- STAND TALK 1
- TALK 5
- TALK 6
- read-standing

**Rationale**: Gentle, contemplative movements. Read-standing fits his scholarly nature in the void.

---

### 2. **Meridia** (Nexus of Paths) - Weaver Guide
**Character**: Mystical, guiding, warm but formal
**Animations**:
- inchino (greeting travelers)
- STAND TALK 1
- TALK 2
- TALK 6

**Rationale**: Formal greeting (inchino) for welcoming seekers. Varied standing talks for guidance.

---

### 3. **Mara** (Village) - Pragmatic Healer
**Character**: Practical, direct, herbalist
**Animations**:
- STAND TALK 1
- TALK2
- TALK4
- TALK M 1

**Rationale**: Active, practical movements. No sitting - she's always working.

---

### 4. **Garin** (Village) - Blacksmith
**Character**: Craftsman, strong, practical
**Animations**:
- STAND TALK 1
- TALK M 1 (masculine talk)
- TALK2
- TALK4

**Rationale**: Strong, masculine gestures. Always standing at the forge.

---

### 5. **Jorin** (Tavern) - Innkeeper/Storyteller
**Character**: Jovial, storyteller, animated
**Animations**:
- TALK SIT 1 (sitting at bar)
- TALK SIT 2 (sitting with patrons)
- STAND TALK 1
- TALK 2

**Rationale**: Mix of sitting (behind bar) and standing (serving). Animated storytelling.

---

### 6. **Elira** (Forest) - Nature Guardian
**Character**: Calm, nurturing, connected to nature
**Animations**:
- STAND TALK 1
- TALK 5
- TALK 6
- read-standing (reading nature)

**Rationale**: Gentle, flowing movements. Read-standing = reading the forest.

---

### 7. **Boros** (Mountain) - Warrior Philosopher
**Character**: Strong, contemplative, disciplined
**Animations**:
- STAND TALK 1
- TALK M 1 (masculine/warrior)
- read-standing (studying philosophy)
- TALK2

**Rationale**: Mix of warrior strength and scholarly contemplation.

---

### 8. **Theron** (City) - Scholar/Merchant
**Character**: Intellectual, merchant of knowledge
**Animations**:
- TALK SIT 1 (at desk)
- TALK SIT 2 (with clients)
- read-standing
- STAND TALK 1

**Rationale**: Scholarly activities - reading, sitting at desk, discussing knowledge.

---

### 9. **Cassian** (City) - Warrior/Guardian
**Character**: Protective, strong, vigilant
**Animations**:
- STAND TALK 1
- TALK M 1 (masculine/warrior)
- TALK2
- TALK4

**Rationale**: Always standing guard. Strong, masculine movements.

---

### 10. **Irenna** (City) - Artist/Dreamer
**Character**: Creative, expressive, artistic
**Animations**:
- STAND TALK 1
- TALK 2
- TALK 5
- TALK 6

**Rationale**: Expressive, varied gestures for artistic personality.

---

### 11. **Lyra** (Sanctum of Whispers) - Memory Keeper
**Character**: Ancient, wise, formal, keeper of memories
**Animations**:
- inchino (formal greeting)
- TALK SIT 1 (at memory archive)
- read-standing
- TALK 5

**Rationale**: Formal, scholarly. Reading memories, greeting respectfully.

---

### 12. **Syra** (Ancient Ruins) - Incomplete Weaver
**Character**: Transformation, echo, incomplete
**Animations**:
- STAND TALK 1
- TALK 6
- TALK 5
- read-standing

**Rationale**: Gentle, ethereal movements. Reading ancient texts in ruins.

---

## Distribution Summary

### By Animation Type

**Scholarly NPCs** (use read-standing):
- Erasmus, Boros, Theron, Lyra, Syra, Elira

**Sitting NPCs** (use TALK SIT):
- Jorin (innkeeper)
- Theron (scholar at desk)
- Lyra (at archive)

**Formal NPCs** (use inchino):
- Meridia (greets travelers)
- Lyra (ancient formality)

**Warrior NPCs** (use TALK M 1):
- Garin (blacksmith)
- Boros (warrior)
- Cassian (guard)

**Active/Practical NPCs** (varied standing talks):
- Mara, Irenna, all others

---

## Quick Reference Table

| NPC | Animations |
|-----|-----------|
| Erasmus | STAND TALK 1, TALK 5, TALK 6, read-standing |
| Meridia | inchino, STAND TALK 1, TALK 2, TALK 6 |
| Mara | STAND TALK 1, TALK2, TALK4, TALK M 1 |
| Garin | STAND TALK 1, TALK M 1, TALK2, TALK4 |
| Jorin | TALK SIT 1, TALK SIT 2, STAND TALK 1, TALK 2 |
| Elira | STAND TALK 1, TALK 5, TALK 6, read-standing |
| Boros | STAND TALK 1, TALK M 1, read-standing, TALK2 |
| Theron | TALK SIT 1, TALK SIT 2, read-standing, STAND TALK 1 |
| Cassian | STAND TALK 1, TALK M 1, TALK2, TALK4 |
| Irenna | STAND TALK 1, TALK 2, TALK 5, TALK 6 |
| Lyra | inchino, TALK SIT 1, read-standing, TALK 5 |
| Syra | STAND TALK 1, TALK 6, TALK 5, read-standing |

---

## Implementation Notes

**For each NPC object**:
1. Name the object: `<NPCName>.<Location>` (e.g. `Boros.Mountains`)
2. Add `npc.lsl` script
3. Add appearance notecard with matching name (e.g. `Boros`)
4. Add ONLY the 4 animations listed for that NPC
5. The dialog will automatically show those 4 animations

**Benefits**:
- Each NPC has unique animation personality
- Talking animations vary (good for visual variety)
- Character-appropriate movements
- Limited to 4 animations per NPC (clean dialog menu)

---

## Optional: Add More Later

If you want to expand, you could add:
- Wave animations (for greetings)
- Combat animations (for warrior NPCs)
- Crafting animations (for Garin, Mara)
- Meditation animations (for Erasmus, Lyra)

But starting with these 4 per NPC gives each character distinct personality while keeping the dialog manageable!
