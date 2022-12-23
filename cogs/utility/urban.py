import discord
from discord.ext import commands
import urbandictionary as ud
from config import urban as config

class Urban(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @commands.command(brief="Search a sentence or word in the urban dictionary",
                    description="Use the urban random command to get 10 random definitions, use urban (search) to search for a meaning and get its definition.",
                    usage = "`urban [random or search]`\n Examples: `urban random`,\n`urban Sidewalk`,\n`urban Father's day`")
    async def urban(self, ctx:commands.Context, *, query:str="random"):
        if query == "random" and config.allow_random == True:
            random = ud.random()
            emb = discord.Embed(title="Dictionary Random")
            emb.set_footer(text="Results are from an API, I am not responsable for results!")
            emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar)
            for i, r in enumerate(random, start=1):
                if i <= config.max_length:
                    emb.add_field(name=r.word, value=r.definition, inline=True)
            await ctx.send(embed=emb)
        elif query != "random" or config.allow_random != False:
            defined = ud.define(query)
            if len(defined) > 1:
                emb = discord.Embed(title=f"Dictionary Search {query}")
                emb.set_footer(text="Results are from an API, I am not responsable for results!")
                emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar)
                emb.add_field(name="1", value=defined[0].definition, inline=True)
                emb.add_field(name="2", value=defined[1].definition, inline=True)
                emb.add_field(name="|", value="|", inline=False)
                emb.add_field(name="Votes 1:", value=f":thumbsup: {str(defined[0].upvotes)} :thumbsdown:{str(defined[0].downvotes)}", inline=True)
                emb.add_field(name="Votes 2:", value=f":thumbsup: {str(defined[1].upvotes)} :thumbsdown:{str(defined[1].downvotes)}", inline=True)
                await ctx.send(embed=emb)
            elif len(defined) == 1:
                emb = discord.Embed(title=f"Dictionary Search {query}")
                emb.set_footer(text="Results are from an API, I am not responsable for results!")
                emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
                emb.add_field(name="1", value=defined[0].definition, inline=False)
                emb.add_field(name="Votes 1:", value=f":thumbsup: {str(defined[0].upvotes)} :thumbsdown:{str(defined[0].downvotes)}", inline=False)
                await ctx.send(embed=emb)
            else:
                await ctx.send("No results found.")

async def setup(bot:commands.Bot):
	await bot.add_cog(Urban(bot))