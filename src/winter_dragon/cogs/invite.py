"""The /invite command group: invite the bot to a guild, or join the support guild."""

lazy from typing import TYPE_CHECKING

lazy from wd_bot.bot import invite_url
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_discord import is_network_error
lazy from wd_discord.permissions import ChannelType
lazy from wd_errors import Refused

lazy from winter_dragon.config import CogConfig, Settings


if TYPE_CHECKING:
    lazy from wd_discord import Client, CommandInteraction, NetworkError
    lazy from wd_discord.entities.channel import BaseChannel


class InviteSettings:
    """Settings for /invite, in its ``cogs.ini`` section."""

    support_invite_max_age = CogConfig(60)
    """Seconds a support guild invite stays valid: it's single-use and meant to be clicked right away."""


NO_SUPPORT_INVITE = "I couldn't create an invite to the support guild."
"""The refusal when the support guild has no channel to invite to, or Discord wouldn't make the invite."""


async def invite_channel(client: Client, guild_id: int) -> BaseChannel | NetworkError | None:
    """Return the channel to invite people to in the guild ``guild_id``: its system channel, else its first text channel.

    ``None`` when the guild has neither.
    """
    guild = await client.guilds.fetch(guild_id)
    if is_network_error(guild):
        return guild
    if guild.system_channel is not None:
        return guild.system_channel
    channels = await guild.fetch_channels()
    if is_network_error(channels):
        return channels
    return next((channel for channel in channels if channel.type == ChannelType.GUILD_TEXT), None)


class Invite(GroupCog, name="invite", description="Invite the bot to your guild, or join its support guild"):
    """Cog for inviting the bot to a guild or getting support."""

    @Cog.command(name="bot", description="Invite this bot to your own guild!")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def bot_invite(self, interaction: CommandInteraction) -> None:
        """Reply with the link that adds the bot to a guild."""
        await interaction.respond(invite_url(), ephemeral=True)

    @Cog.command(name="guild", description="Get invited to the official support guild")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def support_invite(self, interaction: CommandInteraction) -> None:
        """Reply with a single-use, short-lived invite to the support guild."""
        if not Settings.support_guild_id:
            msg = "There is no support guild set up."
            raise Refused(msg)
        channel = await invite_channel(self.bot.client, Settings.support_guild_id)
        if channel is None or is_network_error(channel):
            self.logger.warning(t"No channel to invite to in support guild {Settings.support_guild_id}: {channel}")
            raise Refused(NO_SUPPORT_INVITE)
        invite = await channel.create_invite(max_age=InviteSettings.support_invite_max_age)
        if is_network_error(invite):
            self.logger.warning(t"Could not invite to support guild {Settings.support_guild_id}: {invite}")
            raise Refused(NO_SUPPORT_INVITE, cause=invite)
        await interaction.respond(invite.url, ephemeral=True)
