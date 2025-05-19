"""Module containing channels to help guild moderators."""
import itertools
from collections.abc import Sequence
from typing import cast

import discord
from discord import CategoryChannel, ClientUser, Guild, app_commands
from discord.abc import PrivateChannel
from discord.ext import commands
from sqlmodel import select
from winter_dragon.bot._types.aliases import PermissionsOverwrites
from winter_dragon.bot.constants import (
    CHANGED_COLOR,
    CREATED_COLOR,
    DELETED_COLOR,
    LOG_CHANNEL_NAME,
    MAX_CATEGORY_SIZE,
    MEMBER_UPDATE_PROPERTIES,
)
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.bot.enums.channels import ChannelTypes, LogCategories
from winter_dragon.bot.errors import NoneTypeError
from winter_dragon.bot.settings import Settings
from winter_dragon.database.tables import Channels


LOGS = ChannelTypes.LOGS

class LogChannels(GroupCog):
    """Cog for managing log channels."""

# ----------------------
# Helper Functions Start
# ----------------------

    def get_log_category(self, category_channels: list[CategoryChannel], current_count: int) -> CategoryChannel:
        """Get the log category for the current count of log channels."""
        channel_locator = current_count // MAX_CATEGORY_SIZE
        category_channel = category_channels[channel_locator]
        self.logger.debug(f"{category_channels=}, {channel_locator=}")

        if channel_locator + len(category_channel.channels) > MAX_CATEGORY_SIZE:
            channel_location = (len(category_channel.channels) + channel_locator)
            return self.get_log_category(category_channels, channel_location)
        return category_channel


    def get_member_role_difference(self, before: discord.Member, after: discord.Member) -> str:
        """Get the difference in roles."""
        role_diff_add = [role.mention for role in after.roles if role not in before.roles]
        role_diff_rem = [role.mention for role in after.roles if role in before.roles]
        return " ".join(role_diff_add + role_diff_rem)


    def get_username_difference(self, before: discord.Member, after: discord.Member) -> str:
        """Get the difference in usernames."""
        return (
            f"from `{before.display_name}` to `{after.display_name}`"
            if after.display_name != before.display_name
            else ""
        )


    async def send_channel_logs(
        self,
        guild: discord.Guild,
        embed: discord.Embed,
        log_category: LogCategories | None=None,
    ) -> tuple[None, None]:
        """Send logs to the all appropriate log channel."""
        if not guild:
            self.logger.debug("No guild during Log channel fetching")
            return None, None

        self.logger.debug(f"Searching for log channels {log_category=} and {LogCategories.GLOBAL=}")

        if log_category is not None:
            await self.send_log_to_category(log_category, guild, embed)

        await self.send_log_to_global(guild, embed)
        return None, None


    async def send_log_to_global(
        self,
        guild: discord.Guild,
        embed: discord.Embed,
    ) -> None:
        """Send logs to the global log channel."""
        channel = self.session.exec(select(Channels).where(
            Channels.guild_id == guild.id,
            Channels.name == LogCategories.GLOBAL.name,
        )).first()

        if not channel:
            self.logger.warning(f"No global log channel found for {guild}")
            return

        global_log_channel = discord.utils.get(guild.text_channels, id=channel.id) or None

        self.logger.debug(f"Found: {LogCategories.GLOBAL=} as {global_log_channel=}")
        if global_log_channel is not None:
            await global_log_channel.send(embed=embed)

        self.logger.debug(f"Send logs to {global_log_channel=}")


    async def send_log_to_category(
        self,
        log_category: LogCategories,
        guild: discord.Guild,
        embed: discord.Embed,
    ) -> None:
        """Send logs to the category channel."""
        log_channel_name = log_category.name

        channel = self.session.exec(select(Channels).where(
                Channels.guild_id == guild.id,
                Channels.name == log_channel_name,
            )).first()

        if channel is None:
            self.logger.warning(f"Found no logs channel! {channel=}, {guild=}, {embed=}")
            return

        if mod_channel := discord.utils.get(guild.text_channels, id=channel.id):
            await mod_channel.send(embed=embed)

        self.logger.debug(f"Send logs to {log_channel_name=}")


    def get_entry_role_difference(self, entry: discord.AuditLogEntry) -> list[discord.Role]:
        """Get the role difference from the audit log entry."""
        diffs = []
        for change1, change2 in zip(entry.changes.before, entry.changes.after, strict=False):
            diff = [c1 or c2 for c1, c2 in itertools.zip_longest(change1[1], change2[1])]
            for role in diff:
                if not isinstance(role, discord.Role):
                    self.logger.warning(f"Got {type(role)} from {role}, where expected discord.Role.")
                    continue
                if role := discord.utils.get(entry.guild.roles, id=role.id):
                    diffs.append(role.mention)
        return diffs


    def create_member_left_embed(self, member: discord.Member, entry: discord.AuditLogEntry) -> discord.Embed:
        """Create an embed for when a member leaves the guild."""
        user = entry.user
        if user is None:
            msg = "User is None"
            raise NoneTypeError(msg)
        if entry.action == discord.AuditLogAction.ban:
            return discord.Embed(
                title="Member Banned",
                description=f"{user.mention} Banned {member.mention} {member.name} with reason: {entry.reason or None}",
                color=DELETED_COLOR,
            )
        if entry.action == discord.AuditLogAction.kick:
            return discord.Embed(
                title="Member Kicked",
                description=f"{user.mention} Kicked {member.mention} {member.name} with reason: {entry.reason or None}",
                color=DELETED_COLOR,
            )
        return discord.Embed(
            title="Member Left",
            description=f"{member.mention} {member.name} Left the guild",
            color=DELETED_COLOR,
        )

