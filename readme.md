# Discord Auto-Translate Bot (Argos Translate + Slash Commands)

Minimal bot that auto-detects **non-English** messages and replies with an **English** (or configurable) translation. Uses **Argos Translate** (open-source, offline) for translation and **langdetect** for language detection. Includes **slash commands** to enable/disable per-channel and set the target language.

## Requirements
- Python 3.11+ (or use Docker)
- A Discord Bot Token with **Message Content Intent** enabled

## Environment
- `DISCORD_TOKEN` (required)
- `DEFAULT_TARGET_LANG` (optional, default: `en`)
- `DEV_GUILD_ID` (optional; if set, slash commands register in that guild right away)
- `CONFIG_PATH` (optional, default: `config.json`)
- `ARGOS_PREINSTALL` (optional; comma list like `es->en,fr->en`)

## Run (local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U discord.py argostranslate langdetect
export DISCORD_TOKEN=your_token_here
python bot.py
```

## Run (Docker)
```bash
docker build -t discord-autotranslate .
docker run --rm \
  -e DISCORD_TOKEN=your_token_here \
  -e DEFAULT_TARGET_LANG=en \
  -e DEV_GUILD_ID=123456789012345678 \
  -v $(pwd)/config.json:/app/config.json \
  -v $HOME/.local/share/argos-translate:/root/.local/share/argos-translate \
  discord-autotranslate
```

> Tip: Mounting the Argos models directory persists downloaded translation models between container runs.

## Slash Commands
- `/enable_autotranslate [channel] [target_lang]` — enable auto-translation in a channel (defaults to current channel; default target = server default).
- `/disable_autotranslate [channel]` — disable in a channel (defaults to current).
- `/set_target_lang target_lang` — set server default target language (ISO 639-1, e.g., `en`, `es`).
- `/status_autotranslate [channel]` — show channel status and target.
- `/langs` — list installed Argos language codes.

Permissions: the enable/disable and settings commands require **Manage Server**.

## How it works
1. Listens to messages in enabled channels.
2. Detects source language with `langdetect`.
3. If source != target (default `en`), downloads the Argos model for that pair (first-time), then translates offline.
4. Replies with a clean embed (no mentions).

## Notes
- First translation for a language pair triggers a one-time model download to the Argos cache directory.
- To make startup snappier, set `ARGOS_PREINSTALL` with pairs you expect (e.g., `es->en,fr->en`).

## File layout
- `autoTranslate.py` — single-file bot with slash commands + JSON config.
- `Dockerfile` — container build.

## Troubleshooting
- Slash commands not visible in your test server? Set `DEV_GUILD_ID` to the server ID and restart the bot so commands register there immediately.
- If translations fail for a specific pair, ensure the pair exists in Argos models; try `/langs` to see what’s installed.
