"""The /stats command group: a guild's member counts, shown on demand and as the names of locked voice channels."""

from __future__ import annotations

from dataclasses import dataclass
lazy import asyncio
lazy from enum import StrEnum
lazy from typing import TYPE_CHECKING, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session, select
from wd_db.extension.model import SQLModel
lazy from wd_bot.checks import is_owner
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_discord import ChannelType, Permissions, is_gone, is_network_error
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.resources.channel import ChannelParams, GuildChannelParams, OverwriteParams, OverwriteType
lazy from wd_discord.snowflake import Snowflake
lazy from wd_discord.timestamp import DiscordTime
lazy from wd_errors import Refused, unwrap

lazy from winter_dragon.config import CogConfig


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Iterable, Mapping
    lazy from datetime import datetime

    lazy from wd_discord import Client, GuildCommandInteraction, NetworkError
    lazy from wd_discord.entities import BaseChannel, BaseGuild


class StatsSettings:
    """How often the stats channels are renamed to show the current counts."""

    update_interval = CogConfig(3600)
    """Seconds between two updates; Discord lets a channel be renamed only twice per 10 minutes, so keep it long."""


class StatKind(StrEnum):
    """What a stats channel shows; the category holding them is one too."""

    CATEGORY = "category"
    USERS = "users"
    ONLINE = "online"
    BOTS = "bots"
    CREATED = "created"
    PEAK = "peak"


SHOWN = (StatKind.USERS, StatKind.ONLINE, StatKind.BOTS, StatKind.CREATED, StatKind.PEAK)
"""The stats channels, in the order they're listed in the category."""
CATEGORY_NAME = "Stats"


class StatChannel(SQLModel, table=True):
    """One of a guild's stats channels, or the category holding them."""

    guild_id: int = Field(sa_type=BigInteger, index=True)
    channel_id: int = Field(sa_type=BigInteger, unique=True)
    kind: StatKind


class PeakOnline(SQLModel, table=True):
    """The most users a guild has seen online at once, since its stats channels were added."""

    guild_id: int = Field(sa_type=BigInteger, unique=True)
    peak: int = 0


STATS_TABLES = (StatChannel, PeakOnline)


@dataclass(frozen=True, slots=True)
class GuildCounts:
    """How many members a guild has, how many are bots and how many are online; Discord's counts are approximate."""

    members: int
    bots: int
    online: int
    """Members online, bots included."""
    created: datetime

    @property
    def users(self) -> int:
        """Members that aren't bots."""
        return max(self.members - self.bots, 0)

    @property
    def online_users(self) -> int:
        """Members online that aren't bots, taking every bot to be online."""
        return max(self.online - self.bots, 0)


async def count_bots(guild: BaseGuild) -> int | NetworkError:
    """Count the bots among ``guild``'s members."""
    members = await guild.all_members()
    if is_network_error(members):
        return members
    return sum(member.bot for member in members)


async def guild_counts(guild: BaseGuild) -> GuildCounts | NetworkError:
    """Read ``guild``'s member, bot and online counts."""
    fetched = await guild.fetch(with_counts=True)
    if is_network_error(fetched):
        return fetched
    bots = await count_bots(guild)
    if is_network_error(bots):
        return bots
    model = fetched.model
    return GuildCounts(
        members=model.approximate_member_count or 0,
        bots=bots,
        online=model.approximate_presence_count or 0,
        created=fetched.id.timestamp,
    )


def channel_name(kind: StatKind, counts: GuildCounts, peak: int) -> str:
    """Return the name of the stats channel showing ``kind``."""
    match kind:
        case StatKind.USERS:
            return f"Total Users: {counts.users}"
        case StatKind.ONLINE:
            return f"Online Users: {counts.online_users}"
        case StatKind.BOTS:
            return f"Total Bots: {counts.bots}"
        case StatKind.CREATED:
            return f"Created On: {counts.created:%Y-%m-%d}"
        case StatKind.PEAK:
            return f"Peak Online: {peak}"
        case StatKind.CATEGORY:
            return CATEGORY_NAME


