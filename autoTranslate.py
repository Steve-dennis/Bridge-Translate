import os
import json
import asyncio
from typing import Optional, Dict, Any

import discord
from discord import app_commands
from discord.ext import commands

import argostranslate.package as argos_pkg
import argostranslate.translate as argos_tx

from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

DetectorFactory.seed = 0

DEFAULT_TARGET = os.getenv("DEFAULT_TARGET_LANG", "en")
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")
PREINSTALL = [s.strip() for s in os.getenv("ARGOS_PREINSTALL", "").split(",") if "->" in s]
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ALLOWED_MENTIONS = discord.AllowedMentions.none()

def _empty_cfg() -> Dict[str, Any]:
    return {"guilds": {}}

def load_cfg() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        return _empty_cfg()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _empty_cfg()

def save_cfg(cfg: Dict[str, Any]) -> None:
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)

CFG = load_cfg()

def get_installed_langs():
    return {lang.code: lang for lang in argos_tx.get_installed_languages()}

def ensure_model(src: str, dst: str) -> None:
    installed = get_installed_langs()
    if src in installed and any(t.code == dst for t in installed[src].translations):
        return
    argos_pkg.update_package_index()
    for pkg in argos_pkg.get_available_packages():
        if pkg.from_code == src and pkg.to_code == dst:
            path = pkg.download()
            argos_pkg.install_from_path(path)
            return
    raise ValueError(f"No Argos Translate model found for {src} -> {dst}.")

def translate_text(src: str, dst: str, text: str) -> str:
    ensure_model(src, dst)
    return argos_tx.translate(text, src, dst)

def preinstall_models(specs):
    if not specs:
        return
    argos_pkg.update_package_index()
    available = {(p.from_code, p.to_code): p for p in argos_pkg.get_available_packages()}
    for spec in specs:
        src, dst = spec.split("->", 1)
        if (src, dst) in available:
            path = available[(src, dst)].download()
            argos_pkg.install_from_path(path)

