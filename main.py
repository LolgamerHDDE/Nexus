import discord
from discord.ext import commands
import os
import random
import dotenv
import hashlib
import aiomysql
import requests

dotenv.load_dotenv()

version = "2.0.0"
PREMIUM_SKU = os.getenv("PREMIUM_SKU")

def gravatar_hash(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()

# Create DB pool once on startup

async def create_db_pool():
    bot.db = await aiomysql.create_pool(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        db=os.getenv("DB_NAME"),
    )

class MyBot(commands.Bot):
    async def setup_hook(self):
        # create DB pool before bot is ready
        self.db = await aiomysql.create_pool(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            db=os.getenv("DB_NAME"),
        )

async def log_action(guild_id, action, target_id, moderator_id, reason):
    async with bot.db.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO moderation_logs (guild_id, action, target_id, moderator_id, reason)
                VALUES (%s, %s, %s, %s, %s)
            """, (guild_id, action, target_id, moderator_id, reason))
            await conn.commit()

intents = discord.Intents.all()
bot = MyBot(command_prefix="!", intents=intents)
tree = bot.tree

# Bot Events

@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(activity=discord.activity.Game(name="Under Maintenance!"), status=discord.Status.do_not_disturb)
    print("Bot is ready!")

# Bot Commands

@tree.command(name="help", description="Displays commands and their functions.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(color=0x008000, title="Help Command", description="/help - Displays this dialouge.\n/version - Displays the Current bot version.")
    embed.set_image(url="https://cdn.discordapp.com/avatars/1206984930492678254/a_61fd4ed1058def866549d422e0d93585?size=256")
    
    view = discord.ui.View()
    button = discord.ui.Button(
        label="More Commands",
        url="https://nexus.syncwi.de/commands",
        style=discord.ButtonStyle.link
    )
    view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@tree.command(name="version", description="Displays the current Bot version.")
async def version(interaction: discord.Interaction):
    embed = discord.Embed(color=0x008000, description=f'# Nexus Version 2.0.0\nNexus is fully open-source and released under the MIT License. Republishing is permitted only if “SyncWide Solutions” or “LolgamerHDDE” is credited. Please note that any Nexus replicas or repositories that violate the license terms will be reported and removed from GitHub.\n \nThe official Nexus bot is verified and can be distinguished by its verification badge. When added through the official Nexus site, it will never request administrator privileges.')

    view = discord.ui.View()
    button = discord.ui.Button(
        label="Nexus License",
        url="https://github.com/SyncWide-Solutions/Nexus/blob/main/LICENSE",
        style=discord.ButtonStyle.link
    )
    view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name='iel', description="Sends a random ich_iel meme from Reddit.")
async def iel(interactinon: discord.Interaction):
    rndint = random.randint(1, 75)

    await interactinon.response.send_message(f"https://cdn.syncwi.de/iel/{rndint}.jpg")

@tree.command(name="gravatar", description="Gets a Gravatar profile from an email")
async def gravatar(interaction: discord.Interaction, email: str):
    await interaction.response.defer()

    email_hash = gravatar_hash(email)
    profile_url = f"https://www.gravatar.com/{email_hash}.json"
    avatar_url = f"https://www.gravatar.com/avatar/{email_hash}?s=512"

    try:
        response = requests.get(profile_url, timeout=5)
        if response.status_code != 200:
            embed = discord.Embed(
                title="Gravatar",
                description="No public profile found, but here's the avatar:",
                color=discord.Color.red()
            )
            embed.set_image(url=avatar_url)
            await interaction.followup.send(embed=embed)
            return

        entry = response.json()["entry"][0]

        # Basic profile info
        display_name = entry.get("displayName", "Unknown User")
        about = entry.get("aboutMe", "No bio available.")
        thumbnail = entry.get("thumbnailUrl", avatar_url)
        profile_link = entry.get("profileUrl")

        # Extended info (if available)
        location = entry.get("currentLocation")
        job_title = entry.get("jobTitle")
        company = entry.get("organization")
        pronouns = entry.get("pronouns")

        # Build embed
        embed = discord.Embed(
            description=f"# {display_name}\n\n{about}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=thumbnail)

        if location:
            embed.add_field(name="📍 Location", value=location, inline=True)
        if job_title or company:
            job_text = job_title or ""
            if company:
                job_text += f" @ {company}" if job_title else company
            embed.add_field(name="💼 Work", value=job_text, inline=True)
        if pronouns:
            embed.add_field(name="🙋 Pronouns", value=pronouns, inline=True)

        # Buttons
        view = discord.ui.View()

        if profile_link:
            view.add_item(discord.ui.Button(
                label="View Gravatar Profile",
                url=profile_link,
                style=discord.ButtonStyle.link
            ))

        # Verified accounts (newer API field)
        accounts = entry.get("accounts", []) or entry.get("verifiedAccounts", [])
        for acc in accounts:
            acc_url = acc.get("url")
            acc_name = acc.get("shortname") or acc.get("domain") or acc.get("service_label") or "Account"
            if acc_url:
                view.add_item(discord.ui.Button(
                    label=acc_name,
                    url=acc_url,
                    style=discord.ButtonStyle.link
                ))

        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        await interaction.followup.send(f"⚠️ Error fetching Gravatar profile: `{e}`")

# Moderation Commands

@tree.command(name="ban", description="Bans a user from the server.")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str | None = "No reason provided."):
    try:
        await member.ban(reason=reason)

        # Save to database
        await log_action(ctx.guild.id, "ban", member.id, ctx.author.id, reason)

        embed = discord.Embed(
            title="User Banned",
            description=f"{member.mention} has been banned.\nReason: {reason}",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        await member.send(f"You have been banned from {ctx.guild.name}.\nReason: {reason}")
    except Exception as e:
        await ctx.send(f"⚠️ Could not ban {member.mention}: {e}")

@tree.command(name="kick", description="Kicks a user from the server.")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason:str | None = "No reason provided."):
    try:
        await member.kick(reason=reason)

        # Save to database
        await log_action(ctx.guild.id, "kick", member.id, ctx.author.id, reason)

        embed = discord.Embed(
            title="User Kicked",
            description=f"{member.mention} has been kicked.\nReason: {reason}",
            color=0xFFA500
        )
        await ctx.send(embed=embed)
        await member.send(f"You have been kicked from {ctx.guild.name}.\nReason: {reason}")
    except Exception as e:
        await ctx.send(f"⚠️ Could not kick {member.mention}: {e}")

@tree.command(name="warn", description="Warns a user and logs it to the database.")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason:str | None = "No reason provided."):
    try:
        # Save to database
        await log_action(ctx.guild.id, "warn", member.id, ctx.author.id, reason)

        embed = discord.Embed(
            title="User Warned",
            description=f"{member.mention} has been warned.\nReason: {reason or 'No reason provided.'}",
            color=0xFFFF00
        )
        await ctx.send(embed=embed)

        # DM the user about the warning
        private_embed = discord.Embed(
            title="You have been warned",
            description=f"You have been warned in **{ctx.guild.name}**.\nReason: {reason or 'No reason provided.'}",
            color=0xFFFF00
        )
        await member.send(embed=private_embed)

    except Exception as e:
        await ctx.send(f"⚠️ Could not warn {member.mention}: {e}")

@tree.command(name="logs", description="View moderation logs.")
@commands.has_permissions(administrator=True)
async def logs(interaction: discord.Interaction, member: discord.Member | None = None):
    async with bot.db.acquire() as conn:
        async with conn.cursor() as cur:
            if member:  # Show logs for specific member
                await cur.execute("""
                    SELECT action, target_id, moderator_id, reason, timestamp 
                    FROM moderation_logs
                    WHERE guild_id = %s AND target_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (interaction.guild.id, member.id))
            else:  # Show latest logs for the server
                await cur.execute("""
                    SELECT action, target_id, moderator_id, reason, timestamp 
                    FROM moderation_logs
                    WHERE guild_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (interaction.guild.id,))
            rows = await cur.fetchall()

    if not rows:
        await interaction.response.send_message(
            "📂 No moderation logs found.",
            ephemeral=True
        )
        return

    if member:
        embed = discord.Embed(
            title=f"Moderation Logs for {member}",
            color=discord.Color.orange()
        )
    else:
        embed = discord.Embed(
            title=f"Recent Moderation Logs in {interaction.guild.name}",
            color=discord.Color.orange()
        )

    for action, target_id, moderator_id, reason, timestamp in rows:
        target = interaction.guild.get_member(target_id)
        moderator = interaction.guild.get_member(moderator_id)

        target_name = target.mention if target else f"ID {target_id}"
        moderator_name = moderator.mention if moderator else f"ID {moderator_id}"

        embed.add_field(
            name=f"{action.upper()} • {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            value=f"👤 User: {target_name}\n👮 Moderator: {moderator_name}\n📄 Reason: {reason or 'No reason'}",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    bot.run(token=os.getenv("DISCORD_BOT_TOKEN"))
