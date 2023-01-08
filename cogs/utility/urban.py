import discord
import urbandictionary as ud
from discord import app_commands
from discord.ext import commands

from config import urban as config

# TODO: Make group, and add subcommands
# Urban random, urban query
class Urban(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @app_commands.command(
        name="urban",
        description="Use random command to get 10 random definitions,or for a meaning and get its definition."
        )
    async def slash_urban(self, interaction:discord.Interaction, query:str):
        await interaction.response.defer()
        if query == "random" and config.allow_random == True:
            random = ud.random()
            emb = discord.Embed(title="Dictionary Random")
            emb.set_footer(text="Results are from an API, I am not responsable for results!")
            emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar)
            for i, r in enumerate(random, start=1):
                if i <= config.max_length:
                    emb.add_field(name=r.word, value=r.definition, inline=True)
            await interaction.followup.send(embed=emb)
        elif query != "random" or config.allow_random != False:
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

    @slash_urban.autocomplete("query")
    async def urban_autocomplete_query(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=query, value=query)
            for query in ["random"]
            if current.lower() in query.lower()
        ]

async def setup(bot:commands.Bot):
	await bot.add_cog(Urban(bot))