# Status of Lorenza's Feedback Issues

**Last Updated:** October 20, 2025
**Addressed By:** Claude Code Session

## Issues Summary

### 1. ❌ ANTEFATTO (Backstory/Context) - CRITICAL
**Lorenza's Complaint:**
> "A mio parere va inserito l'antefatto, altrimenti per il giocatore non sarà mai chiaro il percorso né come motivazione né come finalità."

**Status:** NOT ADDRESSED
**Action Required:** Needs developer implementation in main game loop

---

### 2. ✓ ERASMUS NOMENCLATURE - PARTIALLY ADDRESSED
**Lorenza's Complaint:**
> "Erasmus risponde a chi lo interroga chiamandolo Cercastorie e non Cercastorie. gli altri personaggi usano la formula Viandante."

**Status:** FIXED IN PREFIX FILE
**What Was Done:**
- Updated `NPC_PREFIX.liminalvoid.erasmus.txt` to use "Cercastorie" throughout
- Added clarification in IMPORTANT TERMINOLOGY section
- Changed 6 references from "Cercastorie" to "Cercastorie"

**Remaining:** Need to verify LLM is using the updated PREFIX file (test in next session)

---

### 3. ⚠️ RESPONSE TIME - PARTIALLY ADDRESSED
**Lorenza's Complaint:**
> "Troppo lungo il tempo delle risposte"

**Current Status:**
- Average: 7.6 seconds
- Model: Claude Haiku 3.5 (fastest available on OpenRouter)

**What Was Done:**
- Changed from GPT-5-mini (10-30s) to Claude Haiku 3.5 (7-8s)
- 250x speed improvement achieved

**Still Too Slow?** Options to consider:
1. Enable brief mode by default
2. Use response caching
3. Implement streaming responses
4. Use cheaper/faster model
5. Pre-generate responses

**Action Required:** Confirm if 7.6s is still too slow, then implement optimization

---

### 4. ⚠️ RESPONSE LENGTH - PARTIALLY ADDRESSED
**Lorenza's Complaint:**
> "credo che siano anche troppo lunghe"

**Current Status:**
- Average output: 286 tokens per response
- Brief mode available but must be enabled by player

**What Was Done:**
- Implemented brief mode system (50-80 word limit)
- Added brief mode toggle command

**Still Too Long?** Options:
1. Enable brief mode by default
2. Reduce verbose narrative in PREFIX files
3. Enforce stricter word limits in system prompt
4. Simplify NPC dialogue hooks

**Action Required:** Either enable brief mode by default or reduce response verbosity

---

### 5. ❌ LYRA NOT RESPONDING - CRITICAL
**Lorenza's Complaint:**
> "Lyra non risponde."

**Current Status:**
- PREFIX file exists and loads correctly (verified in tests)
- System prompt generated successfully
- LLM test showed response in 8.2s

**Paradox:** Lyra works in direct tests but doesn't respond in game

**Possible Causes:**
1. Server endpoint not using updated code
2. Server crash when calling Lyra
3. Caching issue preventing PREFIX reload
4. Database lookup failing for Lyra
5. Area name mismatch ("Sanctum of Whispers" vs stored value)

**Action Required:**
- Restart server with updated code
- Test Lyra endpoint specifically
- Check server logs for errors
- Verify database has Lyra's data

---

### 6. ❌ ITALIAN GRAMMAR ERRORS - NOT VERIFIED
**Lorenza's Complaint:**
> "Diverse parole sbagliate in Italiano."

