import asyncio
import json
import logging
from typing import Literal, Optional, Self, Union, get_overloads, overload

import discord
from discord import app_commands
from discord.ext import commands, tasks

from tools.config_reader import config
from tools import app_command_tools
from tools.database_tables import Channel, Guild, engine, Session
from tools.database_tables import Autochannel as ACP


# TODO: rewrite VoiceMaster to work with slash
# Abandon this Autochannel project.

AC_TYPE = "autochannel"
ALLOWED_TYPES = ["category", "text", "voice"]


def new_db_permissions(owner: discord.Guild | discord.Member) -> ACP:
    if isinstance(owner, discord.Member):
        permissions = {
            owner.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            owner.guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none()),
            owner: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
        }
    else:
        permissions = {
            owner.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            owner.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
        }

    for k, v in permissions.items():
        perms = {f"{k.id}":v._values} # type: ignore

    with Session(engine) as session:
        acp = ACP(
            owner_id = owner.id,
            permissions = json.dumps(perms)
        )
        session.add(acp)
        session.commit()
    return acp


def get_user_overwrites(owner: discord.Guild | discord.Member) -> discord.PermissionOverwrite:
    with Session(engine) as session:
        acp = session.query(ACP).where(ACP.owner_id == owner.id).first()
        if not acp:
            acp = new_db_permissions(owner)
            return json.loads(acp.permissions)


def audit_guild_channel_update(entry: discord.AuditLogEntry) -> None:
    after: discord.abc.GuildChannel = entry.after

    with Session(engine) as session:
        if acp := session.query(ACP).where(ACP.owner_id == entry.user.id).first():
            acp.permissions = json.dumps(after.overwrites.__dict__)
        else:
            session.add(ACP(
                owner_id = entry.user.id,
                permissions = json.dumps(after.overwrites.__dict__)
            ))
        session.commit()


def get_owner_from_id(owner_id: int, bot: commands.Bot):
    return bot.get_guild(owner_id) or bot.get_user(owner_id)