def detect_lang(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"

def channel_cfg(gid: int, cid: int) -> Dict[str, Any]:
    g = CFG["guilds"].get(str(gid), {})
    return (g.get("channels", {}) or {}).get(str(cid), {})

def guild_cfg(gid: int) -> Dict[str, Any]:
    return CFG["guilds"].get(str(gid), {})

def is_enabled(gid: int, cid: int) -> bool:
    return bool(channel_cfg(gid, cid).get("enabled", False))

def get_target(gid: int, cid: int) -> str:
    ch = channel_cfg(gid, cid)
    if "target" in ch and ch["target"]:
        return ch["target"]
    g = guild_cfg(gid)
    if "default_target" in g and g["default_target"]:
        return g["default_target"]
    return DEFAULT_TARGET

def set_channel(gid: int, cid: int, *, enabled: Optional[bool] = None, target: Optional[str] = None):
    s_gid, s_cid = str(gid), str(cid)
    CFG["guilds"].setdefault(s_gid, {"default_target": DEFAULT_TARGET, "channels": {}})
    CFG["guilds"][s_gid].setdefault("channels", {})
    ch = CFG["guilds"][s_gid]["channels"].get(s_cid, {})
    if enabled is not None:
        ch["enabled"] = enabled
    if target is not None:
        ch["target"] = target
    CFG["guilds"][s_gid]["channels"][s_cid] = ch
    save_cfg(CFG)

def set_guild_default_target(gid: int, target: str):
    s_gid = str(gid)
    CFG["guilds"].setdefault(s_gid, {"default_target": DEFAULT_TARGET, "channels": {}})
    CFG["guilds"][s_gid]["default_target"] = target
    save_cfg(CFG)

def mk_embed(src_lang: str, dst_lang: str, original: str, translated: str, author_name: str) -> discord.Embed:
    e = discord.Embed(title="Auto-translation", description=translated)
    e.add_field(name="Detected", value=src_lang, inline=True)
    e.add_field(name="→", value=dst_lang, inline=True)
    preview = original if len(original) <= 200 else (original[:197] + "…")
    e.add_field(name="Original", value=preview, inline=False)
    e.set_footer(text=f"Requested by {author_name}")
    return e

@bot.event
async def on_ready():
    try:
        preinstall_models(PREINSTALL)
    except Exception:
        pass
    try:
        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            await bot.tree.sync(guild=guild)
        else:
            await bot.tree.sync()
    except Exception:
        pass
    print(f"Logged in as {bot.user} (id={bot.user.id})")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.guild:
        return
    if not is_enabled(message.guild.id, message.channel.id):
        return
    content = (message.content or "").strip()
    if not content:
        return
    loop = asyncio.get_running_loop()
    src = await loop.run_in_executor(None, detect_lang, content)
    dst = get_target(message.guild.id, message.channel.id)
    if src in ("unknown", dst):
        return
    try:
        translated = await loop.run_in_executor(None, translate_text, src, dst, content)
    except Exception as e:
        await message.reply(f"Translation error for `{src}→{dst}`: {e}", allowed_mentions=ALLOWED_MENTIONS)
        return
    embed = mk_embed(src, dst, content, translated, message.author.display_name)
    await message.reply(embed=embed, mention_author=False, allowed_mentions=ALLOWED_MENTIONS)

@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.command(name="enable_autotranslate", description="Enable auto-translation in this or a specified channel.")
@app_commands.describe(channel="Channel to enable (defaults to current)", target_lang="Target ISO 639-1 (e.g., en)")
async def enable_autotranslate(inter: discord.Interaction, channel: Optional[discord.TextChannel] = None, target_lang: Optional[str] = None):
    channel = channel or inter.channel
    if not isinstance(channel, discord.TextChannel):
        await inter.response.send_message("Please specify a text channel.", ephemeral=True)
        return
    set_channel(inter.guild_id, channel.id, enabled=True, target=(target_lang or get_target(inter.guild_id, channel.id)))
    await inter.response.send_message(f"✅ Enabled auto-translation in {channel.mention} → `{get_target(inter.guild_id, channel.id)}`", ephemeral=True)

@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.command(name="disable_autotranslate", description="Disable auto-translation in this or a specified channel.")
@app_commands.describe(channel="Channel to disable (defaults to current)")
async def disable_autotranslate(inter: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    channel = channel or inter.channel
    if not isinstance(channel, discord.TextChannel):
        await inter.response.send_message("Please specify a text channel.", ephemeral=True)
        return
    set_channel(inter.guild_id, channel.id, enabled=False)
    await inter.response.send_message(f"🚫 Disabled auto-translation in {channel.mention}.", ephemeral=True)

@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.command(name="set_target_lang", description="Set the default target language for this server.")
@app_commands.describe(target_lang="Target ISO 639-1 code (e.g., en, es, fr)")
async def set_target_lang(inter: discord.Interaction, target_lang: str):
    set_guild_default_target(inter.guild_id, target_lang)
    await inter.response.send_message(f"🔧 Default target language set to `{target_lang}` for this server.", ephemeral=True)

@app_commands.command(name="status_autotranslate", description="Show auto-translation status for a channel.")
@app_commands.describe(channel="Channel to inspect (defaults to current)")
async def status_autotranslate(inter: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    channel = channel or inter.channel
    if not isinstance(channel, discord.TextChannel):
        await inter.response.send_message("Please specify a text channel.", ephemeral=True)
        return
    enabled = is_enabled(inter.guild_id, channel.id)
    target = get_target(inter.guild_id, channel.id)
    await inter.response.send_message(
        f"**Channel:** {channel.mention}\n**Enabled:** {enabled}\n**Target:** `{target}`",
        ephemeral=True,
    )

@app_commands.command(name="langs", description="List installed Argos language codes.")
async def langs(inter: discord.Interaction):
    installed = sorted(get_installed_langs().keys())
    msg = "Installed: " + (", ".join(installed) if installed else "none") + "\n" \
          "Common ISO 639-1 codes: `en`, `es`, `fr`, `de`, `it`, `pt`, `nl`, `pl`, `ru`, `ja`, `ko`, `zh`"
    await inter.response.send_message(msg, ephemeral=True)

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Set DISCORD_TOKEN environment variable.")
    if DEV_GUILD_ID:
        bot.tree.copy_global_to(guild=discord.Object(id=int(DEV_GUILD_ID)))
    bot.run(token)

if __name__ == "__main__":
    main()
