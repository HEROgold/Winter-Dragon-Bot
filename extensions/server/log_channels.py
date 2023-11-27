import itertools
from typing import Optional, Union

import discord
from discord import CategoryChannel, app_commands
from discord.ext import commands

from tools.config_reader import config
from tools.database_tables import Channel, engine, Session
from enums.log_channels import LogCategories
from tools.msg_checks import is_tic_tac_toe
from _types.cogs import Cog, GroupCog
from _types.bot import WinterDragon


LOGS = "logs"
LOG_CATEGORY = "LOG-CATEGORY"
MEMBER_UPDATE_PROPERTIES = [
    "nick",
    "roles",
    "pending",
    "guild_avatar",
    "guild_permissions",
]
MAX_CATEGORY_SIZE = 50
CREATED_COLOR = 0x00FF00
CHANGED_COLOR = 0xFFFF00
DELETED_COLOR = 0xff0000


class LogChannels(GroupCog):

# ----------------------
# Helper Functions Start
# ----------------------

    def get_log_category(self, category_channels: list[CategoryChannel], current_count: int) -> CategoryChannel:
        channel_locator, _ = divmod(current_count, MAX_CATEGORY_SIZE)
        category_channel = category_channels[channel_locator]
        self.logger.debug(f"{category_channels=}, {channel_locator=}")

        if channel_locator + len(category_channel.channels) > 50:
            channel_location = (len(category_channel.channels) + channel_locator)
            return self.get_log_category(category_channels, channel_location)
        return category_channel


    def get_member_role_difference(self, before: discord.Member, after: discord.Member) -> list[str]:
        role_diff_add = [role.mention for role in after.roles if role not in before.roles]
        role_diff_rem = [role.mention for role in after.roles if role in before.roles]
        return role_diff_add + role_diff_rem


    def get_username_difference(self, before: discord.Member, after: discord.Member) -> str | None:
        return (
            f"from `{before.display_name}` to `{after.display_name}`"
            if after.display_name != before.display_name
            else None
        )


    async def send_channel_logs(
        self,
        log_category: Optional[LogCategories],
        guild: discord.Guild,
        embed: discord.Embed
    ) -> None:
        if not guild:
            self.logger.debug("No guild during DragonLog channel fetching")
            return None, None

        self.logger.debug(f"Searching for log channels {log_category=} and {LogCategories.GLOBAL=}")

        if log_category is not None:
            await self.send_log_to_category(log_category, guild, embed)

        await self.send_log_to_global(guild, embed)


    async def send_log_to_global(
        self,
        guild: discord.Guild,
        embed: discord.Embed
    ) -> None:
        with Session(engine) as session:
            channel = session.query(Channel).where(
                Channel.guild_id == guild.id,
                Channel.name == LogCategories.GLOBAL.value
            ).first()

        if not channel:
            self.logger.warning(f"No global log channel found for {guild}")
            return

        global_log_channel = discord.utils.get(guild.channels, id=channel.id) or None

        self.logger.debug(f"Found: {LogCategories.GLOBAL=} as {global_log_channel=}")
        if global_log_channel is not None:
            await global_log_channel.send(embed=embed)

        self.logger.debug(f"Send logs to {global_log_channel=}")


    async def send_log_to_category(
        self,
        log_category: LogCategories,
        guild: discord.Guild,
        embed: discord.Embed
    ) -> None:
        log_channel_name = log_category.value

        with Session(engine) as session:
            channel = session.query(Channel).where(
                    Channel.guild_id == guild.id,
                    Channel.name == log_channel_name
                ).first()
        
        if channel is None:
            self.logger.warning(f"Found no logs channel! {channel=}, {guild=}, {embed=}")
            return

        if mod_channel := discord.utils.get(guild.channels, id=channel.id):
            await mod_channel.send(embed=embed)

        self.logger.debug(f"Send logs to {log_channel_name=}")


    def get_entry_role_difference(self, entry: discord.AuditLogEntry) -> list[discord.Role]:
        diffs = []
        for change1, change2 in zip(entry.changes.before, entry.changes.after):
            diff = [c1 or c2 for c1, c2 in itertools.zip_longest(change1[1], change2[1])]
            for role in diff:
                role = discord.utils.get(entry.guild.roles, id=role.id)
                diffs.append(role.mention)
        return diffs


    def create_member_left_embed(self, member: discord.Member, entry: discord.AuditLogEntry) -> discord.Embed:
        if entry.action == discord.AuditLogAction.ban:
            return discord.Embed(
                title="Member Banned",
                description=f"{entry.user.mention} Banned {member.mention} {member.name} with reason: {entry.reason or None}",
                color=DELETED_COLOR,
            )
        elif entry.action == discord.AuditLogAction.kick:
            return discord.Embed(
                title="Member Kicked",
                description=f"{entry.user.mention} Kicked {member.mention} {member.name} with reason: {entry.reason or None}",
                color=DELETED_COLOR,
            )
        else:
            return discord.Embed(
                title="Member Left",
                description=f"{member.mention} {member.name} Left the server",
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
        action = entry.action
        self.logger.debug(f"{action=}, {entry.target=}, {entry.__dict__=}")
        enum = discord.enums.AuditLogAction
        if action not in enum:
            await self.generic_change(entry)
        else:
            actions = {
                enum.guild_update: self.on_guild_update,
                enum.channel_create: self.on_guild_channel_create,
                enum.channel_update: self.on_guild_channel_update,
                enum.channel_delete: self.on_guild_channel_delete,
                enum.overwrite_create: self.on_overwrite_create,
                enum.overwrite_update: self.on_overwrite_update,
                enum.overwrite_delete: self.on_overwrite_delete,
                enum.kick: self.on_kick,
                enum.member_prune: self.on_member_prune,
                enum.ban: self.on_ban,
                enum.unban: self.on_unban,
                enum.member_update: self.audit_member_update,
                enum.member_role_update: self.audit_member_update,
                enum.member_move: self.on_member_move,
                enum.member_disconnect: self.on_member_disconnect,
                enum.bot_add: self.on_bot_add,
                enum.role_create: self.on_role_create,
                enum.role_update: self.on_role_update,
                enum.role_delete: self.on_role_delete,
                enum.invite_create: self.on_invite_create,
                enum.invite_update: self.on_invite_update,
                enum.invite_delete: self.on_invite_delete,
                enum.webhook_create: self.on_webhook_create,
                enum.webhook_update: self.on_webhook_update,
                enum.webhook_delete: self.on_webhook_delete,
                enum.emoji_create: self.on_emoji_create,
                enum.emoji_update: self.on_emoji_update,
                enum.emoji_delete: self.on_emoji_delete,
                enum.message_delete: self.audit_message_delete,
                enum.message_bulk_delete: self.audit_message_delete,
                enum.message_pin: self.on_message_pin,
                enum.message_unpin: self.on_message_unpin,
                enum.integration_create: self.on_integration_create,
                enum.integration_update: self.on_integration_update,
                enum.integration_delete: self.on_integration_delete,
                enum.stage_instance_create: self.on_stage_instance_create,
                enum.stage_instance_update: self.on_stage_instance_update,
                enum.stage_instance_delete: self.on_stage_instance_delete,
                enum.sticker_create: self.on_sticker_create,
                enum.sticker_update: self.on_sticker_update,
                enum.sticker_delete: self.on_sticker_delete,
                enum.scheduled_event_create: self.on_scheduled_event_create,
                enum.scheduled_event_update: self.on_scheduled_event_update,
                enum.scheduled_event_delete: self.on_scheduled_event_delete,
                enum.thread_create: self.on_thread_create,
                enum.thread_update: self.on_thread_update,
                enum.thread_delete: self.on_thread_delete,
                enum.app_command_permission_update: self.on_app_command_permission_update,
                enum.automod_rule_create: self.on_automod_rule_create,
                enum.automod_rule_update: self.on_automod_rule_update,
                enum.automod_rule_delete: self.on_automod_rule_delete,
                enum.automod_block_message: self.on_automod_block_message,
                enum.automod_flag_message: self.on_automod_flag_message,
                enum.automod_timeout_member: self.on_automod_timeout_member,
            }
            await actions[action](entry)


    async def on_guild_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.guild_update
        self.logger.debug(f"On guild update: {entry.guild=}, {entry=}")


    async def on_guild_channel_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.channel_create
        self.logger.debug(f"On channel create: {entry.guild=}, {entry.target=}")
        channel: discord.abc.GuildChannel = entry.target

        mention = channel.mention 

        embed = discord.Embed(
            title="Channel Created",
            description=f"{entry.user.mention} created {channel.type} {mention} with reason: {entry.reason or None}",
            color= CREATED_COLOR
        )
        await self.send_channel_logs(LogCategories.CHANNEL_CREATE, entry.guild, embed)


    async def on_guild_channel_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.channel_update
        before: discord.abc.GuildChannel = entry.before
        after: discord.abc.GuildChannel = entry.after
        channel = after or before
        embed = None
        # FIXME: AttributeError: 'AuditLogDiff' object has no attribute 'overwrites'. Documentation suggests it does.
        properties = "name", "position", "type" # "overwrites", 
        # remove X since AuditLogDiff doesn't have them
        # X = "category", "permissions_synced"

        self.logger.debug(f"On channel update: {entry.guild=}, {channel=}")
        if differences := [prop for prop in properties if getattr(before, prop) != getattr(after, prop)]:
            if "name" in differences or before.name != after.name:
                name_change = f"`{before.name}` to `{after.name}` for {after.mention}"
            embed = discord.Embed(
                title="Channel Changed",
                description=f"{entry.user.mention} changed {differences} of channel {name_change or after.mention} with reason: {entry.reason or None}",
                color=CHANGED_COLOR
            )
        if not embed:
            return
        await self.send_channel_logs(LogCategories.CHANNEL_UPDATE, entry.guild, embed)


    async def on_guild_channel_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.channel_delete
        channel = entry.target
        self.logger.debug(f"On channel delete: guild='{entry.guild}' channel='{channel}'")
        channel_type = channel.type if channel.type != discord.object.Object else ''

        embed = discord.Embed(
            title="Channel Deleted",
            description=f"{entry.user.mention} deleted {channel_type}  `{channel.id}` with reason: {entry.reason or None}", # `{channel.name}`, channel has not attrib, name
            color=DELETED_COLOR
        )
        await self.send_channel_logs(LogCategories.CHANNEL_DELETE, entry.guild, embed)


    async def on_invite_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.invite_create
        invite = entry.target
        self.logger.debug(f"On invite create: {invite.guild=}, {invite=}")
        embed = discord.Embed(
            title="Created Invite",
            description=f"{entry.user.mention} Created invite {invite} with reason: {entry.reason or None}",
            color= CREATED_COLOR
            )
        await self.send_channel_logs(LogCategories.INVITE_CREATE, invite.guild, embed)


    async def on_invite_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.invite_update
        invite = entry.target
        self.logger.debug(f"On invite update: {invite.guild=}, {invite=}")
        embed = discord.Embed(
            title="Updated Invite",
            description=f"{entry.user.mention} Updated invite {invite} with reason: {entry.reason or None}",
            color= CREATED_COLOR
            )
        await self.send_channel_logs(LogCategories.INVITE_UPDATE, invite.guild, embed)


    async def on_invite_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.invite_delete
        invite = entry.target
        self.logger.debug(f"On invite delete: {invite.guild=}, {invite=}")
        embed = None
        embed = discord.Embed(
            title="Removed Invite",
            description=f"{entry.user.mention} Removed invite {invite} with reason: {entry.reason or None}",
            color=DELETED_COLOR
            )
        await self.send_channel_logs(LogCategories.INVITE_DELETE, invite.guild, embed)


    async def on_role_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.role_create
        self.logger.debug(f"On role create: guild='{entry.guild}' channel='{entry.target}'")
        role:discord.Role = entry.target
        embed = discord.Embed(
            title="Role Created",
            description=f"{entry.user.mention} created {role.mention or entry.target.mention} with permissions {role.permissions} with reason: {entry.reason or None}",
            color= CREATED_COLOR
            )
        await self.send_channel_logs(LogCategories.ROLE_CREATE, entry.guild, embed)


    async def on_role_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.role_update
        self.logger.debug(f"On role update: guild='{entry.guild}', role='{entry.target}'")
        role:discord.Role = entry.target
        
        embed = discord.Embed(
            title="Role Updated",
            description=f"{entry.user.mention} created {role.mention or entry.target.mention} with reason: {entry.reason or None}",
            color=CHANGED_COLOR
            )
        await self.send_channel_logs(LogCategories.ROLE_UPDATE, entry.guild, embed)


    async def on_role_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.role_delete
        self.logger.debug(f"On role delete: guild='{entry.guild}', role='{entry.target}'")
        role:discord.Role = entry.target
        embed = discord.Embed(
            title="Role Removed",
            description=f"{entry.user.mention} created {role or entry.target} with reason: {entry.reason or None}",
            color=DELETED_COLOR
            )
        await self.send_channel_logs(LogCategories.ROLE_DELETE, entry.guild, embed)


    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
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
                color=CHANGED_COLOR
            )
            await self.send_channel_logs(LogCategories.MEMBER_UPDATE, member.guild, embed)


    async def audit_member_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.member_update
        member: discord.Member = entry.target
        self.logger.debug(f"On member update: guild='{member.guild}', member='{member}'")
        
        if (
            differences := [
                prop for prop in MEMBER_UPDATE_PROPERTIES
                if getattr(entry, prop) != getattr(entry, prop)
            ]
        ):
            update_message = f"{member.mention} got updated with {differences} "
            if "nick" in differences:
                update_message += member.display_name
            if "roles" in differences:
                update_message += self.get_entry_role_difference(entry)

            embed = discord.Embed(
                title="Member Update",
                description=update_message,
                color=CHANGED_COLOR
            )
            await self.send_channel_logs(LogCategories.MEMBER_UPDATE, member.guild, embed)


    async def on_member_move(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.member_move
        embed = discord.Embed(
            title="Member Moved",
            description=f"{entry.user.mention} Moved {entry.target.mention} to {entry.target.channel.mention}",
            color=CHANGED_COLOR
        )
        await self.send_channel_logs(LogCategories.MEMBER_MOVE, entry.guild, embed)


    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        self.logger.debug(f"On member join: guild='{member.guild}' member='{member}'")
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} Joined the server",
            color= CREATED_COLOR
        )
        await self.send_channel_logs(LogCategories.MEMBER_JOINED, member.guild, embed)


    @Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        self.logger.debug(f"On member remove: guild='{member.guild}' member='{member}'")
        embed=None
        async for entry in member.guild.audit_logs(limit=1):
            embed = self.create_member_left_embed(member, entry)
        if not embed:
            raise TypeError(f"Expected discord.Embed, got {embed}")
        await self.send_channel_logs(LogCategories.MEMBER_LEFT, member.guild, embed)


    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not before.clean_content:
            self.logger.debug(f"Empty content on {before=}")
            return
        if before.clean_content == after.clean_content:
            self.logger.debug(f"Message content is the same: {before}")
            return
        if is_tic_tac_toe(before.clean_content):
            self.logger.debug(f"Edited message was tic-tac-toe game: {before}")
            return

        self.logger.debug(f"Message edited: {before.guild=}, {before.channel=}, {before.clean_content=}, {after.clean_content=}")
        embed = discord.Embed(
            title="Message Edited",
            description=f"{before.author.mention} Edited a message",
            color=CHANGED_COLOR
        )
        embed.add_field(name="Old", value=f"`{before.clean_content}`")
        embed.add_field(name="New", value=f"`{after.clean_content}`")
        await self.send_channel_logs(LogCategories.MESSAGE_EDITED, before.guild, embed)


    @Cog.listener()
    async def on_message_delete(self, message: discord.Message, reason: str = None) -> None:
        if isinstance(message, discord.Message):
            message = message
        else:
            self.logger.warning(f"got {type(message)} from {message}, where expected discord.Message.")
            return

        self.logger.debug(f"Message deleted: {message.guild=}, {message.channel=}, {message.clean_content=}")
        if message.clean_content in ["", "Unexpected Error..."]:
            return

        description = f"Deleted message send by {message.author.mention} with reason {reason}"
        embed = discord.Embed(
            title="Message Deleted",
            description=description,
            color=DELETED_COLOR
        )
        embed.add_field(
            name="Content",
            value=f"`{message.clean_content}`"
        )

        await self.send_channel_logs(LogCategories.MESSAGE_DELETE, message.guild, embed)


    async def audit_message_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.message_delete
        if entry != discord.AuditLogEntry:
            self.logger.warning(f"got {type(entry)} from {entry}, where expected discord.AuditLogEntry.")
            return
        
        message: discord.Message = entry.target
        await self.on_message_delete(message, entry.reason)

        # artifacts from audit log
        if entry.action == entry.action.message_delete:
            # 99% other persons message
            self.logger.debug(f"message delete: {message}")
        # TODO: Test and if needs switching to discord.enums
        elif entry.action == entry.action.message_bulk_delete:
            # figure out what to send here
            self.logger.debug(f"bulk delete: {message}")
        else:
            # likely removed own message
            self.logger.debug(f"else: {message}")


    async def on_overwrite_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.overwrite_create
        self.logger.debug(f"On overwrite create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.OVERWRITE_CREATE, entry.guild, discord.Embed(
            title="Overwrite Create",
            description=f"{entry.user.mention} added permissions to {entry.target.type} {entry.extra} for {entry.target} with reason {entry.reason or None}",
            color=CREATED_COLOR
        ))


    async def on_overwrite_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.overwrite_update
        self.logger.debug(f"On overwrite update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.OVERWRITE_UPDATE, entry.guild, discord.Embed(
            title="Overwrite Update",
            description=f"{entry.user.mention} changed permissions of {entry.target.type} {entry.target} for {entry.extra} with reason {entry.reason or None}",
            color=CHANGED_COLOR
        ))


    async def on_overwrite_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.overwrite_delete
        self.logger.debug(f"On overwrite delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.OVERWRITE_DELETE, entry.guild, discord.Embed(
            title="Overwrite Delete",
            description=f"{entry.user.mention} removed permissions from {entry.target.type} {entry.target} for {entry.extra} with reason {entry.reason or None}",
            color=DELETED_COLOR
        ))


    async def on_kick(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.kick
        self.logger.debug(f"on kick: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.KICK, entry.guild, discord.Embed(
            title="Kick",
            description=f"{entry.user.mention} Kicked {entry.target.type} {entry.target} with reason {entry.reason or None}",
            color=DELETED_COLOR
        ))


    async def on_member_prune(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.member_prune
        self.logger.debug(f"on member_prune: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.MEMBER_PRUNE, entry.guild, discord.Embed(
            title="Member Prune",
            description=f"{entry.user.mention} pruned {entry.target.type} {entry.target} with reason {entry.reason or None}",
            color=DELETED_COLOR
        ))


    async def on_ban(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.ban
        self.logger.debug(f"on ban: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.BAN, entry.guild, discord.Embed(
            title="Ban",
            description=f"{entry.user.mention} banned {entry.target.type} {entry.target} with reason {entry.reason or None}",
            color=DELETED_COLOR
        ))


    async def on_unban(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.unban
        self.logger.debug(f"on unban: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.UNBAN, entry.guild, discord.Embed(
            title="Unban",
            description=f"{entry.user.mention} un-banned {entry.target.type} {entry.target} with reason {entry.reason or None}",
            color=CREATED_COLOR
        ))


    async def on_member_disconnect(self, entry: discord.AuditLogEntry) -> None:
        self.logger.debug(f"on member_disconnect: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.MEMBER_DISCONNECT, entry.guild, discord.Embed(
            title="Member Disconnect",
            description=f"{entry.user.mention} disconnected {entry.target.type} {entry.target} from {entry.extra} with reason {entry.reason or None}",
            color=DELETED_COLOR
        ))


    async def on_bot_add(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.bot_add
        self.logger.debug(f"on bot_add: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.BOT_ADD, entry.guild, discord.Embed(
            title="Bot Add",
            description=f"{entry.user.mention} added {entry.target.type} {entry.target} with reason {entry.reason or None}",
            color=CREATED_COLOR
        ))


    async def on_invite_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.invite_update
        self.logger.debug(f"on invite_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.INVITE_UPDATE, entry.guild, discord.Embed(
            title="Invite Update",
            description=f"{entry.user.mention} updated {entry.target.type} {entry.target} with reason {entry.reason or None}",
            color=CHANGED_COLOR
        ))


    async def on_webhook_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.webhook_create
        self.logger.debug(f"on webhook_create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.WEBHOOK_CREATE, entry.guild, discord.Embed(
            title="Webhook Create",
            description=f"{entry.user.mention} created Webhook with reason {entry.reason or None}",
            color=CREATED_COLOR
        ))


    async def on_webhook_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.webhook_update
        self.logger.debug(f"on webhook_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.WEBHOOK_UPDATE, entry.guild, discord.Embed(
            title="Webhook Update",
            description=f"{entry.user.mention} updated Webhook with reason {entry.reason or None}",
            color=CHANGED_COLOR
        ))


    async def on_webhook_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.webook_delete
        self.logger.debug(f"on webhook_delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.WEBHOOK_DELETE, entry.guild, discord.Embed(
            title="Webhook Delete",
            description=f"{entry.user.mention} deleted Webhook with reason {entry.reason or None}",
            color=DELETED_COLOR
        ))


    async def on_emoji_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.emoji_create
        self.logger.debug(f"on emoji_create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.EMOJI_CREATE, entry.guild, discord.Embed(
            title="Emoji Create",
            description=f"{entry.user.mention} Created emoji {entry.target} with reason {entry.reason or None}",
            color=CREATED_COLOR
        ))


    async def on_emoji_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.emoji_update
        self.logger.debug(f"on emoji_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.EMOJI_UPDATE, entry.guild, discord.Embed(
            title="Emoji Update",
            description=f"{entry.user.mention} Updated emoji {entry.target.url} with reason {entry.reason or None}",
            color=CHANGED_COLOR
        ))


    async def on_emoji_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.emoji_delete
        self.logger.debug(f"on emoji_delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.EMOJI_DELETE, entry.guild, discord.Embed(
            title="Emoji Delete",
            description=f"{entry.user.mention} Deleted emoji {entry.target} with reason {entry.reason or None}",
            color=DELETED_COLOR
        ))


    async def on_message_pin(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.message_pin
        self.logger.debug(f"on message_pin: {entry.guild=}, {entry=}")
        channel = entry.extra.channel
        embed = discord.Embed(
            title="Message Pin",
            description=f"{entry.user.mention} Pinned {entry.target.mention}`s message with reason {entry.reason or None}",
            color=CREATED_COLOR
        )
        embed.add_field(
            name="Channel",
            value=channel.mention
        )
        embed.add_field(
            name="Message",
            value=channel.get_partial_message(entry.extra.message_id).jump_url
        )
        await self.send_channel_logs(LogCategories.MESSAGE_PIN, entry.guild, embed)


    async def on_message_unpin(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.message_unpin
        self.logger.debug(f"on message_unpin: {entry.guild=}, {entry=}")
        channel = entry.extra.channel
        embed = discord.Embed(
            title="Message Unpin",
            description=f"{entry.user.mention} Un-Pinned {entry.target.mention}`s message with reason {entry.reason or None}",
            color=DELETED_COLOR
        )
        embed.add_field(
            name="Channel",
            value=channel.mention
        )
        embed.add_field(
            name="Message",
            value=channel.get_partial_message(entry.extra.message_id).jump_url
        )
        await self.send_channel_logs(LogCategories.MESSAGE_UNPIN, entry.guild, embed)

# -----------------------------------------
# TODO: Add Unique msg for each function
# -----------------------------------------


    async def on_integration_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.integration_create
        target: discord.Integration = entry.target
        self.logger.debug(f"on integration_create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.INTEGRATION_CREATE, entry.guild, discord.Embed(
            title="Integration Create",
            description=f"{entry.user.mention} Created integration {target}",
            color=CREATED_COLOR
        ))


    async def on_integration_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.integration_update
        target: discord.Integration = entry.target
        # target.account
        # target.enabled
        # target.guild
        # target.id
        # target.name
        self.logger.debug(f"on integration_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.INTEGRATION_UPDATE, entry.guild, discord.Embed(
            title="Integration Update",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {target}",
            color=CHANGED_COLOR
        ))


    async def on_integration_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.integration_delete
        target: discord.Integration = entry.target
        self.logger.debug(f"on integration_delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.INTEGRATION_DELETE, entry.guild, discord.Embed(
            title="Integration Delete",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {target}",
            color=DELETED_COLOR
        ))


    async def on_stage_instance_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.stage_instance_create
        target: discord.StageInstance = entry.target
        self.logger.debug(f"on stage_instance_create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.STAGE_INSTANCE_CREATE, entry.guild, discord.Embed(
            title="Stage Instance Create",
            description=f"{entry.user.mention} started a stage in {self.bot.get_channel(target.channel_id).mention} with topic {target.topic}",
            color=CREATED_COLOR
        ))


    async def on_stage_instance_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.stage_instance_update
        target: discord.StageInstance = entry.target
        self.logger.debug(f"on stage_instance_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.STAGE_INSTANCE_UPDATE, entry.guild, discord.Embed(
            title="Stage Instance Update",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CHANGED_COLOR
        ))


    async def on_stage_instance_delete(self, entry: discord.AuditLogEntry) -> None:
        # seehttps://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.stage_instance_delete
        target: discord.StageInstance = entry.target
        self.logger.debug(f"on stage_instance_delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.STAGE_INSTANCE_DELETE, entry.guild, discord.Embed(
            title="Stage Instance Delete",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=DELETED_COLOR
        ))


    async def on_sticker_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.sticker_create
        target: discord.Sticker = entry.target
        self.logger.debug(f"on sticker_create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.STICKER_CREATE, entry.guild, discord.Embed(
            title="Sticker Create",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CREATED_COLOR
        ))


    async def on_sticker_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.sticker_update
        target: discord.Sticker = entry.target
        self.logger.debug(f"on sticker_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.STICKER_UPDATE, entry.guild, discord.Embed(
            title="Sticker Update",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CHANGED_COLOR
        ))


    async def on_sticker_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.sticker_delete
        target: discord.Sticker = entry.target
        self.logger.debug(f"on sticker_delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.STICKER_DELETE, entry.guild, discord.Embed(
            title="Sticker Delete",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=DELETED_COLOR
        ))


    async def on_scheduled_event_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.scheduled_event_create
        target: discord.ScheduledEvent = entry.target
        self.logger.debug(f"on scheduled_event_create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.SCHEDULED_EVENT_CREATE, entry.guild, discord.Embed(
            title="Scheduled Event Create",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CREATED_COLOR
        ))


    async def on_scheduled_event_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.scheduled_event_update
        self.logger.debug(f"on scheduled_event_update: {entry.guild=}, {entry=}")
        target: discord.ScheduledEvent = entry.target
        await self.send_channel_logs(LogCategories.SCHEDULED_EVENT_UPDATE, entry.guild, discord.Embed(
            title="Scheduled Event Update",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CHANGED_COLOR
        ))


    async def on_scheduled_event_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.schedules_event_delete
        target: discord.ScheduledEvent = entry.target
        self.logger.debug(f"on scheduled_event_delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.SCHEDULED_EVENT_DELETE, entry.guild, discord.Embed(
            title="Scheduled Event Delete",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=DELETED_COLOR
        ))


    async def on_thread_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.on_thread_create
        target: discord.Thread = entry.target
        self.logger.debug(f"on thread_create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.THREAD_CREATE, entry.guild, discord.Embed(
            title="Thread Create",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CREATED_COLOR
        ))


    async def on_thread_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.on_thread_update
        target: discord.Thread = entry.target
        self.logger.debug(f"on thread_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.THREAD_UPDATE, entry.guild, discord.Embed(
            title="Thread Update",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CHANGED_COLOR
        ))


    async def on_thread_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.on_thread_delete
        target: discord.Thread = entry.target
        self.logger.debug(f"on thread_delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.THREAD_DELETE, entry.guild, discord.Embed(
            title="Thread Delete",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=DELETED_COLOR
        ))


    async def on_app_command_permission_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.app_command_permission_update
        target: Union[discord.PartialIntegration, app_commands.AppCommand] = entry.target
        self.logger.debug(f"on app_command_permission_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.APP_COMMAND_PERMISSION_UPDATE, entry.guild, discord.Embed(
            title="App Command Permission Update",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}"
        ))


    async def on_automod_rule_create(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_rule_create
        target: discord.AutoModRule = entry.target
        self.logger.debug(f"on automod_rule_create: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.AUTOMOD_RULE_CREATE, entry.guild, discord.Embed(
            title="Automod Rule Create",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CREATED_COLOR
        ))


    async def on_automod_rule_update(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_rule_update
        target: discord.AutoModRule = entry.target
        self.logger.debug(f"on automod_rule_update: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.AUTOMOD_RULE_UPDATE, entry.guild, discord.Embed(
            title="Automod Rule Update",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CHANGED_COLOR
        ))


    async def on_automod_rule_delete(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_rule_delete
        target: discord.AutoModRule = entry.target
        self.logger.debug(f"on automod_rule_delete: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.AUTOMOD_RULE_DELETE, entry.guild, discord.Embed(
            title="Automod Rule Delete",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=DELETED_COLOR
        ))


    async def on_automod_block_message(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_block_message
        target: discord.Member = entry.target
        self.logger.debug(f"on automod_block_message: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.AUTOMOD_BLOCK_MESSAGE, entry.guild, discord.Embed(
            title="Automod Block Message",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=DELETED_COLOR
        ))


    async def on_automod_flag_message(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_flag_message
        target: discord.Member = entry.target
        self.logger.debug(f"on automod_flag_message: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.AUTOMOD_FLAG_MESSAGE, entry.guild, discord.Embed(
            title="Automod Flag Message",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=CHANGED_COLOR
        ))


    async def on_automod_timeout_member(self, entry: discord.AuditLogEntry) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_timeout_member
        target: discord.Member = entry.target
        self.logger.debug(f"on automod_timeout_member: {entry.guild=}, {entry=}")
        await self.send_channel_logs(LogCategories.AUTOMOD_TIMEOUT_MEMBER, entry.guild, discord.Embed(
            title="Automod Timeout Member",
            description=f"{entry.user.mention} {entry.action.name} on {entry.target.type} {entry.target}",
            color=DELETED_COLOR
        ))