@dataclass(frozen=True, slots=True)
class RenamePlan:
    """What an update does to a guild's stats channels: rename those showing stale counts, forget deleted ones."""

    renames: dict[int, str]
    """The new name of each channel, by ID, whose name changes."""
    gone: list[StatChannel]
    """The stats channels deleted by hand."""


def plan_renames(stats: Iterable[StatChannel], names: Mapping[int, str | None], counts: GuildCounts, peak: int) -> RenamePlan:
    """Plan updating ``stats`` to ``counts`` and ``peak``, given each existing channel's name by ID.

    Only names that change are renamed, since Discord allows two renames per channel per 10 minutes; the category
    keeps whatever name it was given.
    """
    renames: dict[int, str] = {}
    gone: list[StatChannel] = []
    for stat in stats:
        if stat.channel_id not in names:
            gone.append(stat)
        elif stat.kind is not StatKind.CATEGORY and names[stat.channel_id] != (name := channel_name(stat.kind, counts, peak)):
            renames[stat.channel_id] = name
    return RenamePlan(renames, gone)


def category_params(guild_id: int) -> GuildChannelParams:
    """Return the stats category: listed first, visible to everyone, and joined by nobody."""
    everyone = OverwriteParams(
        id=Snowflake(guild_id),  # the @everyone role shares the guild's ID
        type=OverwriteType.ROLE,
        allow=Permissions.VIEW_CHANNEL,
        deny=Permissions.CONNECT,
    )
    return GuildChannelParams(name=CATEGORY_NAME, type=ChannelType.GUILD_CATEGORY, position=0, permission_overwrites=[everyone])


def stats_embed(name: str, counts: GuildCounts, afk_channel: BaseChannel | None) -> Embed:
    """Return the embed /stats show answers with."""
    # I'd rather have these patterns as a subclass.
    # First asses pro's vs cons on this vs subclass.
    fields = [
        EmbedField(name="Users", value=str(counts.users), inline=True),
        EmbedField(name="Bots", value=str(counts.bots), inline=True),
        EmbedField(name="Online", value=str(counts.online_users), inline=True),
        EmbedField(name="Created on", value=DiscordTime(counts.created).with_relative(), inline=True),
        EmbedField(name="AFK channel", value="None" if afk_channel is None else afk_channel.mention, inline=True),
    ]
    return Embed(title=f"{name} Stats", description=f"Information about {name}", fields=fields)


def guild_stat_channels(session: Session, guild_id: int) -> list[StatChannel]:
    """Return the stats channels recorded for the guild ``guild_id``, category included."""
    return list(session.exec(select(StatChannel).where(StatChannel.guild_id == guild_id)))


def stats_guild_ids(session: Session) -> Generator[int]:
    """Yield every guild with stats channels."""
    yield from session.exec(select(StatChannel.guild_id).distinct())


