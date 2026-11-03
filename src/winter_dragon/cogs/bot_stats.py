"""The /botstats command: what the bot serves right now, for its owners."""

lazy from typing import TYPE_CHECKING

lazy from wd_bot.checks import is_owner
lazy from wd_bot.cogs import Cog
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.timestamp import DiscordTime
lazy from wd_errors import Refused

lazy from winter_dragon.bot_stats import BotStats


if TYPE_CHECKING:
    lazy from wd_discord import CommandInteraction

    lazy from winter_dragon.bot_stats import ShardStats


MAX_SHARD_LINES = 25
"""Shards listed one per line in the embed; past this, only the dead ones are."""


def shard_line(shard: ShardStats) -> str:
    """Return one shard as ``#0 up, 42 ms``."""
    state = "up" if shard.alive else "down"
    latency = "no heartbeat yet" if shard.latency is None else f"{shard.latency * 1000:.0f} ms"
    return f"#{shard.id} {state}, {latency}"


def shards_value(stats: BotStats) -> str:
    """Return the embed's shard field: each shard, or only the dead ones when there are too many to list."""
    if not stats.shards:
        return "Not connected"
    shown = stats.shards if len(stats.shards) <= MAX_SHARD_LINES else [s for s in stats.shards if not s.alive]
    summary = f"{stats.shards_alive}/{len(stats.shards)} up"
    return "\n".join([summary, *map(shard_line, shown[:MAX_SHARD_LINES])])


def stats_embed(stats: BotStats) -> Embed:
    """Return ``stats`` as the /botstats reply."""
    guilds = f"{stats.guilds}" + (f" ({stats.unavailable_guilds} unavailable)" if stats.unavailable_guilds else "")
    fields = [
        EmbedField(name="Guilds", value=guilds, inline=True),
        EmbedField(name="Channels", value=f"{stats.channels} (+{stats.threads} threads)", inline=True),
        EmbedField(name="Members (approx.)", value=str(stats.members), inline=True),
        EmbedField(name="Unique cached users", value=str(stats.cached_users), inline=True),
        EmbedField(name="Online since", value=DiscordTime(stats.launch_time).with_relative(), inline=True),
        EmbedField(name="Version", value=stats.version, inline=True),
        EmbedField(name="Shards", value=shards_value(stats), inline=False),
    ]
    return Embed(title="Bot stats", fields=fields)


class BotStatsCommand(Cog):
    """Shows the bot's owners what it serves: guilds, channels, members, shards and uptime."""

    @Cog.command(name="botstats", description="Show what the bot serves right now (bot owners only)")
    async def botstats(self, interaction: CommandInteraction) -> None:
        """Reply, privately, with a :class:`BotStats` snapshot; only the bot's owners may."""
        user = interaction.user
        if user is None or not await is_owner(self.bot.client, user.id):
            msg = "Only the bot's owners can do that."
            raise Refused(msg)
        await interaction.respond(embeds=[stats_embed(BotStats.of(self.bot))], ephemeral=True)
