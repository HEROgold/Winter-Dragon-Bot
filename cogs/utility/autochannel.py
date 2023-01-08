import asyncio
import contextlib
import json
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database

# TODO: Make group, and add subcommands
# autochannel add, autochannel remove
class Autochannel(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.database_name = "Autochannel"
        self.logger = logging.getLogger("winter_dragon.autochannel")
        if not config.main.use_database:
            self.DBLocation = f"./Database/{self.database_name}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                self.logger.debug(f"{self.database_name} Json Created.")
        else:
            self.logger.debug(f"{self.database_name} Json Loaded.")

    async def get_data(self) -> dict[str, dict[str, dict[str, int]]]:
        if config.main.use_database:
            db = dragon_database.Database()
            data = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.main.use_database:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        # Delete empty channels, and categories every hour since startup.
        # When loaded, loop over all guilds, and check if they are in DB
        await self.cleanup()

    async def cleanup(self):
        self.logger.debug("Cleaning Autochannels...")
        data = await self.get_data()
        self.logger.debug(data)
        for guild_id, guild_channels in data.items():
            guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
            for key, channels in guild_channels.items():
                if key == "AC Channel":
                    continue
                channel = discord.utils.get(guild.voice_channels, id=int(channels["Voice"]))
                with contextlib.suppress(AttributeError):
                    if channel.type is discord.ChannelType.voice:
                        empty = len(channel.members) <= 0
                        if not empty:
                            continue
                        for channel_name, channel_id in channels.items():
                            channel = discord.utils.get(guild.channels, id=int(channel_id))
                            await channel.delete()
                        del data[guild.id][key]
        await self.set_data(data)
        self.logger.debug("Cleaned Autochannels")
        if config.database.PERIODIC_CLEANUP:
            # seconds > minuts > hours
            await asyncio.sleep(60*60*1)
            await self.cleanup()

    async def CreateCategoryChannel(self, guild:discord.Guild, overwrites:discord.PermissionOverwrite, ChannelName:str, position:int=2):
        return await guild.create_category(name=ChannelName, overwrites=overwrites, position=position)

    async def CreateVoiceChannel(self, guild:discord.Guild, CategoryChannel:discord.CategoryChannel, ChannelName:str):
        # sourcery skip: assign-if-exp, inline-immediately-returned-variable, lift-return-into-if, swap-if-expression
        if not CategoryChannel:
            VoiceChannel = await guild.create_voice_channel(name = ChannelName)
        else:
            VoiceChannel = await CategoryChannel.create_voice_channel(name = ChannelName)
        return VoiceChannel

    async def CreateTextChannel(self, guild:discord.Guild, CategoryChannel:discord.CategoryChannel, ChannelName:str):
        # sourcery skip: assign-if-exp, inline-immediately-returned-variable, lift-return-into-if, swap-if-expression
        if not CategoryChannel:
            TextChannel = await guild.create_text_channel(name = ChannelName)
        else:
            TextChannel = await CategoryChannel.create_text_channel(name = ChannelName)
        return TextChannel

    @app_commands.command(name="autochannel", description="Set up voice category and channels, which lets each user make their own channels")
    @app_commands.checks.has_permissions(manage_channels = True)
    @app_commands.checks.bot_has_permissions(manage_channels = True)
    async def slash_autochannel(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
            }
        data = await self.get_data()
        guild_id = str(guild.id)
        # Create/find category channel
        try:
            data[guild_id]
        except Exception as e:
            if isinstance(e, KeyError):
                data[guild_id] = {"AC Channel":{}}
        try:
            ac_id = data[guild_id]["AC Channel"]["id"]
            ac_category_channel = discord.utils.get(guild.channels, id=ac_id)
        except Exception as e:
            if isinstance(e, KeyError):
                CategoryChannel = await self.CreateCategoryChannel(guild=guild, overwrites=overwrites, ChannelName="Autochannel")
                data[guild_id]["AC Channel"] = {"id": CategoryChannel.id}
            else:
                self.logger.error(f"Unexpected Error: {e}")
        # Create/find voice channel
        try:
            voice_channel_id = data[guild_id]["AC Channel"]["Voice"]
            ac_voice_channel = discord.utils.get(guild.channels, id=voice_channel_id)
        except Exception as e:
            if isinstance(e, KeyError):
                VoiceChannel = await self.CreateVoiceChannel(guild=guild, CategoryChannel=CategoryChannel, ChannelName="Join me!")
                data[guild_id]["AC Channel"]["Voice"] = VoiceChannel.id
            else:
                self.logger.error(f"Unexpected Error: {e}")
        # Create/find text channel
        try:
            text_channel_id = data[guild_id]["AC Channel"]["Text"]
            ac_text_chanel = discord.utils.get(guild.channels, id=text_channel_id)
        except Exception as e:
            if isinstance(e, KeyError):
                Textchannel = await self.CreateTextChannel(guild=guild, CategoryChannel=CategoryChannel, ChannelName="AutoChannel Info")
                msg = await Textchannel.send(f"To create your own voice and text channel, just join the voice channel <#{VoiceChannel.id}>")
                await msg.pin()
                data[guild_id]["AC Channel"]["Text"] = Textchannel.id
            else:
                self.logger.error(f"Unexpected Error: {e}")
        await interaction.followup.send("The channels are now set up!")
        await self.set_data(data)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        # sourcery skip: low-code-quality
        data = await self.get_data()
        if after.channel:
            channel = after.channel
            guild = channel.guild
            guild_id = str(guild.id)
            channel_id = channel.id
            voice_id = data[guild_id]["AC Channel"]["Voice"]
            text_id = data[guild_id]["AC Channel"]["Text"]
            if channel_id == voice_id:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(),
                    guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none()),
                    member: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
                }
                try: # Get Users own category channel, or create one
                    CategoryChannel = discord.utils.get(guild.categories, id=(int(data[guild_id][str(member.id)]["id"])))
                except Exception as e:
                    if isinstance(e, KeyError):
                        CategoryChannel = await self.CreateCategoryChannel(guild=guild, overwrites=overwrites, ChannelName=f"{member.name}", position=99)
                        data[guild_id][member.id] = {"id": CategoryChannel.id}
                    else:
                        self.logger.exception(f"Unexpected Error: {e}")
                try: # Get Users own voice channel, or create one
                    VoiceChannel = discord.utils.get(guild.voice_channels, id=(int(data[guild_id][str(member.id)]["Voice"])))
                    await member.move_to(VoiceChannel)
                except Exception as e:
                    if isinstance(e, KeyError):
                        VoiceChannel = await self.CreateVoiceChannel(guild=guild, CategoryChannel=CategoryChannel, ChannelName=f"{member.name}'s Voice")
                        data[guild_id][member.id]["Voice"] = VoiceChannel.id
                        await member.move_to(VoiceChannel)
                    else:
                        self.logger.exception(f"Unexpected Error: {e}")
                try: # Get Users own text channel, or create one
                    TextChannel = discord.utils.get(guild.text_channels, id=(int(data[guild_id][str(member.id)]["Text"])))
                except Exception as e:
                    if isinstance(e, KeyError):
                        TextChannel = await self.CreateTextChannel(guild=guild, CategoryChannel=CategoryChannel, ChannelName=f"{member.name}'s Text")
                        data[guild_id][member.id]["Text"] = TextChannel.id
                    else:
                        self.logger.exception(f"Unexpected Error: {e}")
            await self.set_data(data)
        if before.channel:
            # FIXME: doesnt seem to remove channel and data
            # On_ready does work
            with contextlib.suppress(KeyError):
                channel = before.channel
                guild = channel.guild
                member_id = str(member.id)
                guild_id = str(guild.id)
                channel_id = channel.id
                voice_id:int = data[guild_id][member_id]["Voice"]
                if channel_id == voice_id and len(channel.members) <= 0:
                    category_id:int = data[guild_id][member_id]["id"]
                    text_id:int = data[guild_id][member_id]["Text"]
                    category_channel:discord.CategoryChannel = discord.utils.get(guild.categories, id=category_id)
                    voice_channel:discord.VoiceChannel = discord.utils.get(guild.voice_channels, id=voice_id)
                    AC_text:discord.TextChannel = discord.utils.get(guild.text_channels, id=text_id)
                    await voice_channel.delete()
                    await AC_text.delete()
                    await category_channel.delete()
                    del data[guild_id][member_id]
                    await self.set_data(data)

async def setup(bot:commands.Bot):
	await bot.add_cog(Autochannel(bot))