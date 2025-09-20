# Bridge-Translate
![Language](https://img.shields.io/github/languages/top/Steve-dennis/Bridge-Translate)
![Size](https://img.shields.io/github/languages/code-size/Steve-dennis/Bridge-Translate)
![Issues](https://img.shields.io/github/issues/Steve-dennis/Bridge-Translate)
[![CI](https://github.com/Steve-dennis/Bridge-Translate/actions/workflows/ci.yml/badge.svg)](https://github.com/Steve-dennis/Bridge-Translate/actions/workflows/ci.yml)

Bridge-Translate keeps multilingual Discord servers moving by mirroring messages into a shared language without sending content to third-party APIs. The bot runs fully offline, utilizing dictionary matching to repost conversations in the target language you choose.

**Highlights**
- Self-hosted and privacy-friendly: translations stay on your machine while Argos models download only once per language pair.
- Smart detection modes tuned for Discord chatter, from permissive auto-translate to curated allow-lists and mention-only workflows.
- Mention-aware helpers so bilingual members can request ad-hoc translations without toggling channel settings.
- Slash commands for quick setup: enable channels, choose guild targets, manage personal language preferences, and inspect detection status.

## Quick Start (Modes)
- Basic (default): `/set_detection_mode basic` - always uses the detector's top detected language; often translates on false positives.
- Tolerant: `/set_detection_mode tolerant` - applies decision thresholds and optional re-weighting to reduce false positives; may drop valid translations.
- Curated: `/set_supported_langs en, es, fr` then `/set_detection_mode curated` - restricts languages to a list of supported languages and applies light weighting to make those languages slightly more likely to be detected.
- Strict (explicit): `/set_strict_langs es, fr` then `/set_detection_mode strict` - restrict to an explicit list and applies heavy weighting to make those languages more likely to be detected.
  - If `/set_strict_langs` is not set detection will fallback to users set `/set_user_lang` to create a list of allowed languages.
- Off (mentions only): `/set_detection_mode off` - disable auto‑translate; @mention translate still works.

## First-Time Setup
1) Create a Discord application and bot
- Visit https://discord.com/developers/applications -> New Application -> Bot -> Add Bot.
- Copy the Bot Token and keep it secret.
- Under Bot -> Privileged Gateway Intents -> enable Message Content Intent.

2) Invite the bot to your server
- OAuth2 -> URL Generator -> Scopes: check `bot` and `applications.commands`.
- Bot Permissions: View Channels, Send Messages, Embed Links, Read Message History.
- Open the generated URL, choose your server, and authorize.

3) **Optional** Priors help disambiguate short or ambiguous texts when tolerant detection is enabled.
    Generate `bridge_translate/data/speakers_priors.json` from upstream datasets:
    ```bash
    python scripts/gen_speakers_priors.py           # writes into bridge_translate/data
    python scripts/gen_speakers_priors.py --print   # print to stdout instead
    ```

3) Run the bot in Docker (recommended)
    ```bash
    docker build -t bridge-translate .
    docker run --rm \
      -e DISCORD_TOKEN=your_token_here \
      -e DEFAULT_TARGET_LANG=en \
      -e DEV_GUILD_ID=123456789012345678 \
      -v $(pwd)/config.json:/app/config.json \
      -v $HOME/.local/share/argos-translate:/root/.local/share/argos-translate \
      bridge-translate
    ```

4) Run the bot locally
    ```powershell
    # Powershell
    py -3.11 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -U -r requirements.txt
    $env:DISCORD_TOKEN = "your_token_here"   # or set in config.json
    # Optional: speed up slash command sync for one server
    # $env:DEV_GUILD_ID = "123456789012345678"
    python main.py
    ```

    ```bash
    # Bash
    python3.11 -m venv .venv
    source .venv/bin/activate
    pip install -U -r requirements.txt
    export DISCORD_TOKEN=your_token_here   # or set in config.json
    # Optional: export DEV_GUILD_ID=123456789012345678
    python main.py
    ```
  **Tip**: You can also put the token in your JSON config instead of an environment variable. Add a top-level `discord_token` key to the file referenced by `CONFIG_PATH` (default `config.json`):

```json
{
  "discord_token": "your_token_here",
  "guilds": {}
}
```


## Requirements
- Python 3.11+
- A Discord Bot Token with Message Content Intent enabled

