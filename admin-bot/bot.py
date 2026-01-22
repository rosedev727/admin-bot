import os
import json
import asyncio
from datetime import datetime, timedelta

import discord
from discord import app_commands, Interaction, Object
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & STARTUP
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()
TOKEN           = os.getenv("BOT_TOKEN")
GUILD_ID        = int(os.getenv("GUILD_ID", 0)) or None   # optional; speeds sync
LOG_CHANNEL_ID  = int(os.getenv("LOG_CHANNEL_ID", 0)) or None
STAFF_ROLE_ID   = int(os.getenv("STAFF_ROLE_ID", 0)) or None

WARN_FILE = "warns.json"
MUTED_ROLE_NAME = "Muted"
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True
bot = commands.Bot(command_prefix="!", intents=INTENTS)

# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────
def load_warns() -> dict:
    if not os.path.isfile(WARN_FILE):
        return {}
    with open(WARN_FILE, "r", encoding="utf-8") as fp:
        return json.load(fp)

def save_warns(data: dict):
    with open(WARN_FILE, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)

warn_db = load_warns()

async def log_action(guild: discord.Guild, message: str):
    """Send a log message to the configured mod-log channel."""
    if not LOG_CHANNEL_ID:
        return
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)

async def ensure_muted_role(guild: discord.Guild) -> discord.Role:
    """Create (or fetch) a Muted role that denies SEND_MESSAGES + ADD_REACTIONS."""
    role = discord.utils.get(guild.roles, id=STAFF_ROLE_ID)  # Might not be muted
    muted = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
    if muted:
        return muted
    permissions = discord.Permissions(send_messages=False, add_reactions=False, speak=False)
    muted = await guild.create_role(name=MUTED_ROLE_NAME, permissions=permissions, reason="Create Muted role")
    # Update every text channel perms
    for channel in guild.channels:
        try:
            await channel.set_permissions(muted, send_messages=False, add_reactions=False)
        except Exception:
            continue
    return muted

