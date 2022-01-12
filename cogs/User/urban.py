import discord
from discord.ext import commands
import urbandictionary as ud
from config import urban as config

class urban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="urban (search) | urban random", description="Use the urban random command to get 10 random definitions, use urban (search) to search for a meaning and get its definition.")
    async def urban(self, ctx, *, query):
        if query == "random" and config.allow_random == True:
            i = 0
            random = ud.random()
            emb = discord.Embed(title=f"Dictionary Random")
            emb.set_footer(text="Results are from an API, I am not responsable for results!")
            emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            for r in random:
                i += 1
                if i <= config.max_length:
                    emb.add_field(name=r.word, value=r.definition, inline=True)
            await ctx.send(embed=emb)
        elif query == "random" and config.allow_random == False:
            pass
        else:
            defined = ud.define(query)
            if len(defined) > 1:
                emb = discord.Embed(title=f"Dictionary Search {query}")
                emb.set_footer(text="Results are from an API, I am not responsable for results!")
                emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
                definition = []
                emb.add_field(name="1", value=defined[0].definition, inline=True)
                emb.add_field(name="2", value=defined[1].definition, inline=True)
                emb.add_field(name="|", value="|", inline=False)
                emb.add_field(name="Votes 1:", value=(":thumbsup: " + str(defined[0].upvotes) + " :thumbsdown:" + str(defined[0].downvotes)), inline=True)
                emb.add_field(name="Votes 2:", value=(":thumbsup: " + str(defined[1].upvotes) + " :thumbsdown:" + str(defined[1].downvotes)), inline=True)
                await ctx.send(embed=emb)
            elif len(defined) == 1:
                emb = discord.Embed(title=f"Dictionary Search {query}")
                emb.set_footer(text="Results are from an API, I am not responsable for results!")
                emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
                definition = []
                emb.add_field(name="1", value=defined[0].definition, inline=False)
                emb.add_field(name="Votes 1:", value=(":thumbsup: " + str(defined[0].upvotes) + " :thumbsdown:" + str(defined[0].downvotes)), inline=False)
                await ctx.send(embed=emb)
            else:
                await ctx.send("No results found.")

def setup(bot):
	bot.add_cog(urban(bot))