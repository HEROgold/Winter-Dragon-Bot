import itertools
import logging
from enum import Enum
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from tools.config_reader import config
from tools import app_command_tools
from tools.database_tables import Channel, engine, Session


class LogCategories(Enum):
    GLOBAL: str = "ALL-CATEGORIES"
    CREATEDCHANNELS: str = "CREATEDCHANNELS"
    UPDATEDCHANNELS: str = "UPDATEDCHANNELS"
    DELETEDCHANNELS: str = "DELETEDCHANNELS"
    CREATEDINVITES: str = "CREATEDINVITES"
    MEMBERUPDATES: str = "MEMBERUPDATES"
    MEMBERMOVED: str = "MEMBERMOVED"
    MEMBERJOINED: str = "MEMBERJOINED"
    MEMBERLEFT: str = "MEMBERLEFT"
    EDITEDMESSAGES: str = "EDITEDMESSAGES"
    DELETEDMESSAGES: str = "DELETEDMESSAGES"
    CREATEDROLES: str = "CREATEDROLES"
    UPDATEDROLES: str = "UPDATEDROLES"
    DELETEDROLES: str = "DELETEDROLES"


LOGS = "logs"
LOG_CATEGORY = "LOG-CATEGORY"

# TODO: Remove all listeners in favor for the on_guild_entry_create
class DragonLog(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.act = app_command_tools.Converter(bot=self.bot)


    async def send_dragon_logs(
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
        else:
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

        if mod_channel := discord.utils.get(guild.channels, id=channel.id):
            await mod_channel.send(embed=embed)

        self.logger.debug(f"Send logs to {log_channel_name=}")


    def get_role_difference(self, entry: discord.AuditLogEntry) -> list[discord.Role]:
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
                description=f"{entry.user.mention} Banned {member.mention} with reason: {entry.reason or None}",
                color=0xFF0000,
            )
        elif entry.action == discord.AuditLogAction.kick:
            return discord.Embed(
                title="Member Kicked",
                description=f"{entry.user.mention} Kicked {member.mention} with reason: {entry.reason or None}",
                color=0xFF0000,
            )
        else:
            return discord.Embed(
                title="Member Left",
                description=f"{member.mention} Left the server",
                color=0xFF0000,
            )

# ENTRIES START

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        action = entry.action
        self.logger.debug(f"{action=}, {entry.target=}, {entry.__dict__=}")
        enum = discord.enums.AuditLogAction
        actions = {
                enum.channel_create: await self.on_guild_channel_create(entry),
                enum.channel_delete: await self.on_guild_channel_delete(entry),
                enum.channel_update: await self.on_guild_channel_update(entry),
                enum.role_create: await self.on_role_create(entry),
                enum.role_update: await self.on_role_update(entry),
                enum.role_delete: await self.on_role_delete(entry),
                enum.invite_create: await self.on_invite_create(entry),
                enum.invite_delete: await self.on_invite_delete(entry),
                enum.member_move: await self.on_member_move(entry),
                enum.member_update: await self.audit_member_update(entry, False),
                enum.member_role_update: await self.audit_member_update(entry, True),
                enum.message_delete: await self.audit_message_delete(entry),
            }
        if action not in enum:
            await self.generic_change(entry)
        else:
            await actions[action]


    async def on_guild_channel_create(self, entry: discord.AuditLogEntry) -> None:
        self.logger.debug(f"On channel create: {entry.guild=}, {entry.target=}")
        channel: discord.abc.GuildChannel = entry.target

        mention = channel.mention 

        embed = discord.Embed(
            title="Channel Created",
            description=f"{entry.user.mention} created {channel.type} {mention} with reason: {entry.reason or None}",
            color=0x00FF00
        )
        await self.send_dragon_logs(LogCategories.CREATEDCHANNELS, entry.guild, embed)


    async def on_guild_channel_update(self, entry: discord.AuditLogEntry) -> None:
        before: discord.abc.GuildChannel = entry.before
        after: discord.abc.GuildChannel = entry.after
        channel = after or before
        embed = None
        properties = "overwrites", "name", "position", "type" 
        # remove X since AuditLogDiff doesn't have them
        # X = "category", "permissions_synced"

        self.logger.debug(f"On channel update: {entry.guild=}, {channel=}")
        found_properties = [prop for prop in properties if getattr(before, prop) != getattr(after, prop)]

        if differences := found_properties:
            if "name" in differences or before.name != after.name:
                name_change = f"`{before.name}` to `{after.name}` for {after.mention}"
            embed = discord.Embed(
                title="Channel Changed",
                description=f"{entry.user.mention} changed {differences} of channel {name_change or after.mention} with reason: {entry.reason or None}",
                color=0xFFFF00
                )
        if not embed:
            return
        await self.send_dragon_logs(LogCategories.UPDATEDCHANNELS, entry.guild, embed)


    async def on_guild_channel_delete(self, entry: discord.AuditLogEntry) -> None:
        self.logger.debug(f"On channel delete: guild='{entry.guild}' channel='{channel}'")
        channel = entry.target

        embed = discord.Embed(
            title="Channel Deleted",
            description=f"{entry.user.mention} deleted {channel.type} `{channel.name}` with reason: {entry.reason or None}",
            color=0xff0000
            )
        await self.send_dragon_logs(LogCategories.DELETEDCHANNELS, entry.guild, embed)


    async def on_invite_create(self, entry: discord.AuditLogEntry) -> None:
        invite = entry.target
        self.logger.debug(f"On invite create: {invite.guild=}, {invite=}")
        embed = discord.Embed(
            title="Created Invite",
            description=f"{entry.user} Created invite {invite} with reason: {entry.reason or None}",
            color=0x00ff00
            )
        await self.send_dragon_logs(LogCategories.CREATEDINVITES, invite.guild, embed)


    async def on_invite_delete(self, entry: discord.AuditLogEntry) -> None:
        invite = entry.target
        self.logger.debug(f"On invite delete: {invite.guild=}, {invite=}")
        embed = None
        embed = discord.Embed(
            title="Removed Invite",
            description=f"{entry.user} Removed invite {invite} with reason: {entry.reason or None}",
            color=0xff0000
            )
        await self.send_dragon_logs(LogCategories.CREATEDINVITES, invite.guild, embed)


    async def on_role_create(self, entry: discord.AuditLogEntry) -> None:
        self.logger.debug(f"On role create: guild='{entry.guild}' channel='{entry.target}'")
        role:discord.Role = entry.target
        embed = discord.Embed(
            title="Role Created",
            description=f"{entry.user.mention} created {role.mention or entry.target.mention} with permissions {role.permissions} with reason: {entry.reason or None}",
            color=0x00FF00
            )
        await self.send_dragon_logs(LogCategories.CREATEDROLES, entry.guild, embed)


    async def on_role_update(self, entry: discord.AuditLogEntry) -> None:
        self.logger.debug(f"On role update: guild='{entry.guild}', role='{entry.target}'")
        role:discord.Role = entry.target
        
        embed = discord.Embed(
            title="Role Updated",
            description=f"{entry.user.mention} created {role.mention or entry.target.mention} with reason: {entry.reason or None}",
            color=0xFFFF00
            )
        await self.send_dragon_logs(LogCategories.UPDATEDROLES, entry.guild, embed)


    async def on_role_delete(self, entry: discord.AuditLogEntry) -> None:
        self.logger.debug(f"On role delete: guild='{entry.guild}', role='{entry.target}'")
        role:discord.Role = entry.target
        embed = discord.Embed(
            title="Role Removed",
            description=f"{entry.user.mention} created {role or entry.target} with reason: {entry.reason or None}",
            color=0xFF0000
            )
        await self.send_dragon_logs(LogCategories.DELETEDROLES, entry.guild, embed)


    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        member = before or after
        self.logger.debug(f"On member update: guild='{member.guild}', member='{after}'")
        if before.voice != after.voice:
            self.logger.critical(f"{before.voice=}, {after.voice=}")
        diffs = self.get_role_difference(member) if before.roles != after.roles else ""
        embed = None
        properties = "nick", "roles", "pending", "guild_avatar", "guild_permissions"
        if differences := [prop for prop in properties if getattr(before, prop) != getattr(after, prop)]:
            embed = discord.Embed(
                title="Member Update",
                description=f"{member} got updated with {differences} {diffs}",
                color=0xFFFF00
            )
        if not embed:
            return
        await self.send_dragon_logs(LogCategories.MEMBERUPDATES, member.guild, embed)


    async def audit_member_update(self, entry: discord.AuditLogEntry) -> None:
        member: discord.Member = entry.target
        self.logger.debug(f"On member update: guild='{member.guild}', member='{member}'")
        
        diffs = self.get_role_difference(entry)
        embed = None
        properties = "nick", "roles", "pending", "guild_avatar", "guild_permissions"
        if differences := [prop for prop in properties if getattr(entry, prop) != getattr(entry, prop)]:
            embed = discord.Embed(
                title="Member Update",
                description=f"{member} got updated with {differences} {diffs}",
                color=0xFFFF00
            )
        if not embed:
            return
        await self.send_dragon_logs(LogCategories.MEMBERUPDATES, member.guild, embed)


    async def on_member_move(self, entry: discord.AuditLogEntry) -> None:
        embed = discord.Embed(
            title="Member Moved",
            description=f"{entry.user.mention} Moved {entry.target.mention} to {entry.target.channel}",
            color=0xFFFF00
            )
        await self.send_dragon_logs(LogCategories.MEMBERMOVED, entry.guild, embed)


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        self.logger.debug(f"On member join: guild='{member.guild}' member='{member}'")
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} Joined the server",
            color=0x00FF00
            )
        await self.send_dragon_logs(LogCategories.MEMBERJOINED, member.guild, embed)


    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        self.logger.debug(f"On member remove: guild='{member.guild}' member='{member}'")
        embed=None
        async for entry in member.guild.audit_logs(limit=1):
            embed = self.create_member_left_embed(member, entry)
        if not embed:
            raise TypeError(f"Expected discord.Embed, got {embed}")
        await self.send_dragon_logs(LogCategories.MEMBERLEFT, member.guild, embed)


    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not before.clean_content:
            self.logger.debug(f"Empty content on {before=}")
            return
        if before.clean_content == after.clean_content:
            self.logger.debug(f"Message content is the same: {before}")
            return
        self.logger.debug(f"Message edited: {before.guild=}, {before.channel=}, {before.clean_content=}, {after.clean_content=}")
        embed = discord.Embed(
            title="Message Edited",
            description=f"{before.author.mention} Edited a message",
            color=0xFFFF00
        )
        embed.add_field(name="Old", value=f"`{before.clean_content}`")
        embed.add_field(name="New", value=f"`{after.clean_content}`")
        await self.send_dragon_logs(LogCategories.EDITEDMESSAGES, before.guild, embed)


    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if isinstance(message, discord.Message):
            message = message
        else:
            self.logger.warning(f"got {type(message)} from {message}, where expected discord.AuditLogEntry.")
            return

        self.logger.debug(f"Message deleted: {message.guild=}, {message.channel=}, {message.clean_content=}")
        if message.clean_content == "":
            return

        DESC = f"Deleted message `{message.clean_content}`, send by {message.author.mention} with reason {message.reason or None}"
        embed = discord.Embed(
            title="Message Deleted",
            description=DESC,
            color=0xFF0000
        )

        await self.send_dragon_logs(LogCategories.DELETEDMESSAGES, message.guild, embed)


    async def audit_message_delete(self, entry: discord.AuditLogEntry) -> None:
        if entry != discord.AuditLogEntry:
            self.logger.warning(f"got {type(entry)} from {entry}, where expected discord.AuditLogEntry.")
            return

        message: discord.Message = entry.target

        self.logger.debug(f"Message deleted: {message.guild=}, {message.channel=}, {message.clean_content=}")
        if message.clean_content == "":
            return

        DESC = f"{entry.user.mention or None} Deleted message `{message.clean_content}`, send by {message.author.mention} with reason {entry.reason or None}"
        embed = discord.Embed(
            title="Message Deleted",
            description=DESC,
            color=0xFF0000
        )

        await self.send_dragon_logs(LogCategories.DELETEDMESSAGES, message.guild, embed)

        # artifacts from audit log
        if entry.action == entry.action.message_delete:
            # 99% other persons message
            self.logger.debug(f"message delete: {message}")
        # TODO: Test and see if needs switching to discord.enums
        elif entry.action == entry.action.message_bulk_delete:
            # figure out what to send here
            self.logger.debug(f"bulk delete: {message}")
        else:
            # likely removed own message
            self.logger.debug(f"else: {message}")


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
        await self.send_dragon_logs(None, entry.guild, embed)