# ─────────────────────────────────────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        guild = Object(id=GUILD_ID) if GUILD_ID else None
        await bot.tree.sync(guild=guild)  # fast guild-only sync if ID supplied
        print("Slash commands synced.")
    except Exception as e:
        print(f"Sync failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# MODERATION COMMANDS
# ─────────────────────────────────────────────────────────────────────────────
@app_commands.command(name="warn", description="Warn a user")
@app_commands.describe(member="User to warn", reason="Reason for the warning")
async def warn(inter: Interaction, member: discord.Member, reason: str):
    if not inter.user.guild_permissions.manage_messages:
        return await inter.response.send_message("You lack permission.", ephemeral=True)

    warn_entry = {"moderator": inter.user.id, "reason": reason, "time": datetime.utcnow().isoformat()}
    user_warns = warn_db.get(str(member.id), [])
    user_warns.append(warn_entry)
    warn_db[str(member.id)] = user_warns
    save_warns(warn_db)

    await member.send(f"You have been warned in **{inter.guild.name}**: {reason}")
    await inter.response.send_message(f"Warn issued to {member.mention}. Total warns: **{len(user_warns)}**")
    await log_action(inter.guild, f"⚠️ {member} warned by {inter.user} — {reason} (Total: {len(user_warns)})")

bot.tree.add_command(warn, guild=Object(id=GUILD_ID) if GUILD_ID else None)

@app_commands.command(name="unwarn", description="Remove last warn from a user")
@app_commands.describe(member="User to remove last warn")
async def unwarn(inter: Interaction, member: discord.Member):
    if not inter.user.guild_permissions.manage_messages:
        return await inter.response.send_message("You lack permission.", ephemeral=True)

    user_warns = warn_db.get(str(member.id), [])
    if user_warns:
        removed = user_warns.pop()
        save_warns(warn_db)
        await inter.response.send_message(f"Removed last warn from {member.mention}. Remaining warns: **{len(user_warns)}**")
        await log_action(inter.guild, f"✅ Warn removed from {member} by {inter.user}.")
    else:
        await inter.response.send_message(f"{member.mention} has no warns.", ephemeral=True)

bot.tree.add_command(unwarn, guild=Object(id=GUILD_ID) if GUILD_ID else None)

@app_commands.command(name="warn_list", description="List warns for a user")
@app_commands.describe(member="User to inspect")
async def warn_list(inter: Interaction, member: discord.Member):
    warns = warn_db.get(str(member.id), [])
    if not warns:
        await inter.response.send_message(f"{member.mention} has no warnings.")
        return
    lines = [f"Warnings for **{member}**:"]
    for i, w in enumerate(warns, 1):
        mod = inter.guild.get_member(w["moderator"])
        lines.append(f"{i}. By {mod or 'Unknown'} • {w['reason']} • {w['time']}")
    await inter.response.send_message("\n".join(lines))

bot.tree.add_command(warn_list, name="warn_list", guild=Object(id=GUILD_ID) if GUILD_ID else None)

# Ban
@app_commands.command(name="ban", description="Ban a user")
@app_commands.describe(member="User to ban", reason="Reason")
async def ban(inter: Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not inter.user.guild_permissions.ban_members:
        return await inter.response.send_message("You lack permission.", ephemeral=True)
    await member.ban(reason=reason)
    await inter.response.send_message(f"{member} has been banned.")
    await log_action(inter.guild, f"🔨 {member} banned by {inter.user} — {reason}")

bot.tree.add_command(ban, guild=Object(id=GUILD_ID) if GUILD_ID else None)

# Unban
@app_commands.command(name="unban", description="Unban a user by ID")
@app_commands.describe(user_id="User ID to unban", reason="Reason")
async def unban(inter: Interaction, user_id: str, reason: str = "No reason provided"):
    if not inter.user.guild_permissions.ban_members:
        return await inter.response.send_message("You lack permission.", ephemeral=True)
    user = await bot.fetch_user(int(user_id))
    await inter.guild.unban(user, reason=reason)
    await inter.response.send_message(f"{user} has been unbanned.")
    await log_action(inter.guild, f"♻️ {user} unbanned by {inter.user} — {reason}")

bot.tree.add_command(unban, guild=Object(id=GUILD_ID) if GUILD_ID else None)

# Kick
@app_commands.command(name="kick", description="Kick a user")
@app_commands.describe(member="User to kick", reason="Reason")
async def kick(inter: Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not inter.user.guild_permissions.kick_members:
        return await inter.response.send_message("You lack permission.", ephemeral=True)
    await member.kick(reason=reason)
    await inter.response.send_message(f"{member} has been kicked.")
    await log_action(inter.guild, f"👢 {member} kicked by {inter.user} — {reason}")

bot.tree.add_command(kick, guild=Object(id=GUILD_ID) if GUILD_ID else None)

# Mute
@app_commands.command(name="mute", description="Mute a user for X minutes")
@app_commands.describe(member="User", minutes="Duration in minutes", reason="Reason")
async def mute(inter: Interaction, member: discord.Member, minutes: int = 10, reason: str = "No reason provided"):
    if not inter.user.guild_permissions.moderate_members:
        return await inter.response.send_message("You lack permission.", ephemeral=True)

    muted_role = await ensure_muted_role(inter.guild)
    await member.add_roles(muted_role, reason=reason)
    await inter.response.send_message(f"{member.mention} has been muted for {minutes} minutes.")
    await log_action(inter.guild, f"🔇 {member} muted by {inter.user} for {minutes}m — {reason}")

    # auto-unmute
    await asyncio.sleep(minutes * 60)
    if muted_role in member.roles:
        await member.remove_roles(muted_role, reason="Auto-unmute")
        await log_action(inter.guild, f"🔊 {member} automatically unmuted after {minutes}m")

bot.tree.add_command(mute, guild=Object(id=GUILD_ID) if GUILD_ID else None)

# Unmute
@app_commands.command(name="unmute", description="Remove mute from a user")
@app_commands.describe(member="User to unmute")
async def unmute(inter: Interaction, member: discord.Member):
    if not inter.user.guild_permissions.moderate_members:
        return await inter.response.send_message("You lack permission.", ephemeral=True)
    muted_role = await ensure_muted_role(inter.guild)
    await member.remove_roles(muted_role, reason="Manual unmute")
    await inter.response.send_message(f"{member.mention} has been unmuted.")
    await log_action(inter.guild, f"🔊 {member} unmuted by {inter.user}")

bot.tree.add_command(unmute, guild=Object(id=GUILD_ID) if GUILD_ID else None)

# Purge
@app_commands.command(name="purge", description="Delete recent messages")
@app_commands.describe(amount="Number of messages to delete (max 100)")
async def purge(inter: Interaction, amount: int = 10):
    if not inter.user.guild_permissions.manage_messages:
        return await inter.response.send_message("You lack permission.", ephemeral=True)
    deleted = await inter.channel.purge(limit=min(amount, 100))
    await inter.response.send_message(f"🗑️ Deleted {len(deleted)} messages.", ephemeral=True)
    await log_action(inter.guild, f"🗑️ {inter.user} purged {len(deleted)} messages in {inter.channel}")

bot.tree.add_command(purge, guild=Object(id=GUILD_ID) if GUILD_ID else None)

# Say
@app_commands.command(name="say", description="Make the bot speak")
@app_commands.describe(message="Text to send")
async def say(inter: Interaction, message: str):
    if not inter.user.guild_permissions.manage_messages:
        return await inter.response.send_message("You lack permission.", ephemeral=True)
    await inter.channel.send(message)
    await inter.response.send_message("✅ Sent!", ephemeral=True)

bot.tree.add_command(say, guild=Object(id=GUILD_ID) if GUILD_ID else None)

# ─────────────────────────────────────────────────────────────────────────────
# TICKET SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
TICKET_CATEGORY_NAME = "tickets"

@app_commands.command(name="ticket", description="Open a private support ticket")
@app_commands.describe(subject="Short description of your issue")
async def ticket(inter: Interaction, subject: str):
    existing = discord.utils.get(inter.guild.text_channels, name=f"ticket-{inter.user.id}")
    if existing:
        await inter.response.send_message("You already have an open ticket.", ephemeral=True)
        return

    category = discord.utils.get(inter.guild.categories, name=TICKET_CATEGORY_NAME)
    if category is None:
        category = await inter.guild.create_category(TICKET_CATEGORY_NAME)

    overwrites = {
        inter.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        inter.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
    }
    if STAFF_ROLE_ID:
        staff_role = inter.guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await inter.guild.create_text_channel(
        name=f"ticket-{inter.user.id}",
        category=category,
        overwrites=overwrites,
        topic=f"Ticket for {inter.user} • {subject}"
    )
    await channel.send(f"Hello {inter.user.mention}! A staff member will be with you shortly.\nSubject: **{subject}**")
    await inter.response.send_message(f"🎫 Ticket created: {channel.mention}", ephemeral=True)
    await log_action(inter.guild, f"🎫 Ticket created by {inter.user} – {channel.mention} – {subject}")

bot.tree.add_command(ticket, guild=Object(id=GUILD_ID) if GUILD_ID else None)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    """Close the current ticket channel (must be inside a ticket)."""
    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send("This command must be used inside a ticket channel.")
    await ctx.send("🗑️ Closing ticket in 5 seconds...")
    await asyncio.sleep(5)
    await log_action(ctx.guild, f"❌ Ticket {ctx.channel.name} closed by {ctx.author}")
    await ctx.channel.delete()

# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(TOKEN)