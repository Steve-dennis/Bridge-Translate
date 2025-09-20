# Contributing to Bridge-Translate

Thanks for your interest in contributing! This doc outlines local setup, common tasks, and expectations to keep the project healthy and predictable.

## Prerequisites
- Python 3.11+
- A shell environment (PowerShell on Windows, bash/zsh on Linux/macOS)

## Setup
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U -r requirements-dev.txt
pre-commit install
```

Windows (PowerShell):
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U -r requirements-dev.txt
pre-commit install
```

## Architecture Overview

### Message Flow
1. Listen for new messages in channels that are enabled for auto-translate.
2. Detect the source language with Lingua and apply the guild's detection policy.
3. When the detected language differs from the channel target (default `en`), ensure the Argos model for that language pair is installed, translate the text offline, and reply with an embed that omits mentions.
4. If the original message mentions members with user-level language preferences that differ from the detected language, post an additional summary embed grouped by each preferred language.

### Language Detection
- Lingua powers detection with short-text guards to avoid noise from emoji or fragments.
- Detection modes configured via `/set_detection_mode`:
  - `basic`: top-1 guess; permissive and prone to false positives.
  - `tolerant`: length-scaled thresholds with script-aware relaxation; may return `unknown` when ambiguous.
  - `curated`: restrict detection to `/set_supported_langs` with light weighting; optional boosts from members' preferred languages.
  - `strict`: allow-listed only (explicit via `/set_strict_langs` or derived from `/set_user_lang`), with heavy weighting toward the allowed set.
  - `off`: disables auto-translate while still allowing mention-triggered translations.
- Admin diagnostics: `/detect_status` summarizes the effective policy, while `/diagnostics` (Manage Server) returns a JSON payload.
- Advanced tuning is exposed through environment variables such as `DETECT_CONF_MIN_BASE`, `DETECT_GAP_MIN_BASE`, `DETECT_RATIO_MIN_BASE`, `DETECT_USE_PRIORS`, `DETECT_ALLOWED_STRICT_WEIGHT`, and related thresholds documented in `readme.md`.

### File Layout
- `main.py`: runtime entry point that wires dependencies and delegates to `bridge_translate` modules.
- `bridge_translate/boot.py`: shared startup routine (logging, command registration, bot.run).
- `bridge_translate/config.py`: stateless helpers to load and save configuration files.
- `bridge_translate/detection.py`: Lingua integration, thresholds, and curated/strict helpers.
- `bridge_translate/translate.py`: Argos Translate wrappers (model install, translate, preinstall).
- `bridge_translate/embeds.py`: Discord embed builders for auto-translate and mention summaries.
- `bridge_translate/handlers.py`: event implementations (`on_ready`, `on_message`) with dependency injection hooks for tests.
- `bridge_translate/commands.py`: command implementations, separate from decorators for testability.
- `bridge_translate/commands_public.py`: slash-command decorators that call into `commands.py`.
- `bridge_translate/registry.py`: registers public commands with the bot tree.
- `bridge_translate/state.py`: guild/channel/user configuration helpers and persistence.

## Linting & Formatting
- Ruff (imports, style, formatting):
```bash
ruff check . --fix
ruff format .
```

## Type Checking
- Mypy:
```bash
mypy Discord-Auto-Translate/main.py Discord-Auto-Translate/bridge_translate
# optional strict pass on modules you edit
mypy --strict Discord-Auto-Translate/bridge_translate
```

## Tests
- Run the full suite:
```bash
pytest -vv -ra
```
- Common flags:
```bash
pytest -s --log-cli-level=DEBUG             # show logs and prints
pytest --cov=main --cov-report=term-missing # coverage
pytest -k on_message -vv                    # filter by name
pytest --lf -vv                             # re-run last failures
pytest --maxfail=1 -x                       # fail-fast
```

Notes:
- Tests stub out Discord and Argos Translate; they must not access the network or download models.
- Tests use an isolated `.test-config.json`; don’t rely on your personal `config.json`.

## Running Locally (bot)
```bash
export DISCORD_TOKEN=your_token
python Discord-Auto-Translate/main.py
```
Optional environment:
- `DEV_GUILD_ID` to speed up slash command sync to a single server.
- `DEBUG_COMMANDS=1` to register dev-only commands like `/detect_debug`.

## Boot & Entrypoint
- `bridge_translate.boot.run(...)` centralizes startup: configure logging (defaults to `bridge_translate.boot.default_setup_logging`), register commands (defaults to `bridge_translate.registry.register_public_commands`), resolve the Discord token from `DISCORD_TOKEN`, `cfg.discord_token`, or `cfg.token`, optionally copy commands to `DEV_GUILD_ID`, then call `bot.run`.
- `main.main()` invokes `boot.run(...)` and keeps test-friendly helpers that expose undecorated command implementations when decorators are replaced during tests.

## Pull Request Guidelines
- Keep patches minimal and scoped; avoid unrelated changes.
- Update docs when adding behavior or commands:
  - `readme.md` (usage), `config.example.json` (schema),
  - `CHANGELOG.md` (notable changes), `UPGRADE.md` (behavior changes).
- Run before submitting:
  - `ruff check . --fix && ruff format .`
  - `mypy Discord-Auto-Translate/main.py Discord-Auto-Translate/bridge_translate`
  - `pytest -vv -ra`
- Do not commit secrets; prefer environment variables for tokens.

## Reporting Issues
Please include:
- Repro steps, expected vs. actual behavior
- Relevant logs or error messages (redact tokens)
- Bot mode (basic/tolerant/curated/strict/off) and any relevant guild config

Thank you for helping improve Bridge-Translate!
