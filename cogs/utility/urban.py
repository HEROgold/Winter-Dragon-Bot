import discord
import urbandictionary as ud
from discord import app_commands
from discord.ext import commands

import config

class Urban(commands.GroupCog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @app_commands.command(
        name="random",
        description="get random definitions"
    )
    async def slash_urban_random(self, interaction:discord.Interaction):
        if config.Urban.ALLOW_RANDOM == True:
            random = ud.random()
            emb = discord.Embed(title="Dictionary Random")
            emb.set_footer(text="Results are from an API, I am not responsable for results!")
            emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar)
            for i, r in enumerate(random, start=1):
                if i <= config.Urban.MAX_LENGHT:
                    emb.add_field(name=r.word, value=r.definition, inline=True)
            await interaction.response.send_message(embed=emb)
        else:
            await interaction.response.send_message("Random definitions are disabled", ephemeral=True)

    # FIXME: discord.app_commands.errors.CommandInvokeError: Command 'search' raised an exception: KeyError: 'result_type'
    @app_commands.command(
        name="search",
        description="Look into urban dictionary for a meaning and its definition."
        )
    async def slash_urban(self, interaction:discord.Interaction, query:str):
        defined = ud.define(query)
        if len(defined) > 1:
            emb = discord.Embed(title=f"Dictionary Search {query}")
            emb.set_footer(text="Results are from an API, I am not responsable for results!")
            emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar)
            emb.add_field(name="1", value=defined[0].definition, inline=True)
            emb.add_field(name="2", value=defined[1].definition, inline=True)
            emb.add_field(name="|", value="|", inline=False)
            emb.add_field(name="Votes 1:", value=f":thumbsup: {str(defined[0].upvotes)} :thumbsdown:{str(defined[0].downvotes)}", inline=True)
            emb.add_field(name="Votes 2:", value=f":thumbsup: {str(defined[1].upvotes)} :thumbsdown:{str(defined[1].downvotes)}", inline=True)
            await interaction.followup.send(embed=emb)
        elif len(defined) == 1:
            emb = discord.Embed(title=f"Dictionary Search {query}")
            emb.set_footer(text="Results are from an API, I am not responsable for results!")
            emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar_url)
            emb.add_field(name="1", value=defined[0].definition, inline=False)
            emb.add_field(name="Votes 1:", value=f":thumbsup: {str(defined[0].upvotes)} :thumbsdown:{str(defined[0].downvotes)}", inline=False)
            await interaction.followup.send(embed=emb)
        else:
            await interaction.followup.send("No results found.")

async def setup(bot:commands.Bot):
	await bot.add_cog(Urban(bot))