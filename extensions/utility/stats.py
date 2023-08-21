import logging
import random

import discord
import sqlalchemy
from discord import app_commands
from discord.ext import commands, tasks

from tools.config_reader import config
import tools.rainbow as rainbow
from tools import app_command_tools
from tools.database_tables import Channel, engine, Session

STATS = "stats"


@app_commands.guild_only()
class Stats(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    @commands.Cog.listener()
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

        try:
            peak_count = int(peak_channel.name[13:])
        except ValueError:
            peak_count = 0
        online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
        if online > peak_count:
            await peak_channel.edit(name=f"Peak Online: {peak_count}", reason="Reached new peak of online members")
            self.logger.info(f"New peak online reached for {guild}!")


    async def create_stats_channels(
        self,
        guild: discord.Guild,
        reason: str = None
    ) -> None:
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
            "category_channel": category,
            "online_channel": online_channel,
            "user_channel": user_channel,
            "bot_channel": bot_channel,
            "guild_channel": guild_channel,
            "peak_channel" : peak_channel
        }

        with Session(engine) as session:
            for k, v in channels.items():
                session.add(Channel(
                    id = v.id,
                    guild_id = guild.id,
                    type = STATS,
                    name = k
                    ))
            session.commit()
        self.logger.info(f"Created stats channels for: guild='{guild}'")


    async def remove_stats_channels(
        self,
        guild: discord.Guild,
        reason: str = None
    ) -> None:
        with Session(engine) as session:
            results = session.query(Channel).where(Channel.guild_id == guild.id, Channel.type == STATS)
            channels = results.all()
            self.logger.debug(f"{channels=}, {results=}")
            self.logger.info(f"Removing stats channels for: guild='{guild}', channels='{channels}'")
            for db_channel in channels:
                self.logger.debug(f"{db_channel}")
                try:
                    channel = discord.utils.get(guild.channels, id=db_channel.id)
                    await channel.delete(reason=reason)
                except AttributeError as e:
                    self.logger.exception(e)
                finally:
                    session.execute(sqlalchemy.delete(Channel).where(
                        Channel.guild_id == guild.id,
                        Channel.type == STATS
                    ))
            session.commit()


    @tasks.loop(seconds=3600)
    async def update(self) -> None:  # sourcery skip: low-code-quality
        # Note: keep for loop with if.
        # because fetching guild won't let the bot get members from guild.
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

            try:
                peak_count = int(peak_channel.name[13:])
            except ValueError:
                peak_count = 0

            reason_update = "Stats update"
            online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
            if ((new_name := f"Online Users: {online}") != online_channel.name):
                await online_channel.edit(name=new_name, reason=reason_update)

            users = sum(member.bot == False for member in guild.members)
            if ((new_name := f"Total Users: {users}") != user_channel.name):
                await user_channel.edit(name=new_name, reason=reason_update)

            bots = sum(member.bot == True for member in guild.members)
            if ((new_name := f"Online Bots: {bots}") != bot_channel.name):
                await bot_channel.edit(name=new_name, reason=reason_update)

            age = guild.created_at.strftime("%Y-%m-%d")
            if ((new_name := f"Created On: {age}") != guild_channel.name):
                await guild_channel.edit(name=new_name, reason=reason_update)

            peak_online = max(online, peak_count)
            if ((new_name := f"Peak Online: {peak_online}") != peak_channel.name):
                await peak_channel.edit(name=new_name, reason=reason_update)

            self.logger.debug(f"Channels Stats: {peak_online},{users}, {bots}, {online},  {age}, {list(guild.members)}")
            self.logger.info(f"Updated stat channels: guild='{guild}'")


    # TODO: transform to fetch sql
    async def get_guild_stats_channels(
        self, guild: discord.Guild
    ) -> tuple[
        discord.VoiceChannel,
        discord.VoiceChannel,
        discord.VoiceChannel,
        discord.VoiceChannel,
        discord.VoiceChannel,
    ]:
        guild_id: dict = self.data[str(guild.id)]
        category: dict = list(guild_id.values())[0]
        channels = list(category.values())[0]
        user_channel_id = channels["user_channel"]
        online_channel_id = channels["online_channel"]
        bot_channel_id = channels["bot_channel"]
        peak_channel_id = channels["peak_online"]
        guild_channel_id = channels["guild_channel"]
        peak_channel = guild.get_channel(peak_channel_id) or await guild.fetch_channel(peak_channel_id)
        guild_channel = guild.get_channel(guild_channel_id) or await guild.fetch_channel(guild_channel_id)
        bot_channel = guild.get_channel(bot_channel_id) or await guild.fetch_channel(bot_channel_id)
        user_channel = guild.get_channel(user_channel_id) or await guild.fetch_channel(user_channel_id)
        online_channel = guild.get_channel(online_channel_id) or await guild.fetch_channel(online_channel_id)
        return peak_channel, guild_channel, bot_channel, user_channel, online_channel


    @app_commands.command(name="show", description="Get some information about the server!")
    async def slash_stats_show(self, interaction:discord.Interaction) -> None:
        guild = interaction.guild
        bots = sum(member.bot == True for member in guild.members)
        online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
        creation_date = guild.created_at.strftime("%Y-%m-%d")
        embed=discord.Embed(title=f"{guild.name} Stats", description=f"Information about {guild.name}", color=random.choice(rainbow.RAINBOW))
        embed.add_field(name="Users", value=guild.member_count, inline=True)
        embed.add_field(name="Bots", value=bots, inline=True)
        embed.add_field(name="Online", value=online, inline=True)
        embed.add_field(name="Created on", value=creation_date, inline=True)
        try:
            embed.add_field(name="Afk channel", value=guild.afk_channel.mention, inline=True)
        except AttributeError as e:
            self.logger.warning(f"Error caused by non-existing AFK channel: {e}")
        self.logger.debug(f"Showing guild stats: {interaction.guild=}, {interaction.user=}")
        await interaction.response.send_message(embed=embed)


    @app_commands.command(
        name="add",
        description="This command will create the Stats category which will show some stats about the server."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_stats_category_add(self, interaction:discord.Interaction) -> None:
        _, c_mention = await app_command_tools.Converter(bot=self.bot).get_app_sub_command(self.slash_stats_category_add)
        with Session(engine) as session:
            result = session.execute(sqlalchemy.select(Channel).where(Channel.guild_id == interaction.guild.id, Channel.type == STATS))
            if result.all():
                await interaction.response.send_message("Stats channels already set up", ephemeral=True)
            else:
                await interaction.response.defer(ephemeral=True)
                await self.create_stats_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using {c_mention}")
                await interaction.followup.send("Stats channels are set up")


    @app_commands.command(
        name="remove",
        description="This command removes the stat channels. Including the Category and all channels in there."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_stats_category_remove(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            result = session.execute(sqlalchemy.select(Channel).where(Channel.guild_id == interaction.guild.id, Channel.type == STATS))
            if not result.all():
                await interaction.response.send_message("No stats channels found to remove.", ephemeral=True)
                return
        _, c_mention = await app_command_tools.Converter(bot=self.bot).get_app_sub_command(self.slash_stats_category_remove)
        await interaction.response.defer(ephemeral=True)
        await self.remove_stats_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using {c_mention}")
        await interaction.followup.send("Removed stats channels")


    @app_commands.command(name="reset", description="Reset stats of all servers")
    @app_commands.guilds(config.getint("Main", "support_guild_id"))
    @commands.is_owner()
    async def reset_stats(self, interaction:discord.Interaction) -> None:
        self.logger.warning(f"Resetting all guild/stats channels > by: {interaction.user}")
        with Session(engine) as session:
            result = session.query(Channel).where(Channel.guild_id == interaction.guild.id and Channel.type == STATS)
            for channel in result.all():
                guild_id = channel.guild_id
                guild = discord.utils.get(self.bot.guilds, id=guild_id)
                if not guild:
                    self.logger.debug(f"skipping reset of {guild_id}")
                    continue
                await self.remove_stats_channels(guild=guild, reason="Resetting all stats channels")
                await self.create_stats_channels(guild=guild, reason="Resetting all stats channels")
                self.logger.info(f"Reset stats for: {guild}")
        await interaction.response.send_message("Reset all server stat channels", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Stats(bot))