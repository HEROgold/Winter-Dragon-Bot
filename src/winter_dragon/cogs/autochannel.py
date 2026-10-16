"""The /autochannel command group: joining a guild's hub voice channel gives a member a voice channel of their own.

The member's channel is created next to the hub, the member is moved into it, and it is deleted once everyone left.
Who is in which voice channel is tracked from GUILD_CREATE's voice states and every VOICE_STATE_UPDATE since.
"""

from __future__ import annotations

from dataclasses import dataclass, field
lazy import asyncio
lazy from collections import defaultdict
lazy from typing import TYPE_CHECKING, Annotated, Unpack, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session, select
from wd_db.extension.model import SQLModel
lazy from wd_bot.cogs import BotArgs, Cog, GroupCog
lazy from wd_bot.commands import ChannelTypes

# Command resolves option annotations from module globals at runtime, so Channel must be available here.
lazy from wd_discord import (
    Channel,
    ChannelType,
    Member,
    Permissions,
    is_gone,
    is_network_error,
)
lazy from wd_discord.errors import ApiResponseError
lazy from wd_discord.gateway import EventName
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.resources.channel import ChannelParams, GuildChannelParams, OverwriteParams, OverwriteType
lazy from wd_discord.resources.channel.params import MAX_USER_LIMIT
lazy from wd_errors import Refused, unwrap


if TYPE_CHECKING:
    lazy from collections.abc import Iterable

    lazy from wd_discord import GatewayGuild, GuildCommandInteraction, NetworkError, PartialMember, VoiceState
    lazy from wd_discord.entities import PartialGuild
    lazy from wd_discord.snowflake import Snowflake


MAX_NAME_LENGTH = 100
"""Discord's limit on a channel name's length."""
OWNER_PERMISSIONS = (
    Permissions.VIEW_CHANNEL
    | Permissions.CONNECT
    | Permissions.SPEAK
    | Permissions.STREAM
    | Permissions.PRIORITY_SPEAKER
    | Permissions.MUTE_MEMBERS
    | Permissions.DEAFEN_MEMBERS
    | Permissions.MOVE_MEMBERS
    | Permissions.MANAGE_CHANNELS
)
"""What a member may do in their own channel: run it, but not change who may see it."""
CREATE_REASON = "Automatic channel"


class AutoChannelHub(SQLModel, table=True):
    """A guild's hub: the voice channel that gives whoever joins it a channel of their own."""

    guild_id: int = Field(sa_type=BigInteger, unique=True)
    channel_id: int = Field(sa_type=BigInteger)
    max_channels: int = 0
    """How many automatic channels the guild allows at once; 0 means no limit."""


class AutoChannel(SQLModel, table=True):
    """A member's automatic channel."""

    guild_id: int = Field(sa_type=BigInteger, index=True)
    owner_id: int = Field(sa_type=BigInteger, index=True)
    channel_id: int = Field(sa_type=BigInteger, unique=True)


class AutoChannelSettings(SQLModel, table=True):
    """How a member wants their automatic channels: its name and user limit, in every guild."""

    user_id: int = Field(sa_type=BigInteger, unique=True)
    name: str | None = None
    """The channel's name; ``None`` names it after the member."""
    user_limit: int = 0
    """How many users fit in the channel; 0 means no limit."""


AUTOCHANNEL_TABLES = (AutoChannelHub, AutoChannel, AutoChannelSettings)


@dataclass
class VoiceOccupancy:
    """Who is in which voice channel, per guild, as far as the gateway told."""

    _channels: defaultdict[int, dict[int, int]] = field(default_factory=lambda: defaultdict(dict))
    """Per guild, the voice channel each connected member is in."""

    def reset(self, guild_id: int, states: Iterable[VoiceState]) -> None:
        """Forget what was known about ``guild_id``, and learn ``states`` instead."""
        self._channels[guild_id] = {int(state.user.id): int(state.channel.id) for state in states if state.channel is not None}

    def move(self, guild_id: int, user_id: int, channel_id: int | None) -> int | None:
        """Record that ``user_id`` is now in ``channel_id``, or left voice when ``None``; return where they were."""
        before = self._channels[guild_id].pop(user_id, None)
        if channel_id is not None:
            self._channels[guild_id][user_id] = channel_id
        return before

    def occupied(self, guild_id: int, channel_id: int) -> bool:
        """Whether anyone is in the voice channel ``channel_id``."""
        return channel_id in self._channels[guild_id].values()