# ENTRIES END
# COMMANDS START

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
            result = session.query(Channel).where(
                Channel.type == LOGS,
                Channel.guild_id == interaction.guild.id
            )
            channels = result.all()
            if len(channels) > 0:
                await interaction.response.send_message("DragonLog channels are already set up.")
                return

        await interaction.response.defer(ephemeral=True)
        with Session(engine) as session:
            category_channel = await guild.create_category(name="Dragon DragonLog", overwrites=overwrites, position=99, reason="Adding DragonLog channels")
            session.add(Channel(id = category_channel.id, name=LOG_CATEGORY, type=LOGS, guild_id=category_channel.guild.id))
            for log_category in LogCategories:
                log_category_name = log_category.value
                text_channel = await category_channel.create_text_channel(name=f"{log_category_name.lower()}", reason="Adding DragonLog channels")
                session.add(Channel(
                    id = text_channel.id,
                    name = log_category_name,
                    type = LOGS,
                    guild_id = text_channel.guild.id,
                ))
            session.commit()
        await interaction.followup.send("Set up DragonLog category and channels")
        self.logger.info(f"Setup DragonLog for {interaction.guild}")


    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.cooldown(1, 100)
    @app_commands.command(
        name = "remove",
        description = "Disables automatic moderation for this server, and removes the log channels.",
        )
    async def slash_DragonLog_remove(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            result = session.query(Channel).where(
                Channel.type == LOGS,
                Channel.guild_id == interaction.guild.id
            )
            channels = result.all()
            if len(channels) == 0:
                _, c_mention = await self.act.get_app_sub_command(self.slash_DragonLog_add)
                await interaction.followup.send(f"Can't find DragonLogChannels Consider using {c_mention}")
                return

            # Defer to avoid timeout
            await interaction.response.defer(ephemeral=True)
            for channel in channels:
                try:
                    dc_channel = self.bot.get_channel(channel.id)
                    if dc_channel is None:
                        dc_channel = discord.utils.get(interaction.guild.channels, id=channel.id)
                        self.logger.debug(f"utils.get {dc_channel=}")
                    await dc_channel.delete()
                    session.delete(channel)
                except AttributeError as e:
                    self.logger.debug(f"{dc_channel=}")
                    self.logger.exception(e)
            session.commit()

        await interaction.followup.send("Removed DragonLogChannels")
        self.logger.info(f"Removed DragonLog for {interaction.guild}")


    @app_commands.command(
        name = "update",
        description = "Update DragonLog channels"
        )
    @app_commands.guilds(config.getint("Main", "support_guild_id"))
    @commands.is_owner()
    async def slash_DragonLog_update(self, interaction: discord.Interaction, guild_id: str = None) -> None:
        # defer here to avoid timeout
        await interaction.response.defer(ephemeral=True)

        if guild_id:
            guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
        else:
            guild = None

        await self.update_DragonLog(guild=guild)
        await interaction.followup.send("Updated DragonLog channels on all servers!")


    async def update_DragonLog(self, guild: discord.Guild = None) -> None:
        self.logger.debug(f"Updating DragonLog for {guild=}")
        if guild is None:
            with Session(engine) as session:
                result = session.query(Channel.guild_id).where(Channel.type == LOGS).distinct().group_by(Channel.guild_id)
                guild_ids = result.all()
            for guild_id in guild_ids[0]:
                guild = discord.utils.get(self.bot.guilds, id=guild_id)
                await self.update_DragonLog(guild=guild)

        with Session(engine) as session:
            result = session.query(Channel).where(
                Channel.type == LOGS,
                Channel.guild_id == guild.id
            )
            channels = result.all()
            category = session.query(Channel).where(
                Channel.name == LOG_CATEGORY,
                Channel.type == LOGS,
                Channel.guild_id == guild.id
            ).first()

        category_channel = discord.utils.get(guild.categories, id=category.id)
        difference = []
        known_names = [channel.name.lower() for channel in channels]

        difference.extend(
            j for j in [i.value.lower() for i in LogCategories]
            if j not in known_names
            )
        self.logger.debug(f"{channels=}, {known_names=}, {difference=}")
        with Session(engine) as session:
            for channel_diff in difference:
                new_log_channel = await category_channel.create_text_channel(channel_diff, reason="DragonLog update")
                self.logger.info(f"Updated DragonLog for {guild=} with {new_log_channel=}")
                session.add(Channel(
                    id = new_log_channel.id,
                    name = channel_diff,
                    type = LOGS,
                    guild_id = category_channel.guild.id,
                ))
            session.commit()


# COMMANDS END

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DragonLog(bot))
