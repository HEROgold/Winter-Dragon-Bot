import contextlib
import itertools
import json
import logging
import os
import re

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database


class Automod(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.data = {
            "DUMMY_GUILD_ID":{
                "DUMMY_CATEGORY_ID":{
                    "DUMMY_CHANNEL_NAME": 0
                }
            }
        }
        self.DATABASE_NAME = self.__class__.__name__
        self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")
        self.AutomodCategories = [
            "All-categories",
            "CreatedChannels",
            "UpdatedChannels",
            "DeletedChannels",
            "CreatedInvites",
            "MemberUpdates",
            "MemberJoined",
            "MemberLeft",
            "MessageEdited",
            "MessageDeleted"
        ]
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
            self.setup_json()

    def setup_json(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = self.data
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME} Json Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.data:
            self.data = await self.get_data()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    async def get_automod_channels(self, mod_channel:str, guild:discord.Guild) -> tuple[discord.TextChannel, discord.TextChannel]:
        if not self.data:
            self.data = await self.get_data()
        if not guild:
            self.logger.debug("No guild during fetch: Likely caused by sending embed in user DM's")
            return None, None
        guild_id = str(guild.id)
        automod_channel = None
        allmod_channel = None
        with contextlib.suppress(KeyError, TypeError):
            for category_channel_id in self.data[guild_id]:
                category_channel_id = str(category_channel_id)
                automod_channel_id = self.data[guild_id][category_channel_id][mod_channel.lower()]
                allmod_channel_id = self.data[guild_id][category_channel_id]["all-categories"]
                automod_channel:discord.TextChannel = discord.utils.get(guild.channels, id=int(automod_channel_id))
                allmod_channel:discord.TextChannel = discord.utils.get(guild.channels, id=int(allmod_channel_id))
            return (automod_channel, allmod_channel)

    @commands.Cog.listener()
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_guild_channel_create(self, channel:discord.abc.GuildChannel) -> None:
        self.logger.debug(f"On channel create: guild='{channel.guild}' channel='{channel}'")
        async for entry in channel.guild.audit_logs(limit=1):
            if entry.action == discord.AuditLogAction.channel_create:
                embed = discord.Embed(
                    title="Channel Created",
                    description=f"{entry.user.mention} created {channel.type} {entry.target.mention or channel.mention} with reason: {entry.reason or None}",
                    color=0x00FF00
                    )
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("CreatedChannels", channel.guild)
            await automod_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_guild_channel_update(self, before:discord.abc.GuildChannel, after:discord.abc.GuildChannel) -> None:
        channel = after or before
        self.logger.debug(f"On channel update: guild='{channel.guild}' channel='{channel}'")
        embed = None
        async for entry in channel.guild.audit_logs(limit=1):
            if entry.action == discord.AuditLogAction.channel_update:
                properts = "overwrites", "category", "permissions_synced", "name", "position", "type"
                if differences := [prop for prop in properts if getattr(before, prop) != getattr(after, prop)]:
                    if "name" in differences or before.name != after.name:
                        name_change = f"`{before.name}` to `{after.name}`"
                    embed = discord.Embed(
                        title="Channel Changed",
                        description=f"{entry.user.mention} changed {differences} of channel {name_change or after.mention} with reason: {entry.reason or None}",
                        color=0xFFFF00
                        )
        if not embed:
            return
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("updatedchannels", channel.guild)
            await automod_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_guild_channel_delete(self, channel:discord.abc.GuildChannel) -> None:
        self.logger.debug(f"On channel delete: guild='{channel.guild}' channel='{channel}'")
        embed = None
        async for entry in channel.guild.audit_logs(limit=1):
            if entry.action == discord.AuditLogAction.channel_delete:
                embed = discord.Embed(
                    title="Channel Deleted",
                    description=f"{entry.user.mention} deleted {channel.type} {channel.name} with reason: {entry.reason or None}",
                    color=0xff0000
                    )
        if not embed:
            return
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("DeletedChannels", channel.guild)
            await automod_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_invite_create(self, invite:discord.Invite) -> None:
        self.logger.debug(f"On invite create: guild='{invite.guild}' invite='{invite}'")
        embed = None
        async for entry in invite.guild.audit_logs(limit=1):
            if entry.action == discord.AuditLogAction.invite_create:
                embed = discord.Embed(
                    title="Created Invite",
                    description=f"{entry.user} Created invite {entry.target or invite} with reason: {entry.reason or None}",
                    color=0x00ff00
                    )
        if not embed:
            return
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("CreatedInvites", invite.guild)
            await automod_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_member_update(self, before:discord.Member, after:discord.Member) -> None:
        member = before or after
        self.logger.debug(f"On member update: guild='{member.guild}', member='{member}'")
        embed = None
        async for entry in member.guild.audit_logs(limit=1):
            if entry.action == discord.AuditLogAction.member_role_update:
                diffs = self.get_role_difference(entry)
            else:
                diffs = ""
            if entry.action in [discord.AuditLogAction.member_update, discord.AuditLogAction.member_role_update]:
                properts = "nick", "roles", "pending", "guild_avatar", "guild_permissions"
                if differences := [prop for prop in properts if getattr(before, prop) != getattr(after, prop)]:
                    embed = discord.Embed(
                        title="Member Update", description=f"{entry.user.mention} Changed {differences} {diffs} of {before.mention} with reason: {entry.reason or None}",
                        color=0xFFFF00
                        )
        if not embed:
            return
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("memberupdates", after.guild)
            await automod_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member) -> None:
        self.logger.debug(f"On member join: guild='{member.guild}' member='{member}'")
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("MemberJoined", member.guild)
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} Joined the server",
            color=0x00FF00
            )
        await automod_channel.send(embed=embed)
        await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_member_remove(self, member:discord.Member) -> None:
        self.logger.debug(f"On member remove: guild='{member.guild}' member='{member}'")
        embed=None
        async for entry in member.guild.audit_logs(limit=1):
            embed = self.get_member_left_embed(member, entry)
        if not embed:
            raise TypeError(f"Expected discord.Embed, got {embed}")
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("memberleft", member.guild)
            await automod_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)

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

    def get_role_difference(self, entry:discord.AuditLogEntry) -> list[discord.Role]:
        diffs = []
        for change1, change2 in zip(entry.changes.before, entry.changes.after):
            diff = [c1 or c2 for c1, c2 in itertools.zip_longest(change1[1], change2[1])]
            for role in diff:
                role = discord.utils.get(entry.guild.roles, id=role.id)
                diffs.append(role.mention)
        return diffs

    # TODO: Filter out Tic-tac-toe
    @commands.Cog.listener()
    async def on_message_edit(self, before:discord.Message, after:discord.Message) -> None:
        ttt_regex = r"(?:\|  (?:_|o|x)  )+\|\n\|(?:(?:_____)+(?:\+|))+(?:\|\n|\|)"
        reg_found = re.findall(ttt_regex, before.clean_content)
        if reg_found != []:
            self.logger.debug(f"Message edited but is Tic-Tac-Toe: guild={before.guild}, channel={before.channel}, content=`{before.clean_content}`, found=`{reg_found}`")
            return
        if before.clean_content() is None:
            self.logger.debug(f"Empty content on Before=`{before}")
            return
        self.logger.debug(f"Message edited: guild={before.guild}, channel={before.channel}, content=`{before.clean_content}`, changed=`{after.clean_content}`")
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("MessageEdited", before.guild)
        embed = discord.Embed(
            title="Message Edited",
            description=f"{before.author.mention} Edited a message",
            color=0xFFFF00
        )
        embed.add_field(name="Old", value=f"`{before.clean_content}`")
        embed.add_field(name="New", value=f"`{after.clean_content}`")
        if automod_channel is None or allmod_channel is None:
            return
        await automod_channel.send(embed=embed)
        await allmod_channel.send(embed=embed)

    # FIXME/TODO: doesn`t post on purge
    @commands.Cog.listener()
    @app_commands.checks.bot_has_permissions(view_audit_log=True)
    async def on_message_delete(self, message:discord.Message) -> None:
        self.logger.debug(f"Message deleted: guild='{message.guild}', channel='{message.channel}', content='{message.clean_content}'")
        with contextlib.suppress(TypeError):
            automod_channel, allmod_channel = await self.get_automod_channels("MessageDeleted", message.guild)
        async for entry in message.guild.audit_logs(limit=1):
                embed = discord.Embed(
                    title="Message Deleted",
                    description=f"{entry.user.mention} Deleted message `{message.clean_content}`, send by {message.author.mention} with reason {entry.reason or None}",
                    color=0xFF0000
                )
                await automod_channel.send(embed=embed)
                await allmod_channel.send(embed=embed)
                # Idk, maybe not needed tbh
                if entry.action == entry.action.message_delete:
                    # 99% other persons message
                    pass
                elif entry.action == entry.action.message_bulk_delete:
                    # figure out what to send here
                    self.logger.debug(entry)
                else:
                    # likely removed own message
                    self.logger.debug(entry)

    @app_commands.command(
        name = "add",
        description = "Enables automatic moderation/logging for this server, and creates a channel for all logs."
        )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator = True)
    @app_commands.checks.bot_has_permissions(manage_channels = True)
    @app_commands.checks.cooldown(1, 100)
    async def slash_automod_add(self, interaction:discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none())
        }
        if not self.data:
            self.data = await self.get_data()
        try:
            if self.data[str(guild.id)]:
                await interaction.followup.send("Automod channels are already set up.")
                return
        except KeyError as e:
            self.logger.exception(e)
        AutomodCategories = self.AutomodCategories
        CategoryChannel = await guild.create_category(name="Dragon Automod", overwrites=overwrites, position=99)
        self.data[guild.id] = {CategoryChannel.id: {}}
        for AutomodCategory in AutomodCategories:
            TextChannel = await CategoryChannel.create_text_channel(name=f"{AutomodCategory}")
            self.data[guild.id][CategoryChannel.id][TextChannel.name] = TextChannel.id
        await interaction.followup.send("Set up automod category and channels")
        self.logger.info(f"Setup automod for {interaction.guild}")
        await self.set_data(self.data)

    @app_commands.command(
        name = "remove",
        description = "Disables automatic moderation for this server, and removes the log channels.",
        )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator = True)
    @app_commands.checks.bot_has_permissions(manage_channels = True)
    @app_commands.checks.cooldown(1, 100)
    async def slash_automod_remove(self, interaction:discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if not self.data:
            self.data = await self.get_data()
        guild = interaction.guild
        for CatChannelId, Channels in self.data[str(guild.id)].items():
            for ChannelName, ChannelId in Channels.items():
                TextChannel:discord.TextChannel = discord.utils.get(guild.text_channels, id=ChannelId)
                await TextChannel.delete()
                del ChannelName
            CategoryChannel:discord.CategoryChannel = discord.utils.get(guild.categories, id=int(CatChannelId))
            await CategoryChannel.delete()
            del CatChannelId
        del self.data[str(guild.id)]
        await self.set_data(self.data)
        await interaction.followup.send("Removed and disabled AutomodChannels")
        self.logger.info(f"Removed automod for {interaction.guild}")

    @app_commands.command(
        name = "update",
        description = "Update automod channels"
        )
    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    async def slash_automod_update(self, interaction:discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        if not self.data:
            self.data = await self.get_data()
        categories = [i.lower() for i in self.AutomodCategories]
        try:
            await self.update_automod(categories)
        except Exception as e:
            await interaction.followup.send(e, ephemeral=True)
            self.logger.exception(e)
        await interaction.followup.send("Updated automod channels on all servers!")
        await self.set_data(self.data)

    async def update_automod(self, categories) -> None:
        for guild_id, v in self.data.items():
            guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
            difference = []
            for category_id, channels in v.items():
                category_obj = discord.utils.get(guild.categories, id=int(category_id))
                difference.extend(channel for channel in categories if channel not in channels.keys())
            for channel_name in difference:
                channel_name:str
                new_log_channel = await category_obj.create_text_channel(channel_name, reason="Automod update")
                self.data[guild_id][category_id][channel_name] = new_log_channel.id
            self.logger.info(f"Updated automod for guild=`{guild}`")

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Automod(bot))
