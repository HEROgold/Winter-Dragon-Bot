import discord, re , datetime, emoji, json, os, asyncio
from discord.ext import commands
import discord.utils
from random import *

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.path.exists('./Database/Poll.json'):
            with open("./Database/Poll.json", "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                print("Poll Json Created.")
        else:
            print("Poll Json Loaded.")

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

    def get_data(self):
        with open('.\\Database/Poll.json', 'r') as f:
            data = json.load(f)
            print(f"Get Data:\n data")
        return data

    def set_data(self, data):
        with open('.\\Database/Poll.json','w') as f:
            print(f"Set Data:\n {data}")
            json.dump(data, f)

    @commands.Cog.listener() #on reaction added to message check if already reacted, then remove reaction if already reacted.
    async def on_raw_reaction_add(self, payload):
        data = self.get_data()
        if str(payload.message_id) in data:
            channel = await self.bot.fetch_channel(payload.channel_id)
            emoji = payload.emoji
            message = await channel.fetch_message(payload.message_id)
            guild = await self.bot.fetch_guild(payload.guild_id)
            member = await self.bot.fetch_user(payload.user_id)
            if not member.bot:
                messages = data[str(message.id)]
                print(messages, data)
                if str(member.id) in messages:
                    await message.remove_reaction(emoji, member)
                    dm = await member.create_dm()
                    await dm.send("Your second reaction has been removed from the vote.\n To vote for something else, remove your previous reaction!")
                    await asyncio.sleep(1)
                    data[str(message.id)][str(member.id)] = member.id
                    self.set_data(data)
                else:
                    data[str(message.id)][str(member.id)] = member.id
                    self.set_data(data)
                    print(f"{member.id} added to the poll list")
            else:
                print(f"{member} is a Bot, Cannot add to the poll listlist")

    @commands.Cog.listener() #if 1st reaction removed, allow user to react again. FIX WHEN BOT REMVES REACTION THIS REMOVES USER FROM LIST ALLOWING FOR 
    async def on_raw_reaction_remove(self, payload):
        data = self.get_data()
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        guild = await self.bot.fetch_guild(payload.guild_id)
        member = await self.bot.fetch_user(payload.user_id)
        if str(message.id) in data:
            guild = await self.bot.fetch_guild(payload.guild_id)
            member = await self.bot.fetch_user(payload.user_id)
            users = data[str(message.id)]
            print("reaction removed")
            if str(member.id) in users:
                del users[str(member.id)]
                print(f"{member.id} removed from poll list")
                self.set_data(data)
            else:
                print(f"{member.id} is not in poll list")

    @commands.has_permissions(mention_everyone=True) # the command to initiate the voting.
    @commands.command(aliases=("vote","voting"), pass_context=True, brief="Usage: poll {question} [anwser1] [answer2]), {} and [] necessary", description="Use this command to create a poll, (Only works with custom emoji's.)")
    async def poll(self, ctx):
        data = self.get_data()
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
            print(f"{emoji} emoji added")
        await ctx.message.delete()
        data[send_embed.id] = {}
        self.set_data(data)

def setup(bot):
	bot.add_cog(Poll(bot))