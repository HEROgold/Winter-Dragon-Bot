import itertools
import pickle
import logging
import os
import re
from enum import Enum
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from tools import dragon_database

class LogCategories(Enum):
    GLOBAL:str = "ALL-CATEGORIES"
    CREATEDCHANNELS:str = "CREATEDCHANNELS"
    UPDATEDCHANNELS:str = "UPDATEDCHANNELS"
    DELETEDCHANNELS:str = "DELETEDCHANNELS"
    CREATEDINVITES:str = "CREATEDINVITES"
    MEMBERUPDATES:str = "MEMBERUPDATES"
    MEMBERMOVED:str = "MEMBERMOVED"
    MEMBERJOINED:str = "MEMBERJOINED"
    MEMBERLEFT:str = "MEMBERLEFT"
    EDITEDMESSAGES:str = "EDITEDMESSAGES"
    DELETEDMESSAGES:str = "DELETEDMESSAGES"
    CREATEDROLES:str = "CREATEDROLES"
    UPDATEDROLES:str = "UPDATEDROLES"
    DELETEDROLE:str = "DELETEDROLES"


class DragonLog(commands.GroupCog):
    data: dict
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.data = {}
        self.DATABASE_NAME = self.__class__.__name__
        self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = self.get_data()
        if not self.data:
            self.data = {}

    async def cog_unload(self) -> None:
        self.set_data(self.data)

    def check_guild_data(self, guild:str|discord.Guild) -> None:
        if guild == discord.Guild:
            guild = str(guild.id)
        try:
            self.data[guild]
        except KeyError:
            self.data[guild] = {}

    def check_disabled(self, guild:discord.Guild, category:LogCategories) -> bool:
        try:
            self.data[str(guild.id)]["disabled"][category]
            return True
        except KeyError:
            return False

    async def get_dragon_log_channels(self, log_category:Optional[LogCategories], guild:discord.Guild) -> tuple[discord.TextChannel, discord.TextChannel]:
        if not guild:
            self.logger.debug("No guild during DragonLog channel fetching")
            return None, None
        guild_id = str(guild.id)
        if log_channel := log_category.value:
            log_channel:str
            self.logger.debug(f"{log_channel}, {log_category}")
            mod_channel:discord.TextChannel = discord.utils.get(
                guild.channels,
                id=int(
                    self.data[guild_id][category_channel_id][log_channel.lower()]
                )
            ) or None
        try:
            for category_channel_id in self.data[guild_id]:
                category_channel_id = str(category_channel_id)
                global_log_channel_id = self.data[guild_id][category_channel_id][LogCategories.GLOBAL.value.lower()]
                global_log_channel:discord.TextChannel = discord.utils.get(
                    guild.channels, id=int(global_log_channel_id)
                ) or None
            self.logger.debug("Returning named and global log channels")
            return mod_channel, global_log_channel
        except (KeyError, TypeError):
            self.logger.debug(f"Guild has no automod category: {guild}")

    def get_role_difference(self, entry:discord.AuditLogEntry) -> list[discord.Role]:
        diffs = []
        for change1, change2 in zip(entry.changes.before, entry.changes.after):
            diff = [c1 or c2 for c1, c2 in itertools.zip_longest(change1[1], change2[1])]
            for role in diff:
                role = discord.utils.get(entry.guild.roles, id=role.id)
                diffs.append(role.mention)
        return diffs

    def get_member_left_embed(self, member:discord.Member, entry:discord.AuditLogEntry) -> discord.Embed:
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
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_audit_log_entry_create(self, entry:discord.AuditLogEntry) -> None:
        action = discord.AuditLogAction
        # self.logger.debug(f"Action: {action}, Target:{entry.target} Dict: {entry.__dict__}")
        # await self.generic_change(entry)
        match entry.action:
            case action.channel_create:
                await self.on_guild_channel_create(entry)
            case action.channel_delete:
                await self.on_guild_channel_delete(entry)
            case action.channel_update:
                await self.on_guild_channel_update(entry)
            case action.invite_create:
                await self.on_invite_create(entry)
            case action.member_update:
                await self.on_member_update(entry, False)
            case action.member_role_update:
                await self.on_member_update(entry, True)
            case action.member_move:
                await self.on_member_move(entry)
            case action.role_create:
                await self.on_role_create(entry)
            case action.role_update:
                await self.on_role_update(entry)
            case action.role_delete:
                await self.on_role_delete(entry)
            case _:
                await self.generic_change(entry)

    async def on_guild_channel_create(self, entry:discord.AuditLogEntry) -> None:
        self.logger.debug(f"On channel create: guild='{entry.guild}' channel='{entry.target}'")
        self.check_disabled(entry.guild, LogCategories.CREATEDCHANNELS)
        channel = entry.target
        embed = discord.Embed(
            title="Channel Created",
            description=f"{entry.user.mention} created {channel.type} {channel.mention or entry.target.mention} with reason: {entry.reason or None}",
            color=0x00FF00
            )
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.CREATEDCHANNELS, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_guild_channel_update(self, entry:discord.AuditLogEntry) -> None:
        self.check_disabled(entry.guild, LogCategories.UPDATEDCHANNELS)
        before:discord.abc.GuildChannel = entry.before
        after:discord.abc.GuildChannel = entry.after
        channel = after or before
        self.logger.debug(f"On channel update: guild='{entry.guild}' channel='{channel}'")
        embed = None
        properts = "overwrites", "category", "permissions_synced", "name", "position", "type"
        if differences := [prop for prop in properts if getattr(before, prop) != getattr(after, prop)]:
            if "name" in differences or before.name != after.name:
                name_change = f"`{before.name}` to `{after.name}` for {after.mention}"
            embed = discord.Embed(
                title="Channel Changed",
                description=f"{entry.user.mention} changed {differences} of channel {name_change or after.mention} with reason: {entry.reason or None}",
                color=0xFFFF00
                )
        if not embed:
            return
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.UPDATEDCHANNELS, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_guild_channel_delete(self, entry:discord.AuditLogEntry) -> None:
        self.check_disabled(entry.guild, LogCategories.DELETEDCHANNELS)
        channel: discord.abc.GuildChannel = entry.before
        self.logger.debug(f"On channel delete: guild='{entry.guild}' channel='{channel}'")
        embed = None
        embed = discord.Embed(
            title="Channel Deleted",
            description=f"{entry.user.mention} deleted {channel.type} `{channel.name}` with reason: {entry.reason or None}",
            color=0xff0000
            )
        if not embed:
            return
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.DELETEDCHANNELS, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    # TODO: print invite code, bug? entry.target is not invite
    # on_invite_create as event does seem to work.
    async def on_invite_create(self, entry:discord.AuditLogEntry) -> None:
        self.check_disabled(entry.guild, LogCategories.CREATEDINVITES)
        invite:discord.Invite = entry.target
        self.logger.debug(f"On invite create: guild='{entry.guild}' invite='{invite}'")
        embed = None
        embed = discord.Embed(
            title="Created Invite",
            description=f"{entry.user} Created invite {entry.target or invite} with reason: {entry.reason or None}",
            color=0x00ff00
            )
        if not embed:
            return
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.CREATEDINVITES, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_member_update(self, entry:discord.AuditLogEntry, is_role:bool) -> None:
        self.check_disabled(entry.guild, LogCategories.MEMBERUPDATES)
        before:discord.Member = entry.before
        after:discord.Member = entry.after
        self.logger.debug(f"On member update: guild='{entry.guild}', member='{after}'")
        diffs = self.get_role_difference(entry) if is_role else ""
        embed = None
        properts = "nick", "roles", "pending", "guild_avatar", "guild_permissions"
        if differences := [prop for prop in properts if getattr(before, prop) != getattr(after, prop)]:
            embed = discord.Embed(
                title="Member Update", description=f"{entry.user.mention} Changed {differences} {diffs} of {before.mention} with reason: {entry.reason or None}",
                color=0xFFFF00
                )
        if not embed:
            return
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.MEMBERUPDATES, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_member_move(self, entry:discord.AuditLogEntry) -> None:
        self.check_disabled(entry.guild, LogCategories.MEMBERMOVED)
        embed = discord.Embed(
            title="Member Joined",
            description=f"{entry.user.mention} Moved {entry.target.mention} to {entry.target.channel}",
            color=0x00FF00
            )
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.MEMBERMOVED, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_member_join(self, member:discord.Member) -> None:
        self.check_disabled(member.guild, LogCategories.MEMBERJOINED)
        self.logger.debug(f"On member join: guild='{member.guild}' member='{member}'")
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} Joined the server",
            color=0x00FF00
            )
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.MEMBERJOINED, member.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_member_remove(self, member:discord.Member) -> None:
        self.check_disabled(member.guild, LogCategories.MEMBERLEFT)
        self.logger.debug(f"On member remove: guild='{member.guild}' member='{member}'")
        embed=None
        async for entry in member.guild.audit_logs(limit=1):
            embed = self.get_member_left_embed(member, entry)
        if not embed:
            raise TypeError(f"Expected discord.Embed, got {embed}")
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.MEMBERLEFT, member.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    # TODO: Needs to look cleaner, also doesnt always get type. IE on invite remove
    async def generic_change(self, entry:discord.AuditLogEntry) -> None:
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
        # self.logger.debug(f"Triggered generic_change:\nENTRY: {entry}\nENTRY CHANGES: {entry.changes}\n")
        embed.add_field(name="Old", value="\u200b", inline=True)
        embed.add_field(name="New", value="\u200b", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        for change1, change2 in zip(entry.changes.before, entry.changes.after):
            embed.add_field(name=change1[0], value=change1[1], inline=True)
            embed.add_field(name=change2[0], value=change2[1], inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False)
        try:
            _, allmod_channel = await self.get_dragon_log_channels(None, entry.guild)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_role_create(self, entry:discord.AuditLogEntry) -> None:
        self.check_disabled(entry.guild, LogCategories.CREATEDROLES)
        self.logger.debug(f"On role create: guild='{entry.guild}' channel='{entry.target}'")
        role:discord.Role = entry.target
        embed = discord.Embed(
            title="Role Created",
            description=f"{entry.user.mention} created {role.mention or entry.target.mention} with permissions {role.permissions} with reason: {entry.reason or None}",
            color=0x00FF00
            )
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.CREATEDROLES, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_role_update(self, entry:discord.AuditLogEntry) -> None:
        self.check_disabled(entry.guild, LogCategories.UPDATEDROLES)
        self.logger.debug(f"On role update: guild='{entry.guild}', role='{entry.target}'")
        role:discord.Role = entry.target
        
        embed = discord.Embed(
            title="Role Updated",
            description=f"{entry.user.mention} created {role.mention or entry.target.mention} with reason: {entry.reason or None}",
            color=0xFFFF00
            )
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.UPDATEDROLES, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    async def on_role_delete(self, entry:discord.AuditLogEntry) -> None:
        self.check_disabled(entry.guild, LogCategories.DELETEDROLE)
        self.logger.debug(f"On role delete: guild='{entry.guild}', role='{entry.target}'")
        role:discord.Role = entry.target
        embed = discord.Embed(
            title="Role Removed",
            description=f"{entry.user.mention} created {role or entry.target} with reason: {entry.reason or None}",
            color=0xFF0000
            )
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.DELETEDROLE, entry.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before:discord.Message, after:discord.Message) -> None:
        self.check_disabled(after.guild, LogCategories.EDITEDMESSAGES)
        ttt_regex = r"(?:\|  (?:_|o|x)  )+\|\n\|(?:(?:_____)+(?:\+|))+(?:\|\n|\|)" # NOSONAR
        reg_found = re.findall(ttt_regex, before.clean_content)
        if reg_found != []:
            self.logger.debug(f"Message edited but is Tic-Tac-Toe: guild={before.guild}, channel={before.channel}, content=`{before.clean_content}`, found=`{reg_found}`")
            return
        if before.clean_content is None:
            self.logger.debug(f"Empty content on Before=`{before}")
            return
        if before.clean_content == after.clean_content:
            return
        self.logger.debug(f"Message edited: guild={before.guild}, channel={before.channel}, content=`{before.clean_content}`, changed=`{after.clean_content}`")
        embed = discord.Embed(
            title="Message Edited",
            description=f"{before.author.mention} Edited a message",
            color=0xFFFF00
        )
        embed.add_field(name="Old", value=f"`{before.clean_content}`")
        embed.add_field(name="New", value=f"`{after.clean_content}`")
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.EDITEDMESSAGES, before.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass

    # FIXME/TODO: doesn`t post on purge
    @commands.Cog.listener()
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_message_delete(self, message:discord.Message) -> None:
        self.check_disabled(message.guild, LogCategories.DELETEDMESSAGES)
        self.logger.debug(f"Message deleted: guild='{message.guild}', channel='{message.channel}', content='{message.clean_content}'")
        async for entry in message.guild.audit_logs(limit=1):
            if message.clean_content == "":
                return
            embed = discord.Embed(
                title="Message Deleted",
                description=f"{entry.user.mention} Deleted message `{message.clean_content}`, send by {message.author.mention} with reason {entry.reason or None}",
                color=0xFF0000
            )
        try:
            dragon_log_channel, allmod_channel = await self.get_dragon_log_channels(LogCategories.DELETEDMESSAGES, message.guild)
            await dragon_log_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)
        except TypeError:
            pass
            # Idk, maybe not needed tbh
            # if entry.action == entry.action.message_delete:
            #     # 99% other persons message
            #     pass
            # elif entry.action == entry.action.message_bulk_delete:
            #     # figure out what to send here
            #     self.logger.debug(entry)
            # else:
            #     # likely removed own message
            #     self.logger.debug(entry)

