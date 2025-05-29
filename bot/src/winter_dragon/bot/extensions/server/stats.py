"""Module that contains relevant classes to display stats about the guild."""
import random
from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Generator
from typing import TYPE_CHECKING, NoReturn

import discord
from discord import Guild, VoiceChannel, app_commands
from discord.ext import commands
from sqlmodel import select
from bot.src.winter_dragon.bot._types.kwargs import BotKwarg
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.enums.channels import ChannelTypes
from winter_dragon.bot.errors import NoneTypeError
from winter_dragon.bot.settings import Settings
from winter_dragon.bot.tools import rainbow
from winter_dragon.database.tables import Channels


if TYPE_CHECKING:
    from winter_dragon.bot._types.aliases import PermissionsOverwrites


STATS = ChannelTypes.STATS


def get_peak_count(channel: Channels | discord.abc.GuildChannel) -> int:
    """Get the peak count from the channel name."""
    try:
        return int(channel.name[13:])
    except ValueError:
        return 0


class StatChannel(LoggerMixin, ABC, metaclass=ABCMeta):
    """Base class for all stat channels."""

    update_reason = "Updating Stats channels"

    def __init__(self, channel: VoiceChannel | None) -> None:
        """Initialize the stat channel."""
        self.channel = channel

    @abstractmethod
    async def update(self) -> None:
        """Update the channel name to display the current values."""

class PeakStat(StatChannel):
    """Class for the peak stat channel."""

    @property
    def peak_count(self) -> int:
        """Get the peak count from the channel name."""
        return 0 if self.channel is None else get_peak_count(self.channel)

    @property
    def currently_online(self) -> int:
        """Get the current number of online members."""
        if self.channel is None:
            return 0
        return sum(member.status != discord.Status.offline and not member.bot for member in self.channel.guild.members)

    async def update(self) -> None:
        """Update the peak channel name to display the current peak."""
        if self.channel is None:
            return
        if self.peak_count >= self.currently_online:
            return
        new_name = f"Peak Online: {self.peak_count}"
        if new_name == self.channel.name:
            return
        self.logger.debug(f"Updating peak channel name: {self.channel.name} -> {new_name}")
        await self.channel.edit(name=new_name, reason=self.update_reason)

class GuildStat(StatChannel):
    """Class for the guild creation date channel."""

    async def update(self) -> None:
        """Update the guild channel name to display the creation date."""
        if self.channel is None:
            return
        age = self.channel.guild.created_at.strftime("%Y-%m-%d")
        new_name = f"Created On: {age}"
        if new_name == self.channel.name:
            return
        self.logger.debug(f"Updating guild channel name: {self.channel.name} -> {new_name}")
        await self.channel.edit(name=new_name, reason=self.update_reason)

class BotStat(StatChannel):
    """Class for the bot stat channel."""

    async def update(self) -> None:
        """Update the bot channel name to display the number of bots."""
        if self.channel is None:
            return
        bot_count = sum(member.bot is True for member in self.channel.guild.members)
        new_name = f"Total Bots: {bot_count}"
        if new_name == self.channel.name:
            return
        self.logger.debug(f"Updating bot channel name: {self.channel.name} -> {new_name}")
        await self.channel.edit(name=new_name, reason=self.update_reason)

class UserStat(StatChannel):
    """Class for the user stat channel."""

    @property
    def user_count(self) -> int:
        """Get the number of users in the channel.

        Returns 0 if the channel is None.
        """
        if self.channel is None:
            return 0
        return sum(member.bot is False for member in self.channel.members)

    async def update(self) -> None:
        """Update the user channel name to display the number of users."""
        if self.channel is None:
            return
        new_name = f"Total Users: {self.user_count}"
        if new_name == self.channel.name:
            return
        self.logger.debug(f"Updating user channel name: {self.channel.name} -> {new_name}")
        await self.channel.edit(name=new_name, reason=self.update_reason)

