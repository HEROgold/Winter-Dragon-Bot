"""Cog focused solely on provisioning and maintaining log channels.

Historical context:
        This file previously contained many event listeners (member join/leave/update,
        message edit/delete, audit log entry processing, generic diff helpers, etc.).
        Those responsibilities have been migrated to the dedicated modular event
        system under ``winter_dragon.bot.events``.  The event handlers now create
        embeds and dispatch them through the central Audit / Message event handler
        classes which route messages to the appropriate log channels.

Current scope:
        Only retain functionality necessary for:
            * Detecting previously created log categories/channels and syncing them
                to the database (``/detect``)
            * Creating all required category + text channels (``/add``)
            * Removing all log channels (``/remove``)
            * Updating / backfilling missing channels (``/update``)
            * Internal helpers for category selection and ensuring required counts.

If you need to modify how events are transformed into embeds or how they are
sent, look in ``winter_dragon.bot.events`` instead of re-adding listeners here.
"""

from collections.abc import AsyncGenerator, Sequence
from typing import cast

import discord
from discord import (
    AuditLogAction,
    CategoryChannel,
    ClientUser,
    Guild,
    TextChannel,
    app_commands,
)
from discord.abc import PrivateChannel
from discord.ext import commands
from sqlmodel import select

from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.config import Config
from winter_dragon.bot.core.permissions import PermissionsOverwrites
from winter_dragon.bot.core.settings import Settings
from winter_dragon.database.channel_types import ChannelTypes
from winter_dragon.database.tables import Channels


LOGS = ChannelTypes.LOGS
MAX_CATEGORY_SIZE = 50


