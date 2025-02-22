from datetime import UTC, datetime, timedelta
from textwrap import dedent

import discord
from discord import (
    ContentFilter,
    Locale,
    MFALevel,
    NotificationLevel,
    PermissionOverwrite,
    SystemChannelFlags,
    VerificationLevel,
    app_commands,
)

from core.bot import WinterDragon
from core.cogs import GroupCog
from extensions.server.log_channels import LogChannels
from extensions.server.stats import Stats
from extensions.server.welcome import Welcome


class Guild(GroupCog):
    WEEK = 604_800


    @app_commands.checks.cooldown(1, WEEK)
    @app_commands.command(name="create", description="Creates a new guild, and makes you the owner.")
    async def slash_create(  # noqa: PLR0913
        self,
        interaction: discord.Interaction,
        name: str,
        invite_code: str | None = None,
        discoverable: bool = True,
        disable_invites: bool = True,
        disable_widget: bool = True,
    ) -> None:
        """Initialize."""
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = await self.bot.create_guild(name="Initializing guild")
        rules_channel = await guild.create_text_channel(
            "rules",
            position=0,
            topic="Rules channel",
            overwrites={guild.default_role: PermissionOverwrite(view_channel=True)},
        )
        afk_channel = await guild.create_voice_channel(
            "AFK",
            position=0,
            overwrites={guild.default_role: PermissionOverwrite(connect=False, view=False)},
        )
        system_channel = await guild.create_text_channel(
            "system",
            position=0,
            topic="System channel",
            overwrites={guild.default_role: PermissionOverwrite(view_channel=True)},
        )
        safety_alerts_channel = await guild.create_text_channel(
            "safety-alerts",
            position=0,
            topic="Safety alerts channel",
        )
        await guild.edit(
            reason="Initializing guild",
            name=name,
            description=guild.description,
            community=True,
            rules_channel=rules_channel,
            public_updates_channel=guild.public_updates_channel,
            afk_channel=afk_channel,
            # icon=guild.icon,
            # banner=guild.banner,
            # splash=guild.splash,
            # discovery_splash=guild.discovery_splash,
            owner=interaction.user,
            afk_timeout=600,
            default_notifications=NotificationLevel.only_mentions,
            verification_level=VerificationLevel.highest,
            explicit_content_filter=ContentFilter.no_role,
            # vanity_code=None,
            system_channel=system_channel,
            system_channel_flags=SystemChannelFlags(join_notifications=True, premium_subscriptions=True),
            preferred_locale=Locale.british_english,
            premium_progress_bar_enabled=True,
            discoverable=discoverable,
            invites_disabled=disable_invites,
            widget_enabled=False,
            # widget_channel=None,
            mfa_level=MFALevel.require_2fa,
            raid_alerts_disabled=False,
            safety_alerts_channel=safety_alerts_channel,
            invites_disabled_until=datetime.now(tz=UTC) + timedelta(days=1),
            dms_disabled_until=datetime.now(tz=UTC) + timedelta(days=1),
        )
        if invite_code:
            await guild.edit(vanity_code=invite_code)
        if not disable_widget:
            await guild.edit(
                widget_enabled=True,
                widget_channel=await guild.create_text_channel("widget", position=0, topic="Widget channel"),
            )
        await interaction.followup.send("Guild initialized!")
        await system_channel.send(dedent(
            f"""Guild initialized!
            Use {self.get_command_mention(LogChannels.slash_log_add)} to setup logging channels.
            Use {self.get_command_mention(LogChannels.slash_log_remove)} to remove logging channels.
            Use {self.get_command_mention(Stats.slash_stats_category_add)} to add stat channels (i.e. Member count).
            Use {self.get_command_mention(Stats.slash_stats_category_remove)} to remove stat channels
            Use {self.get_command_mention(Welcome.slash_set_msg)} to set a custom welcome message.
            Use {self.get_command_mention(Welcome.slash_enable)} to enable welcome messages.
            Use {self.get_command_mention(Welcome.slash_disable)} to disable welcome messages.""",
        ))


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Guild(bot))
