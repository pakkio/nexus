### opencode.md

#### Build, Lint, and Test Commands

##### General Testing
- **Run All Tests**: `pytest`
- **Run Specific Test File**: `python -m pytest <file>`
- **Run Individual Test Module**: `python <module>_test.py` (e.g., `python chat_manager_test.py`)

##### Code Formatting
- **Apply Formatting**: `black .`

##### Running the Application
- **Start the RPG**:
  - Default: `python main.py`
  - Force Mockup Mode: `python main.py --mockup`
  - Show Help: `python main.py --help`
- **Load Game Data**:
  - Mockup System: `python load.py --storyboard <file.txt> --mockup`
  - MySQL Database: `python load.py --storyboard <file.txt> --db`

##### Second Life (SL) Integration
- **Web Interface**: `python lsl_main_gradio.py`
- **Command-Line Simulator**: `python lsl_main_simulator.py --mockup --player <avatar_name>`

#### Code Style Guidelines

##### Imports
- Follow standard Python import order (stdlib -> third-party -> local).
- Use absolute imports where possible.

##### Formatting
- Formatting is enforced using `black` configured in `pyproject.toml`.

##### Types
- Utilize type hints consistently across functions and methods.
- Functions and methods should explicitly define input and output types.

##### Naming Conventions
- **Files and Modules**: Use `snake_case` for Python file names.
- **Classes**: Follow `PascalCase` for class names.
- **Variables and Functions**: Use `snake_case`.

##### Error Handling
- Centralized graceful degradation for system failures (fallbacks like placeholders or defaults for missing LLM responses or DB issues).

##### Testing Practices
- Place unit tests in dedicated `<module>_test.py` files.
- Use `pytest` fixtures (`conftest.py`) and mock data (`mock_fixtures.py`) for test setup.

##### Other Practices
- Maintain modularity for commands (each command has a separate handler in `command_handlers/`).
- Coverage includes inline self-tests for directly executable modules.