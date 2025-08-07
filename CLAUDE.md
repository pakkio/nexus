# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Testing and Quality
- `pytest` - Run all tests
- `python -m pytest <file>` - Run specific test file
- `python <module>_test.py` - Run individual test modules (e.g. `python chat_manager_test.py`)

### Running the Application
- `python main.py` - Start the text RPG with default settings (uses mockup if DB not configured)
- `python main.py --mockup` - Force using file-based mockup system
- `python main.py --help` - Show all command-line options
- `python load.py --storyboard <file.txt> --mockup` - Load game data into mockup system
- `python load.py --storyboard <file.txt> --db` - Load game data into MySQL database

### Second Life/LSL Integration
- `python lsl_main_gradio.py` - Web interface with SL header simulation
- `python lsl_main_simulator.py --mockup --player <avatar_name>` - Command-line LSL simulator
- `python test_sl_integration.py` - Run Second Life integration tests
- See [README-SL.md](README-SL.md) for comprehensive SL integration documentation

### Development Tools
- `python <module>.py` - Many modules include self-tests when run directly
- `poetry install` - Install dependencies (Poetry is configured)
- `poetry run python <command>` - Run commands within Poetry environment
- `black .` - Code formatting (configured in pyproject.toml)

### Game Commands
- `/areas` - Show all available areas with access levels and location information
- `/describe <area_name>` - Get detailed description of a specific location including NPCs, objects, and lore
- `/go <area>` - Move to a different area
- `/talk <npc_name>` - Start conversation with an NPC
- `/who` - Show NPCs in current area
- `/whereami` - Show current location and status
- `/npcs` - List all known NPCs across areas
- `/hint` - Consult with wise guide for guidance
- `/inventory` or `/inv` - Show player inventory and credits
- `/give <item> [to <npc>]` - Give item to NPC
- `/stats` - Show conversation statistics
- `/profile` - Show player psychological profile
- `/history` - Show conversation history
- `/help` - Show all available commands
- `/exit` or `/quit` - Exit the game

## Architecture Overview

This is an **AI-powered text RPG engine** called "Eldoria" that creates dynamic narrative experiences through LLM-driven NPCs and player profiling.

### Core Architecture

**Multi-Modal Data Storage**: The system supports both MySQL database and file-based mockup storage, allowing development without database setup.

**LLM Integration**: Uses OpenRouter API for multiple AI models:
- NPC dialogue generation
- Player psychological profiling  
- Natural language command interpretation
- Wise guide selection

**Second Life Integration**: Comprehensive LSL-compatible features:
- Real-time NPC deployment in virtual worlds
- Contextual SL commands (emotes, animations, object lookups)
- LSL HTTP header processing and response formatting
- Avatar context awareness and spatial references

**Modular Command System**: Commands are handled by dedicated modules in `command_handlers/` directory, with a central processor dispatching user input.

### Key Components

**Game State Management** (`main_core.py`):
- Central interaction loop
- State persistence across sessions
- Profile updates and item management
- Hint mode for consulting wise guides

**Chat Management** (`chat_manager.py`):
- Manages conversation history with NPCs
- Handles LLM streaming responses
- Tracks conversation statistics and tokens

**Database Abstraction** (`db_manager.py`):
- Unified interface for both MySQL and file-based storage
- Player profiles, inventory, conversation history
- NPC and storyboard data management

**Player Profiling** (`player_profile_manager.py`):
- Dynamic psychological analysis using LLMs
- Tracks traits, decision patterns, motivations
- Influences NPC responses and game hints

### Data-Driven Content

**NPCs**: Defined in `NPC.<area>.<name>.txt` files with standardized AI-friendly schema:

*New Standardized Schema Structure:*
- `# CORE PERSONALITY` - Basic character traits and behavior patterns
- `# QUEST MECHANICS` - Trading rules, required items, success/failure conditions  
- `# AI BEHAVIOR INSTRUCTIONS` - Conversation tracking and conditional responses
- `# SECOND LIFE INTEGRATION` - SL-specific commands and environment data
- `# TRADING MECHANICS` - Item exchange and credit systems

*Legacy Schema Fields (still supported):*
- `Emotes:` - Available gesture animations for SL
- `Animations:` - Character animations and actions
- `Lookup:` - In-world objects that can be referenced
- `Llsettext:` - Floating text display capabilities

**Locations**: Defined in `Location.<name>.txt` files with comprehensive area data:
- `Setting_Description:` - Rich environmental descriptions
- `Veil_Connection:` - Mystical/lore significance
- `Interactive_Objects:` - Items players can interact with
- `Special_Properties:` - Unique location mechanics
- `Connected_Locations:` - Navigation pathways
- `Quest_Relevance:` - Role in story progression

**Storyboards**: Game narratives in `Storyboard.<name>.txt` files defining world lore, themes, and overarching story.

**Dynamic Systems**:
- Item giving/receiving through `[GIVEN_ITEMS: item1, X Credits]` tags in NPC responses
- Plot flags and player state persistence  
- Multi-area exploration with both NPC areas and detailed Location data
- Enhanced `/describe` command for rich location exploration
- Second Life command generation: `[lookup=object;llSetText=message;emote=gesture;anim=action]`

### Environment Configuration

**Required**: `.env` file with OpenRouter API configuration:
```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_DEFAULT_MODEL=google/gemma-2-9b-it:free
PROFILE_ANALYSIS_MODEL=mistralai/mistral-7b-instruct:free
```

**Optional**: MySQL database credentials for persistent storage (defaults to mockup system).

### Testing Strategy

Most modules include embedded tests that run when executed directly. Core functionality is covered by:
- `chat_manager_tests.py` - Chat session management
- `db_manager_test.py` - Database operations
- `main_core_test.py` - Core game loop logic
- Individual module tests in `<module>_test.py` files

The system uses pytest fixtures in `conftest.py` and mock data in `mock_fixtures.py` for testing.

### Development Notes

**Gradio Integration**: Multiple Gradio web interfaces available (`main_gradio.py`, `main_gradio2.py`, etc.) for web-based interaction.

**Second Life Integration**: LSL-compatible modules for virtual world deployment:
- `lsl_main_gradio.py` - Web interface with SL header simulation
- `lsl_main_simulator.py` - Command-line simulator with SL context
- `game_system_api.py` - Core API with LSL text formatting

**File Structure**: Game uses three database directories for different contexts (`database_gradio_sim/`, `database_lsl_sim/`, `database_gradio_context_sim/`).

**Error Handling**: Extensive error handling with graceful degradation - missing LLM responses get placeholder text, DB failures fall back to defaults.