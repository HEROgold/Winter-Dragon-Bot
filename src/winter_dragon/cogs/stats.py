"""The /stats command group: a guild's member counts, shown on demand and as the names of locked voice channels."""

from __future__ import annotations

from dataclasses import dataclass
lazy import asyncio
lazy from enum import StrEnum
lazy from typing import TYPE_CHECKING, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session, select
from wd_db.extension.model import SQLModel
lazy from wd_bot.checks import is_owner, member_has
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_config.stats import StatsSettings
lazy from wd_discord import ChannelType, Permissions, is_network_error
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.entities.guild import MAX_MEMBERS_PER_PAGE
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.resources.channel import ChannelParams, GuildChannelParams, OverwriteParams, OverwriteType
lazy from wd_discord.snowflake import Snowflake
lazy from wd_discord.timestamp import DiscordTime


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Iterable
    lazy from datetime import datetime

    lazy from wd_bot.commands import Command
    lazy from wd_discord import Client, CommandInteraction, NetworkError
    lazy from wd_discord.entities import BaseGuild


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
    """Count the bots among ``guild``'s members, a page of members at a time."""
    bots = 0
    after: Snowflake | None = None
    while True:
        page = await guild.members(after=after)
        if is_network_error(page):
            return page
        members = list(page)
        bots += sum(member.bot for member in members)
        if len(members) < MAX_MEMBERS_PER_PAGE:
            return bots
        after = members[-1].id


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