class OnlineStat(StatChannel):
    """Class for the online stat channel."""

    @property
    def online_count(self) -> int:
        """Get the number of online users in the channel.

        Returns 0 if the channel is None.
        """
        if self.channel is None:
            return 0
        return sum(member.status != discord.Status.offline and not member.bot for member in self.channel.members)

    async def update(self) -> None:
        """Update the online channel name to display the number of online users."""
        if self.channel is None:
            return
        new_name = f"Online Users: {self.online_count}"
        if new_name == self.channel.name:
            return
        self.logger.debug(f"Updating online channel name: {self.channel.name} -> {new_name}")
        await self.channel.edit(name=new_name, reason=self.update_reason)



class StatChannels:
    """Container for all stat channels related to one guild."""

    __slots__ = (
        "bot_channel",
        "guild_channel",
        "online_channel",
        "peak_channel",
        "user_channel",
    )

    def __init__(
        self,
        peak_channel: PeakStat | None = None,
        guild_channel: GuildStat | None = None,
        bot_channel: BotStat | None = None,
        user_channel: UserStat | None = None,
        online_channel: OnlineStat | None = None,
    ) -> None:
        """Initialize the stat channels."""
        self.peak_channel = peak_channel
        self.guild_channel = guild_channel
        self.bot_channel = bot_channel
        self.user_channel = user_channel
        self.online_channel = online_channel

    def __iter__(self) -> Generator[StatChannel, None, NoReturn]:
        """Return all stat channels."""
        for channel in self._get_channels():
            if channel:
                yield channel
        raise StopIteration

    def _get_channels(self) -> tuple[StatChannel | None, ...]:
        return (self.peak_channel, self.guild_channel, self.bot_channel, self.user_channel, self.online_channel)