# ENTRIES END
# COMMANDS START

    @app_commands.command(
        name = "add",
        description = "Enables automatic moderation/logging for this server, and creates a channel for all logs."
        )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.cooldown(1, 100)
    async def slash_DragonLog_add(self, interaction:discord.Interaction) -> None:
        # defer here to avoid getting timeout
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none())
        }
        guild_id = str(guild.id)
        try:
            if self.data[guild_id]:
                await interaction.followup.send("DragonLog channels are already set up.")
                return
        except KeyError as e:
            self.logger.error(e)
        category_channel = await guild.create_category(name="Dragon DragonLog", overwrites=overwrites, position=99, reason="Adding DragonLog channels")
        category_channel_id = str(category_channel.id)
        self.data[guild_id] = {category_channel_id: {}}
        for log_category in LogCategories:
            log_category:str = log_category.value
            text_channel = await category_channel.create_text_channel(name=f"{log_category.lower()}", reason="Adding DragonLog channels")
            self.data[guild_id][category_channel_id][text_channel.name] = text_channel.id
        await interaction.followup.send("Set up DragonLog category and channels")
        self.logger.info(f"Setup DragonLog for {interaction.guild}")
        self.set_data(self.data)

    @app_commands.command(
        name = "remove",
        description = "Disables automatic moderation for this server, and removes the log channels.",
        )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.cooldown(1, 100)
    async def slash_DragonLog_remove(self, interaction:discord.Interaction) -> None:
        # Defer here to avoid timeout
        await interaction.response.defer(ephemeral=True)
        if not self.data:
            self.data = self.get_data()
        guild = interaction.guild
        try:
            for category_channel_id, channels in self.data[str(guild.id)].items():
                channels:dict
                try:
                    for channel_name, channel_id in channels.items():
                        text_channel:discord.TextChannel = discord.utils.get(guild.text_channels, id=channel_id)
                        await text_channel.delete()
                        del channel_name
                except AttributeError:
                    continue
                category_channel:discord.CategoryChannel = discord.utils.get(guild.categories, id=int(category_channel_id))
                await category_channel.delete()
                del category_channel_id
        except KeyError:
            await interaction.followup.send("Can't find DragonLogChannels Consider using </DragonLog add:1067239606044606585>")
        del self.data[str(guild.id)]
        self.set_data(self.data)
        await interaction.followup.send("Removed and disabled DragonLogChannels")
        self.logger.info(f"Removed DragonLog for {interaction.guild}")

    @app_commands.command(
        name = "update",
        description = "Update DragonLog channels"
        )
    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    async def slash_DragonLog_update(self, interaction:discord.Interaction, guild_id:str=None) -> None:
        # defer here to avoid timeout
        await interaction.response.defer(ephemeral=True)
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        if not self.data:
            self.data = self.get_data()
        if guild_id:
            guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
        else:
            guild = None
        await self.update_DragonLog(guild=guild)
        await interaction.followup.send("Updated DragonLog channels on all servers!")

    async def update_DragonLog(self, guild:discord.Guild=None) -> None:
        self.logger.debug(f"Updating DragonLog for guild=`{guild}`")
        if not guild:
            for guild_id in self.data: # type: ignore
                guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
                await self.update_DragonLog(guild=guild)
        difference = []
        try:
            disabled = self.data[str(guild.id)]["disabled"]
        except KeyError:
            disabled = []
        guild_data = self.data[str(guild.id)]
        guild_data: dict
        for category_id, channels in guild_data.items():
            try:
                category_id = int(category_id)
            except ValueError:
                continue
            category_obj = discord.utils.get(guild.categories, id=category_id)
            difference.extend(
                channel for channel in [i.value.lower() for i in LogCategories]
                if channel not in disabled
                if channel not in channels.keys()
                )
        for channel_name in difference:
            channel_name:str
            new_log_channel = await category_obj.create_text_channel(channel_name, reason="DragonLog update")
            self.data[str(guild.id)][str(category_id)][channel_name] = new_log_channel.id
        self.logger.info(f"Updated DragonLog for guild=`{guild}`")
        self.set_data(self.data)

