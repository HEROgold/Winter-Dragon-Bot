import discord
from discord.ext import commands
import discord.utils
from random import *
import re
import datetime
import emoji
import sqlite3
import os

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        conn = sqlite3.connect("./Database/Poll.db")
        c = conn.cursor()
        try:
            c.execute("""CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id int
            )""")
        except Exception as i:
            print(f"\n\nMESSAGS\n{i}\n\n")
        try:
            c.execute("""CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id int
            )""")
        except Exception as i:
            print(f"\n\n USERS\n{i}\n\n")
        try:
            c.execute("""CREATE TABLE reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY (message_id) REFERENCES messages(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
        except Exception as i:
            print(f"\n\n REACTIONS\n{i}\n\n")
        self.c = c
        self.conn = conn

    def find_message(self, ctx):
           # this is the index of the first character of the title
           first = ctx.find('{') + 1
           # index of the last character of the title
           last = ctx.find('}')
           if first == 0 or last == -1:
               return "Use { and } to specify message, and use [ and ] to specify options."
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
    async def on_raw_reaction_add(self, payload):
        if c.execute(f"SELECT * FROM messages WHERE message_id={payload.message_id}" != None):
            channel = await self.bot.fetch_channel(payload.channel_id)
            emoji = payload.emoji
            message = await channel.fetch_message(payload.message_id)
            guild = await self.bot.fetch_guild(payload.guild_id)
            member = await self.bot.fetch_user(payload.user_id)
            if not member.bot:
                if c.execute(f"SELECT * FROM reactions WHERE message_id={payload.message_id}, user_id={payload.user_id}" != None):
                    await message.remove_reaction(emoji, member)
                    dm = await member.create_dm()
                    await dm.send("Your second reaction has been removed from the vote.\n To vote for something else, remove your previous reaction!")
                else:
                    c.execute(f"INSERT INTO users VALUES {payload.user_id}")
                    print(f"{member.id} added to the poll list {users}")
            else:
                print(f"{member} is a Bot, Cannot add to the poll list")
        else:
            print(f"Message id {payload.message_id} not in database")
        conn.commit()
        conn.close()

    @commands.Cog.listener() #if 1st reaction removed, allow user to react again.
    async def on_raw_reaction_remove(self, payload):
        if c.execute(f"SELECT * FROM messages WHERE message_id={payload.message_id}" != None):
            guild = await self.bot.fetch_guild(payload.guild_id)
            member = await self.bot.fetch_user(payload.user_id)
            if c.execute(f"SELECT * FROM messagse WHERE message_id={payload.message_id}" == member.id):
                c.execute(f"DELETE FROM messages WHERE message_id={payload.message_id}")
                print(f"{member.id} removed from poll list {users} from {payload.message_id}")
            else:
                print(f"{member.id} is not in poll list {payload.message_id}")
        conn.commit()
        conn.close()

    @commands.has_permissions(mention_everyone=True) # the command to initiate the voting.
    @commands.command(aliases=("vote","voting"), pass_context=True, brief="Usage: poll {question} [anwser1] [answer2]), {} and [] necessary", description="Use this command to create a poll, (Only works with custom emoji's.)")
    async def poll(self, ctx):
        i = 0
        message = self.find_message(ctx.message.clean_content)
        option = self.find_options(ctx.message.clean_content, [])
        emojis = self.find_emoji(ctx)
        member = ctx.author
        emb = discord.Embed(title="Vote Here!", description=f"{message}", colour=(randint(0,16777215)))
        emb.set_author(name=(member.display_name), icon_url=(member.avatar_url))
        emb.timestamp = datetime.datetime.now()
        emb.set_footer(text="Time > ")
        for choice, emoji in zip(option, emojis):
            i += 1
            emb.add_field(name=f"Option {i}", value=choice, inline=True)

        send_embed = await ctx.send(embed=emb)

        for emoji in emojis:
            await send_embed.add_reaction(emoji)
            print(f"{emoji} emoji added to {ctx.message.id}")
        c.execute(f"INSERT INTO messages VALUES {ctx.message.id}")
        conn.commit()
        conn.close()
        await ctx.message.delete()

def setup(bot):
	bot.add_cog(Poll(bot))