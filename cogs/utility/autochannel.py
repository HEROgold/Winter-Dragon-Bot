import contextlib
import logging
import os
import pickle

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from tools import app_command_tools, dragon_database


@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels = True)
@app_commands.checks.bot_has_permissions(manage_channels = True)
class Autochannel(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = await self.get_data()
        if config.Database.PERIODIC_CLEANUP:
            self.database_cleanup.start()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    @tasks.loop(seconds=3600)
    async def database_cleanup(self) -> None:
        self.logger.info("Cleaning Autochannels...")
        for guild_id, autochannel_categories in list(self.data.items()):
            guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
            cleaned = await self._clean_categories(autochannel_categories, guild)
            if cleaned == True:
                self.logger.debug(f"Most (or all) channels from {guild_id} are cleaned.")
                # del self.data[autochannel_categories]
        await self.set_data(self.data)
        self.logger.info("Database cleaned up")

    async def _clean_categories(self, autochannel_categories:dict, guild:discord.Guild) -> dict:
        self.logger.info(f"Cleaning {guild} Category {autochannel_categories}")
        cleaned = False
        for key, channels in list(autochannel_categories.items()):
            if key == "AC Channel":
                continue
            cleaned = await self._clean_channels(channels, guild)
            if cleaned == False:
                continue
            del self.data[str(guild.id)][key]
        return cleaned

    async def _clean_channels(self, channels:dict, guild:discord.Guild) -> bool:
        self.logger.info(f"Cleaning Channels {channels}")
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
    async def slash_autochannel_remove(self, interaction:discord.Interaction) -> None:
        if not self.data:
            self.data = await self.get_data()
        guild_id = str(interaction.guild.id)
        try:
            self.data[guild_id]
            (guild_data := self.data[guild_id])
            guild_data:dict
        except KeyError:
            _, c_mention = await app_command_tools.Converter(bot=self.bot).get_app_sub_command(self.slash_autochannel_add)
            await interaction.response.send_message(f"No autochannel found. use {c_mention} to add them.")
            return
        guild = discord.utils.get(self.bot.guilds, id=guild_id)
        await interaction.response.defer()
        with contextlib.suppress(AttributeError):
            for channels in list(guild_data.values()):
                self.logger.debug(f"Deleting {channels}")
                category_channel = discord.utils.get(guild.channels, id=int(channels["id"]))
                voice_channel = discord.utils.get(guild.channels, id=int(channels["Voice"]))
                text_channel = discord.utils.get(guild.channels, id=int(channels["Text"]))
                await category_channel.delete()
                await voice_channel.delete()
                await text_channel.delete()
            del self.data[guild_id]
        await self.set_data(self.data)
        await interaction.followup.send("Removed the autochannels")

    @app_commands.command(
        name = "add",
        description = "Set up voice category and channels, which lets each user make their own channels"
        )
    async def slash_autochannel_add(self, interaction:discord.Interaction) -> None:
        await interaction.response.defer()
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
            }
        await self._setup_autochannel(guild, overwrites)
        _, c_mention = await app_command_tools.Converter(bot=self.bot).get_app_sub_command(self.slash_autochannel_remove)
        await interaction.followup.send(f"The channels are set up!\n use {c_mention} before adding again to avoid issues.")
        await self.set_data(self.data)

    async def _setup_autochannel(self, guild:discord.Guild, overwrites:discord.PermissionOverwrite) -> None:
        CategoryChannel = await self._get_autochannel_category(guild, overwrites, "AC Channel")
        VoiceChannel = await self._get_autochannel_voice(guild, CategoryChannel, "AC Channel")
        TextChannel = await self._get_autochannel_text(guild, CategoryChannel, "AC Channel")
        await VoiceChannel.edit(name="Join Me!", reason="Autochannel rename")
        await TextChannel.edit(name="Autochannel Info", reason="Autochannel rename")

    async def _get_autochannel_text(
        self,
        guild:discord.Guild,
        CategoryChannel:discord.CategoryChannel,
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
            TextChannel = await CategoryChannel.create_text_channel(
                name=text_channel_name, reason="Autochannel"
            )
            msg = await TextChannel.send(
                f"To create your own voice and text channel, just join the voice channel <#{self.data[guild_id]['AC Channel']['Voice']}>"
            )
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
                VoiceChannel = await CategoryChannel.create_voice_channel(name=voice_channel_name, reason="Autochannel")
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
                try:
                    self.data[guild_id][category_name] = {"id": CategoryChannel.id}
                except KeyError:
                    self.data[guild_id] = {category_name:{"id": CategoryChannel.id}}
                self.logger.debug(f"Created {CategoryChannel}")
        return CategoryChannel

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState) -> None:
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
            TextChannel = await self._get_autochannel_text(guild, CategoryChannel, text_channel_name=member_id)
            await member.move_to(VoiceChannel)
            if CategoryChannel.name == member_id:
                await CategoryChannel.edit(name=f"{member.name}'s Channels", reason="Autochannel Renamed to username")
            if VoiceChannel.name == member_id:
                await VoiceChannel.edit(name=f"{member.name}'s Voice", reason="Autochannel Renamed to username")
            if TextChannel.name == member_id:
                await TextChannel.edit(name=f"{member.name}'s Text", reason="Autochannel Renamed to username")
        if before.channel:
            # remove against spam, maybe start self.database_cleanup?
            # Test code below, before removing anything under contexlib.
            # await self._clean_categories(autochannel_categories=str(member.id), guild_id=str(before.channel.guild.id))
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
                category_channel = discord.utils.get(guild.categories, id=int(category_id))
                voice_channel = discord.utils.get(guild.voice_channels, id=int(voice_id))
                AC_text = discord.utils.get(guild.text_channels, id=int(text_id))
                await voice_channel.delete(reason="Autochannel is empty")
                await AC_text.delete(reason="Autochannel is empty")
                await category_channel.delete(reason="Autochannel is empty")
                del self.data[guild_id][member_id]
        await self.set_data(self.data)

async def setup(bot:commands.Bot) -> None:
	await bot.add_cog(Autochannel(bot))
