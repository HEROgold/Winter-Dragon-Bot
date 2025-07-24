"""Module to help users create a new guild."""

import random
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
from winter_dragon.bot.config import Config
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.extensions.server.log_channels import LogChannels
from winter_dragon.bot.extensions.server.stats import Stats
from winter_dragon.bot.extensions.server.welcome import Welcome


class GuildCreator(GroupCog):
    """Cog for creating a new guild."""

    INIT_NAME = "Initializing guild"
    WEEK = 604_800
    guild_check_interval = Config(3600, int)

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Listen for when a member joins the guild."""
        if member.id != self.bot.user.id and member.guild.owner == self.bot.user:
            await member.guild.edit(owner=member, reason="Transferring ownership to first joined member.")

    async def cog_load(self) -> None:
        """Load the cog."""
        await super().cog_load()
        # Configure loop interval from config
        self._check_guilds.change_interval(seconds=self.guild_check_interval)
        self._check_guilds.start()

    @loop()
    async def _check_guilds(self) -> None:
        """Check if the bot is the owner of any guilds."""
        for guild in self.bot.guilds:
            if guild.owner == self.bot.user or guild.name.startswith(self.INIT_NAME):
                self.logger.warning(f"Guild {guild.name} ({guild.id}) is initializing, and not yet claimed!")
                owners = list(self.bot.owner_ids) if self.bot.owner_ids is not None else [self.bot.owner_id]
                new_owner_id = random.choice(owners)  # noqa: S311
                if not new_owner_id:
                    self.logger.warning("No owner IDs found.")
                    continue
                new_owner = self.bot.get_user(new_owner_id)
                if not new_owner:
                    self.logger.warning(f"Owner ID {new_owner_id} not found.")
                    continue
                invite = await guild.channels[0].create_invite(reason="Transferring ownership to a bot owner.")
                await new_owner.dm_channel.send(f"Transferring ownership of guild to you. {invite.url}")

    @app_commands.checks.cooldown(1, WEEK)
    @app_commands.command(name="create", description="Creates a new guild, and makes you the owner.")
    async def slash_create(  # noqa: PLR0913
        self,
        interaction: discord.Interaction,
        name: str,
        invite_code: str | None = None,
        *,
        discoverable: bool = True,
        disable_invites: bool = True,
        disable_widget: bool = True,
    ) -> None:
        """Create a new guild for the user, then invite the user."""
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = await self.bot.create_guild(name=self.INIT_NAME)
        invite = await guild.channels[0].create_invite()
        await interaction.followup.send(invite.url)
        rules_channel = await guild.create_text_channel(
            "rules",
            position=0,
            topic="Rules channel",
            overwrites={guild.default_role: PermissionOverwrite(view_channel=True)},
        )
        afk_channel = await guild.create_voice_channel(
            "AFK",
            position=0,
            overwrites={guild.default_role: PermissionOverwrite(connect=False, view_channel=False)},
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
        if invite_code:
            await guild.edit(vanity_code=invite_code)
        if not disable_widget:
            await guild.edit(
                widget_enabled=True,
                widget_channel=await guild.create_text_channel("widget", position=0, topic="Widget channel"),
            )
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
        await guild.edit(
            reason="Initializing guild",
            name=name,
            description=guild.description,
            community=True,
            rules_channel=rules_channel,
            public_updates_channel=guild.public_updates_channel,
            afk_channel=afk_channel,
            #/icon=guild.icon,
            #/banner=guild.banner,
            #/splash=guild.splash,
            #/discovery_splash=guild.discovery_splash,
            owner=interaction.user,
            afk_timeout=600,
            default_notifications=NotificationLevel.only_mentions,
            verification_level=VerificationLevel.highest,
            explicit_content_filter=ContentFilter.all_members,
            #/vanity_code=None,
            system_channel=system_channel,
            system_channel_flags=SystemChannelFlags(join_notifications=True, premium_subscriptions=True),
            preferred_locale=Locale.british_english,
            premium_progress_bar_enabled=True,
            discoverable=discoverable,
            invites_disabled=disable_invites,
            widget_enabled=False,
            # /widget_channel=None,
            mfa_level=MFALevel.require_2fa,
            raid_alerts_disabled=False,
            safety_alerts_channel=safety_alerts_channel,
            invites_disabled_until=datetime.now(tz=UTC) + timedelta(days=1),
            dms_disabled_until=datetime.now(tz=UTC) + timedelta(days=1),
        )


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(GuildCreator(bot=bot))