# ----------------------
# Helper Functions End
# ----------------------

# -------------
# Entries Start
# -------------

    @Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        """Handle audit log entry creation."""
        action = entry.action
        self.logger.debug(f"{action=}, {entry.target}, {entry.__dict__=}")
        enum = discord.enums.AuditLogAction
        if action not in enum:
            await self.generic_change(entry)


    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Handle member updates."""
        member = after or before
        self.logger.debug(f"On member update: guild='{member.guild}', member='{after}'")
        if before.voice != after.voice:
            self.logger.critical(f"{before.voice=}, {after.voice=}")

        if (
            differences := [
                prop for prop in MEMBER_UPDATE_PROPERTIES
                if getattr(before, prop) != getattr(after, prop)
            ]
        ):
            update_message = f"{member.mention} got updated with {differences} "
            if "nick" in differences:
                update_message += self.get_username_difference(before, after)
            if "roles" in differences:
                update_message += self.get_member_role_difference(before, after)

            embed = discord.Embed(
                title="Member Update",
                description=update_message,
                color=CHANGED_COLOR,
            )
            await self.send_channel_logs(member.guild, embed, LogCategories.MEMBER_UPDATE)


    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Handle member joining."""
        self.logger.debug(f"On member join: guild='{member.guild}' member='{member}'")
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} Joined the guild",
            color= CREATED_COLOR,
        )
        await self.send_channel_logs(member.guild, embed, LogCategories.MEMBER_JOINED)


    @Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Handle member removal."""
        self.logger.debug(f"On member remove: guild='{member.guild}' member='{member}'")
        embed=None
        async for entry in member.guild.audit_logs(limit=1):
            embed = self.create_member_left_embed(member, entry)
        if not embed:
            msg = f"Expected discord.Embed, got {embed}"
            raise TypeError(msg)
        await self.send_channel_logs(member.guild, embed, LogCategories.MEMBER_LEFT)


    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """Handle message editing."""
        if not before.guild:
            self.logger.debug(f"Guild not found on {before=}")
            return
        if not before.clean_content:
            self.logger.debug(f"Empty content on {before=}")
            return
        if before.clean_content == after.clean_content:
            self.logger.debug(f"Message content is the same: {before}")
            return

        self.logger.debug(
            f"Message edited: {before.guild=}, {before.channel=}, {before.clean_content=}, {after.clean_content=}",
        )
        embed = discord.Embed(
            title="Message Edited",
            description=f"{before.author.mention} Edited a message",
            color=CHANGED_COLOR,
        )
        embed.add_field(name="Old", value=f"`{before.clean_content}`")
        embed.add_field(name="New", value=f"`{after.clean_content}`")
        await self.send_channel_logs(before.guild, embed, LogCategories.MESSAGE_EDITED)


    @Cog.listener()
    async def on_message_delete(self, message: discord.Message, reason: str | None = None) -> None:
        """Handle message deletion."""
        if not message.guild:
            self.logger.warning(f"Guild not found on {message=}, maybe DM?")
            self.logger.debug(f"Message deleted: {message.channel=}, {message.clean_content=}")
            return

        if not isinstance(message, discord.Message):
            self.logger.warning(f"got {type(message)} from {message}, where expected discord.Message.")
            return

        self.logger.debug(f"Message deleted: {message.guild=}, {message.channel=}, {message.clean_content=}")
        if message.clean_content in ["", "Unexpected Error..."]:
            return

        description = f"Deleted message send by {message.author.mention} with reason {reason}"
        embed = discord.Embed(
            title="Message Deleted",
            description=description,
            color=DELETED_COLOR,
        )
        embed.add_field(
            name="Content",
            value=f"`{message.clean_content}`",
        )

        await self.send_channel_logs(message.guild, embed, LogCategories.MESSAGE_DELETE)

    async def generic_change(self, entry: discord.AuditLogEntry) -> None:
        """Handle a generic change in the audit log."""
        e_before_type = getattr(entry.before.type, "__name__", entry.target)
        e_type = getattr(entry.target.type, "__name__", e_before_type) # type: ignore[]
        e_mention = getattr(entry.target, "mention", "")

        embed = discord.Embed(
            title="Generic Change (WIP)",
            description=f"{entry.user.mention} Changed `{e_type}` {e_mention} with reason: {entry.reason or None}", # type: ignore[]
            color=0x123456,
        )
        self.logger.debug(f"Triggered generic_change:\nENTRY: {entry}\nENTRY CHANGES: {entry.changes}\n")
        embed.add_field(name="Old", value="\u200b", inline=True)
        embed.add_field(name="New", value="\u200b", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        for change1, change2 in zip(entry.changes.before, entry.changes.after, strict=False):
            embed.add_field(name=change1[0], value=change1[1], inline=True)
            embed.add_field(name=change2[0], value=change2[1], inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False)
        await self.send_channel_logs(entry.guild, embed)

# ------------
# Entries End
# ------------

# ---------------
# Commands Start
# ---------------

    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.cooldown(1, 100)
    @app_commands.command(
        name = "add",
        description = "Enables automatic moderation/logging for this guild, and creates a channel for all logs.",
    )
    async def slash_log_add(self, interaction: discord.Interaction) -> None:
        """Create log channels for the guild. Creates category channels, to insert the channels into."""
        guild = interaction.guild
        bot_user = self.bot.user
        if guild is None:
            msg = "Guild is None"
            raise NoneTypeError(msg)
        if bot_user is None:
            msg = "Bot user is None"
            raise NoneTypeError(msg)
        channels = self.get_db_log_channels(guild)
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
        self.session.commit()

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
        div, mod = divmod(len(LogCategories), MAX_CATEGORY_SIZE)
        category_count = div + (1 if mod > 0 else 0)

        for i in range(category_count):
            category_channel = await guild.create_category(
                name=f"{bot_user.display_name} Log {i+1}",
                overwrites=overwrites,
                position=99,
                reason="Adding Log channels",
            )
            category_channels.append(category_channel)
            Channels.update(Channels(
                id = category_channel.id,
                name = LOG_CHANNEL_NAME,
                type = LOGS,
                guild_id = category_channel.guild.id,
            ))
        return category_channels

    async def create_log_channels(self, category_channels: list[CategoryChannel]) -> None:
        """Create log channels in the logging categories."""
        for i, log_category in enumerate(LogCategories):
            log_category_name = log_category.name.title()
            category_channel = self.get_log_category(category_channels, i)

            text_channel = await category_channel.create_text_channel(
                name=f"{log_category_name.lower()}",
                reason="Adding Log channels",
            )
            Channels.update(Channels(
                id = text_channel.id,
                name = log_category_name,
                type = LOGS,
                guild_id = text_channel.guild.id,
            ))

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
        description="Disables automatic moderation for this guild, and removes the log channels.")
    async def slash_log_remove(self, interaction:discord.Interaction) -> None:
        """Remove all log channels for this guild."""
        guild = interaction.guild
        if guild is None:
            msg = "Guild is None"
            raise NoneTypeError(msg)
        result = self.session.exec(select(Channels).where(
            Channels.type == LOGS,
            Channels.guild_id == guild.id,
        ))
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
                raise NoneTypeError(msg)
            await dc_channel.delete()
            self.session.delete(channel)
        self.session.commit()

        await interaction.followup.send("Removed LogChannels")
        self.logger.info(f"Removed Log for {interaction.guild}")


    @app_commands.guilds(Settings.support_guild_id)
    @commands.is_owner()
    @app_commands.command(name = "update", description = "Update Log channels")
    async def slash_log_update(self, interaction: discord.Interaction, guild_id: int | None=None) -> None:
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
            guild_id = (
                self.session.exec(select(Channels.guild_id)
                    .where(Channels.type == LOGS),
                    ).first()
            )
            return await self.update_log(guild=discord.utils.get(self.bot.guilds, id=guild_id))

        channels = self.session.exec(select(Channels).where(
            Channels.type == LOGS,
            Channels.guild_id == guild.id,
        )).all()

        div, mod = divmod(len(LogCategories), MAX_CATEGORY_SIZE)
        required_category_count = div + (1 if mod > 0 else 0)

        category_channels = await self.update_required_category_count(guild, required_category_count)

        difference: list[str] = []
        known_names = [channel.name.lower() for channel in channels]

        difference.extend(
            j for j in [i.name.lower() for i in LogCategories]
            if j not in known_names
        )
        self.logger.debug(f"{channels=}, {known_names=}, {difference=}")

        for i, channel_name in enumerate(difference):
            category_channel = self.get_log_category(category_channels, i)

            new_log_channel = await category_channel.create_text_channel(channel_name, reason="Log update")
            self.logger.info(f"Updated Log for {guild=} with {new_log_channel=}")
            Channels.update(Channels(
                id = new_log_channel.id,
                name = channel_name,
                type = LOGS,
                guild_id = category_channel.guild.id,
            ))
        self.session.commit()
        return None


    async def update_required_category_count(self, guild: discord.Guild, required_category_count: int) -> list[CategoryChannel]:
        """Update the required category count for the guild."""
        categories = self.session.exec(select(Channels).where(
            Channels.name == LOG_CHANNEL_NAME,
            Channels.type == LOGS,
            Channels.guild_id == guild.id,
        )).all()
        category_channels = [
            discord.utils.get(guild.categories, id=category.id)
            for category in categories
        ]
        current_category_count = len(category_channels) or len(categories)

        if current_category_count < required_category_count:
            for i in range(current_category_count, required_category_count):
                bot_user = self.bot.user
                if bot_user is None:
                    msg = "Bot user is None"
                    raise NoneTypeError(msg)
                category_channel = await guild.create_category(
                    name=f"{bot_user.display_name} Log {i+1}",
                    overwrites= {
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
                Channels.update(Channels(
                    id = category_channel.id,
                    name = LOG_CHANNEL_NAME,
                    type = LOGS,
                    guild_id = category_channel.guild.id,
                ))
        self.session.commit()

        return cast("list[CategoryChannel]", category_channels)

# ------------
# Commands End
# ------------

async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(LogChannels(bot))
