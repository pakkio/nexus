---
title: nexus
app_file: main_gradio2.py
sdk: gradio
sdk_version: 5.32.0
---
# Eldoria: AI-Assisted Text RPG Engine

Eldoria is a Python-based command-line application that provides a framework for creating and playing AI-assisted text-based role-playing games. It leverages Large Language Models (LLMs) for dynamic NPC dialogue, player psychological profiling, and even for selecting in-game guides. The system is designed to be data-driven, allowing game content (story, NPCs, areas) to be defined in simple text files.

## Core Features

*   **Multi-Model LLM Integration:** Uses different specialized LLMs for specific purposes:
    *   **Dialogue LLM** - Powers dynamic NPC conversations
    *   **Profile Analysis LLM** - Analyzes player psychology and behavior patterns
    *   **Guide Selection LLM** - Intelligently selects wise guides based on story context
    *   **Command Interpretation LLM** - Processes natural language commands
*   **Advanced Statistics Tracking:** Comprehensive LLM usage monitoring with real-time dashboards showing token usage, performance metrics, and activity status across all model types.
*   **Dynamic Player Profiling:** The system analyzes player interactions and dialogue choices to build and update a psychological profile for the player. This profile can subtly influence NPC behavior and hints.
*   **Data-Driven Content:** Game worlds, including storyboards and Non-Player Characters (NPCs), are defined in external `.txt` files, making content creation and modification accessible.
*   **Intelligent Hint System & Wise Guide:** Players can request hints from a "Wise Guide" NPC. The system uses an LLM to select the most appropriate NPC for this role based on the story's context.
*   **Command & Natural Language Input:** Players can interact using explicit commands (e.g., `/go tavern`) or by typing natural language phrases which the system attempts to interpret.
*   **Inventory & Basic Game State:** Manages player inventory, credits, and plot flags.
*   **Persistent State:** Player progress, inventory, and conversation history can be saved either to a MySQL database or a local file-based mockup system.
*   **Terminal Formatting:** Utilizes ANSI escape codes for colored and styled text output, enhancing readability.
*   **Modular Design:** Components like chat management, database interaction, LLM wrapping, and command handling are separated into distinct modules.

## Technology Stack

*   Python 3.x
*   **LLM Integration:** `requests` (for OpenRouter API)
*   **Database (Optional):** `mysql-connector-python`
*   **Environment Management:** `python-dotenv`
*   **Testing (Development):** `pytest`

## Prerequisites

