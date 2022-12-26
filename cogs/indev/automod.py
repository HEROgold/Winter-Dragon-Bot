import contextlib
import itertools
import logging
import discord
import os
import json
from discord.ext import commands
from discord import app_commands


class AutoMod(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.DBLocation = "./Database/Automod.json"
        self.AutomodCategories = [
            "All-categories",
            "CreatedChannels",
            "UpdatedChannels",
            "DeletedChannels",
            "CreatedInvites",
            "MemberUpdates",
            "NewMemberJoined"
        ]
        # Create database if it doesn't exist, else load it
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                logging.info("Automod Json Created.")
        else:
            logging.info("Automod Json Loaded.")

    # Helper functions to laod and update database
    async def get_data(self) -> dict[str,dict[str,dict[str,int]]]:
        with open(self.DBLocation, 'r') as f:
            data = json.load(f)
        return data

    async def set_data(self, data:dict):
        with open(self.DBLocation,'w') as f:
            json.dump(data, f)

    # Helper function for getting (auto)mod channels
    async def get_automod_channels(self, mod_channel:str, guild:discord.Guild) -> tuple[discord.TextChannel, discord.TextChannel]:
        data = await self.get_data()
        guild_id = str(guild.id)
        # Convert to string for json/dict syntax
        # For loop keyerror
        automod_channel = None
        allmod_channel = None
        with contextlib.suppress(KeyError, TypeError):
            for category_channel_id in data[guild_id]:
                category_channel_id = str(category_channel_id)
                # Get channels to send the messages in
                automod_channel_id = data[guild_id][category_channel_id][mod_channel]
                allmod_channel_id = data[guild_id][category_channel_id]["all-categories"]
                automod_channel:discord.TextChannel = discord.utils.get(guild.channels, id=int(automod_channel_id))
                allmod_channel:discord.TextChannel = discord.utils.get(guild.channels, id=int(allmod_channel_id))
            return (automod_channel, allmod_channel)

    # functions to help create channels
    async def CreateCategoryChannel(self, guild:discord.Guild, overwrites, ChannelName:str, position:int=2) -> discord.CategoryChannel:
        return await guild.create_category(name=ChannelName, overwrites=overwrites, position=position)

    async def CreateTextChannel(self, guild:discord.Guild, CategoryChannel:discord.CategoryChannel, ChannelName:str) -> discord.TextChannel:
        # sourcery skip: assign-if-exp, inline-immediately-returned-variable, lift-return-into-if, swap-if-expression
        if not CategoryChannel:
            return await guild.create_text_channel(name = ChannelName)
        else:
            return await CategoryChannel.create_text_channel(name = ChannelName)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel:discord.abc.GuildChannel):
        async for entry in channel.guild.audit_logs(limit=1):
            if entry.action is discord.AuditLogAction.channel_create:
                embed = discord.Embed(title="Channel Created", description=f"{entry.user.mention} created {channel.type} {entry.target.mention or channel.mention}", color=0x00FF00)
        automod_channel, allmod_channel = await self.get_automod_channels("createdchannels", channel.guild)
        await automod_channel.send(embed=embed)
        await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before:discord.abc.GuildChannel, after:discord.abc.GuildChannel):
        channel = after or before
        async for entry in channel.guild.audit_logs(limit=1):
            if entry.action is discord.AuditLogAction.channel_update:
                properts = "overwrites", "category", "permissions_synced", "name", "position", "type"
                if differences := [prop for prop in properts if getattr(before, prop) != getattr(after, prop)]:
                    embed = discord.Embed(title="Channel Changed", description=f"{entry.user.mention} changed {differences} of channel {after.mention}", color=0xFFFF00)
        with contextlib.suppress(Exception,):
            automod_channel, allmod_channel = await self.get_automod_channels("updatedchannels", channel.guild)
            await automod_channel.send(embed=embed)
            await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel:discord.abc.GuildChannel):
        async for entry in channel.guild.audit_logs(limit=1):
            if entry.action is discord.AuditLogAction.channel_delete:
                embed = discord.Embed(title="Channel Deleted", description=f"{entry.user.mention} deleted {channel.type} {channel.name}", color=0xff0000)
        automod_channel, allmod_channel = await self.get_automod_channels("deletedchannels", channel.guild)
        await automod_channel.send(embed=embed)
        await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite:discord.Invite):
        async for entry in invite.guild.audit_logs(limit=1):
            if entry.action is discord.AuditLogAction.invite_create:
                embed = discord.Embed(title="Created Invite", description=f"{entry.user} Created invite {entry.target or invite}", color=0x00ff00)
        automod_channel, allmod_channel = await self.get_automod_channels("createdinvites", invite.guild)
        await automod_channel.send(embed=embed)
        await allmod_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        user = before or after
        async for entry in user.guild.audit_logs(limit=1):
            if entry.action is discord.AuditLogAction.member_role_update:
                diffs = self.get_role_difference(entry)
            else:
                diffs = ""
            if entry.action in [discord.AuditLogAction.member_update, discord.AuditLogAction.member_role_update]:
                properts = "nick", "roles", "pending", "guild_avatar", "guild_permissions"
                if differences := [prop for prop in properts if getattr(before, prop) != getattr(after, prop)]:
                    embed = discord.Embed(title="Member Update", description=f"{entry.user.mention} Changed {differences} {diffs} of {before.mention}", color=0xFFFF00)
        automod_channel, allmod_channel = await self.get_automod_channels("memberupdates", after.guild)
        await automod_channel.send(embed=embed)
        await allmod_channel.send(embed=embed)

    def get_role_difference(self, entry:discord.AuditLogEntry) -> list[discord.Role]:
        diffs = []
        for change1, change2 in zip(entry.changes.before, entry.changes.after):
            diff = [c1 or c2 for c1, c2 in itertools.zip_longest(change1[1], change2[1])]
            for role in diff:
                role = discord.utils.get(entry.guild.roles, id=role.id)
                diffs.append(role.mention)
        return diffs

    @app_commands.command(name = "automod_update",
                    description = "Update automod channels")
    @commands.guild_only()
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def slash_automod_update(self, interaction:discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("You may not this command!")
            return
        await interaction.response.defer(ephemeral=True)
        data = await self.get_data()
        categories = [i.lower() for i in self.AutomodCategories]
        try:
            for guild_id, v in data.items():
                guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
                difference = []
                for category_id, channels in v.items():
                    category_obj = discord.utils.get(guild.categories, id=int(category_id))
                    difference.extend(channel for channel in categories if channel not in channels.keys())
                for channel_name in difference:
                    channel_name:str
                    new_log_channel = await self.CreateTextChannel(guild=guild, CategoryChannel=category_obj, ChannelName=channel_name)
                    data[guild_id][category_id][channel_name] = new_log_channel.id
        except Exception as e:
            await interaction.followup.send(e, ephemeral=True)
            logging.error(e)
        await interaction.followup.send("Updated automod channels on all servers!")
        await self.set_data(data)

    @app_commands.command(name = "automod_add",
                    description = "Enables automatic moderation for this server, and creates a channel for all logs.")
    @commands.guild_only()
    @commands.has_permissions(administrator = True)
    @commands.bot_has_permissions(manage_channels = True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def slash_automod_add(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.all())
        }
        data = await self.get_data()
        try:
            if data[str(guild.id)]:
                await interaction.followup.send("Automod channels are already set up.")
                return
        except KeyError as e:
            logging.info(e)
        AutomodCategories = self.AutomodCategories
        CategoryChannel = await self.CreateCategoryChannel(guild=guild, overwrites=overwrites, ChannelName="Dragon Automod", position=99)
        data[guild.id] = {CategoryChannel.id: {}}
        for AutomodCategory in AutomodCategories:
            TextChannel = await self.CreateTextChannel(guild=guild, CategoryChannel=CategoryChannel, ChannelName=f"{AutomodCategory}")
            data[guild.id][CategoryChannel.id][TextChannel.name] = TextChannel.id
        await interaction.followup.send("Set up automod category and channels")
        await self.set_data(data)

    @app_commands.command(
        name = "automod_remove",
        description = "Disables automatic moderation for this server, and removes the log channels.",
        )
    @commands.guild_only()
    @commands.has_permissions(administrator = True)
    @commands.bot_has_permissions(manage_channels = True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def slash_automod_remove(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = await self.get_data()
        guild = interaction.guild
        for CatChannelId, Channels in data[str(guild.id)].items():
            for ChannelName, ChannelId in Channels.items():
                TextChannel:discord.TextChannel = discord.utils.get(guild.text_channels, id=ChannelId)
                await TextChannel.delete()
                del ChannelName
            CategoryChannel:discord.CategoryChannel = discord.utils.get(guild.categories, id=int(CatChannelId))
            await CategoryChannel.delete()
            del CatChannelId
        del data[str(guild.id)]
        await self.set_data(data)
        await interaction.followup.send("Removed and disabled AutomodChannels")

async def setup(bot:commands.Bot):
    await bot.add_cog(AutoMod(bot))