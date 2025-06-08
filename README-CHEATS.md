# 🎮 The Shattered Veil - Player Guide & Quest Walkthrough

## 🚀 Quick Start Commands

```bash
# Start the game
python main.py --mockup

# Load the game world (run once)
python load.py --storyboard Storyboard.TheShatteredVeil.txt --mockup

# Start with specific player name
python main.py --mockup --player YourName

# Debug mode (see profile updates)
python main.py --mockup --debug
```

## 🗺️ Areas & NPCs Overview

| **Area** | **NPC** | **Role** | **Key Item** |
|----------|---------|----------|--------------|
| **Sanctum of Whispers** | Lyra | Wise Guide, Supreme Weaver | Echo Loom |
| **Ancient Ruins** | Syra | Incomplete Weaver | Ancient Memory Crystal |
| **Village** | Garin | Memory Smith | Iron Shavings |
| **Village** | Mara | Memory Herbalist | Healing Potion |
| **Forest** | Elira | Guardian of Natural Node | Forest Seed |
| **Mountain** | Boros | First Monk of Balance | Ancient Iron Ore |
| **Tavern** | Jorin | Keeper of Lost Dreams | Sacred Offering Bowl |
| **City** | Theron | Leader of Progressives | Code of Tabula Rasa |
| **City** | Cassian | Opportunistic Bureaucrat | Wisdom Scroll |
| **City** | Irenna | Puppeteer of Resistance | Enchanted Puppet |
| **Liminal Void** | Erasmus | Ambassador of Oblivion | Vision of Fertile Void |
| **Nexus of Paths** | Meridia | Weaver of Destiny | Loom of New Beginning |

## 🎯 Complete Quest Walkthrough

### 📋 **MAIN QUEST: The Memory Chain**

**Starting Requirements:** 50+ Credits (default starting amount: 220)

#### **Step 1: Village → Mara**
```
/go village
/talk mara
[Give 50 Credits]
→ Receive: Healing Potion
```

#### **Step 2: Forest → Elira**
```
/go forest
/talk elira
[Give Healing Potion]
→ Receive: Forest Seed
```

#### **Step 3: Mountain → Boros**
```
/go mountain
/talk boros
[Give Forest Seed]
→ Receive: Ancient Iron Ore
```

#### **Step 4: Village → Garin**
```
/go village
/talk garin
[Give Ancient Iron Ore]
→ Receive: Iron Shavings
```

#### **Step 5: Tavern → Jorin**
```
/go tavern
/talk jorin
[Give Iron Shavings]
→ Receive: Sacred Offering Bowl
```

#### **Step 6: Ancient Ruins → Syra**
```
/go ancient
/talk syra
[Give Sacred Offering Bowl filled with water]
→ Receive: Ancient Memory Crystal
```

#### **Step 7: Sanctum → Lyra (MAIN REWARD)**
```
/go sanctum
/talk lyra
[Give Ancient Memory Crystal]
→ Receive: Echo Loom (Major Artifact)
```

### 💰 **SIDE QUEST: The Wisdom Path**

#### **Step 1: City → Cassian**
```
/go city
/talk cassian
[Give 100 Credits]
→ Receive: Wisdom Scroll
```

#### **Step 2: City → Theron**
```
/go city
/talk theron
[Give Wisdom Scroll]
→ Receive: Code of Tabula Rasa
```

### 🎭 **ADVANCED QUEST: The Memory Thread**

**Requirements:** Complete several other quests first

#### **City → Irenna**
```
/go city
/talk irenna
[Complete other questlines first to unlock Memory Thread]
→ Receive: Enchanted Puppet
```

### 🌌 **ENDGAME: The Ultimate Choice**

#### **Nexus → Meridia (FINAL QUEST)**
```
/go nexus
/talk meridia
[Bring Master Key - proof of completing multiple faction questlines]
→ Receive: Loom of New Beginning (Game Ending Choice)
```

## 🎲 Essential Commands

### **Movement & Exploration**
```
/go <area>          # Move to area (tavern, village, city, forest, mountain, etc.)
/whereami           # Show current location
/areas              # List all available areas
/who                # List NPCs in current area
/talk <npc_name>    # Talk to specific NPC
/talk .             # Talk to any available NPC
```

### **Inventory & Items**
```
/inventory          # Show your items and credits
/inv                # Short version of inventory
/give <item_name>   # Give item to current NPC
/give <amount> Credits  # Give credits to current NPC
```

### **Game System**
```
/hint               # Consult Lyra (the Wise Guide) for advice
/endhint            # Stop consulting the Wise Guide
/profile            # View your character's psychological profile
/stats              # Show dialogue stats + LLM status overview
/session_stats      # Show dialogue session + comprehensive breakdown
/all_stats          # Complete multi-model LLM statistics dashboard
/clear              # Clear conversation history with current NPC
/help               # Show all available commands
/exit               # Exit the game
```

## 💡 Pro Tips & Strategies

### **Credit Management**
- **Starting Credits:** 220
- **Budget Wisely:** Main quest needs 50, side quest needs 100
- **Total Required:** 150 Credits minimum for both quest lines
- **Leftover Credits:** 70 remaining for other activities

### **Optimal Quest Order**
1. **Start with Main Quest** (most important for story progression)
2. **Do Side Quest** if you have enough credits (100 needed)
3. **Explore philosophical NPCs** (Erasmus, other city NPCs)
4. **Advance to Endgame** (Meridia) only after significant progress

### **Conversation Strategy**
- **Be respectful** - NPCs respond to tone and approach
- **Show genuine interest** - Ask follow-up questions
- **Demonstrate understanding** - NPCs value wisdom over wealth
- **Use /hint** when stuck - Lyra provides guidance as Wise Guide