class LogChannels(GroupCog, auto_load=True):
    """Manage log channel/category provisioning and synchronization.

    All runtime event logging is handled by modules in ``winter_dragon.bot.events``.
    """

    log_channel_name = Config("LOG-CATEGORY")

    # ----------------------
    # Helper Functions Start
    # ----------------------

    def get_log_category(self, category_channels: list[CategoryChannel], current_count: int) -> CategoryChannel:
        """Get the log category for the current count of log channels."""
        channel_locator = current_count // MAX_CATEGORY_SIZE
        category_channel = category_channels[channel_locator]
        self.logger.debug(f"{category_channels=}, {channel_locator=}")

        if channel_locator + len(category_channel.channels) > MAX_CATEGORY_SIZE:
            channel_location = len(category_channel.channels) + channel_locator
            return self.get_log_category(category_channels, channel_location)
        return category_channel

    # NOTE: All previous embed construction & log dispatch helpers removed.
    # Event dispatch now happens in winter_dragon.bot.events.* modules.

    # ----------------------
    # Helper Functions End
    # ----------------------

    # Removed legacy @Cog.listener() methods; see winter_dragon.bot.events.*

    # ---------------
    # Commands Start
    # ---------------

    @app_commands.command(name="detect", description="Finds already existing log channels from this bot in the guild.")
    async def slash_detect(self, interaction: discord.Interaction) -> None:
        """Detect existing log channels in the guild."""
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            f"Found log channels:\n{''.join([channel[0].mention async for channel in self.detect_channels(interaction)])}",
        )

    async def detect_channels(self, interaction: discord.Interaction) -> AsyncGenerator[tuple[TextChannel, Channels]]:
        """Detect existing log channels in the guild, and updates them in the database, then yields them."""
        guild = interaction.guild
        bot_user = self.bot.user
        if guild is None:
            msg = "Guild is None"
            raise TypeError(msg)
        if bot_user is None:
            msg = "Bot user is None"
            raise TypeError(msg)
        categories = guild.categories
        logging_categories = [category for category in categories if f"{bot_user.display_name} Log " in category.name]
        logging_channels = [channel for category in logging_categories for channel in category.text_channels]
        # Update the database with the found channels
        for channel in logging_channels:
            log_channel = Channels(
                id=channel.id,
                name=channel.name,
                type=LOGS,
                guild_id=channel.guild.id,
            )
            Channels.update(log_channel)
            yield channel, log_channel

    # TODO(Herogold, #5): This requires the bot to have Administrator.  # noqa: FIX002
    # Failing case: Command user is guild owner, and has administrator due to a role
    # The bot does have manage_channels, but not administrator permissions
    # This will cause the command to fail, raising 403 forbidden.
    # When the bot is given administrator, it works.
    #
    # NOTE: Permission nuance — some guild owners report HTTP 403 when the bot lacks
    # Administrator but has Manage Channels. If reproducible, adjust the decorator
    # checks to reflect the minimal required scope.
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.cooldown(1, 100)
    @app_commands.command(
        name="add",
        description="Enables automatic moderation/logging for this guild, and creates a channel for all logs.",
    )
    async def slash_log_add(self, interaction: discord.Interaction) -> None:
        """Create log channels for the guild. Creates category channels, to insert the channels into."""
        guild = interaction.guild
        bot_user = self.bot.user
        if guild is None:
            msg = "Guild is None"
            raise TypeError(msg)
        if bot_user is None:
            msg = "Bot user is None"
            raise TypeError(msg)
        channels = self.get_db_log_channels(guild) or [channel[1] async for channel in self.detect_channels(interaction)]
        if len(channels) > 0:
            await interaction.response.send_message("Log channels are already set up.")
            return

        await interaction.response.defer(ephemeral=True)

        overwrites: PermissionsOverwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none()),
        }

        category_channels = await self.create_categories(guild, bot_user, overwrites)
        await self.create_log_channels(category_channels)

        category_mention = ", ".join(i.mention for i in category_channels)
        await interaction.followup.send(
            f"Set up Log category and channels under {category_mention}",
        )
        self.logger.info(f"Setup Log for {interaction.guild}")

    async def create_categories(
        self,
        guild: Guild,
        bot_user: ClientUser,
        overwrites: PermissionsOverwrites,
    ) -> list[CategoryChannel]:
        """Create log categories and channels."""
        category_channels: list[CategoryChannel] = []
        div, mod = divmod(len(AuditLogAction), MAX_CATEGORY_SIZE)
        category_count = div + (1 if mod > 0 else 0)

        for i in range(category_count):
            category_channel = await guild.create_category(
                name=f"{bot_user.display_name} Log {i + 1}",
                overwrites=overwrites,
                position=99,
                reason="Adding Log channels",
            )
            category_channels.append(category_channel)
            Channels.update(
                Channels(
                    id=category_channel.id,
                    name=self.log_channel_name,
                    type=LOGS,
                    guild_id=category_channel.guild.id,
                ),
            )
        return category_channels

    async def create_log_channels(self, category_channels: list[CategoryChannel]) -> None:
        """Create log channels in the logging categories."""
        for i, audit_action in enumerate(AuditLogAction):
            log_category_name = audit_action.name.title()
            category_channel = self.get_log_category(category_channels, i)

            text_channel = await category_channel.create_text_channel(
                name=f"{log_category_name.lower()}",
                reason="Adding Log channels",
            )
            Channels.update(
                Channels(
                    id=text_channel.id,
                    name=log_category_name,
                    type=LOGS,
                    guild_id=text_channel.guild.id,
                ),
            )

    def get_db_log_channels(self, guild: Guild) -> Sequence[Channels]:
        """Get all log channels from the database."""
        return self.session.exec(
            select(Channels).where(
                Channels.type == LOGS,
                Channels.guild_id == guild.id,
            ),
        ).all()

    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.cooldown(1, 100)
    @app_commands.command(
        name="remove",
        description="Disables automatic moderation for this guild, and removes the log channels.",
    )
    async def slash_log_remove(self, interaction: discord.Interaction) -> None:
        """Remove all log channels for this guild."""
        guild = interaction.guild
        if guild is None:
            msg = "Guild is None"
            raise TypeError(msg)
        result = self.session.exec(
            select(Channels).where(
                Channels.type == LOGS,
                Channels.guild_id == guild.id,
            ),
        )
        channels = list(result.all())
        if not channels:
            c_mention = await self.get_command_mention(self.slash_log_add)
            await interaction.followup.send(f"Can't find LogChannels. Try using {c_mention}")
            return

        # Defer to avoid timeout
        await interaction.response.defer(ephemeral=True)
        channels.sort(key=lambda channel: isinstance(discord.utils.get(guild.channels, id=channel.id), CategoryChannel))

        for channel in channels:
            dc_channel = self.bot.get_channel(channel.id) or discord.utils.get(guild.channels, id=channel.id)
            if dc_channel is None or isinstance(dc_channel, PrivateChannel):
                msg = "Channel is None"
                raise TypeError(msg)
            await dc_channel.delete()
            self.session.delete(channel)
        self.session.commit()

        await interaction.followup.send("Removed LogChannels")
        self.logger.info(f"Removed Log for {interaction.guild}")

    @app_commands.guilds(Settings.support_guild_id)
    @commands.is_owner()
    @app_commands.command(name="update", description="Update Log channels")
    async def slash_log_update(self, interaction: discord.Interaction, guild_id: int | None = None) -> None:
        """Update all log channels for the guild."""
        # defer here to avoid timeout
        await interaction.response.defer(ephemeral=True)

        guild = discord.utils.get(self.bot.guilds, id=guild_id) if guild_id else None
        await self.update_log(guild=guild)
        await interaction.followup.send("Updated Log channels on all servers!")

    async def update_log(self, guild: discord.Guild | None = None) -> None:
        """Update log channels for a guild."""
        self.logger.debug(f"Updating Log for {guild=}")
        if guild is None:
            guild_id = self.session.exec(
                select(Channels.guild_id).where(Channels.type == LOGS),
            ).first()
            return await self.update_log(guild=discord.utils.get(self.bot.guilds, id=guild_id))

        channels = self.session.exec(
            select(Channels).where(
                Channels.type == LOGS,
                Channels.guild_id == guild.id,
            ),
        ).all()

        div, mod = divmod(len(AuditLogAction), MAX_CATEGORY_SIZE)
        required_category_count = div + (1 if mod > 0 else 0)

        category_channels = await self.update_required_category_count(guild, required_category_count)

        difference: list[str] = []
        known_names = [channel.name.lower() for channel in channels]

        difference.extend(j for j in [i.name.lower() for i in AuditLogAction] if j not in known_names)
        self.logger.debug(f"{channels=}, {known_names=}, {difference=}")

        for i, channel_name in enumerate(difference):
            category_channel = self.get_log_category(category_channels, i)

            new_log_channel = await category_channel.create_text_channel(channel_name, reason="Log update")
            self.logger.info(f"Updated Log for {guild=} with {new_log_channel=}")
            Channels.update(
                Channels(
                    id=new_log_channel.id,
                    name=channel_name,
                    type=LOGS,
                    guild_id=category_channel.guild.id,
                ),
            )
        self.session.commit()
        return None

    async def update_required_category_count(self, guild: discord.Guild, required_category_count: int) -> list[CategoryChannel]:
        """Update the required category count for the guild."""
        categories = self.session.exec(
            select(Channels).where(
                Channels.name == self.log_channel_name,
                Channels.type == LOGS,
                Channels.guild_id == guild.id,
            ),
        ).all()
        category_channels = [discord.utils.get(guild.categories, id=category.id) for category in categories]
        current_category_count = len(category_channels) or len(categories)

        if current_category_count < required_category_count:
            for i in range(current_category_count, required_category_count):
                bot_user = self.bot.user
                if bot_user is None:
                    msg = "Bot user is None"
                    raise TypeError(msg)
                category_channel = await guild.create_category(
                    name=f"{bot_user.display_name} Log {i + 1}",
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        guild.me: discord.PermissionOverwrite.from_pair(
                            discord.Permissions.all(),
                            discord.Permissions.none(),
                        ),
                    },
                    position=99,
                    reason="Adding Log channels",
                )
                category_channels.append(category_channel)
                Channels.update(
                    Channels(
                        id=category_channel.id,
                        name=self.log_channel_name,
                        type=LOGS,
                        guild_id=category_channel.guild.id,
                    ),
                )
        self.session.commit()

        return cast("list[CategoryChannel]", category_channels)


# ------------
# Commands End
# ------------