## Environment
- `DISCORD_TOKEN` (required unless set in config)
- `DEFAULT_TARGET_LANG` (optional, default: `en`)
- `DEV_GUILD_ID` (optional; if set, slash commands register in that guild immediately)
- `CONFIG_PATH` (optional, default: `config.json`)
- `ARGOS_PREINSTALL` (optional; comma list like `es->en,fr->en`)
- `DEFAULT_ENABLE_ALL` (optional, default: `false`) - when `true`, treats all channels as enabled unless explicitly configured.
- `DETECTION_MODE_DEFAULT` (optional, default: `basic`) - default detection mode for guilds without an explicit setting.
  - Modes: `basic` (top‑1), `tolerant` (thresholds), `curated` (allow‑listed with mild weighting), `strict` (allow‑listed with heavy weighting), `off` (disable auto‑translate; mentions still work).
  - Change per server via `/set_detection_mode <basic|tolerant|curated|strict|off>`.
- `DETECT_USE_PRIORS` (optional, default: `false`) - reweight detection with language priors for short/ambiguous texts.
- `DETECT_PRIOR_ALPHA` (optional, default: `0.3`) - strength of priors when enabled.
- `DETECT_ALLOWED_STRICT_WEIGHT` (optional, default: `5.0`) - weighting applied to allow‑listed candidates in `strict` mode.
- `DETECT_ALLOWED_CURATED_WEIGHT` (optional, default: `2.0`) - weighting applied to allow‑listed candidates in `curated` mode.
- `DETECT_CANDIDATE_FLOOR` (optional, default: `0.25`) - in non‑basic modes, candidates with confidence below this are dropped before gating/weighting.
- Threshold tuning (optional; advanced): `DETECT_CONF_MIN_BASE` (0.88), `DETECT_GAP_MIN_BASE` (0.10), `DETECT_RATIO_MIN_BASE` (1.30),
  `DETECT_CONF_MIN_BOOST` (0.10), `DETECT_GAP_MIN_BOOST` (0.10), `DETECT_RATIO_MIN_BOOST` (0.50),
  `DETECT_SCRIPT_RELAX` (true), `DETECT_CONF_RELAX` (0.05), `DETECT_GAP_RELAX` (0.05), `DETECT_RATIO_RELAX` (0.20).
 - `DEBUG_COMMANDS` (optional, default: `false`) - when `true`, registers debug commands like `/detect_debug`.

## Developer Guide
For architecture notes, detection behavior details, file layout, linting, testing, and entrypoint information see `CONTRIBUTING.md`.



## Slash Commands
- `/enable_autotranslate [channel] [target_lang]` - enable auto-translation in a channel (defaults to current; target falls back to server default).
- `/disable_autotranslate [channel]` - disable in a channel (defaults to current).
- `/set_target_lang target_lang` - set server default target language (ISO 639-1, e.g., `en`, `es`).
- `/status_autotranslate [channel]` - show channel status and target.
- `/langs` - list installed Argos language codes.
- `/set_user_lang [user] target_lang` - set a user's preferred language for mention translations (users can set their own; managing others requires Manage Server).
- `/clear_user_lang [user]` - clear a user's preferred language (users can clear their own; managing others requires Manage Server).
- `/list_user_langs` - list users with preferred languages (Manage Server only).
- `/autotranslate_help` - show available commands and quick tips (ephemeral).
- `/set_detection_mode <basic|tolerant|curated|strict|off>` - choose detection behavior for auto-translate in this server.
- `/set_supported_langs <codes>` - set server supported source languages for curated/strict (comma/space‑separated list of ISO 639‑1 codes).
- `/get_supported_langs` - show server supported languages used by curated/strict.
- `/set_strict_langs <codes>` - set an explicit strict‑mode allow‑list (overrides deriving from user preferences).
- `/get_strict_langs` - show strict‑mode allow‑list (empty means derive from user preferences).
- `/diagnostics [text]` - admin‑only JSON diagnostics: mode, metrics, and effective allow‑list.

Server-wide:
- `/enable_autotranslate_all [target_lang]` - enable auto-translation in all channels (per-channel settings can still override).
- `/disable_autotranslate_all` - disable server-wide auto-translation.
- `/set_howto_on_enable <true|false>` - toggle first-time how-to message when enabling a channel.

**Permissions**: the enable/disable and settings commands require Manage Server.
