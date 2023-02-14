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

class Autochannel(commands.GroupCog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.database_name = "Autochannel"
        self.logger = logging.getLogger("winter_dragon.autochannel")
        self.data = None
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.database_name}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = self.data
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.database_name} Json Created.")
        else:
            self.logger.info(f"{self.database_name} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        # TODO:
        # Delete empty channels, and categories every hour since startup.
        # When loaded, loop over all guilds, and check if they are in DB
        # await self.database_cleanup()
        self.data = await self.get_data()

    async def cog_unload(self):
        await self.set_data(self.data)


    async def database_cleanup(self):
        self.logger.info("Cleaning Autochannels...")
        if not self.data:
            self.data = await self.get_data()
        for guild_id, guild_categories in list(self.data.items()):
            cleaned = await self._clean_categories(guild_categories, guild_id)
            if cleaned == True:
                del self.data[guild_categories]
        await self.set_data(self.data)
        self.logger.info("Database cleaned up")
        if config.Database.PERIODIC_CLEANUP:
            # seconds > minuts > hours
            await asyncio.sleep(60*60*1)
            await self.database_cleanup()

    # TODO: cleaned == true when data is empty > aka all channels are cleaned
    # ??? Needs testing
    async def _clean_categories(self, guild_categories:dict, guild_id:str) -> dict:
        self.logger.info(f"Cleaning Category {guild_categories}")
        cleaned = False
        guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
        for key, channels in list(guild_categories.items()):
            if key == "AC Channel":
                continue
            cleaned = await self._clean_channels(channels, guild)
            if cleaned == False:
                break
        return cleaned

    async def _clean_channels(self, channels:dict, guild:discord.Guild) -> bool:
        self.logger.info(f"Cleaning Channels {channels}")
        guild = discord.utils.get(self.bot.guilds, id=int(guild))
        channel = discord.utils.get(guild.voice_channels, id=int(channels["Voice"]))
        with contextlib.suppress(AttributeError):
            if channel.type is discord.ChannelType.voice:
                empty = len(channel.members) <= 0
                if not empty:
                    return False
                for channel_id in channels.values():
                    channel = discord.utils.get(guild.channels, id=int(channel_id))
                    await channel.delete()
        return True

    @app_commands.command(
        name = "remove",
        description="Remove the autochannel from this server"
    )
    @app_commands.checks.has_permissions(manage_channels = True)
    @app_commands.checks.bot_has_permissions(manage_channels = True)
    async def slash_autochannel_remove(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.data:
            self.data = await self.get_data()
        guild_id = interaction.guild.id
        if not (guild_data := self.data[str(guild_id)]):
            await interaction.followup.send("No autochannel found. use `/autochannel add` to add them.")
            return
        guild_data:dict
        guild = discord.utils.get(self.bot.guilds, id=guild_id)
        with contextlib.suppress(AttributeError):
            for channels in list(guild_data.values()):
                self.logger.debug(f"Deleting {channels}")
                category_channel = discord.utils.get(guild.channels, id=int(channels["id"]))
                voice_channel = discord.utils.get(guild.channels, id=int(channels["Voice"]))
                text_channel = discord.utils.get(guild.channels, id=int(channels["Text"]))
                await category_channel.delete()
                await voice_channel.delete()
                await text_channel.delete()
            del self.data[str(guild_id)]
        await self.set_data(self.data)
        # Why this suppress here?
        with contextlib.suppress(discord.app_commands.CommandInvokeError):
            await interaction.followup.send("Removed the autochannels")

    @app_commands.command(
        name = "add",
        description = "Set up voice category and channels, which lets each user make their own channels"
        )
    @app_commands.checks.has_permissions(manage_channels = True)
    @app_commands.checks.bot_has_permissions(manage_channels = True)
    async def slash_autochannel_add(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
            }
        await self._setup_autochannel(guild, overwrites)
        await interaction.followup.send("The channels are set up!\n use `/autochannel remove` before adding again to avoid issues.")
        await self.set_data(self.data)

    async def _setup_autochannel(self, guild:discord.Guild, overwrites:discord.PermissionOverwrite) -> None:
        CategoryChannel = await self._get_autochannel_category(guild, overwrites, "AC Channel")
        VoiceChannel = await self._get_autochannel_voice(guild, CategoryChannel, "AC Channel")
        TextChannel = await self._get_autochannel_text(guild, CategoryChannel, VoiceChannel, "AC Channel")
        await VoiceChannel.edit(name="Join Me!", reason="Autochannel rename")
        await TextChannel.edit(name="Autochannel Info", reason="Autochannel rename")

    async def _get_autochannel_text(
        self,
        guild:discord.Guild,
        CategoryChannel:discord.CategoryChannel,
        VoiceChannel:discord.VoiceChannel,
        text_channel_name:str
    ) -> discord.TextChannel:
        guild_id = str(guild.id)
        if not self.data:
            self.data = await self.get_data()
        try:
            text_channel_id = self.data[guild_id][text_channel_name]["Text"]
            TextChannel = discord.utils.get(guild.channels, id=text_channel_id)
            if not TextChannel:
                raise KeyError
            self.logger.debug(f"Found {TextChannel}")
        except KeyError:
            TextChannel = await CategoryChannel.create_text_channel(name=text_channel_name)
            msg = await TextChannel.send(f"To create your own voice and text channel, just join the voice channel <#{VoiceChannel.id}>")
            await msg.pin()
            self.data[guild_id][text_channel_name]["Text"] = TextChannel.id
            self.logger.debug(f"Created {TextChannel}")
        return TextChannel

    async def _get_autochannel_voice(
        self,
        guild:discord.Guild,
        CategoryChannel:discord.CategoryChannel,
        voice_channel_name:str
    ) -> discord.VoiceChannel:
        guild_id = str(guild.id)
        if not self.data:
            self.data = await self.get_data()
        try:
            voice_channel_id = self.data[guild_id][voice_channel_name]["Voice"]
            VoiceChannel = discord.utils.get(guild.channels, id=voice_channel_id)
            if not VoiceChannel:
                raise KeyError
            self.logger.debug(f"Found {VoiceChannel}")
        except KeyError:
                VoiceChannel = await CategoryChannel.create_voice_channel(name=voice_channel_name)
                self.data[guild_id][voice_channel_name]["Voice"] = VoiceChannel.id
                self.logger.debug(f"Created {VoiceChannel}")
        return VoiceChannel

    async def _get_autochannel_category(
        self,
        guild:discord.Guild,
        overwrites:discord.PermissionOverwrite,
        category_name:str
    ) -> discord.CategoryChannel:
        """Get or create category channels, then returns the Channel and changed data/dict

        Args:
            guild (discord.Guild):
            overwrites (discord.PermissionOverwrite):
            guild_id (str): Guild Id to look for

        Returns:
            discord.CategoryChannel:
        """
        guild_id = str(guild.id)
        if not self.data:
            self.data = await self.get_data()
        try:
            ac_id = self.data[guild_id][category_name]["id"]
            CategoryChannel = discord.utils.get(guild.channels, id=ac_id)
            if not CategoryChannel:
                raise KeyError
            self.logger.debug(f"Found {CategoryChannel}")
        except KeyError:
                CategoryChannel = await guild.create_category(name=category_name, overwrites=overwrites, reason="Autochannel")
                self.data[guild_id][category_name] = {"id": CategoryChannel.id}
                self.logger.debug(f"Created {CategoryChannel}")
        return CategoryChannel

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        if not self.data:
            self.data = await self.get_data()
        if after.channel:
            guild = after.channel.guild
            guild_id = str(guild.id)
            channel_id = after.channel.id
            with contextlib.suppress(KeyError):
                voice_id = self.data[guild_id]["AC Channel"]["Voice"]
                text_id = self.data[guild_id]["AC Channel"]["Text"]
            if channel_id != voice_id:
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(),
                guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none()),
                member: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
            }
            member_id = str(member.id)
            CategoryChannel = await self._get_autochannel_category(guild, overwrites, category_name=member_id)
            VoiceChannel = await self._get_autochannel_voice(guild, CategoryChannel, voice_channel_name=member_id)
            TextChannel = await self._get_autochannel_text(guild, CategoryChannel, VoiceChannel, text_channel_name=member_id)
            await member.move_to(VoiceChannel)
            if CategoryChannel.name == member_id:
                await CategoryChannel.edit(name=f"{member.name}'s Channels", reason="Autochannel Renamed to username")
            if VoiceChannel.name == member_id:
                await VoiceChannel.edit(name=f"{member.name}'s Voice", reason="Autochannel Renamed to username")
            if TextChannel.name == member_id:
                await TextChannel.edit(name=f"{member.name}'s Text", reason="Autochannel Renamed to username")
        if before.channel:
            with contextlib.suppress(KeyError):
                channel = before.channel
                guild = channel.guild
                member_id = str(member.id)
                guild_id = str(guild.id)
                channel_id = channel.id
                voice_id = self.data[guild_id][member_id]["Voice"]
                if channel_id != voice_id or len(channel.members) > 0:
                    return
                category_id = self.data[guild_id][member_id]["id"]
                text_id = self.data[guild_id][member_id]["Text"]
                category_channel = discord.utils.get(guild.categories, id=category_id)
                voice_channel = discord.utils.get(guild.voice_channels, id=voice_id)
                AC_text = discord.utils.get(guild.text_channels, id=text_id)
                await voice_channel.delete(reason="Autochannel is empty")
                await AC_text.delete(reason="Autochannel is empty")
                await category_channel.delete(reason="Autochannel is empty")
                del self.data[guild_id][member_id]
        await self.set_data(self.data)

async def setup(bot:commands.Bot):
	await bot.add_cog(Autochannel(bot))