@app_commands.guild_only()
class Stats(GroupCog):
    """Cog that contains all guild stats related commands."""

    def __init__(self, *args: *BotKwarg, **kwargs: *BotKwarg) -> None:
        """Initialize the stats cog."""
        super().__init__(*args, **kwargs)
        self.stat_channels: dict[Guild, StatChannels] = {
            i: StatChannels(*self.get_guild_stats_channels(i))
            for i in self.bot.guilds
        }

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Update the appropriate stats channels when a member update is fired."""
        member = before or after
        self.logger.debug(f"Member update: {member.guild=}, {member=}")
        guild = member.guild
        if peak_online := (
            self.session.exec(
                select(Channels).where(
                    Channels.guild_id == guild.id,
                    Channels.name == "peak_channel",
                ),
            ).first()
        ):
            peak_channel = guild.get_channel(peak_online.id)
            if not isinstance(peak_channel, VoiceChannel):
                msg = f"Expected VoiceChannel during stat channel update, got {type(peak_channel)}"
                self.logger.warning(msg)
                return
            await PeakStat(peak_channel).update()

    async def create_stats_channels(
        self,
        guild: discord.Guild | None,
        reason: str | None = None,
    ) -> None:
        """Create all stats channels for a guild."""
        if guild is None:
            msg = "Expected discord.Guild"
            raise NoneTypeError(msg)

        overwrite: PermissionsOverwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            guild.me: discord.PermissionOverwrite(connect=True),
        }

        category = await guild.create_category(name=STATS.name.capitalize(), overwrites=overwrite, position=0)
        user_channel = await category.create_voice_channel(name="Total Users:", reason=reason)
        online_channel = await category.create_voice_channel(name="Online Users:", reason=reason)
        bot_channel = await category.create_voice_channel(name="Total Bots:", reason=reason)
        guild_channel = await category.create_voice_channel(name="Created On:", reason=reason)
        peak_channel = await category.create_voice_channel(name="Peak Online:", reason=reason)

        channels: dict[str, discord.abc.GuildChannel] = {
            "category_channel": category,
            "user_channel": user_channel,
            "online_channel": online_channel,
            "bot_channel": bot_channel,
            "guild_channel": guild_channel,
            "peak_channel": peak_channel,
        }

        for k, v in channels.items():
            Channels.update(
                Channels(
                    id=v.id,
                    guild_id=guild.id,
                    type=ChannelTypes.STATS,
                    name=k,
                ),
            )
        self.session.commit()
        self.logger.info(f"Created stats channels for: guild='{guild}'")

    async def remove_stats_channels(
        self,
        guild: discord.Guild | None,
        reason: str | None = None,
    ) -> None:
        """Remove all stats channels for a guild."""
        if guild is None:
            msg = "Expected discord.guild"
            raise NoneTypeError(msg)

        channels = self.session.exec(
            select(Channels).where(
                Channels.guild_id == guild.id,
                Channels.type == STATS,
            ),
        ).all()

        self.logger.debug(f"{channels=}")
        self.logger.info(f"Removing stats channels for: guild='{guild}', channels='{channels}'")

        for db_channel in channels:
            self.logger.debug(f"removing {db_channel}")
            try:
                if channel := discord.utils.get(guild.channels, id=db_channel.id):
                    await channel.delete(reason=reason)
            except AttributeError:
                self.logger.exception("")
            finally:
                self.session.delete(db_channel)
        self.session.commit()

    async def cog_load(self) -> None:
        """Load the cog."""
        await super().cog_load()
        self.update.start()

    @loop(seconds=3600)
    async def update(self) -> None:
        """Update all stat channels periodically."""
        # Note: keep for loop with if.
        # because fetching guild won't let the bot get members from guild.
        self.logger.info("Updating all stat channels")
        guilds = self.bot.guilds
        for guild in guilds:
            if not self.session.exec(
                select(Channels).where(
                    Channels.guild_id == guild.id,
                    Channels.type == STATS,
                ),
            ).first():
                continue
            self.logger.info(f"Updating stat channels: guild='{guild}'")
            channels = self.get_guild_stats_channels(guild)
            self.stat_channels[guild] = StatChannels(
                channels[0],
                channels[1],
                channels[2],
                channels[3],
                channels[4],
            )
            for channel in self.stat_channels[guild]:
                await channel.update()
            self.logger.info(f"Updated stat channels: guild='{guild}'")

    def get_guild_stats_channels(
        self,
        guild: discord.Guild,
    ) -> tuple[
        PeakStat | None,
        GuildStat | None,
        BotStat | None,
        UserStat | None,
        OnlineStat | None,
    ]:
        """Get all stat channels for a guild."""
        user_channel = None
        online_channel = None
        bot_channel = None
        peak_channel = None
        guild_channel = None
        channels = self.session.exec(
            select(Channels).where(
                Channels.type == STATS,
                Channels.guild_id == guild.id,
            ),
        ).all()

        for channel in channels:
            self.logger.debug(f"check if stats channel: {channel=}")
            match channel.name:
                case "user_channel":
                    user_channel = UserStat(discord.utils.get(guild.voice_channels, id=channel.id))
                case "online_channel":
                    online_channel = OnlineStat(discord.utils.get(guild.voice_channels, id=channel.id))
                case "bot_channel":
                    bot_channel = BotStat(discord.utils.get(guild.voice_channels, id=channel.id))
                case "peak_channel":
                    peak_channel = PeakStat(discord.utils.get(guild.voice_channels, id=channel.id))
                case "guild_channel":
                    guild_channel = GuildStat(discord.utils.get(guild.voice_channels, id=channel.id))
                case "category_channel" | "stats":
                    continue
                case _:
                    self.logger.debug(f"not a stats channel: {channel}")
                    msg = f"Unexpected channel {channel.name}"
                    raise ValueError(msg)
        self.logger.debug(f"Returning stat channels, {peak_channel, guild_channel, bot_channel, user_channel, online_channel}")
        return peak_channel, guild_channel, bot_channel, user_channel, online_channel


    @app_commands.command(name="show", description="Get some information about the guild!")
    async def slash_stats_show(self, interaction: discord.Interaction) -> None:
        """Show some stats about the guild."""
        guild = interaction.guild
        if guild is None:
            msg = "Expected Guild"
            raise NoneTypeError(msg)
        if guild.afk_channel is None:
            msg = "No afk channel found"
            raise NoneTypeError(msg)

        embed = discord.Embed(
            title=f"{guild.name} Stats",
            description=f"Information about {guild.name}",
            color=random.choice(rainbow.RAINBOW),  # noqa: S311
        )

        embed.add_field(
            name="Users",
            value=sum(member.bot is False for member in guild.members),
            inline=True,
        )

        embed.add_field(
            name="Bots",
            value=sum(member.bot is True for member in guild.members),
            inline=True,
        )

        embed.add_field(
            name="Online",
            value=sum(member.status != discord.Status.offline and not member.bot for member in guild.members),
            inline=True,
        )

        embed.add_field(
            name="Created on",
            value=guild.created_at.strftime("%Y-%m-%d"),
            inline=True,
        )

        try:
            embed.add_field(
                name="Afk channel",
                value=guild.afk_channel.mention,
                inline=True,
            )
        except AttributeError as e:
            self.logger.warning(f"No afk-channel found: {e}")

        self.logger.debug(f"Showing guild stats to {interaction.user}: {interaction.guild=}, {interaction.user=}")
        await interaction.response.send_message(embed=embed)

    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.command(
        name="add",
        description="This command will create the Stats category which will show some stats about the guild.",
    )
    async def slash_stats_category_add(self, interaction: discord.Interaction) -> None:
        """Create stat channels."""
        if interaction.guild is None:
            msg = "Expected Guild"
            raise NoneTypeError(msg)

        if self.session.exec(
            select(Channels).where(
                Channels.guild_id == interaction.guild.id,
                Channels.type == STATS,
            ),
        ).all():
            rem_mention = self.get_command_mention(self.slash_stats_category_remove)
            await interaction.response.send_message(
                f"Stats channels already set up use {rem_mention} to remove them",
                ephemeral=True,
            )
            return

        c_mention = self.get_command_mention(self.slash_stats_category_add)

        await interaction.response.defer(ephemeral=True)
        await self.create_stats_channels(
            guild=interaction.guild,
            reason=f"Requested by {interaction.user.display_name} using {c_mention}",
        )
        await interaction.followup.send("Stats channels are set up")

    @app_commands.command(
        name="remove",
        description="This command removes the stat channels. Including the Category and all channels in there.",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_stats_category_remove(self, interaction: discord.Interaction) -> None:
        """Remove stat channels."""
        if interaction.guild is None:
            msg = "Expected Guild"
            raise NoneTypeError(msg)

        channels = self.session.exec(
            select(Channels).where(
                Channels.guild_id == interaction.guild.id,
                Channels.type == STATS,
            ),
        ).all()
        if not channels:
            add_mention = self.get_command_mention(self.slash_stats_category_add)
            await interaction.response.send_message(
                f"No stats channels found to remove, use {add_mention} to add them",
                ephemeral=True,
            )
            return

        c_mention = self.get_command_mention(self.slash_stats_category_remove)

        await interaction.response.defer(ephemeral=True)
        await self.remove_stats_channels(
            guild=interaction.guild,
            reason=f"Requested by {interaction.user.display_name} using {c_mention}",
        )
        await interaction.followup.send("Removed stats channels")

    @app_commands.command(name="reset", description="Reset stats of all servers")
    @app_commands.guilds(Settings.support_guild_id)
    @commands.is_owner()
    async def reset_stats(self, interaction: discord.Interaction) -> None:
        """Reset all stats on the stat channels."""
        if interaction.guild is None:
            msg = "Expected Guild"
            raise NoneTypeError(msg)

        self.logger.warning(f"Resetting all guild/stats channels > by: {interaction.user}")
        await interaction.response.defer(ephemeral=True)

        channels = self.session.exec(
            select(Channels).where(
                Channels.guild_id == interaction.guild.id,
                Channels.type == STATS,
            ),
        ).all()

        seen = []

        for channel in channels:
            guild_id = channel.guild_id
            if guild_id in seen:
                self.logger.debug(f"already updated {guild_id}")
                continue

            guild = discord.utils.get(self.bot.guilds, id=guild_id)
            seen.append(guild_id)
            await self.remove_stats_channels(guild=guild, reason="Resetting all stats channels")
            await self.create_stats_channels(guild=guild, reason="Resetting all stats channels")
            self.logger.info(f"Reset stats for: {guild}")
        await interaction.followup.send("Reset all guild stat channels")


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Stats(bot))
