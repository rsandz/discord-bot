# Discord Hangouts Scheduler Bot

A Discord bot (and CLI tool) for scheduling and managing alarms and notifications in Discord servers or from the command line. Features include timezone-aware alarms, logical scheduling suggestions, and integration with OpenAI LLMs.

## Directory Structure

- `discordbot/` - Main Python package (source code)
- `tests/` - Unit tests
- `data/` - SQLite database location

## Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/) for dependency management
- OpenAI API key (for LLM features)
- (Optional) Discord bot token (for Discord integration)

## Setup

1. Install dependencies:
    ```bash
    poetry install
    ```
2. Set environment variables:
    - `OPENAI_API_KEY` (required)
    - `DISCORD_TOKEN` (if using Discord integration)

## Running the Bot

### CLI Mode (default)
Run the CLI-based scheduler:
```bash
poetry run python3 discordbot/main.py
```

### Discord Bot Mode
Run with Discord integration (requires `DISCORD_TOKEN`):
```bash
poetry run python3 discordbot/main.py --discord
```

You can also pass `--discord-token <YOUR_TOKEN>` to override the environment variable.

## Running Tests

To run the tests for this project using Poetry, execute the following command:

```bash
poetry run python3 -m unittest discover tests
```

This will run all the unit tests in the `tests` directory.