import random

import discord
from discord import app_commands
from discord.ext import commands, tasks

from _types.bot import WinterDragon
from _types.cogs import Cog, GroupCog
from _types.enums import ChannelTypes
from extensions.server.log_channels import NoneTypeError
from tools import rainbow
from tools.config_reader import config
from tools.database_tables import Channel, Session, engine


STATS = ChannelTypes.STATS.name


def get_peak_count(channel: Channel | discord.abc.GuildChannel | None) -> int:
    try:
        return int(channel.name[13:])
    except ValueError:
        return 0


@app_commands.guild_only()
class Stats(GroupCog):
    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        member = before or after
        self.logger.debug(f"Member update: {member.guild=}, {member=}")
        guild = member.guild
        with Session(engine) as session:
            if peak_online := session.query(Channel).where(Channel.guild_id == guild.id, Channel.name == "peak_channel").first():
                await self.update_peak(guild, peak_online)


    async def update_peak(self, guild: discord.Guild, peak_online: Channel) -> None:
        peak_channel_id = peak_online.id
        peak_channel = discord.utils.get(guild.channels, id=peak_channel_id)

        peak_count = get_peak_count(peak_channel)
        online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
        if online > peak_count:
            await peak_channel.edit(name=f"Peak Online: {peak_count}", reason="Reached new peak of online members")
            self.logger.info(f"New peak online reached for {guild}!")


    async def create_stats_channels(
        self,
        guild: discord.Guild | None,
        reason: str | None = None,
    ) -> None:
        if guild is None:
            msg = "Expected discord.Guild"
            raise NoneTypeError(msg)

        overwrite = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            guild.me: discord.PermissionOverwrite(connect=True),
        }

        category = await guild.create_category(name=STATS, overwrites=overwrite, position=0)
        user_channel = await category.create_voice_channel(name="Total Users:", reason=reason)
        online_channel = await category.create_voice_channel(name="Online Users:", reason=reason)
        bot_channel = await category.create_voice_channel(name="Total Bots:", reason=reason)
        peak_channel = await category.create_voice_channel(name="Peak Online:", reason=reason)
        guild_channel = await category.create_voice_channel(name="Created On:", reason=reason)

        channels: dict[str, discord.abc.GuildChannel] = {
            "online_channel": online_channel,
            "user_channel": user_channel,
            "bot_channel": bot_channel,
            "guild_channel": guild_channel,
            "peak_channel" : peak_channel,
            "category_channel": category,
        }

        with Session(engine) as session:
            for k, v in channels.items():
                Channel.update(Channel(
                    id = v.id,
                    guild_id = guild.id,
                    type = STATS,
                    name = k,
                ))
            session.commit()
        self.logger.info(f"Created stats channels for: guild='{guild}'")


    async def remove_stats_channels(
        self,
        guild: discord.Guild | None,
        reason: str | None = None,
    ) -> None:
        if guild is None:
            NoneTypeError("Expected discord.guild")

        with Session(engine) as session:
            channels = session.query(Channel).where(
                Channel.guild_id == guild.id,
                Channel.type == STATS,
            ).all()

            self.logger.debug(f"{channels=}")
            self.logger.info(f"Removing stats channels for: guild='{guild}', channels='{channels}'")

            for db_channel in channels:
                self.logger.debug(f"removing {db_channel}")
                try:
                    channel = discord.utils.get(guild.channels, id=db_channel.id)
                    await channel.delete(reason=reason)
                except AttributeError:
                    self.logger.exception("")
                finally:
                    session.delete(db_channel)
            session.commit()


    async def cog_load(self) -> None:
        self.update.start()


    @tasks.loop(seconds=3600)
    async def update(self) -> None:
        # Note: keep for loop with if.
        # because fetching guild won't let the bot get members from guild.
        self.logger.info("Updating all stat channels")
        guilds = self.bot.guilds
        for guild in guilds:
            with Session(engine) as session:
                if not session.query(Channel).where(Channel.guild_id == guild.id, Channel.type == STATS):
                    continue
            self.logger.info(f"Updating stat channels: guild='{guild}'")

            peak_channel, \
            guild_channel, \
            bot_channel, \
            user_channel, \
            online_channel = await self.get_guild_stats_channels(guild)
            self.logger.debug(f"Channels list: {peak_channel}, {user_channel}, {bot_channel}, {online_channel}, {guild_channel}")

            peak_count = get_peak_count(peak_channel)
            reason_update = "Updating Stats channels"
            online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
            users = sum(member.bot is False for member in guild.members)
            bots = sum(member.bot is True for member in guild.members)
            age = guild.created_at.strftime("%Y-%m-%d")
            peak_online = max(online, peak_count)

            if ((new_name := f"Online Users: {online}") != online_channel.name):
                await online_channel.edit(name=new_name, reason=reason_update)

            if ((new_name := f"Total Users: {users}") != user_channel.name):
                await user_channel.edit(name=new_name, reason=reason_update)

            if ((new_name := f"Total Bots: {bots}") != bot_channel.name):
                await bot_channel.edit(name=new_name, reason=reason_update)

            if ((new_name := f"Created On: {age}") != guild_channel.name):
                await guild_channel.edit(name=new_name, reason=reason_update)

            if ((new_name := f"Peak Online: {peak_online}") != peak_channel.name):
                await peak_channel.edit(name=new_name, reason=reason_update)

            self.logger.debug(f"Channels Stats: {peak_online},{users}, {bots}, {online},  {age}, {len(list(guild.members))}")
            self.logger.info(f"Updated stat channels: guild='{guild}'")


    async def get_guild_stats_channels(
        self, guild: discord.Guild,
    ) -> tuple[
        discord.abc.GuildChannel | None,
        discord.abc.GuildChannel | None,
        discord.abc.GuildChannel | None,
        discord.abc.GuildChannel | None,
        discord.abc.GuildChannel | None,
    ]:
        with Session(engine) as session:
            channels = session.query(Channel).where(
                Channel.type == STATS,
                Channel.guild_id == guild.id,
            ).all()

            for channel in channels:
                self.logger.debug(f"check if stats channel: {channel=}")
                match channel.name:
                    case "user_channel":
                        user_channel = guild.get_channel(channel.id)
                    case "online_channel":
                        online_channel = guild.get_channel(channel.id)
                    case "bot_channel":
                        bot_channel = guild.get_channel(channel.id)
                    case "peak_channel":
                        peak_channel = guild.get_channel(channel.id)
                    case "guild_channel":
                        guild_channel = guild.get_channel(channel.id)
                    case "category_channel" | "stats":
                        continue
                    case _:
                        self.logger.debug(f"not a stats channel: {channel}")
                        msg = f"Unexpected channel {channel.name}"
                        raise ValueError(msg)
        self.logger.debug(f"Returning stat channels, {peak_channel, guild_channel, bot_channel, user_channel, online_channel}")
        return peak_channel, guild_channel, bot_channel, user_channel, online_channel


    @app_commands.command(name="show", description="Get some information about the server!")
    async def slash_stats_show(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        embed = discord.Embed(
            title=f"{guild.name} Stats",
            description=f"Information about {guild.name}",
            color=random.choice(rainbow.RAINBOW),
        )

        embed.add_field(
            name="Users",
            value=sum(member.bot is False for member in guild.members),
            inline=True,
        )

        embed.add_field(
            name="Bots",
            value=sum(member.bot is True for member in guild.members),
            inline=True,
        )

        embed.add_field(
            name="Online",
            value=sum(member.status != discord.Status.offline and not member.bot for member in guild.members),
            inline=True,
        )

        embed.add_field(
            name="Created on",
            value=guild.created_at.strftime("%Y-%m-%d"),
            inline=True,
        )

        try:
            embed.add_field(
                name="Afk channel",
                value=guild.afk_channel.mention,
                inline=True,
            )
        except AttributeError as e:
            self.logger.warning(f"No afk-channel found: {e}")

        self.logger.debug(f"Showing guild stats to {interaction.user}: {interaction.guild=}, {interaction.user=}")
        await interaction.response.send_message(embed=embed)


    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.command(name="add", description="This command will create the Stats category which will show some stats about the server.")
    async def slash_stats_category_add(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            if session.query(Channel).where(
                Channel.guild_id == interaction.guild.id,
                Channel.type == STATS,
            ).all():
                rem_mention = self.get_command_mention(self.slash_stats_category_remove)
                await interaction.response.send_message(f"Stats channels already set up use {rem_mention} to remove them", ephemeral=True)
                return

            c_mention = self.get_command_mention(self.slash_stats_category_add)

            await interaction.response.defer(ephemeral=True)
            await self.create_stats_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using {c_mention}")
            await interaction.followup.send("Stats channels are set up")


    @app_commands.command(name="remove", description="This command removes the stat channels. Including the Category and all channels in there.")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_stats_category_remove(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            channels = session.query(Channel).where(
                Channel.guild_id == interaction.guild.id,
                Channel.type == STATS,
            ).all()
            if not channels:
                add_mention = self.get_command_mention(self.slash_stats_category_add)
                await interaction.response.send_message(f"No stats channels found to remove, use {add_mention} to add them", ephemeral=True)
                return

        c_mention = self.get_command_mention(self.slash_stats_category_remove)

        await interaction.response.defer(ephemeral=True)
        await self.remove_stats_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using {c_mention}")
        await interaction.followup.send("Removed stats channels")


    @app_commands.command(name="reset", description="Reset stats of all servers")
    @app_commands.guilds(config.getint("Main", "support_guild_id"))
    @commands.is_owner()
    async def reset_stats(self, interaction:discord.Interaction) -> None:
        self.logger.warning(f"Resetting all guild/stats channels > by: {interaction.user}")
        await interaction.response.defer(ephemeral=True)

        with Session(engine) as session:
            channels = session.query(Channel).where(
                Channel.guild_id == interaction.guild.id,
                Channel.type == STATS,
            ).all()

            seen = []

            for channel in channels:
                guild_id = channel.guild_id
                if guild_id in seen:
                    self.logger.debug(f"already updated {guild_id}")
                    continue

                guild = discord.utils.get(self.bot.guilds, id=guild_id)
                seen.append(guild_id)
                await self.remove_stats_channels(guild=guild, reason="Resetting all stats channels")
                await self.create_stats_channels(guild=guild, reason="Resetting all stats channels")
                self.logger.info(f"Reset stats for: {guild}")
        await interaction.followup.send("Reset all server stat channels")


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Stats(bot))
