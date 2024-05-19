from discord import app_commands
from discord.ext import commands
import discord
import json
import lib.functions as fun

class Profile_Checker(commands.Cog):

    def __init__(self, client):
        print("[Cog] Profile Checker has been initiated")
        self.client = client
        
    with open("./json/config.json", "r") as f:
        config = json.load(f)
    
    @app_commands.command(name="profile", description="Searches a profile")
    @app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction, steamid_or_url:str):
        await interaction.response.defer(ephemeral=True)
        user_ids = await fun.get_player_ids(steamid_or_url)
        if not user_ids:
            await interaction.followup.send(f"I was unable to find a user using {steamid_or_url}", ephemeral=True)
            return
        user_profile = await fun.get_player_info(player_id=user_ids.bmid)
        kill_stats = await fun.player_stats(bmid=user_ids.bmid)
        embed = discord.Embed(title=f"{user_profile.player_name}", description=f"[Steam]({user_profile.profile_url}) - [Battlemetrics](https://www.battlemetrics.com/rcon/players/{user_ids.bmid})", color=int(self.config['additional']['embed_color'], base=16))
        embed.set_thumbnail(url=user_profile.avatar_url)
        embed.set_footer(text="Gnomeslayers Profile Viewer.")
        embed.add_field(name="Hours across Rust", value=f"Total Hours: {user_profile.playtime}, Training: {user_profile.playtime_training}", inline=False)
        for server in user_profile.playtime_servers:
            embed.add_field(name=f"{server['name']}", value=f"{server['time']} hours", inline=False)
        ratio = kill_stats.kills_two_weeks / kill_stats.deaths_two_weeks
        ratio = round(ratio, 2)
        embed.add_field(name="STATS!! (14days)", value=f"Ratio: {ratio}\nKills - {kill_stats.kills_two_weeks}\nDeaths:{kill_stats.deaths_two_weeks}", inline=False)
        await interaction.followup.send(embed=embed)

async def setup(client):
    await client.add_cog(Profile_Checker(client))