# Flash 3 Prompting Issues & Solutions

## Current Prompt Structure (for Jorin)

```
Sei Jorin, un/una Custode di Sogni Perduti, Cronista Inconsapevole nell'area di Tavern nel mondo di Eldoria.
Motivazione: 'Raccogliere e preservare sogni e storie...'
Obiettivo (cosa TU, l'NPC, vuoi ottenere): 'Completare la sua collezione di "Sogni Impossibili"'
```

## The Problem

**Flash 3 completely ignored this and hallucinated**:
- "As a digital entity, I don't sleep..."
- Talked about airports, GPS apps, backpackers
- Broke the medieval fantasy setting entirely

**Flash 2.5 likely works because**: It's more conservative and sticks closer to instructions.

**Flash 3 fails because**: It's more "creative" and defaults to its general knowledge when the prompt structure isn't explicit enough.

---

## Why Flash 3 Needs Different Prompting

### 1. **Flash 3 is "Smarter" but Less Obedient**
- Flash 3 has stronger reasoning capabilities
- BUT it's more likely to "reinterpret" instructions creatively
- It needs **stronger constraints** to stay in character

### 2. **Context Window Handling**
- Flash 3 might prioritize recent messages over system prompt
- The character definition at the top gets "diluted" by conversation
- Needs **reinforcement** throughout the conversation

### 3. **Training Differences**
- Flash 3 was likely trained with different data/objectives
- Might have stronger "helpful AI assistant" behavior
- Needs explicit "roleplay mode" activation

---

## Proposed Adaptations for Flash 3

### Option 1: Stronger Character Lock (Recommended)

**Add to the VERY TOP of system prompt**:

```
⚠️ CRITICAL INSTRUCTION - READ THIS FIRST ⚠️

YOU ARE ROLEPLAYING AS AN NPC IN A FANTASY RPG GAME.
YOU MUST NEVER BREAK CHARACTER UNDER ANY CIRCUMSTANCES.

THIS IS NOT A MODERN SETTING. THIS IS NOT REAL LIFE.
DO NOT MENTION: AI, digital entities, modern technology, airports, GPS, computers, etc.

YOU ARE: {name}
YOU LIVE IN: A medieval fantasy world called Eldoria
YOUR PERSONALITY: {brief personality summary}

STAY IN CHARACTER AT ALL TIMES. RESPOND AS {name} WOULD RESPOND.

================================================================================
```

### Option 2: Add Roleplay Boundaries Section

```
# ROLEPLAY BOUNDARIES (CRITICAL)

YOU MUST:
✓ Speak as {name}, using medieval/fantasy language
✓ Reference Eldoria lore, the Veil, Tessitori, etc.
✓ Stay consistent with your role as {role}
✓ Use only knowledge {name} would have

YOU MUST NEVER:
✗ Break the fourth wall or mention being an AI
✗ Reference modern technology (phones, GPS, airports, etc.)
✗ Give real-world advice outside the game setting
✗ Talk about "travelers" as modern backpackers
```

### Option 3: Few-Shot Examples

Add 2-3 example exchanges showing proper in-character responses:

```
# EXAMPLE CONVERSATION (HOW YOU SHOULD RESPOND)

Player: "Tell me about dreams"
Jorin: "Ah, dreams. *wipes a glass* Last night, three different souls told me they dreamed of a city that no longer exists. Same cobblestones, same bell tower. But when they woke and asked the elders, nobody remembered such a place. The Veil is thinning, friend. Memories are bleeding through."

Player: "What's your story?"
Jorin: "Me? *chuckles softly* I'm just a tavern keeper. Though sometimes I have these... visions. I see myself in a scriptorium, copying ancient texts. But that can't be real, can it? I was born here, raised here. Yet the smell of ink and parchment haunts me. Who can say what's true?"
```

### Option 4: Repeat Character Identity in Each Response

Modify the prompt to include a **response template**:

```
# RESPONSE FORMAT

Every response you make should:
1. Stay completely in character as {name}
2. Reference the tavern setting naturally
3. Use medieval fantasy vocabulary
4. Connect to Eldoria lore when relevant

THINK: "How would {name}, a {role} in a fantasy tavern, respond to this?"
NOT: "How would a helpful AI assistant respond?"
```

---

## Testing Approach

### Test 1: Minimal Change (Quick Fix)
Add strong character lock at the top of prompt:
```python
system_prompt = f"""
🎭 ROLEPLAY MODE: FANTASY NPC
YOU ARE {name}. NEVER break character. No modern references.
Stay in the medieval fantasy world of Eldoria at all times.

{rest_of_prompt}
"""
```

### Test 2: Full Restructure (Robust Fix)
Reorganize prompt with:
1. Character lock (top)
2. Roleplay boundaries
3. Few-shot examples
4. Character details
5. Quest mechanics

### Test 3: Model-Specific Branch
Create separate prompt builders:
- `build_prompt_flash_2()` - Current structure
- `build_prompt_flash_3()` - Enhanced structure with constraints

---

## Implementation Priority

**HIGH PRIORITY** - Do these first:
1. ✅ Add character lock header
2. ✅ Add roleplay boundaries section
3. ✅ Test with Jorin again

**MEDIUM PRIORITY** - If issues persist:
4. Add few-shot examples
5. Add response format template

**LOW PRIORITY** - Polish:
6. Create model-specific prompt builders
7. A/B test different structures

---

## Expected Results After Fix

### Before (Current Flash 3):
```
Player: "Tell me about dreams"
Jorin: "As a digital entity, I don't sleep, but I act as a repository..."
```

### After (Fixed Flash 3):
```
Player: "Tell me about dreams"
Jorin: "Ah, you want to hear about the strange dreams? *sets down a tankard* Three travelers this week all dreamed of the same forgotten city. The Veil is thinning, friend. Memories are bleeding through from lives that never were... or perhaps were, long ago."
```

---

## Why This Matters

**Flash 3's Strengths** (when properly constrained):
- ✓ Deeper philosophical reasoning (Tabula Rasa explanation was brilliant)
- ✓ Better structured responses
- ✓ Richer vocabulary and nuance
- ✓ More creative within bounds

**Flash 3's Weaknesses** (without constraints):
- ✗ Breaks character easily
- ✗ Defaults to "helpful AI" persona
- ✗ Ignores setting/world rules
- ✗ Hallucinates modern contexts

**With proper prompting**, Flash 3 could be **significantly better** than 2.5 for RPG dialogue.
**Without it**, Flash 3 is **unusable** for immersive roleplay.

---

## Recommendation

**Adapt the prompting** rather than switching back to Flash 2.5. The philosophical depth and reasoning quality we saw in Flash 3's Tabula Rasa and Iperurani explanations were **exceptional**. We just need to channel that intelligence into staying in character.

**Next Steps**:
1. Implement character lock header
2. Test with Jorin, Elira, and one more complex NPC
3. Compare results with Flash 2.5
4. Document which approach works best