*   Python 3.8+
*   Pip (Python package installer)
*   Git (for cloning the repository)
*   (Optional) MySQL Server if you intend to use a real database.

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd eldoria-engine # Or your repository name
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Create a `requirements.txt` file with the following content (or use one if provided):
    ```txt
    requests
    python-dotenv
    mysql-connector-python
    # pytest (for development/testing)
    ```
    Then install:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory of the project. This file will store your API keys and database credentials.
    ```env
    # --- OpenRouter API Configuration ---
    OPENROUTER_API_KEY="sk-or-v1-..." # Your OpenRouter API Key
    OPENROUTER_APP_URL="http://localhost:3000" # Your app's URL (can be placeholder)
    OPENROUTER_APP_TITLE="EldoriaClient" # Your app's name

    # --- Default LLM Models (via OpenRouter) ---
    # Model for NPC dialogue
    OPENROUTER_DEFAULT_MODEL="google/gemma-2-9b-it:free"
    # Model for player profile analysis (can be same as default)
    PROFILE_ANALYSIS_MODEL="mistralai/mistral-7b-instruct:free"
    # Model for selecting the "Wise Guide" NPC
    GUIDE_SELECTION_MODEL="openai/gpt-4.1-nano" # Or another suitable model

    # --- NLP Command Interpretation (Optional - Models for this are defined above) ---
    NLP_COMMAND_INTERPRETATION_ENABLED="true" # true or false
    NLP_COMMAND_CONFIDENCE_THRESHOLD="0.7" # 0.0 to 1.0
    # NLP_COMMAND_MODEL="google/gemma-2-9b-it:free" # If you want a specific model for this, otherwise uses PROFILE_ANALYSIS_MODEL or OPENROUTER_DEFAULT_MODEL

    # --- Database Configuration (Optional - for MySQL) ---
    # DB_HOST="localhost"
    # DB_PORT="3306"
    # DB_USER="your_db_user"
    # DB_PASSWORD="your_db_password"
    # DB_NAME="eldoria_db"
    # DB_TIMEOUT="10"
    ```
    *   **Important:** Get an API key from [OpenRouter.ai](https://openrouter.ai/).
    *   You can find available model identifiers on OpenRouter. The free models are good for testing.
    *   If you don't set database variables, or if you use the `--mockup` flag, the system will use a local file-based mockup.

5.  **Database Setup (Optional - for MySQL):**
    *   Ensure your MySQL server is running.
    *   Create a database (e.g., `eldoria_db`).
    *   The application will attempt to create the necessary tables (`PlayerState`, `PlayerInventory`, `NPCs`, `Storyboards`, `ConversationHistory`, `PlayerProfiles`) on first run if they don't exist, provided it can connect to the database specified in `.env`.

6.  **Load Game Data:**
    The game world (story, NPCs) is defined in `.txt` files. You need to load this data into the system.
    The `load.py` script handles this.

    *   **To load into the mockup file system (default if DB is not configured or `--mockup` is used implicitly by `main.py`):**
        ```bash
        python load.py --storyboard Storyboard.TheShatteredVeil.txt --mockup
        # Or for the other storyboard:
        # python load.py --storyboard Storyboard.TheQuadCosmos.txt --mockup
        ```
        This will create/populate a `database/` directory (or the one specified by `--mockup-dir`) with JSON files representing the game data.

    *   **To load into a MySQL database:**
        First, ensure your `.env` file has the correct `DB_HOST`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`.
        ```bash
        python load.py --storyboard Storyboard.TheShatteredVeil.txt --db
        # Or:
        # python load.py --storyboard Storyboard.TheShatteredVeil.txt --host <db_host> --user <user> --password <pass> --dbname <db_name>
        ```
        This will connect to your MySQL database, truncate existing `NPCs` and `Storyboards` tables, and load the new data. Player-specific tables (`PlayerState`, `PlayerInventory`, `ConversationHistory`, `PlayerProfiles`) are not truncated by `load.py`.

    *   **Resetting the Game (`reset_game` concept):**
        There isn't a single `reset_game` script provided in the PAK. However, you can achieve a full reset by:
        1.  **For MySQL:**
            *   Dropping and recreating the database.
            *   Alternatively, truncating all game-related tables (NPCs, Storyboards, PlayerState, PlayerInventory, ConversationHistory, PlayerProfiles).
            *   Then, running `python load.py --storyboard <your_story.txt> --db` to repopulate static world data.
        2.  **For Mockup:**
            *   Deleting the mockup directory (e.g., `rm -rf database/`).
            *   Running `python load.py --storyboard <your_story.txt> --mockup` to recreate and repopulate it.

## Running the Game

Once set up and data is loaded, you can run the game using `main.py`.

*   **Basic Usage (using mockup by default if DB isn't fully configured in .env):**
    ```bash
    python main.py
    ```
    This will typically start you in the "Sanctum of Whispers" (if "The Shattered Veil" storyboard is loaded) or try to determine a starting point.

*   **Using Mockup Explicitly:**
    ```bash
    python main.py --mockup
    ```

*   **Starting in a Specific Area/NPC:**
    ```bash
    python main.py --mockup --area Forest --npc Elira
    python main.py --mockup --area City
    ```

*   **Using a Specific LLM Model:**
    ```bash
    python main.py --mockup --model "anthropic/claude-3-haiku"
    ```

*   **Specifying a Player ID:**
    ```bash
    python main.py --mockup --player MyHeroName
    ```

*   **Debug Mode (shows more internal info, including profile updates):**
    ```bash
    python main.py --mockup --debug
    ```

*   **Show LLM Stats Automatically:**
    ```bash
    python main.py --mockup --show-stats
    ```

*   **Connecting to MySQL (if configured in `.env` and data loaded with `--db`):**
    If your `.env` is correctly set up for MySQL, `main.py` will attempt to use it by default unless `--mockup` is specified.
    ```bash
    python main.py # Attempts to use DB if .env is configured
    ```

## Game Mechanics & Concepts

### Interacting
*   **Dialogue:** Simply type what you want to say to the current NPC.
*   **Commands:** Start with a `/`. Key commands include:
    *   `/help`: Shows available commands.
    *   `/go <area_name_fragment>`: Move to an area (e.g., `/go tavern`, `/go ancient`).
    *   `/talk <npc_name>`: Talk to a specific NPC in your current area (e.g., `/talk Lyra`).
    *   `/talk .`: Talk to a random (actually, the first available) NPC in the current area.
    *   `/who`: List NPCs in the current area.
    *   `/whereami`: Show current location and NPC.
    *   `/inventory` or `/inv`: Show your items and credits.
    *   `/give <item_name>`: Give an item to the current NPC.
    *   `/give <amount> Credits`: Give credits.
    *   `/hint`: Consult the "Wise Guide" for advice.
    *   `/endhint`: Stop consulting the Wise Guide and return to your previous context.
    *   `/profile`: View your character's psychological profile.
    *   `/stats`: Show LLM stats for the last dialogue turn with status overview.
    *   `/session_stats`: Show dialogue session stats plus comprehensive breakdown.
    *   `/all_stats`: Show comprehensive statistics dashboard for all LLM types.
    *   `/clear`: Clears the current in-memory conversation history with the NPC.
    *   `/exit` or `/quit`: Exit the game.
*   **Natural Language Commands:** The system attempts to interpret common phrases as commands (e.g., "vado in taverna" might become `/go Tavern`).

### Player Profile
As you interact, the game builds a psychological profile based on your choices, dialogue, and actions. This includes:
*   `core_traits`: Numerical values for traits like Curiosity, Caution, Empathy, Aggression, etc.
*   `decision_patterns`: Tags describing your common decision-making approaches.
*   `key_experiences_tags`: Tags for significant events or interactions.
*   `interaction_style_summary`: A textual summary of how you tend to interact.
*   `veil_perception`: Your character's evolving view of the "Veil" (if relevant to the story).
*   `trust_levels`: How much your character trusts others in general or specific NPCs.
*   `inferred_motivations`: What seems to be driving your character.

This profile can be viewed with `/profile` and is used by the LLM to subtly tailor NPC responses and hints from the Wise Guide.

### Hint System & Wise Guide
The `/hint` command allows you to consult a "Wise Guide" NPC.
*   The `wise_guide_selector.py` module uses a dedicated LLM to analyze the main storyboard and the list of available NPCs to determine who is best suited for this role (e.g., Lyra in "The Shattered Veil").
*   When you use `/hint`, your current conversation is paused, and a new one begins with the Wise Guide. The guide is provided with context about your recent interactions and your player profile to give relevant advice.
*   `/endhint` returns you to your previous conversation.
*   Hint consultations are tracked separately from regular dialogue in the stats system.

### Multi-Model LLM Statistics
The system provides comprehensive tracking and monitoring of all LLM usage:
*   **Real-time Status Indicators:** Color-coded emoji indicators show which LLM types are active
*   **Performance Metrics:** Token usage, timing, throughput for each model type
*   **Usage Categories:**
    *   🟢 **Dialogue** - Regular NPC conversations
    *   🟡 **Profile** - Player psychological analysis 
    *   🔵 **Guide Selection** - Wise guide consultations
    *   🟠 **Command Interpretation** - Natural language processing
*   **Statistical Commands:**
    *   `/stats` - Last dialogue turn + status overview
    *   `/session_stats` - Current session + comprehensive breakdown
    *   `/all_stats` - Complete multi-model dashboard with detailed breakdowns

### Inventory, Credits & Plot Flags
*   **Inventory:** You can acquire items, which are stored in your inventory.
*   **Credits:** The game includes a basic currency system.
*   **Plot Flags:** Internal variables that track story progression or player achievements. These are managed by the game logic and can influence NPC dialogue or available options (though this is more an implicit feature of how an NPC's `system_prompt` might be designed to react to them).

## Creating Content

Game content is defined in `.txt` files.

### Storyboard Files
*   Format: `Storyboard.<YourStoryName>.txt`
*   Structure:
    ```text
    Name: <Title of the Story>
    Description:
    <Paragraph 1 of the story description/premise.>
    <Paragraph 2, and so on.>
    Temi: (or Themes:)
    - <Theme 1>
    - <Theme 2>
    ```
*   Example: `Storyboard.TheShatteredVeil.txt`

### NPC Files
*   Format: `NPC.<AreaName>.<NPCName>.txt` (e.g., `NPC.Forest.Elira.txt`)
    *   The `AreaName` and `NPCName` from the filename are used as part of the NPC's unique `code` in the database/mockup (e.g., `forest.elira`).
*   Structure (Key-Value pairs, multi-line values are appended):
    ```text
    Name: <NPC's Display Name>
    Area: <Area where the NPC is found>
    Role: <NPC's role or job>
    Motivation: <What drives this NPC? Can be multi-line.>
    Goal: <What does this NPC want to achieve? Can be multi-line.>
    Needed Object: <Specific item the NPC might need from the player for a quest.>
    Treasure: <Item the NPC might give as a reward. Format: "Item Name" or "X Credits">
    Veil Connection: <How this NPC relates to the central theme/mystery (e.g., the Veil). Can be multi-line.>
    PlayerHint: <A hint for the player on how to interact or what this NPC offers/needs. Can be multi-line.>
    Dialogue Hooks:
    - "<A sample line of dialogue or typical phrase>"
    - "<Another hook, perhaps situational>"
    - "(Contextual_Hook_Category): Specific type of hook, e.g., (Initial)"
    - "  - <Hook under the category>"
    ```
*   **Important for NPC giving items/credits:**
    If an NPC's dialogue results in them giving an item or credits to the player, the LLM is instructed to append a special line at the VERY END of its response:
    `[GIVEN_ITEMS: ItemName1, Amount Credits, ItemName2, ...]`
    Example: `[GIVEN_ITEMS: Healing Potion, 50 Credits]`
    The `main_core.py` parses this tag to update the player's inventory and credits.

## Example Scenario: "Office Life"

Let's create a minimal "Office Life" scenario.

1.  **Create `Storyboard.OfficeLife.txt`:**
    ```text
    Name: A Day at OmniCorp
    Description:
    Welcome to OmniCorp, where the coffee is lukewarm and the deadlines are always looming.
    Navigate the treacherous waters of office politics, try to get your work done, and maybe uncover
    the mystery of the perpetually jammed printer.
    Temi:
    - Bureaucracy
    - Teamwork (or lack thereof)
    - The daily grind
    ```

2.  **Create `NPC.Office.Bob.txt`:**
    ```text
    Name: Bob
    Area: Office
    Role: Senior Accountant, Perpetually Stressed
    Motivation: Finish the quarterly reports before his ulcer acts up. Avoid any extra work.
    Goal: Get the TPS report figures from Alice.
    Needed Object: TPS Report Figures
    Treasure: Stapler (He has many, might give one if very grateful)
    Veil Connection: Believes the printer is possessed by the ghost of a disgruntled intern.
    PlayerHint: Bob needs figures from Alice for his report. He's stressed and not very helpful unless it benefits him. Offering coffee might make him more receptive.
    Dialogue Hooks:
    - "Don't talk to me unless it's about those TPS figures."
    - "Is it 5 o'clock yet? This quarter is killing me."
    - "If Alice doesn't get me those numbers, heads will roll. Mostly mine."
    - "(If offered coffee): Oh, thank heavens. Maybe I can think straight for five minutes."
    ```

3.  **Create `NPC.Office.Alice.txt`:**
    ```text
    Name: Alice
    Area: Office
    Role: Marketing Specialist, Overworked
    Motivation: Launch the new "SynergyMax" campaign successfully. Get Bob off her back about some report.
    Goal: Get approval for the new campaign slogan from Carol in HR.
    Needed Object: Campaign Slogan Approval
    Treasure: OmniCorp Branded Pen
    Veil Connection: Suspects a rival department is sabotaging the coffee machine.
    PlayerHint: Alice is busy with her campaign. She needs Carol's approval for a slogan. She might have the TPS figures Bob needs if you help her.
    Dialogue Hooks:
    - "SynergyMax is going to be huge, if I can just get this slogan approved!"
    - "Bob needs what now? Ugh, tell him I'm swamped. Unless... you could help me with something?"
    - "Carol in HR holds the keys to my campaign's success. And my sanity."
    ```

4.  **Create `NPC.HR.Carol.txt`:**
    ```text
    Name: Carol
    Area: HR Department
    Role: HR Manager, Stickler for Rules
    Motivation: Ensure all company policies are followed. Maintain order and compliance.
    Goal: Process all pending employee onboarding forms.
    Needed Object: Signed Onboarding Form (from a new hire, perhaps the player?)
    Treasure: "Employee of the Month" Certificate (Blank)
    Veil Connection: Secretly writes fan fiction about inter-departmental romances.
    PlayerHint: Carol is all about procedure. She might approve Alice's slogan if she's in a good mood, perhaps after some tedious HR task is completed for her.
    Dialogue Hooks:
    - "Policy 3.4.b clearly states all slogan proposals require form HR-1138."
    - "Have you seen the new hire's onboarding form? It's missing from my inbox."
    - "Creative slogans are fine, Alice, as long as they don't violate the company's inclusivity guidelines."
    ```

5.  **Load the "Office Life" Scenario (into mockup):**
    ```bash
    python load.py --storyboard Storyboard.OfficeLife.txt --mockup
    ```

6.  **Run the Game with the "Office Life" Scenario:**
    ```bash
    python main.py --mockup --area Office --npc Bob --player Intern1
    ```

    You'll start by talking to Bob. You can then try:
    *   Asking Bob about the TPS report.
    *   `/go Office` (if you want to see who else is there, then `/talk Alice`)
    *   `/go HR Department` then `/talk Carol`
    *   Try to get the TPS figures from Alice and give them to Bob.
    *   Try to get slogan approval from Carol for Alice.
    *   Use `/hint` to see who the "Wise Guide" is (it might be Carol due to her central HR role, or perhaps no one specific in this simple scenario).

## Directory Structure (Key Components)


.
├── Storyboard.TheShatteredVeil.txt # Example storyboard data
├── Storyboard.TheQuadCosmos.txt # Another example storyboard
├── NPC.AreaName.NPCName.txt # Numerous NPC data files
├── command_handlers/ # Python files for specific '/' command logic
│ ├── handle_go.py
│ └── ...
├── .env # For API keys and credentials (you create this)
├── chat_manager.py # Manages chat sessions and history
├── command_interpreter.py # Interprets natural language into commands
├── command_processor.py # Dispatches commands to handlers or LLM
├── db_manager.py # Handles database (MySQL/mockup) interactions
├── hint_manager.py # Logic for providing hints via Wise Guide
├── llm_stats_tracker.py # Multi-model LLM statistics tracking system
├── llm_wrapper.py # Interface to the LLM (OpenRouter)
├── load.py # Script to load story/NPC data
├── main.py # Main application entry point
├── main_core.py # Core interaction loop logic
├── main_utils.py # Utility functions for main
├── player_profile_manager.py # Manages dynamic player psychological profile
├── session_utils.py # Utilities for managing game sessions, NPCs
├── terminal_formatter.py # ANSI terminal formatting
├── wise_guide_selector.py # Selects the "Wise Guide" NPC
└── requirements.txt # Python dependencies (you create or is provided)

## Future Enhancements (Ideas)

*   **GUI:** A web-based or desktop GUI instead of CLI.
*   **More Complex Quest System:** Formal quest objects, tracking, and rewards.
*   **Combat System:** If desired for the RPG type.
*   **Skill/Attribute System:** Beyond the psychological profile.
*   **Multiplayer:** Allow multiple players to interact in the same world.
*   **Visual Maps/Area Descriptions:** More immersive world representation.
*   **Advanced NLP:** Finer-grained intent recognition and entity extraction.

## Contributing

Contributions are welcome! Please feel free to fork the repository, make changes, and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License