class AutomaticChannel:
    _discord_channel: Union[discord.CategoryChannel, discord.TextChannel, discord.VoiceChannel]
    _database_channel: ACP
    _id: int
    _name: Literal["category", "text", "voice"]
    _type: str = AC_TYPE


    @property
    def discord_channel(self) -> discord.CategoryChannel | discord.TextChannel | discord.VoiceChannel:
        return self._discord_channel


    @property
    def database_channel(self) -> Channel:
        return self._database_channel


    @property
    def name(self) -> Literal['category', 'text', 'voice']:
        return self._name


    @property
    def id(self) -> int:
        # self._id, self._discord_channel.id and self._database_channel.id should all be the same!
        if self._discord_channel.id == self._id \
        and self._database_channel.id == self._id:
            return self._id
        else:
            raise ValueError(f"database id and discord id mismatch: {self._database_channel.id}, {self._discord_channel} should both be {self._id}")


    @overload
    def __init__(
        self,
        discord_channel: discord.abc.GuildChannel,
        database_channel: Channel,
    ) -> None:
        pass


    @overload
    def __init__(
        self,
        discord_channel: discord.abc.GuildChannel
    ) -> None:
        pass


    @overload
    def __init__(
        self,
        database_channel: Channel,
        bot: commands.Bot
    ) -> None:
        pass


    def __init__(
        self,
        discord_channel: Optional[discord.abc.GuildChannel],
        database_channel: Optional[Channel],
        bot: Optional[commands.Bot],
    ) -> None:
        """
        Initializes an instance of the AutoChannel class.

        Args:
            discord_channel (discord.abc.GuildChannel): The Discord channel associated with the AutoChannel.
            database_channel (Channel): The database channel associated with the AutoChannel.
            bot (Optional[commands.Bot]): The Discord bot instance.

        Returns:
            None

        Raises:
            AttributeError: Raised when the wrong argument combination is provided.
            See overloaded functions for valid combinations

        Behavior:
        - If both `discord_channel` and `database_channel` are provided, their values are set.
        - If `discord_channel` is provided and `database_channel` is not provided,
        the `_database_channel` attribute is set by retrieving the database channel from `discord_channel`.
        - If `discord_channel` is not provided and `database_channel` is provided,
        the `_discord_channel` attribute is set by retrieving the Discord channel from `database_channel` and `bot`.
        """
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.logger.debug(f"{self}")
        self.session = Session(engine)

        if discord_channel and database_channel:
            self._discord_channel = discord_channel
            self._database_channel = database_channel
        elif discord_channel and not bot:
            self._database_channel = self._get_database_from_discord(discord_channel)
        elif database_channel and bot:
            self._discord_channel = self._get_discord_from_database(database_channel, bot)
        else:
            combinations = get_overloads(self.__init__) # TODO: test and check if results look good
            raise ValueError(f"Wrong argument combination, valid options are {combinations}")
        
        if database_channel.name not in ALLOWED_TYPES:
            raise ValueError(f"Expected one of {ALLOWED_TYPES} not {database_channel.name}")

        self._id = self.database_channel.id or self.discord_channel.id
        self._name = database_channel.name


    def _get_discord_from_database(
        self,
        database_channel: Channel,
        bot: commands.Bot
    ) -> discord.abc.GuildChannel:
        return discord.utils.get(bot.get_all_channels(), database_channel.id)


    def _get_database_from_discord(self, discord_channel: discord.abc.GuildChannel) -> Channel:
        return self.session.query(Channel).where(Channel.id == discord_channel.id).first()

    # TODO: add type hinting for overloaded create
    # each overload should show each expected combination of arguments

    @classmethod
    async def create(
        cls,
        guild: discord.Guild,
        channel_type: Literal["category", "text", "voice"] = None,
        reason: Optional[str] = None,
        overwrites: Optional[discord.PermissionOverwrite] = None,
        position: Optional[int] = None,
        owner: discord.Guild | discord.Member = None
    ) -> Self:
        """
        Creates a new channel in a Discord guild, and database row.

        Args:
            guild (discord.Guild): The guild in which to create the channel.
            channel_type ("category", "text", "voice", optional): The type of channel to create. Defaults to None.
            reason (str, optional): The reason for creating the channel. Defaults to None.
            overwrites (discord.PermissionOverwrite, optional): The permission overwrites for the channel. Defaults to None.
            position (int, optional): The position of the channel. Defaults to None.

        Returns:
            AutomaticChannel: An object representing the created channel and database row.

        Raises:
            ValueError: Raised when `channel_type` is None and not one of the allowed types.
        """
        try:
            logger = cls.logger
        except AttributeError:
            logger = logging.getLogger(f"{config['Main']['bot_name']}.AutomaticChannelCreate") # {cls.__name__}

        name = f"{owner}'s {channel_type}"
        # TODO: get_user_overwrites should return the dict of permissions, not or {}
        overwrites = overwrites or get_user_overwrites(owner) or {
            owner.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            owner.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none()),
        }
        logger.debug(f"{guild=}, {overwrites=}")

        logger.debug(f"creating {channel_type=}")
        if channel_type is None:
            raise ValueError(f"channel_type is None not one of {ALLOWED_TYPES}")
        elif channel_type == "category":
            discord_channel = await guild.create_category(name, reason=reason, overwrites=overwrites, position=position)
            logger.debug("created category")
        elif channel_type == "text":
            discord_channel = await guild.create_text_channel(name, reason=reason, overwrites=overwrites, position=position)
            logger.debug("created text")
        elif channel_type == "voice":
            discord_channel = await guild.create_voice_channel(name, reason=reason, overwrites=overwrites, position=position)
            logger.debug("created voice")
        else:
            logger.warning(f"unexpected {channel_type=}")

        discord_channel: discord.abc.GuildChannel
        logger.debug(f"channel: {discord_channel}")

        try:
            session = cls.session
        except AttributeError:
            session = Session(engine)

        channel = Channel(
            id = discord_channel.id,
            guild_id = discord_channel.guild.id,
            name = channel_type,
            type = AC_TYPE,
            autochannel_id = session.query(ACP).where(ACP.owner_id == owner.id)
        )

        session.add(channel)
        session.commit()
        session.close()

        return AutomaticChannel(
            discord_channel=discord_channel,
            database_channel=channel
        )


    def __dell__(self) -> None:
        self.session.close()


    def delete(self, reason: str) -> None:
        """
        1. Deletes the Discord channel associated with the instance.
        2. Deletes the database channel associated with the instance.
        3. Deletes the instance itself.

        Args:
            reason (str): The reason for the deletion.

        Returns:
            None
        """
        asyncio.ensure_future(self._discord_channel.delete(reason=reason))
        self.session.delete(self._database_channel)
        self.session.commit()