def owner_overwrite(user_id: Snowflake) -> OverwriteParams:
    """Return the overwrite letting the member ``user_id`` run their own channel."""
    return OverwriteParams(id=user_id, type=OverwriteType.MEMBER, allow=OWNER_PERMISSIONS)


def default_name(display_name: str) -> str:
    """Return the name of a member's channel when they didn't choose one."""
    return f"{display_name}'s channel"[:MAX_NAME_LENGTH]


def channel_params(member: Member, parent_id: Snowflake | None, settings: AutoChannelSettings) -> GuildChannelParams:
    """Return ``member``'s new channel: under ``parent_id``, named and limited as their ``settings`` say."""
    return GuildChannelParams(
        name=settings.name or default_name(member.display_name),
        type=ChannelType.GUILD_VOICE,
        parent_id=parent_id,
        user_limit=settings.user_limit,
        permission_overwrites=[owner_overwrite(member.id)],
    )


def hub_of(session: Session, guild_id: int) -> AutoChannelHub | None:
    """Return the guild ``guild_id``'s hub, if it has one."""
    return session.exec(select(AutoChannelHub).where(AutoChannelHub.guild_id == guild_id)).first()


def owned_channel(session: Session, guild_id: int, owner_id: int) -> AutoChannel | None:
    """Return the automatic channel the member ``owner_id`` has in the guild ``guild_id``, if any."""
    query = select(AutoChannel).where(AutoChannel.guild_id == guild_id, AutoChannel.owner_id == owner_id)
    return session.exec(query).first()


def settings_of(session: Session, user_id: int) -> AutoChannelSettings:
    """Return the member ``user_id``'s channel settings; defaults when they never set any."""
    found = session.exec(select(AutoChannelSettings).where(AutoChannelSettings.user_id == user_id)).first()
    return found or AutoChannelSettings(user_id=user_id)


