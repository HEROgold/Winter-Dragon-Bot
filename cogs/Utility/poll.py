import discord
from discord.ext import commands
import discord.utils
from random import *
import re
import datetime
import emoji

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    users = []

    def find_message(self, ctx):
           # this is the index of the first character of the title
           first = ctx.find('{') + 1
           # index of the last character of the title
           last = ctx.find('}')
           if first == 0 or last == -1:
               return "Use { and } to specify message"
           return ctx[first:last]

    def find_options(self, ctx, options):
          # first index of the first character of the option
          first = ctx.find('[') + 1
          # index of the last character of the title
          last = ctx.find(']')
          if (first == 0 or last == -1):
              if len(options) < 2:
                  return "Use [ and ] to specify a option. Example for multiple options: [trees] [apples]"
              else:
                  return options
          options.append(ctx[first:last])
          ctx = ctx[last+1:]
          return self.find_options(ctx, options)

    def find_emoji(self, ctx):
        custom_emoji = re.findall(r"<:\w*:\d*>", ctx.message.clean_content)
        return custom_emoji

    @commands.Cog.listener() #on reaction added to message check if already reacted, then remove reaction if already reacted.
    async def on_raw_reaction_add(self, ctx):
        channel = await self.bot.fetch_channel(ctx.channel_id)
        emoji = ctx.emoji
        message = await channel.fetch_message(ctx.message_id)
        guild = await self.bot.fetch_guild(ctx.guild_id)
        member = await self.bot.fetch_user(ctx.user_id)
        users = self.users
        if not member.bot:
            if member.id in users:
                await message.remove_reaction(emoji, member)
                dm = await member.create_dm()
                await dm.send("Your second reaction has been removed from the vote.\n To vote for something else, remove your previous reaction!")
            else:
                users.append(member.id)
                print(f"{member.id} added to the users {users}")
        else:
            print(f"{member} is a Bot, Cannot add to the list")

    @commands.Cog.listener() #if 1st reaction removed, allow user to react again.
    async def on_raw_reaction_remove(self, ctx):
        guild = await self.bot.fetch_guild(ctx.guild_id)
        member = await self.bot.fetch_user(ctx.user_id)
        print("reaction removed")
        users = self.users
        if member.id in users:
            users.remove(member.id)
            print(f"{member.id} removed from {users}")
        else:
            print(f"{member.id} is not in {users}")

    @commands.has_permissions(mention_everyone=True) # the command to initiate the voting.
    @commands.command(aliases=("vote","voting"), pass_context=True)
    async def poll(self, ctx):
        i = 0
        message = self.find_message(ctx.message.clean_content)
        option = self.find_options(ctx.message.clean_content, [])
        emojis = self.find_emoji(ctx)
        member = ctx.author
        emb = discord.Embed(title="Vote Here!", description=f"{message}", colour=(randint(0,16777215)))
        emb.set_author(name=(member.display_name), icon_url=(member.avatar_url))
        emb.timestamp = datetime.datetime.now()
        emb.set_footer(text="Time might be in the wrong timezone")
        for choice, emoji in zip(option, emojis):
            i += 1
            emb.add_field(name=f"Option {i}", value=choice, inline=True)

        send_embed = await ctx.send(embed=emb)

        for emoji in emojis:
            await send_embed.add_reaction(emoji)
            print(f"{emoji} emoji added")
        await ctx.message.delete()

def setup(bot):
	bot.add_cog(Poll(bot))