# TODO: figure out if AC channel or users channel
class AutomaticChannels:
    """A class that represents a collection of automatic channels."""
    def __init__(self, owner: discord.Guild | discord.Member, bot: commands.Bot) -> None:
        """Fetch existing automaticChannels from guild, if nothing is found create them
        """
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.session = Session(engine)
        self.owner = owner
        self.bot = bot
        self.async_init.start()


    @tasks.loop(count=1)
    async def async_init(self):
        owner = self.owner

        acp = self.session.query(ACP).where(ACP.owner_id == owner.id).first()
        if acp is None or not acp.channels:
            self.logger.warning("No known AutoChannels found")
            await self._create(owner)
            return

        self.logger.debug(f"Searching for autochannels, {acp=}")
        await self.search_autochannels(acp)
        self.logger.debug(f"End of loop. {self.category}, {self.text}, {self.voice}")


    async def search_autochannels(self, acp: ACP) -> None:
        for channel in acp.channels:
            self.logger.debug(f"{channel=}")
            if channel.type == AC_TYPE and channel.name in ALLOWED_TYPES:
                self.logger.debug(f"{channel} is guild autochannel")
                if channel.name == "category":
                    self.category = AutomaticChannel(database_channel=channel, bot=self.bot)
                    if not self.category:
                        continue
                    self.logger.debug(f"Found {self.category=}")
                elif channel.name == "text":
                    self.text = AutomaticChannel(database_channel=channel, bot=self.bot)
                    if not self.text:
                        continue
                    self.logger.debug(f"Found {self.text=}")
                elif channel.name == "voice":
                    self.voice = AutomaticChannel(database_channel=channel, bot=self.bot)
                    if not self.voice:
                        continue
                    self.logger.debug(f"Found {self.voice=}")
                else:
                    self.logger.debug(f"{channel.name=}")
                    break
        else:
            self.logger.debug("No channels found, how did we get here? 007")
            # await self._create()


    async def _create(self, owner: discord.Guild | discord.Member) -> None:
        self.logger.debug(f"creating autochannels for {owner}")
        overwrites = get_user_overwrites(owner)
        self.logger.debug("got perms")

        guild = owner.guild if isinstance(owner, discord.Member) else owner
        self.logger.debug("found guild")

        self.category = await AutomaticChannel.create(
            guild,
            channel_type="category",
            reason=f"New Automatic Channel for {owner}",
            overwrites=overwrites,
            owner=owner
        )
        self.logger.debug("created category")
        self.text = await AutomaticChannel.create(
            guild,
            channel_type="text",
            reason=f"New Automatic Channel for {owner}",
            overwrites=overwrites,
            owner=owner
        )
        self.logger.debug("created text")
        self.voice = await AutomaticChannel.create(
            guild,
            channel_type="voice",
            reason=f"New Automatic Channel for {owner}",
            overwrites=overwrites,
            owner=owner
        )
        self.logger.debug("created voice")
        self.logger.debug(f"Created new: {self.category}, {self.text}, {self.voice}")


    def __dell__(self) -> None:
        self.session.close()


    def delete(self, reason: str) -> None:
        """
        This method only exists to pass the `reason` parameter

        1. Deletes the Discord channel associated with the instance.
        2. Deletes the database channel associated with the instance.
        3. Deletes the instance itself.

        Args:
            reason (str): The reason for the deletion.

        Returns:
            None
        """
        self.category.delete(reason=reason)
        self.text.delete(reason=reason)
        self.voice.delete(reason=reason)


@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels = True)
@app_commands.checks.bot_has_permissions(manage_channels = True)
class Autochannel(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.act = app_command_tools.Converter(bot=self.bot)


    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        enum = discord.enums.AuditLogAction
        if entry.action == enum.channel_update:
            audit_guild_channel_update(entry)


    async def cog_load(self) -> None:
        self.database_cleanup.start()

    @tasks.loop(seconds=3600)
    async def database_cleanup(self) -> None:
        self.logger.info("Cleaning User Autochannels.")
        with Session(engine) as session:
            autochannels = session.query(ACP).all()
            guilds = session.query(Guild).all()
            guild_ids = [i.id for i in guilds]
            for autochannel in autochannels:
                if autochannel.id in guild_ids:
                    continue
                ac = AutomaticChannels(get_owner_from_id(autochannel.owner_id, self.bot), self.bot)
                if len(ac.voice.discord_channel.members) == 0:
                    ac.delete(reason="Automatic Channels Cleanup")
            session.commit()


    @database_cleanup.before_loop
    async def before_cleanup(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    @app_commands.command(
        name = "add",
        description = "Set up voice category and channels, which lets each user make their own channels"
    )
    async def slash_autochannel_add(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        ac = AutomaticChannels(interaction.guild, self.bot)
        _, c_mention = await app_command_tools.Converter(bot=self.bot).get_app_sub_command(self.slash_autochannel_remove)
        await interaction.followup.send(f"The channels are set up!\n use {c_mention} before adding again to avoid issues.")
        # with Session(engine) as session:
        #     result = session.execute(sqlalchemy.select(Channel).where(
        #         Channel.guild_id == interaction.guild.id,
        #         Channel.type == AC_TYPE
        #     ))
        #     if result.first():
        #         await interaction.response.send_message("Autochannel channels already set up", ephemeral=True)
        #         return
        # guild = interaction.guild
        # overwrites = {
        #     guild.default_role: discord.PermissionOverwrite(),
        #     guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
        # }
        # await self._setup_autochannel(guild, overwrites)


    @app_commands.command(
        name = "remove",
        description="Remove the autochannel from this server"
    )
    async def slash_autochannel_remove(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        ac = AutomaticChannels(interaction.guild, self.bot)
        _, c_mention_remove = await self.act.get_app_sub_command(self.slash_autochannel_remove)
        ac.delete(reason=f"Requested by {interaction.user.display_name} using {c_mention_remove}")
        await interaction.followup.send("Removed the autochannels")
        # with Session(engine) as session:
        #     result = session.execute(sqlalchemy.select(Channel).where(
        #         Channel.guild_id == interaction.guild.id, Channel.type == AC_TYPE
        #     ))
        #     if not result.all():
        #         _, c_mention_add = await self.act.get_app_sub_command(self.slash_autochannel_add)
        #         await interaction.response.send_message(f"No autochannel found. use {c_mention_add} to add them.")
        #         return
        # await self.remove_auto_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using {c_mention_remove}")


async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Autochannel(bot))
