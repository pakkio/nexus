# NPC Narrative Prefix System

## Overview

Each NPC now receives a **personalized narrative context** that contains ONLY the information relevant to their character and role in the story. This replaces the previous approach of sending the full 70KB narrative to all NPCs or the wise guide.

## Implementation

### File Structure

**Naming Convention**: `NPC_PREFIX.<area>.<npcname>.txt`

Example:
- `NPC_PREFIX.city.irenna.txt`
- `NPC_PREFIX.village.garin.txt`
- `NPC_PREFIX.sanctumofwhispers.lyra.txt`

### File Sizes (Words / Tokens)

| NPC | Area | Words | Est. Tokens | Content Focus |
|-----|------|-------|-------------|---------------|
| **Erasmus** | Liminal Void | 264 | ~350 | Three Choices, Oblio philosophy, Final Promise |
| **Syra** | Ancient Ruins | 286 | ~380 | Ciotola mission, Cristallo importance, Transformation |
| **Jorin** | Tavern | 309 | ~410 | Latte della Memoria, Ciotola exchange, Dream Journal |
| **Mara** | Village | 304 | ~400 | Potion sale, Teleport flower, Connection to Elira |
| **Garin** | Village | 315 | ~420 | Metal memory, Iron exchange, Reconciliation tools |
| **Elira** | Forest | 328 | ~440 | Nature test, Healing philosophy, Nodo Primordiale |
| **Boros** | Mountain | 392 | ~520 | Flow philosophy, Mountain test, Mineral exchange |
| **Cassian** | City | 462 | ~615 | Money/Information power, Pergamena, Tabula Rasa |
| **Theron** | City | 501 | ~670 | Revolutionary philosophy, Dissolution advocacy, Codice |
| **Irenna** | City | 536 | ~715 | Living marionettes, Art vs Oblio, Final theater show |
| **Meridia** | Nexus | 586 | ~780 | Master Key, Final Choice, Multiple realities |
| **Lyra** | Sanctum | 608 | ~810 | Telaio dell'Eco, Chess test, Mission endpoint |

**Average Size**: 408 words (~545 tokens per NPC)

## Token Savings Analysis

### Previous System
- **Full narrative**: ~70,000 characters (~20,000 tokens)
- **Condensed narrative**: ~3,500 characters (~1,000 tokens) - used only by wise guide

### New System
- **Per NPC**: 264-608 words (350-810 tokens)
- **Average**: 408 words (~545 tokens per NPC)

### Savings
- **Compared to full narrative**: 97% reduction (20,000 → 545 tokens)
- **Compared to condensed**: 45% reduction (1,000 → 545 tokens)
- **Total savings across 12 NPCs**: ~18,000 tokens per NPC if using full narrative

## Content Design Philosophy

Each prefix file contains:

1. **Role in Story** - NPC's unique position in the narrative arc
2. **Mission Details** - What they need, what they give, why it matters
3. **Mission Chain Context** - Who comes before/after them in exchanges
4. **Directions** - Where they guide the Cercastorie next
5. **Philosophy/Themes** - Their worldview and symbolic meaning
6. **Relationships** - Key connections to other NPCs
7. **Final Reality** - What happens to them in different endings
8. **Special Knowledge** - Unique information only they possess

## Technical Integration

### Loading Function (`session_utils.py:88-112`)
```python
def _load_npc_narrative_prefix(npc_area: str, npc_name: str) -> str:
    """Load NPC-specific narrative context prefix."""
    area_normalized = npc_area.lower().replace(' ', '').replace('_', '')
    name_normalized = npc_name.lower().replace(' ', '').replace('_', '')
    prefix_filename = f"NPC_PREFIX.{area_normalized}.{name_normalized}.txt"

    try:
        with open(prefix_filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""  # No prefix for this NPC - okay
```

### System Prompt Integration (`session_utils.py:154-166`)
The NPC prefix is loaded and inserted **at the TOP** of the system prompt, before the standard character information:

```
================================================================================
CONTESTO NARRATIVO PERSONALIZZATO PER TE
================================================================================
[NPC-specific narrative context loaded from prefix file]
================================================================================

Sei {name}, un/una {role}...
[Standard character info continues]
```

## Benefits

1. **Contextual Awareness**: Each NPC knows their role in the larger story
2. **Mission Clarity**: NPCs understand why their exchanges matter
3. **Relationship Awareness**: NPCs know about connected characters
4. **Token Efficiency**: 97% reduction vs full narrative
5. **Personalization**: Each NPC receives only relevant information
6. **Maintainability**: Easy to update individual NPC contexts

## Future Enhancements

Potential improvements:
- Dynamic prefix generation based on story progress
- Include player's current quest state in prefix
- Add conditional sections based on completed missions
- Generate NPC-to-NPC awareness (who has met whom)

## Testing

To test NPC prefix loading:
```bash
python3 main.py --mockup --area City --npc Irenna --model "openai/gpt-4o-mini"
```

The NPC should demonstrate awareness of:
- Their role in the mission chain
- Other NPCs they're connected to
- The philosophical themes they represent
- Directions to the next location

## Wise Guide Context

The wise guide (Erasmus during `/hint` mode) receives:
- Condensed narrative (~1.3KB)
- Character/location map (~1KB)
- **Total**: ~2.3KB context

Regular NPCs receive:
- Personalized prefix (350-810 tokens)
- Character file from NPC.txt
- **Total**: ~1-2KB context

This creates a balanced system where NPCs are informed but not overwhelmed with irrelevant information.
