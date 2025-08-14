# CRUSH.md

## Build/Lint/Test Commands

### Testing
- `pytest` - Run all tests
- `python -m pytest <file>` - Run specific test file
- `python <module>_test.py` - Run individual test modules (e.g. `python chat_manager_test.py`)

### Running Application
- `python main.py` - Start the text RPG with default settings
- `python main.py --mockup` - Force using file-based mockup system
- `python load.py --storyboard <file.txt> --mockup` - Load game data into mockup system

### Linting/Formatting
- `black .` - Format code (configured in pyproject.toml)
- `poetry install` - Install dependencies

## Code Style Guidelines

### Imports
- Use absolute imports when possible
- Group imports in standard order: standard library, third-party, local
- Avoid wildcard imports

### Formatting
- Use Black formatter (line length 88)
- Use double quotes for strings
- Use 4 spaces for indentation

### Types
- Use type hints for function parameters and return values
- Prefer explicit types over generic "Any"

### Naming Conventions
- Variables/functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE

### Error Handling
- Use specific exception types rather than generic except
- Always log errors appropriately
- Gracefully degrade when external services fail

### Additional Notes
- Most modules include self-tests when run directly
- Use existing libraries and utilities already in the codebase
- Follow existing patterns in the codebase