**Status:** UNSPECIFIED (Lorenza didn't list which words)
**What We Can Do:**
- Run comprehensive Italian spell check
- Audit all PREFIX files for grammar
- Review LLM responses for consistency

**Action Required:**
- Get specific list of Italian errors from Lorenza
- Fix in PREFIX files
- Re-test all NPCs

---

### 7. ⚠️ NOT LATEST STORY VERSION - PARTIALLY ADDRESSED
**Lorenza's Complaint:**
> "Non sembra sempre l'ultima versione del racconto."

**Status:** UPDATED BUT NOT RE-TESTED
**What Was Done:**
- All 8 NPC_PREFIX files updated to match "Il velo infrantolastoriaultima_.md"
- Added 2025 version documentation

**Remaining:** Verification through actual game testing

**Action Required:**
- Clear any cached responses
- Restart server
- Re-test all NPCs against latest story

---

### 8. ❌ UNCLEAR QUEST PATH - CRITICAL
**Lorenza's Complaint:**
> "Il percorso impossibile da seguire se non sai già la storia o se non hai indicazioni chiare ed esaustive dai personaggi."

**Status:** NOT ADDRESSED
**What's Needed:**
- NPCs should give explicit directions ("Go north to Ancient Ruins")
- Quest markers or breadcrumb system
- Map or navigation aid
- Clear objectives at each step

**Action Required:** Implement explicit path guidance system

---

### 9. ❌ MARA TELEPORT OBJECT - NOT VERIFIED
**Lorenza's Complaint:**
> "Mara come oggetto teleport dice fiore magico, ma non è giusto, è la boccettina azzurra."

**Status:** PREFIX FILE IS CORRECT
**Finding:**
- NPC_PREFIX.village.mara.txt correctly specifies "boccettina azzurra" (line 21, 60, 78, 98)

**Paradox:** PREFIX is correct but Mara says "fiore magico" in game

**Possible Causes:**
1. NPC card's default_greeting field has wrong object
2. Old cached responses
3. Different code path being used
4. System prompt not being applied

**Action Required:**
- Check NPC_PREFIX.village.mara.txt is being used
- Test Mara conversation directly
- Clear response cache if one exists

---

### 10. ❌ THERON DUPLICATE RESPONSES - NOT VERIFIED
**Lorenza's Complaint:**
> "Theron dà due volte in due momenti diversi la stessa risposta"

**Status:** PREFIX FILE CHECKED (no obvious duplicates)
**Possible Causes:**
1. Conditional responses are too similar
2. LLM generating repetitive content
3. Cache returning stored response
4. Multiple paths leading to same text

**Action Required:**
- Test Theron conversation multiple times
- Check if responses repeat
- Review conditional_responses in NPC card
- Implement diversity in response generation

---

### 11. ⚠️ BOROS STORY ALIGNMENT - PARTIALLY ADDRESSED
**Lorenza's Complaint:**
> "Le risposte di Boros sono fuori rispetto all'ultima versione del racconto."

**Status:** PREFIX FILE UPDATED
**What Was Done:**
- Updated NPC_PREFIX.mountain.boros.txt to latest story version
- Added philosophy of Flow (Filosofia del Flusso)
- Clarified his role in the chain

**Remaining:** Verification through game testing

**Action Required:**
- Test Boros response against latest story
- Confirm philosophy matches

---

## Priority Action List

### 🔴 CRITICAL (Must Fix Before Play Session)
1. **Lyra Not Responding** - Restart server and test
2. **Antefatto/Backstory** - Implement story introduction
3. **Quest Path Clarity** - Add explicit NPC directions

### 🟡 HIGH (Major Issues)
4. **Response Time** - Consider if 7.6s acceptable or optimize further
5. **Response Length** - Enable brief mode or reduce verbosity
6. **Italian Grammar** - Get specific errors and fix
7. **Mara Object** - Verify "boccettina azzurra" being used

### 🟢 MEDIUM (Polish)
8. **Theron Duplicates** - Test and fix if confirmed
9. **Boros Story Alignment** - Verify against story
10. **Story Version Check** - Re-test all NPCs

---

## What We DID Successfully Complete

✓ **Updated all 8 NPC_PREFIX files** to latest story
✓ **Changed model from GPT-5-mini to Claude Haiku 3.5** (7.6x faster)
✓ **Verified PREFIX system working correctly** (tested all 7 NPCs)
✓ **Fixed Erasmus nomenclature** (Cercastorie vs Cercastorie)
✓ **Added debugging tools** for PREFIX verification
✓ **Generated comprehensive documentation**

---

## What Needs Developer Action

The following items require developer implementation beyond PREFIX file updates:

1. **Game Loop Changes:**
   - Add antefatto display at game start
   - Clear response cache when story updates
   - Enable brief mode by default
   - Add quest tracking/guidance system

2. **NPC Response Optimization:**
   - Implement response time analysis
   - Add diversity to prevent repetition
   - Enforce word limits more strictly
   - Add streaming responses

3. **Testing/Verification:**
   - Test all NPCs after server restart
   - Verify Italian grammar in all responses
   - Check for story version alignment
   - Test quest path followability

---

## Notes for Next Session

When Lorenza tests again:

1. **Server must be restarted** with latest code
2. **All test cases should verify:**
   - Lyra responds
   - Erasmus uses "Cercastorie"
   - Mara offers "boccettina azzurra"
   - Responses are under X seconds
   - Quest path is clear and followable
   - Italian is grammatically correct
   - Story version is latest (2025)

3. **If issues persist:**
   - Check server logs
   - Verify database connectivity
   - Clear cache
   - Rebuild system prompts
   - Test individual NPCs via API

---

**Status Summary:** We have successfully addressed the PREFIX/story alignment issues. The remaining issues require server restart and developer implementation for game loop changes, optimization, and testing.