class AutoChannels(
    GroupCog,
    name="autochannel",
    description="Voice channels of your own, made by joining the hub channel",
    contexts=[InteractionContextType.GUILD],
):
    """Gives a member who joins the hub their own voice channel, and deletes it once it's empty."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Start without knowing who is in which voice channel; GUILD_CREATE fills that in."""
        super().__init__(**kwargs)
        self.voice = VoiceOccupancy()
        self._lock = asyncio.Lock()

    @override
    async def load(self) -> None:
        """Create the autochannel tables if missing."""
        self.create_tables(*AUTOCHANNEL_TABLES)

    @Cog.listener(EventName.GUILD_CREATE)
    async def on_guild_create(self, guild: GatewayGuild) -> None:
        """Learn who is in which voice channel, then delete the automatic channels that emptied while offline."""
        guild_id = int(guild.id)
        self.voice.reset(guild_id, guild.voice_states)
        with Session(self.bind) as session:
            channels = list(session.exec(select(AutoChannel).where(AutoChannel.guild_id == guild_id)))
        for channel in channels:
            if not self.voice.occupied(guild_id, channel.channel_id):
                await self.delete_channel(channel)

    @Cog.listener(EventName.VOICE_STATE_UPDATE)
    async def on_voice_state_update(self, state: VoiceState) -> None:
        """Give a member joining the hub their own channel, and delete an automatic channel the member left empty."""
        if state.guild is None:
            return
        guild_id, user_id = int(state.guild.id), int(state.user.id)
        async with self._lock:
            after = None if state.channel is None else int(state.channel.id)
            before = self.voice.move(guild_id, user_id, after)
            with Session(self.bind) as session:
                hub = hub_of(session, guild_id)
                left = None if before is None or before == after else self._auto_channel(session, before)
            if hub is not None and after == hub.channel_id and state.member is not None:
                await self.give_channel(state.member, hub)
            if left is not None and not self.voice.occupied(guild_id, left.channel_id):
                await self.delete_channel(left)

    @staticmethod
    def _auto_channel(session: Session, channel_id: int) -> AutoChannel | None:
        return session.exec(select(AutoChannel).where(AutoChannel.channel_id == channel_id)).first()

    async def give_channel(self, member: Member | PartialMember, hub: AutoChannelHub) -> None:
        """Move ``member`` into their automatic channel, creating it next to ``hub`` when they have none.

        A member whose channel is gone gets a new one; one who couldn't be moved for another reason (they left voice
        meanwhile, say) keeps theirs.
        """
        guild_id, user_id = int(member.guild_id), int(member.id)
        with Session(self.bind) as session:
            existing = owned_channel(session, guild_id, user_id)
            count = len(session.exec(select(AutoChannel).where(AutoChannel.guild_id == guild_id)).all())
            settings = settings_of(session, user_id)
        if existing is not None:
            moved = await member.move_to(member.guild.channel(existing.channel_id), reason=CREATE_REASON)
            if not (isinstance(moved, ApiResponseError) and moved.unknown_resource):
                if is_network_error(moved):
                    self.logger.debug(t"Could not move {user_id} to their channel {existing.channel_id}: {moved}")
                return
            await self.delete_channel(existing)
            count -= 1
        if hub.max_channels and count >= hub.max_channels:
            await self._tell(member, "This server has as many automatic channels as it allows; try again later.")
            return
        failure = await self.create_channel(member, hub, settings)
        if failure is not None:
            self.logger.warning(t"Could not give {user_id} a channel in guild {guild_id}: {failure}")

    async def create_channel(
        self,
        member: Member | PartialMember,
        hub: AutoChannelHub,
        settings: AutoChannelSettings,
    ) -> NetworkError | None:
        """Create ``member``'s channel in the hub's category, remember it and move them into it."""
        client = self.bot.client
        hub_channel = await client.channels.partial(hub.channel_id).fetch()
        if is_network_error(hub_channel):
            return hub_channel
        full = member if isinstance(member, Member) else await member.fetch()
        if is_network_error(full):
            return full
        params = channel_params(full, None if hub_channel.parent is None else hub_channel.parent.id, settings)
        channel = await client.guilds.partial(hub.guild_id).create_channel(params, reason=f"{CREATE_REASON} for {full.id}")
        if is_network_error(channel):
            return channel
        record = AutoChannel(guild_id=hub.guild_id, owner_id=int(full.id), channel_id=int(channel.id))
        with Session(self.bind) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        moved = await full.move_to(channel, reason=CREATE_REASON)
        if is_network_error(moved):  # they left the hub before their channel was ready
            await self.delete_channel(record)
            return moved
        return None

    async def delete_channel(self, channel: AutoChannel) -> None:
        """Delete the automatic ``channel`` and forget it once it's gone; one that's left is tried again later."""
        deleted = await self.bot.client.channels.partial(channel.channel_id).delete(reason="Automatic channel is empty")
        if not is_gone(deleted):
            self.logger.warning(t"Could not delete automatic channel {channel.channel_id}: {deleted}")
            return
        with Session(self.bind) as session:
            found = session.get(AutoChannel, channel.id)
            if found is not None:
                session.delete(found)
                session.commit()

    async def _tell(self, member: Member | PartialMember, message: str) -> None:
        """DM ``member`` ``message``; members with closed DMs just don't hear it."""
        sent = await self.bot.client.users.partial(member.id).send(message)
        if is_network_error(sent):
            self.logger.debug(t"Could not DM {member.id}: {sent}")

    @Cog.command(  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
        name="setup",
        description="Create a category with a hub channel members join to get their own",
        requires=Permissions.MANAGE_GUILD,
    )
    async def setup(self, interaction: GuildCommandInteraction, category_name: str, hub_name: str) -> None:
        """Create the category ``category_name`` holding the hub voice channel ``hub_name``."""
        guild_id = int(interaction.guild_id)
        with Session(self.bind) as session:
            exists = hub_of(session, guild_id) is not None
        if exists:
            msg = f"This server has a hub already; {self.mention(self.mark)} moves it."
            raise Refused(msg)
        if not (0 < len(category_name) <= MAX_NAME_LENGTH and 0 < len(hub_name) <= MAX_NAME_LENGTH):
            msg = f"Keep both names under {MAX_NAME_LENGTH} characters."
            raise Refused(msg)
        hub = unwrap(
            await self._create_hub(interaction.guild, category_name, hub_name),
            "I couldn't create the hub; do I have the Manage Channels permission?",
        )
        with Session(self.bind) as session:
            session.add(AutoChannelHub(guild_id=guild_id, channel_id=int(hub.id)))
            session.commit()
        await interaction.respond(f"All set: joining {hub.mention} gives members their own channel.", ephemeral=True)

    @staticmethod
    async def _create_hub(guild: PartialGuild, category_name: str, hub_name: str) -> Channel | NetworkError:
        """Create the category ``category_name`` and the hub voice channel ``hub_name`` in it; return the hub."""
        category = await guild.create_channel(GuildChannelParams(name=category_name, type=ChannelType.GUILD_CATEGORY))
        if is_network_error(category):
            return category
        return await guild.create_channel(
            GuildChannelParams(name=hub_name, type=ChannelType.GUILD_VOICE, parent_id=category.id),
            reason="Automatic channels hub",
        )

    @Cog.command(  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
        name="mark",
        description="Make a voice channel the hub members join to get their own",
        requires=Permissions.MANAGE_GUILD,
    )
    async def mark(
        self,
        interaction: GuildCommandInteraction,
        channel: Annotated[Channel, ChannelTypes(ChannelType.GUILD_VOICE)],
    ) -> None:
        """Make ``channel`` the guild's hub, replacing the one it had."""
        guild_id = int(interaction.guild_id)
        with Session(self.bind) as session:
            hub = hub_of(session, guild_id) or AutoChannelHub(guild_id=guild_id, channel_id=int(channel.id))
            hub.channel_id = int(channel.id)
            session.add(hub)
            session.commit()
        await interaction.respond(f"Joining {channel.mention} now gives members their own channel.", ephemeral=True)

    @Cog.command(  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
        name="guild-limit",
        description="Set how many automatic channels this server allows at once",
        requires=Permissions.MANAGE_GUILD,
    )
    async def guild_limit(self, interaction: GuildCommandInteraction, limit: int) -> None:
        """Allow at most ``limit`` automatic channels at once, 0 for no limit."""
        if limit < 0:
            msg = "Give me 0 for no limit, or a positive number."
            raise Refused(msg)
        with Session(self.bind) as session:
            hub = hub_of(session, int(interaction.guild_id))
            if hub is not None:
                hub.max_channels = limit
                session.add(hub)
                session.commit()
        if hub is None:
            msg = f"Set up a hub first, with {self.mention(self.setup)}."
            raise Refused(msg)
        shown = "no limit" if limit == 0 else f"at most {limit} at once"
        await interaction.respond(f"This server now allows {shown} automatic channels.", ephemeral=True)

    @Cog.command(name="limit", description="Set how many users fit in your channel")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def set_limit(self, interaction: GuildCommandInteraction, limit: int) -> None:
        """Remember ``limit`` as the invoker's user limit, and apply it to their channel here if they have one."""
        if not 0 <= limit <= MAX_USER_LIMIT:
            msg = f"Give me 0 for no limit, or up to {MAX_USER_LIMIT}."
            raise Refused(msg)
        await self._change(interaction, ChannelParams(user_limit=limit), user_limit=limit)

    @Cog.command(name="name", description="Set the name of your channel")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def set_name(self, interaction: GuildCommandInteraction, name: str) -> None:
        """Remember ``name`` as the invoker's channel name, and rename their channel here if they have one."""
        if not 0 < len(name) <= MAX_NAME_LENGTH:
            msg = f"Keep the name under {MAX_NAME_LENGTH} characters."
            raise Refused(msg)
        await self._change(interaction, ChannelParams(name=name), name=name)

    async def _change(self, interaction: GuildCommandInteraction, params: ChannelParams, **setting: str | int) -> None:
        """Save the invoker's ``setting``, then apply ``params`` to their channel in this guild, if they have one."""
        user_id = int(interaction.user.id)
        with Session(self.bind) as session:
            settings = settings_of(session, user_id)
            for key, value in setting.items():
                setattr(settings, key, value)
            session.add(settings)
            session.commit()
            owned = owned_channel(session, int(interaction.guild_id), user_id)
        if owned is None:
            await interaction.respond("Saved; your next channel gets it.", ephemeral=True)
            return
        edited = await self.bot.client.channels.partial(owned.channel_id).edit(params, reason=f"Asked by its owner {user_id}")
        if is_network_error(edited):
            msg = f"Saved, but I couldn't change your channel: {edited}"
            raise Refused(msg, cause=edited)
        await interaction.respond(f"Saved and applied to {edited.mention}.", ephemeral=True)