def stats_embed(name: str, counts: GuildCounts, afk_channel_id: Snowflake | None) -> Embed:
    """Return the embed /stats show answers with."""
    fields = [
        EmbedField(name="Users", value=str(counts.users), inline=True),
        EmbedField(name="Bots", value=str(counts.bots), inline=True),
        EmbedField(name="Online", value=str(counts.online_users), inline=True),
        EmbedField(name="Created on", value=DiscordTime(counts.created).with_relative(), inline=True),
        EmbedField(name="AFK channel", value="None" if afk_channel_id is None else f"<#{afk_channel_id}>", inline=True),
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
        """Rename ``guild_id``'s stats channels to the current counts, and record a new peak.

        Only channels whose name changes are renamed, since Discord allows two renames per channel per 10 minutes.
        Channels deleted by hand are forgotten.
        """
        guild = self.bot.client.guilds.partial(guild_id)
        counts = await guild_counts(guild)
        channels = await guild.channels()
        if is_network_error(counts) or is_network_error(channels):
            self.logger.warning(t"Could not read guild {guild_id} to update its stats: {counts} {channels}")
            return
        names = {int(channel.id): channel.name for channel in channels}
        with Session(self.bind) as session:
            peak = self._raise_peak(session, guild_id, counts.online_users)
            for stat in guild_stat_channels(session, guild_id):
                if stat.channel_id not in names:
                    session.delete(stat)
                    continue
                name = channel_name(stat.kind, counts, peak)
                if stat.kind is not StatKind.CATEGORY and names[stat.channel_id] != name:
                    renamed = await self.bot.client.channels.partial(stat.channel_id).edit(ChannelParams(name=name))
                    if is_network_error(renamed):
                        self.logger.warning(t"Could not rename stats channel {stat.channel_id}: {renamed}")
            session.commit()

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
        everyone = OverwriteParams(
            id=Snowflake(guild_id),  # the @everyone role shares the guild's ID
            type=OverwriteType.ROLE,
            allow=Permissions.VIEW_CHANNEL,
            deny=Permissions.CONNECT,
        )
        category = await guild.create_channel(
            GuildChannelParams(
                name=CATEGORY_NAME,
                type=ChannelType.GUILD_CATEGORY,
                position=0,
                permission_overwrites=[everyone],
            ),
            reason=reason,
        )
        if is_network_error(category):
            return category
        created = [StatChannel(guild_id=guild_id, channel_id=int(category.id), kind=StatKind.CATEGORY)]
        failure = None
        with Session(self.bind) as session:
            peak = self._raise_peak(session, guild_id, counts.online_users)
            for kind in SHOWN:
                params = GuildChannelParams(
                    name=channel_name(kind, counts, peak),
                    type=ChannelType.GUILD_VOICE,
                    parent_id=category.id,
                )
                channel = await guild.create_channel(params, reason=reason)
                if is_network_error(channel):
                    failure = channel
                    break
                created.append(StatChannel(guild_id=guild_id, channel_id=int(channel.id), kind=kind))
            session.add_all(created)
            session.commit()
        return failure

    async def remove_channels(self, client: Client, stats: Iterable[StatChannel], *, reason: str) -> None:
        """Delete the channels of ``stats``, category last, and forget them; channels already gone are just forgotten."""
        ordered = sorted(stats, key=lambda stat: stat.kind is StatKind.CATEGORY)
        with Session(self.bind) as session:
            for stat in ordered:
                deleted = await client.channels.partial(stat.channel_id).delete(reason=reason)
                if is_network_error(deleted):
                    self.logger.warning(t"Could not delete stats channel {stat.channel_id}: {deleted}")
                session.delete(session.merge(stat))
            session.commit()

    @Cog.command(name="show", description="Show this server's member counts")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def show(self, interaction: CommandInteraction) -> None:
        """Answer with an embed of the guild's member counts."""
        partial = interaction.guild
        guild = None if partial is None else await partial.fetch()
        counts = None if partial is None else await guild_counts(partial)
        if guild is None or counts is None or is_network_error(guild) or is_network_error(counts):
            await interaction.respond("I couldn't read this server's counts.", ephemeral=True)
            return
        await interaction.respond(embeds=[stats_embed(guild.name, counts, guild.afk_channel_id)])

    @Cog.command(name="add", description="Add a category of channels showing this server's member counts")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def add(self, interaction: CommandInteraction) -> None:
        """Create the stats channels, unless the guild has them already; needs MANAGE_CHANNELS."""
        guild = interaction.guild
        if guild is None or not member_has(interaction, Permissions.MANAGE_CHANNELS):
            await interaction.respond("You need the Manage Channels permission for that.", ephemeral=True)
            return
        with Session(self.bind) as session:
            exists = bool(guild_stat_channels(session, int(guild.id)))
        if exists:
            await interaction.respond(
                f"This server has stats channels already; {self.mention(self.remove)} removes them.",
                ephemeral=True,
            )
            return
        await interaction.defer(ephemeral=True)
        failure = await self.create_channels(self.bot.client, int(guild.id), reason=self._reason(interaction, self.add))
        message = "Stats channels are set up." if failure is None else f"I couldn't set up every stats channel: {failure}"
        await interaction.followup(message, ephemeral=True)

    @Cog.command(name="remove", description="Remove the stats category and its channels")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def remove(self, interaction: CommandInteraction) -> None:
        """Delete the guild's stats channels; needs MANAGE_CHANNELS."""
        guild = interaction.guild
        if guild is None or not member_has(interaction, Permissions.MANAGE_CHANNELS):
            await interaction.respond("You need the Manage Channels permission for that.", ephemeral=True)
            return
        with Session(self.bind) as session:
            stats = guild_stat_channels(session, int(guild.id))
        if not stats:
            await interaction.respond(f"This server has no stats channels; {self.mention(self.add)} adds them.", ephemeral=True)
            return
        await interaction.defer(ephemeral=True)
        await self.remove_channels(self.bot.client, stats, reason=self._reason(interaction, self.remove))
        await interaction.followup("Removed the stats channels.", ephemeral=True)

    @Cog.command(name="reset", description="Recreate the stats channels of every server (bot owners only)")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def reset(self, interaction: CommandInteraction) -> None:
        """Delete and recreate every guild's stats channels; only the bot's owners may."""
        user = interaction.user
        if user is None or not await is_owner(self.bot.client, user.id):
            await interaction.respond("Only the bot's owners can do that.", ephemeral=True)
            return
        await interaction.defer(ephemeral=True)
        reason = self._reason(interaction, self.reset)
        with Session(self.bind) as session:
            by_guild = {guild_id: guild_stat_channels(session, guild_id) for guild_id in stats_guild_ids(session)}
        failed = []
        for guild_id, stats in by_guild.items():
            await self.remove_channels(self.bot.client, stats, reason=reason)
            if await self.create_channels(self.bot.client, guild_id, reason=reason) is not None:
                failed.append(guild_id)
        self.logger.info(t"Reset the stats channels of {len(by_guild)} guilds, failing for {failed}")
        message = f"Reset the stats channels of {len(by_guild)} servers."
        await interaction.followup(
            message if not failed else f"{message} Failed for: {', '.join(map(str, failed))}",
            ephemeral=True,
        )

    @classmethod
    def _reason(cls, interaction: CommandInteraction, command: Command) -> str:
        """Return the audit-log reason for using ``command``, naming who asked for it."""
        user = interaction.user
        who = "someone" if user is None else f"{user.username} ({user.id})"
        return f"Requested by {who} using /{cls.path_of(command)}"