# -----------------------------------------
# END: Add Unique msg for each function
# -----------------------------------------


    async def generic_change(self, entry: discord.AuditLogEntry) -> None:
        try:
            e_type = entry.target.type.__name__
            if not e_type or e_type == "None":
                raise AttributeError
        except AttributeError:
            try:
                e_type = entry.before.type.__name__
            except AttributeError:
                e_type = entry.target
        try:
            e_mention = entry.target.mention
        except AttributeError:
            e_mention = ""

        embed = discord.Embed(
            title="Generic Change (WIP)",
            description=f"{entry.user.mention} Changed `{e_type}` {e_mention} with reason: {entry.reason or None}",
            color=0x123456
        )
        self.logger.debug(f"Triggered generic_change:\nENTRY: {entry}\nENTRY CHANGES: {entry.changes}\n")
        embed.add_field(name="Old", value="\u200b", inline=True)
        embed.add_field(name="New", value="\u200b", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        for change1, change2 in zip(entry.changes.before, entry.changes.after):
            embed.add_field(name=change1[0], value=change1[1], inline=True)
            embed.add_field(name=change2[0], value=change2[1], inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False)
        await self.send_channel_logs(None, entry.guild, embed)

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
        description = "Enables automatic moderation/logging for this server, and creates a channel for all logs."
    )
    async def slash_DragonLog_add(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none())
        }
        with Session(engine) as session:
            channels = session.query(Channel).where(
                Channel.type == LOGS,
                Channel.guild_id == interaction.guild.id
            ).all()
            if len(channels) > 0:
                await interaction.response.send_message("DragonLog channels are already set up.")
                return

        await interaction.response.defer(ephemeral=True)
        with Session(engine) as session:
            category_channels: list[CategoryChannel] = []
            div, mod = divmod(len(LogCategories), MAX_CATEGORY_SIZE)
            category_count = div + (1 if mod > 0 else 0)

            for i in range(category_count):
                category_channel = await guild.create_category(
                    name=f"Dragon DragonLog {i+1}",
                    overwrites=overwrites,
                    position=99,
                    reason="Adding DragonLog channels"
                )
                category_channels.append(category_channel)
                Channel.update(Channel(
                    id = category_channel.id,
                    name = LOG_CATEGORY,
                    type = LOGS,
                    guild_id = category_channel.guild.id
                ))

            for i, log_category in enumerate(LogCategories):
                log_category_name = log_category.value

                category_channel = self.get_log_category(category_channels, i)

                text_channel = await category_channel.create_text_channel(
                    name=f"{log_category_name.lower()}",
                    reason="Adding DragonLog channels"
                )
                Channel.update(Channel(
                    id = text_channel.id,
                    name = log_category_name,
                    type = LOGS,
                    guild_id = text_channel.guild.id,
                ))
            session.commit()

        await interaction.followup.send(f"Set up DragonLog category and channels under {', '.join(i.mention for i in category_channels)}")
        self.logger.info(f"Setup DragonLog for {interaction.guild}")


    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.cooldown(1, 100)
    @app_commands.command(name="remove", description="Disables automatic moderation for this server, and removes the log channels.")
    async def slash_DragonLog_remove(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            result = session.query(Channel).where(
                Channel.type == LOGS,
                Channel.guild_id == interaction.guild.id
            )
            channels = result.all()
            if len(channels) == 0:
                c_mention = await self.get_command_mention(self.slash_DragonLog_add)
                await interaction.followup.send(f"Can't find DragonLogChannels Consider using {c_mention}")
                return

            # Defer to avoid timeout
            await interaction.response.defer(ephemeral=True)

            # filter category channels to be last in list
            for channel in list(channels):
                if (
                    isinstance(
                        discord.utils.get(interaction.guild.channels, id=channel.id),
                        CategoryChannel
                    ) and
                    len(channels) > 1
                ):
                    channels.remove(channel)
                    channels.append(channel)

            for channel in channels:
                try:
                    dc_channel = self.bot.get_channel(channel.id)
                    if dc_channel is None:
                        dc_channel = discord.utils.get(interaction.guild.channels, id=channel.id)
                        self.logger.debug(f"utils.get {dc_channel=}")
                    try:
                        await dc_channel.delete()
                    except AttributeError:
                        pass
                    session.delete(channel)
                except AttributeError as e:
                    self.logger.debug(f"{dc_channel=}")
                    self.logger.exception(e)
            session.commit()

        await interaction.followup.send("Removed DragonLogChannels")
        self.logger.info(f"Removed DragonLog for {interaction.guild}")


    @app_commands.guilds(config.getint("Main", "support_guild_id"))
    @commands.is_owner()
    @app_commands.command(name = "update", description = "Update DragonLog channels")
    async def slash_DragonLog_update(self, interaction: discord.Interaction, guild_id: int = None) -> None:
        # defer here to avoid timeout
        await interaction.response.defer(ephemeral=True)

        guild = discord.utils.get(self.bot.guilds, id=guild_id) if guild_id else None
        await self.update_DragonLog(guild=guild)
        await interaction.followup.send("Updated DragonLog channels on all servers!")


    async def update_DragonLog(self, guild: discord.Guild = None) -> None:
        self.logger.debug(f"Updating DragonLog for {guild=}")
        if guild is None:
            with Session(engine) as session:
                guild_ids = session.query(Channel.guild_id).where(Channel.type == LOGS).distinct().group_by(Channel.guild_id).all()
            for guild_id in guild_ids[0]:
                return await self.update_DragonLog(guild=discord.utils.get(self.bot.guilds, id=guild_id))

        with Session(engine) as session:
            channels = session.query(Channel).where(
                Channel.type == LOGS,
                Channel.guild_id == guild.id
            ).all()

        div, mod = divmod(len(LogCategories), MAX_CATEGORY_SIZE)
        required_category_count = div + (1 if mod > 0 else 0)

        category_channels = await self.update_required_category_count(guild, required_category_count)

        difference: list[str] = []
        known_names = [channel.name.lower() for channel in channels]

        difference.extend(
            j for j in [i.value.lower() for i in LogCategories]
            if j not in known_names
        )
        self.logger.debug(f"{channels=}, {known_names=}, {difference=}")

        with Session(engine) as session:
            for i, channel_name in enumerate(difference):
                category_channel = self.get_log_category(category_channels, i)

                new_log_channel = await category_channel.create_text_channel(channel_name, reason="DragonLog update")
                self.logger.info(f"Updated DragonLog for {guild=} with {new_log_channel=}")
                Channel.update(Channel(
                    id = new_log_channel.id,
                    name = channel_name,
                    type = LOGS,
                    guild_id = category_channel.guild.id,
                ))
            session.commit()


    async def update_required_category_count(self, guild: discord.Guild, required_category_count) -> list[CategoryChannel]:
        with Session(engine) as session:
            categories = session.query(Channel).where(
                Channel.name == LOG_CATEGORY,
                Channel.type == LOGS,
                Channel.guild_id == guild.id
            ).all()
            category_channels: list[CategoryChannel] = [
                discord.utils.get(guild.categories, id=category.id) for category in categories
            ]
            current_category_count = len(category_channels) or len(categories) 

            if current_category_count < required_category_count:
                for i in range(current_category_count, required_category_count):
                    category_channel = await guild.create_category(
                        name=f"Dragon DragonLog {i+1}",
                        overwrites= {
                            guild.default_role: discord.PermissionOverwrite(view_channel=False),
                            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none())
                        },
                        position=99,
                        reason="Adding DragonLog channels"
                    )
                    category_channels.append(category_channel)
                    Channel.update(Channel(
                        id = category_channel.id,
                        name = LOG_CATEGORY,
                        type = LOGS,
                        guild_id = category_channel.guild.id
                    ))
            session.commit()
        return category_channels

# ------------
# Commands End
# ------------

async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(LogChannels(bot))