class Stats(GroupCog, name="stats", description="Show this server's member counts", contexts=[InteractionContextType.GUILD]):
    """Shows a guild's member counts, and keeps a locked category of voice channels named after them up to date."""

    _task: asyncio.Task[None] | None = None

    @override
    async def load(self) -> None:
        """Create the stats tables if missing, then start the background task renaming the stats channels."""
        self.create_tables(*STATS_TABLES)
        self._task = self.bot.loop.create_task(self._run())

    @override
    async def unload(self) -> None:
        """Stop the background task."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        await super().unload()

    async def _run(self) -> None:
        """Update every guild's stats channels every :attr:`StatsSettings.update_interval` seconds, forever."""
        while True:
            try:
                await self.update_all()
            except Exception:
                self.logger.exception(t"Updating stats channels failed")
            await asyncio.sleep(StatsSettings.update_interval)

    async def update_all(self) -> None:
        """Update the stats channels of every guild that has them."""
        with Session(self.bind) as session:
            guild_ids = list(stats_guild_ids(session))
        for guild_id in guild_ids:
            await self.update_guild(guild_id)

    async def update_guild(self, guild_id: int) -> None:
        """Rename ``guild_id``'s stats channels to the current counts, record a new peak, and forget deleted ones."""
        guild = self.bot.client.guilds.partial(guild_id)
        counts = await guild_counts(guild)
        channels = await guild.fetch_channels()
        if is_network_error(counts) or is_network_error(channels):
            self.logger.warning(t"Could not read guild {guild_id} to update its stats: {counts} {channels}")
            return
        names = {int(channel.id): channel.name for channel in channels}
        with Session(self.bind) as session:
            peak = self._raise_peak(session, guild_id, counts.online_users)
            plan = plan_renames(guild_stat_channels(session, guild_id), names, counts, peak)
            for stat in plan.gone:
                session.delete(stat)
            session.commit()
        for channel_id, name in plan.renames.items():
            renamed = await self.bot.client.channels.partial(channel_id).edit(ChannelParams(name=name))
            if is_network_error(renamed):
                self.logger.warning(t"Could not rename stats channel {channel_id}: {renamed}")

    @staticmethod
    def _raise_peak(session: Session, guild_id: int, online: int) -> int:
        """Record ``online`` as ``guild_id``'s peak if it's higher than the one recorded; return the peak."""
        record = session.exec(select(PeakOnline).where(PeakOnline.guild_id == guild_id)).first() or PeakOnline(
            guild_id=guild_id,
        )
        record.peak = max(record.peak, online)
        session.add(record)
        return record.peak

    async def create_channels(self, client: Client, guild_id: int, *, reason: str) -> NetworkError | None:
        """Create ``guild_id``'s locked stats category and its channels, named after the current counts."""
        guild = client.guilds.partial(guild_id)
        counts = await guild_counts(guild)
        if is_network_error(counts):
            return counts
        with Session(self.bind) as session:
            peak = self._raise_peak(session, guild_id, counts.online_users)
            session.commit()
        names = {kind: channel_name(kind, counts, peak) for kind in SHOWN}
        created, failure = await self._create_stat_channels(guild, names, reason=reason)
        with Session(self.bind) as session:
            session.add_all(created)
            session.commit()
        return failure

    @staticmethod
    async def _create_stat_channels(
        guild: BaseGuild,
        names: Mapping[StatKind, str],
        *,
        reason: str,
    ) -> tuple[list[StatChannel], NetworkError | None]:
        """Create the stats category and a channel per entry of ``names``; return what was made and what stopped it."""
        guild_id = int(guild.id)
        category = await guild.create_channel(category_params(guild_id), reason=reason)
        if is_network_error(category):
            return [], category
        created = [StatChannel(guild_id=guild_id, channel_id=int(category.id), kind=StatKind.CATEGORY)]
        for kind, name in names.items():
            params = GuildChannelParams(name=name, type=ChannelType.GUILD_VOICE, parent_id=category.id)
            channel = await guild.create_channel(params, reason=reason)
            if is_network_error(channel):
                return created, channel
            created.append(StatChannel(guild_id=guild_id, channel_id=int(channel.id), kind=kind))
        return created, None

    async def remove_channels(self, client: Client, stats: Iterable[StatChannel], *, reason: str) -> bool:
        """Delete the channels of ``stats``, category last, forgetting each one that's gone; whether all of them are.

        A channel that couldn't be deleted for another reason stays recorded, so removing again retries it; so does the
        category while any of its channels is left.
        """
        ordered = sorted(stats, key=lambda stat: stat.kind is StatKind.CATEGORY)
        gone: list[StatChannel] = []
        for tried, stat in enumerate(ordered):
            if stat.kind is StatKind.CATEGORY and len(gone) < tried:
                continue
            deleted = await client.channels.partial(stat.channel_id).delete(reason=reason)
            if is_gone(deleted):
                gone.append(stat)
            else:
                self.logger.warning(t"Could not delete stats channel {stat.channel_id}: {deleted}")
        with Session(self.bind) as session:
            for stat in gone:
                session.delete(session.merge(stat))
            session.commit()
        return len(gone) == len(ordered)

    @Cog.command(name="show", description="Show this server's member counts")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def show(self, interaction: GuildCommandInteraction) -> None:
        """Answer with an embed of the guild's member counts."""
        unreadable = "I couldn't read this server's counts."
        guild = unwrap(await interaction.guild.fetch(), unreadable)
        counts = unwrap(await guild_counts(interaction.guild), unreadable)
        await interaction.respond(embeds=[stats_embed(guild.name, counts, guild.afk_channel)])

    @Cog.command(  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
        name="add",
        description="Add a category of channels showing this server's member counts",
        requires=Permissions.MANAGE_CHANNELS,
    )
    async def add(self, interaction: GuildCommandInteraction) -> None:
        """Create the stats channels, unless the guild has them already."""
        guild_id = int(interaction.guild_id)
        with Session(self.bind) as session:
            exists = bool(guild_stat_channels(session, guild_id))
        if exists:
            msg = f"This server has stats channels already; {self.mention(self.remove)} removes them."
            raise Refused(msg)
        await interaction.defer(ephemeral=True)
        reason = self.audit_reason(interaction, self.add, "Requested")
        if (failure := await self.create_channels(self.bot.client, guild_id, reason=reason)) is not None:
            msg = f"I couldn't set up every stats channel: {failure}"
            raise Refused(msg, cause=failure)
        await interaction.followup("Stats channels are set up.", ephemeral=True)

    @Cog.command(  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
        name="remove",
        description="Remove the stats category and its channels",
        requires=Permissions.MANAGE_CHANNELS,
    )
    async def remove(self, interaction: GuildCommandInteraction) -> None:
        """Delete the guild's stats channels."""
        with Session(self.bind) as session:
            stats = guild_stat_channels(session, int(interaction.guild_id))
        if not stats:
            msg = f"This server has no stats channels; {self.mention(self.add)} adds them."
            raise Refused(msg)
        await interaction.defer(ephemeral=True)
        reason = self.audit_reason(interaction, self.remove, "Requested")
        if not await self.remove_channels(self.bot.client, stats, reason=reason):
            msg = "I couldn't delete every stats channel; run it again to retry the rest."
            raise Refused(msg)
        await interaction.followup("Removed the stats channels.", ephemeral=True)

    @Cog.command(name="reset", description="Recreate the stats channels of every server (bot owners only)")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def reset(self, interaction: GuildCommandInteraction) -> None:
        """Delete and recreate every guild's stats channels; only the bot's owners may."""
        if not await is_owner(self.bot.client, interaction.user.id):
            msg = "Only the bot's owners can do that."
            raise Refused(msg)
        await interaction.defer(ephemeral=True)
        reason = self.audit_reason(interaction, self.reset, "Requested")
        with Session(self.bind) as session:
            by_guild = {guild_id: guild_stat_channels(session, guild_id) for guild_id in stats_guild_ids(session)}
        failed = []
        for guild_id, stats in by_guild.items():
            removed = await self.remove_channels(self.bot.client, stats, reason=reason)
            if not removed or await self.create_channels(self.bot.client, guild_id, reason=reason) is not None:
                failed.append(guild_id)
        self.logger.info(t"Reset the stats channels of {len(by_guild)} guilds, failing for {failed}")
        message = f"Reset the stats channels of {len(by_guild)} servers."
        await interaction.followup(
            message if not failed else f"{message} Failed for: {', '.join(map(str, failed))}",
            ephemeral=True,
        )