### **Character Development**
- Your **psychological profile** updates based on choices
- **Decision patterns** influence NPC responses
- **Profile viewing** with `/profile` shows your character growth
- **Debug mode** (`--debug` flag) shows profile updates in real-time
- **Profile analysis** tracked separately in stats (🟡 Profile LLM usage)

### **🤖 AI Performance Monitoring**
- **Token Efficiency:** Monitor input/output ratios across model types
- **Response Timing:** Track LLM response speeds for performance optimization
- **Model Usage Patterns:** See which AI features you use most
- **Session Analytics:** Comprehensive breakdown of all AI interactions

## 🔍 Secret Areas & Special NPCs

### **Liminal Void → Erasmus**
- **Access:** Available after making philosophical progress
- **Special:** Offers unique perspective on the Veil crisis
- **Reward:** Vision of the Fertile Void (philosophical insight)
- **Note:** Doesn't require items, only open conversation

### **Nexus of Paths → Meridia**
- **Access:** Only after proving understanding of multiple factions
- **Special:** Final choice for the game's ending
- **Requirement:** Master Key (earned through extensive questlines)
- **Note:** This is the game's climactic moment

## 🎨 NPCs by Philosophy

### **Preservationists (Memory Keepers)**
- **Lyra** (Sanctum) - Wise Guide, wants to preserve Weaver memories
- **Syra** (Ruins) - Incomplete Weaver, guards ancient knowledge
- **Elira** (Forest) - Nature guardian, values balance and empathy

### **Progressives (Future Seekers)**  
- **Theron** (City) - Believes Veil is a prison, seeks liberation
- **Cassian** (City) - Opportunistic bureaucrat, values survival
- **Irenna** (City) - Artist preserving truth through performance

### **Balancers (Middle Path)**
- **Boros** (Mountain) - Seeks transformation, not preservation or destruction
- **Garin** (Village) - Forges objects that resist oblivion
- **Mara** (Village) - Pragmatic healer, focuses on protecting people

### **Outsiders (Unique Perspectives)**
- **Jorin** (Tavern) - Unknowingly collects lost memories
- **Erasmus** (Liminal) - Transformed by Oblivion, offers alien perspective
- **Meridia** (Nexus) - Final arbiter, represents ultimate choice

## 🐛 Debug Commands & Cheats

### **Developer Mode**
```bash
# Enable verbose output
python main.py --mockup --debug

# Show statistics automatically
python main.py --mockup --show-stats

# Start in specific area with specific NPC
python main.py --mockup --area Village --npc Garin

# Use specific LLM model
python main.py --mockup --model "anthropic/claude-3-haiku"

# Use different models for different purposes
python main.py --mockup \
  --model "anthropic/claude-3-haiku" \
  --profile-analysis-model "openai/gpt-4o-mini" \
  --guide-selection-model "google/gemma-2-9b-it:free"
```

### **📊 Advanced Stats Monitoring**
```
/all_stats          # Complete LLM usage dashboard
                    # Shows: 🟢 Dialogue • 🟠 Commands • 🟡 Profile • 🔵 Guide
                    # Includes: Token usage, timing, throughput per model type
                    # Displays: Real-time status indicators and session totals

/stats              # Quick dialogue stats + status overview
/session_stats      # Current session + all model types breakdown
```

### **🎯 Model Type Tracking**
- **🟢 Dialogue:** Regular NPC conversations
- **🟠 Command Interpretation:** Natural language processing  
- **🟡 Profile Analysis:** Player psychological profiling
- **🔵 Guide Selection:** Wise guide consultation sessions
- **🔴 Inactive:** Model types not yet used in session

### **File Locations (Mockup Mode)**
```
database/PlayerState/        # Player progress saves
database/PlayerProfiles/     # Character psychological profiles  
database/ConversationHistory/ # Chat logs with NPCs (dialogue tracked separately)
database/NPCs/               # NPC data files
database/Storyboards/        # World lore and story data
```

### **📈 Statistics Data**
- **In-Memory Tracking:** LLM stats tracked globally during session
- **Model Type Classification:** Each AI call categorized by purpose
- **Performance Metrics:** Token usage, timing, throughput per model
- **Real-time Dashboard:** Live status indicators and usage breakdowns

## 🎭 Roleplay Suggestions

### **Character Archetypes**
- **The Scholar** - Focuses on understanding all perspectives before choosing
- **The Pragmatist** - Makes choices based on practical outcomes
- **The Idealist** - Follows philosophical principles regardless of cost
- **The Mediator** - Seeks compromise and balance between factions

### **Conversation Approaches**
- **Respectful Inquiry** - Ask thoughtful questions about NPC motivations
- **Philosophical Challenge** - Engage with deeper themes about memory and identity  
- **Practical Focus** - Concentrate on concrete solutions and outcomes
- **Emotional Connection** - Share personal thoughts and feelings

## 🏆 Achievements & Milestones

### **Quest Completion**
- ✅ **Memory Chain Master** - Complete the main quest line to Lyra
- ✅ **Wisdom Seeker** - Complete the side quest to Theron  
- ✅ **Faction Diplomat** - Successfully interact with all three philosophical factions
- ✅ **Ultimate Choice** - Reach Meridia and make the final decision

### **Exploration Rewards**
- ✅ **World Traveler** - Visit all areas in the game
- ✅ **Social Butterfly** - Talk to every NPC at least once
- ✅ **Deep Thinker** - Have meaningful conversations with philosophical NPCs
- ✅ **Profile Master** - Develop a complex psychological profile through varied choices

---

*Remember: This is an AI-driven narrative experience. NPCs will respond dynamically to your choices and conversation style. No two playthroughs are exactly the same!*