# TODO: autocomplete doesnt work with enum.value.lower

    # Split enabled and disabled into 2 functions.
    # def get_enabled_disabled(self, guild_id) -> tuple[list, list]:
    #     try:
    #         enabled = self.data[guild_id]["enabled"]
    #     except KeyError:
    #         self.data[guild_id]["enabled"] = []
    #         disabled = self.data[guild_id]["enabled"]
    #     try:
    #         disabled = self.data[guild_id]["disabled"]
    #     except KeyError:
    #         self.data[guild_id]["disabled"] = []
    #         disabled = self.data[guild_id]["disabled"]
    #     return enabled, disabled

    # @app_commands.command(
    #     name = "enable",
    #     description = "Enables automatic moderation for a specific category.",
    #     )
    # @app_commands.guild_only()
    # @app_commands.checks.has_permissions(administrator=True)
    # @app_commands.checks.bot_has_permissions(manage_channels=True)
    # async def slash_DragonLog_enable(self, interaction:discord.Interaction, category:str) -> None:
    #     guild_id = str(interaction.guild.id)
    #     self.check_guild_data(guild_id)
    #     enabled, disabled = self.get_enabled_disabled(guild_id)
    #     if category not in enabled:
    #         enabled.append(category)
    #         await self.update_DragonLog(guild=interaction.guild)
    #         await interaction.response.send_message(f"Enabled {category}", ephemeral=True)
    #     elif category == "All-categories":
    #         await interaction.response.send_message("Cannot change All-categories", ephemeral=True)
    #     else:
    #         await interaction.response.send_message(f"{category} is already enabled", ephemeral=True)
    #     if category in disabled:
    #         disabled.pop(category)
    #     self.set_data(self.data)

    # @slash_DragonLog_enable.autocomplete("category")
    # async def enable_autocomplete_category(self, interaction:discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
    #     return [
    #         app_commands.Choice(name=i, value=i)
    #         for i in LogCategories
    #         if current.lower() in i.value.lower()
    #     ]

    # @app_commands.command(
    #     name = "disable",
    #     description = "Disables automatic moderation for a specific category.",
    #     )
    # @app_commands.guild_only()
    # @app_commands.checks.has_permissions(administrator=True)
    # @app_commands.checks.bot_has_permissions(manage_channels=True)
    # async def slash_DragonLog_disable(self, interaction:discord.Interaction, category:str) -> None:
    #     guild_id = str(interaction.guild.id)
    #     self.check_guild_data(guild_id)
    #     enabled, disabled = self.get_enabled_disabled(guild_id)
    #     if category not in disabled:
    #         disabled.append(category)
    #         await interaction.response.send_message(f"Disabled {category}", ephemeral=True)
    #     elif category == "All-categories":
    #         await interaction.response.send_message("Cannot change All-categories", ephemeral=True)
    #     else:
    #         await interaction.response.send_message(f"{category} is already disabled", ephemeral=True)
    #     if category in enabled:
    #         enabled.pop(category)
    #     self.set_data(self.data)

    # @slash_DragonLog_disable.autocomplete("category")
    # async def disable_autocomplete_category(self, interaction:discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
    #     return [
    #         app_commands.Choice(name=i, value=i)
    #         for i in LogCategories
    #         if current.lower() in i.value.lower()
    #     ]

# COMMANDS END

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(DragonLog(bot))
