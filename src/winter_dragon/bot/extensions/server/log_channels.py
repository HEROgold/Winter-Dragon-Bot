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

from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.config import Config
from winter_dragon.bot.core.permissions import PermissionsOverwrites
from winter_dragon.bot.core.settings import Settings
from winter_dragon.database.channel_types import Tags
from winter_dragon.database.tables import Channels


MAX_CATEGORY_SIZE = 50


class LogChannels(GroupCog, auto_load=True):
    """Manage log channel/category provisioning and synchronization.

    All runtime event logging is handled by modules in ``winter_dragon.bot.events``.
    """

    log_category_name = Config("LOG-CATEGORY")

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
                guild_id=channel.guild.id,
            )
            Channels.update(log_channel)
            log_channel.link_tag(self.session, Tags.LOGS)
            yield channel, log_channel

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
            guild.me: discord.PermissionOverwrite.from_pair(
                discord.Permissions(
                    view_channel=True,
                    manage_channels=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    manage_messages=True,
                ),
                discord.Permissions.none(),
            ),
        }

        category_channels: list[CategoryChannel] = await self.create_categories(guild, bot_user, overwrites)
        await self.create_log_channels(category_channels)

        category_mention = " ".join(i.mention for i in category_channels)
        await interaction.followup.send(
            f"Set up Log category and channels under {category_mention}",
        )
        self.logger.info(f"Setup Log for {interaction.guild}")

    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.command(
        name="set",
        description="Set an existing text channel to handle a specific log type.",
    )
    async def slash_log_set(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        log_type: str,
    ) -> None:
        """Bind a Discord text channel to a given audit log action."""
        guild = interaction.guild
        if guild is None:
            msg = "Guild is None"
            raise TypeError(msg)

        if channel.guild.id != guild.id:
            await interaction.response.send_message("Select a channel from this guild.", ephemeral=True)
            return

        normalized = log_type.lower()
        try:
            audit_action = AuditLogAction[normalized]
        except KeyError:
            available = ", ".join(action.name.title() for action in AuditLogAction)
            await interaction.response.send_message(
                f"Unknown log type. Available types: {available}",
                ephemeral=True,
            )
            return

        audit_name = audit_action.name.title()
        db_channel = Channels(
            id=channel.id,
            name=audit_name,
            guild_id=guild.id,
        )
        Channels.update(db_channel)
        db_channel.link_tag(self.session, Tags.LOGS)
        await interaction.response.send_message(
            f"Linked {channel.mention} to `{audit_name}` events.",
            ephemeral=True,
        )

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
            db_category = Channels(
                id=category_channel.id,
                name=self.log_category_name,
                guild_id=category_channel.guild.id,
            )
            Channels.update(db_category)
            db_category.link_tag(self.session, Tags.LOGS)
        return category_channels

    async def create_log_channels(self, category_channels: list[CategoryChannel]) -> None:
        """Create log channels in the logging categories."""
        category_types: list[str] = ["global"] + [i.name for i in AuditLogAction]
        for i, audit_action in enumerate(category_types):
            log_category_name = audit_action.title()
            category_channel = self.get_log_category(category_channels, i)

            text_channel = await category_channel.create_text_channel(
                name=f"{log_category_name.lower()}",
                reason="Adding Log channels",
            )
            db_channel = Channels(
                id=text_channel.id,
                name=log_category_name,
                guild_id=text_channel.guild.id,
            )
            Channels.update(db_channel)
            # Tag global channel with both LOGS and GLOBAL
            if i == 0:  # First channel is global
                db_channel.link_tag(self.session, Tags.LOGS)
                db_channel.link_tag(self.session, Tags.AGGREGATE)
            else:
                db_channel.link_tag(self.session, Tags.LOGS)

    def get_db_log_channels(self, guild: Guild) -> Sequence[Channels]:
        """Get all log channels from the database."""
        return Channels.get_by_tag(self.session, Tags.LOGS, guild.id)

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
        channels = Channels.get_by_tag(self.session, Tags.LOGS, guild.id)
        if not channels:
            c_mention = self.get_command_mention(self.slash_log_add)
            await interaction.followup.send(f"Can't find LogChannels. Try using {c_mention}")
            return

        # Defer to avoid timeout
        await interaction.response.defer(ephemeral=True)
        channels.sort(key=lambda channel: isinstance(discord.utils.get(guild.channels, id=channel.id), CategoryChannel))

        for channel in channels:
            if channel.id is None:
                self.logger.warning("Channel's ID is None, %s", channel)
                continue
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
            all_log_channels = Channels.get_by_tag(self.session, Tags.LOGS)
            guild_id = all_log_channels[0].guild_id if all_log_channels else None
            if guild_id:
                return await self.update_log(guild=discord.utils.get(self.bot.guilds, id=guild_id))
            return None

        channels = Channels.get_by_tag(self.session, Tags.LOGS, guild.id)
        div, mod = divmod(len(AuditLogAction), MAX_CATEGORY_SIZE)
        required_category_count = div + (1 if mod > 0 else 0)
        category_channels = await self.update_required_category_count(guild, required_category_count)
        await self.ensure_aggregate_channel_first(guild, category_channels)
        channels = Channels.get_by_tag(self.session, Tags.LOGS, guild.id)

        known_names = [channel.name.lower() for channel in channels]

        # Add 'global' to known names since we ensured it exists
        if "global" not in known_names:
            known_names.append("global")

        difference: list[str] = []
        difference.extend(j for j in [i.name.lower() for i in AuditLogAction] if j not in known_names)
        self.logger.debug(f"{channels=}, {known_names=}, {difference=}")

        for i, channel_name in enumerate(difference):
            category_channel = self.get_log_category(category_channels, i)

            new_log_channel = await category_channel.create_text_channel(channel_name, reason="Log update")
            self.logger.info(f"Updated Log for {guild=} with {new_log_channel=}")
            channel_record = Channels(
                id=new_log_channel.id,
                name=channel_name,
                guild_id=category_channel.guild.id,
            )
            Channels.update(channel_record)
            channel_record.link_tag(self.session, Tags.LOGS)
        self.session.commit()
        return None

    async def ensure_aggregate_channel_first(
        self,
        guild: discord.Guild,
        category_channels: list[CategoryChannel],
    ) -> None:
        """Ensure the aggregate logging channel is at the top of the first category."""
        if not category_channels:
            return

        first_category = category_channels[0]
        global_channels = Channels.get_by_tags(
            self.session,
            [Tags.AGGREGATE, Tags.LOGS],
            guild.id,
            match_all=True,
        )
        db_channel = global_channels[0] if global_channels else None

        if db_channel:
            global_channel = discord.utils.get(guild.text_channels, id=db_channel.id)

            if global_channel and global_channel.category_id == first_category.id:
                if global_channel != first_category.channels[0]:
                    self.logger.info(f"Moving global channel to top of {first_category.name}")
                    await global_channel.edit(position=0, reason="Ensuring global channel is first")
            elif global_channel and global_channel.category_id != first_category.id:
                self.logger.info(f"Moving global channel to first category {first_category.name}")
                if len(first_category.channels) >= MAX_CATEGORY_SIZE:
                    last_channel = max(
                        (ch for ch in first_category.text_channels),
                        key=lambda ch: ch.position,
                    )
                    if len(category_channels) > 1:
                        second_category = category_channels[1]
                        self.logger.info(f"Moving {last_channel.name} to second category to make room")
                        await last_channel.edit(category=second_category, position=0, reason="Making room for global channel")
                await global_channel.edit(category=first_category, position=0, reason="Moving global to first position")
        else:
            self.logger.info("Creating missing global channel at top of first category")

            # If first category is full, move last channel to second category
            if len(first_category.channels) >= MAX_CATEGORY_SIZE and len(category_channels) > 1:
                last_channel = max(
                    (ch for ch in first_category.text_channels),
                    key=lambda ch: ch.position,
                )
                second_category = category_channels[1]
                self.logger.info(f"Moving {last_channel.name} to second category to make room")
                await last_channel.edit(category=second_category, position=0, reason="Making room for global channel")

            global_channel = await first_category.create_text_channel(
                name="global",
                position=0,
                reason="Creating global log channel",
            )
            channel_record = Channels(
                id=global_channel.id,
                name="Global",
                guild_id=guild.id,
            )
            Channels.update(channel_record)
            channel_record.link_tag(self.session, Tags.LOGS)
            channel_record.link_tag(self.session, Tags.AGGREGATE)
            self.session.commit()

    async def update_required_category_count(self, guild: discord.Guild, required_category_count: int) -> list[CategoryChannel]:
        """Update the required category count for the guild."""
        all_log_channels = Channels.get_by_tag(self.session, Tags.LOGS, guild.id)
        categories = [c for c in all_log_channels if c.name == self.log_category_name]
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
                            discord.Permissions(
                                view_channel=True,
                                manage_channels=True,
                                send_messages=True,
                                embed_links=True,
                                attach_files=True,
                                read_message_history=True,
                                manage_messages=True,
                            ),
                            discord.Permissions.none(),
                        ),
                    },
                    position=99,
                    reason="Adding Log channels",
                )
                category_channels.append(category_channel)
                db_category = Channels(
                    id=category_channel.id,
                    name=self.log_category_name,
                    guild_id=category_channel.guild.id,
                )
                Channels.update(db_category)
                db_category.link_tag(self.session, Tags.LOGS)
        self.session.commit()

        return cast("list[CategoryChannel]", category_channels)

    @slash_log_set.autocomplete("log_type")
    async def log_type_autocomplete(
        self,
        interaction: discord.Interaction,  # noqa: ARG002
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete available audit log types for the set command."""
        term = current.lower()
        actions: list[str] = ["global"] + [action.name for action in AuditLogAction]
        choices = [
            app_commands.Choice(name=action.replace("_", " ").title(), value=action)
            for action in actions
            if not term or term in action.lower() or term in action.replace("_", " ").lower()
        ]
        return choices[:25] or [
            app_commands.Choice(name=action.replace("_", " ").title(), value=action) for action in actions[:25]
        ]


# ------------
# Commands End
# ------------
