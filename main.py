import discord
from discord.ext import commands
import os
import random
import dotenv
import hashlib
import requests

dotenv.load_dotenv()

version = "2.0.0"
PREMIUM_SKU = os.getenv("PREMIUM_SKU")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

def gravatar_hash(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()

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

if __name__ == "__main__":
    bot.run(token=os.getenv("DISCORD_BOT_TOKEN"))
