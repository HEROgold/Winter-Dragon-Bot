import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlalchemy

import config
from tools import app_command_tools
from tools.database_tables import Channel, engine, Session
from tools.database_tables import AutochannelBlacklist as AAB
from tools.database_tables import AutochannelBlacklist as AAW


# TODO
# Add blacklist for each user to use
# Add whitelist fo each user to use
# /blacklist member:<TAG>
# /whitelist member:<TAG>
# Build permissions for channels based on these.


@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels = True)
@app_commands.checks.bot_has_permissions(manage_channels = True)
class Autochannel(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.act = app_command_tools.Converter(bot=self.bot)


    async def cog_load(self) -> None:
        self.database_cleanup.start()

    @tasks.loop(seconds=3600)
    async def database_cleanup(self) -> None:
        self.logger.info("Cleaning Autochannels.")
        with Session(engine) as session:
            results = session.query(Channel).where(
                Channel.type == "autochannel",
                Channel.name != f"{config.Autochannel.AUTOCHANNEL_NAME} category",
                Channel.name != f"{config.Autochannel.AUTOCHANNEL_NAME} text",
                Channel.name != f"{config.Autochannel.AUTOCHANNEL_NAME} voice",
            )
            channels = results.all()
            self.logger.debug(f"to clean: {channels=}")
            for channel in channels:
                dc_channel = self.bot.get_channel(channel.id)
                self.logger.debug(f"cleaning {channel=}, {dc_channel}")
                if len(dc_channel.members) > 0 or dc_channel.type != discord.VoiceChannel:
                    self.logger.debug(f"user in {channel=}, {dc_channel=}")
                    continue
                self.logger.debug(f"getting user channels: {channel.name=}")
                # get all channels with same name,
                user_channels = session.query(Channel).where(Channel.type == "autochannel", Channel.name == channel.name).all()
                for user_channel in user_channels:
                    self.logger.debug(f"cleaning user channel: {user_channel=}")
                    dc_user_channel = self.bot.get_channel(channel.id)
                    await dc_user_channel.delete()
                    session.delete(user_channel)
            session.commit()

                # Else if name matches channels clean
            # db_category_channel = session.query(Channel).where(
            #     Channel.guild_id == guild.id and Channel.type == "autochannel" and Channel.name == f"{member.id} category"
            #     ).first()
            # db_text_channel = session.query(Channel).where(
            #     Channel.guild_id == guild.id and Channel.type == "autochannel"  and Channel.name == f"{member.id} text"
            #     ).first()
            # db_voice_channel = session.query(Channel).where(
            #     Channel.guild_id == guild.id and Channel.type == "autochannel" and Channel.name == f"{member.id} voice"
            #     ).first()
            # for guild_id, autochannel_categories in list(self.data.items()):
            #     if len(autochannel_categories) <= 1:
            #         self.logger.debug(f"skipping cleaning: {len(autochannel_categories)=}")
            #         if len(autochannel_categories) == 0:
            #             del self.data[autochannel_categories]
            #         continue
            #     guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
            #     cleaned = await self._clean_categories(autochannel_categories, guild)
            #     if cleaned == True:
            #         self.logger.debug(f"Most (or all) channels from {guild.name} are cleaned.")
            # self.set_data(self.data)
            # self.logger.info("database cleaned up")


    @database_cleanup.before_loop # type: ignore
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    # async def _clean_categories(self, autochannel_categories: dict, guild: discord.Guild) -> dict:
    #     self.logger.debug(f"Cleaning `{guild.name}` Auto channels")
    #     cleaned = False
    #     for key, channels in list(autochannel_categories.items()):
    #         if key == config.Autochannel.AUTOCHANNEL_NAME:
    #             self.logger.debug(f"Skipping clean: {guild.name}, {key == config.Autochannel.AUTOCHANNEL_NAME=}")
    #             continue
    #         cleaned = await self._clean_channels(channels, guild)
    #         if cleaned == False:
    #             continue
    #         del self.data[str(guild.id)][key]
    #     return cleaned


    # async def _clean_channels(self, channels:dict, guild:discord.Guild) -> bool:
    #     self.logger.info(f"Cleaning Channels {channels}")
    #     channel = discord.utils.get(guild.voice_channels, id=int(channels["Voice"]))
    #     if channel.type is discord.ChannelType.voice:
    #         empty = len(channel.members) <= 0
    #         if not empty:
    #             return False
    #         for channel_id in channels.values():
    #             channel = discord.utils.get(guild.channels, id=int(channel_id))
    #             try:
    #                 await channel.delete()
    #             except AttributeError as e:
    #                 self.logger.debug(f"{e}")
    #     return True


    @app_commands.command(
        name = "remove",
        description="Remove the autochannel from this server"
    )
    async def slash_autochannel_remove(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            result = session.execute(sqlalchemy.select(Channel).where(
                Channel.guild_id == interaction.guild.id, Channel.type == "autochannel"
            ))
            if not result.all():
                _, c_mention_add = await self.act.get_app_sub_command(self.slash_autochannel_add)
                await interaction.response.send_message(f"No autochannel found. use {c_mention_add} to add them.")
                return
        await interaction.response.defer()
        _, c_mention_remove = await self.act.get_app_sub_command(self.slash_autochannel_remove)
        await self.remove_auto_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using {c_mention_remove}")
        await interaction.followup.send("Removed the autochannels")


    async def remove_auto_channels(
        self,
        guild: discord.Guild,
        reason: str = None
    ) -> None:
        with Session(engine) as session:
            results = session.query(Channel).where(Channel.guild_id == guild.id, Channel.type == "autochannel")
            channels = results.all()
            self.logger.debug(f"{channels=}, {results=}")
            self.logger.info(f"Removing stats channels for: guild='{guild}', channels='{channels}'")
            for db_channel in channels:
                self.logger.debug(f"{db_channel}")
                try:
                    channel = discord.utils.get(guild.channels, id=db_channel.id)
                    await channel.delete(reason=reason)
                    session.execute(sqlalchemy.delete(Channel).where(Channel.id == channel.id))
                except AttributeError as e:
                    self.logger.exception(e)
            session.commit()


    @app_commands.command(
        name = "add",
        description = "Set up voice category and channels, which lets each user make their own channels"
    )
    async def slash_autochannel_add(self, interaction: discord.Interaction) -> None:
        with Session(engine) as session:
            result = session.execute(sqlalchemy.select(Channel).where(
                Channel.guild_id == interaction.guild.id, Channel.type == "autochannel"
            ))
            if result.all():
                await interaction.response.send_message("Autochannel channels already set up", ephemeral=True)
                return
        guild = interaction.guild
        overwrites = self._create_overwrites(interaction.user)
        await interaction.response.defer()
        await self._setup_autochannel(guild, overwrites)
        _, c_mention = await app_command_tools.Converter(bot=self.bot).get_app_sub_command(self.slash_autochannel_remove)
        await interaction.followup.send(f"The channels are set up!\n use {c_mention} before adding again to avoid issues.")


    async def _setup_autochannel(
        self,
        guild: discord.Guild,
        overwrites: discord.PermissionOverwrite
    ) -> None:
        category_channel = await self._get_autochannel_category(guild, overwrites, config.Autochannel.AUTOCHANNEL_NAME)
        voice_channel = await self._get_autochannel_voice(guild, category_channel, config.Autochannel.AUTOCHANNEL_NAME)
        text_channel = await self._get_autochannel_text(guild, category_channel, config.Autochannel.AUTOCHANNEL_NAME)
        
        await voice_channel.edit(name="Join Me!", reason="Autochannel rename")
        await text_channel.edit(name="Autochannel Info", reason="Autochannel rename")
        msg = await text_channel.send(f"To create your own voice and text channel, just join <#{voice_channel.id}>")
        await msg.pin()


    async def _get_autochannel_text(
        self,
        guild: discord.Guild,
        category_channel: discord.CategoryChannel,
        text_channel_name: str
    ) -> discord.TextChannel:
        self.logger.debug("Getting autochannel text")
        with Session(engine) as session:
            result = session.query(Channel).where(
                Channel.guild_id == guild.id, Channel.type == "autochannel", Channel.name == f"{text_channel_name} text"
            )
            if channel := result.first():
                self.logger.debug(f"Found {channel}")
                text_channel = self.bot.get_channel(result.first().id)

            text_channel = await category_channel.create_text_channel(name=text_channel_name, reason="Autochannel")
            session.add(Channel(
                id = text_channel.id,
                name = f"{text_channel_name} text",
                type = "autochannel",
                guild_id = text_channel.guild.id,
            ))
            session.commit()

            self.logger.debug(f"Created {text_channel=}")

        return text_channel


    async def _get_autochannel_voice(
        self,
        guild: discord.Guild,
        category_channel: discord.CategoryChannel,
        voice_channel_name: str
    ) -> discord.VoiceChannel:
        self.logger.debug("Getting autochannel voice")
        with Session(engine) as session:
            result = session.query(Channel).where(Channel.guild_id == guild.id, Channel.type == "autochannel", Channel.name == f"{voice_channel_name} voice")
            if channel := result.first():
                self.logger.debug(f"Found {channel}")
                voice_channel = self.bot.get_channel(result.first().id)

            voice_channel = await category_channel.create_voice_channel(name=voice_channel_name, reason="Autochannel")
            session.add(Channel(
                id = voice_channel.id,
                name = f"{voice_channel_name} voice",
                type = "autochannel",
                guild_id = voice_channel.guild.id,
            ))
            session.commit()
            self.logger.debug(f"Created {voice_channel=}")

        return voice_channel


    async def _get_autochannel_category(
        self,
        guild: discord.Guild,
        overwrites: discord.PermissionOverwrite,
        category_name: str
    ) -> discord.CategoryChannel:
        self.logger.debug("Getting autochannel category")
        with Session(engine) as session:
            result = session.query(Channel).where(Channel.guild_id == guild.id, Channel.type == "autochannel", Channel.name == f"{category_name} category")
            if channel := result.first():
                self.logger.debug(f"Found {channel}")
                category_channel = self.bot.get_channel(result.first().id)

            category_channel = await guild.create_category(name=category_name, overwrites=overwrites, reason="Autochannel")
            session.add(Channel(
                id = category_channel.id,
                name = f"{category_name} category",
                type = "autochannel",
                guild_id = category_channel.guild.id,
            ))
            session.commit()
            self.logger.debug(f"Created {category_channel=}")

        return category_channel


    # FIXME: Doesn't seem to print/work
    # TODO: add helper functions to make this more clear
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        self.logger.debug(f"{member} moved from {before or None} to {after or None}")

        if before.channel:
            return await self._remove_user_autochannels(member, before)

        guild = member.guild
        overwrites = self._create_overwrites(member)
        ac_voice_channel = await self._get_autochannel_voice(guild, category_channel, config.Autochannel.AUTOCHANNEL_NAME)

        if after.channel != ac_voice_channel:
            return

        guild = after.channel.guild
        channel_id = after.channel.id
        category_channel = await self._get_autochannel_category(guild, overwrites, str(member.id))
        voice_channel = await self._get_autochannel_voice(guild, category_channel, str(member.id))
        text_channel = await self._get_autochannel_text(guild, category_channel, str(member.id))

        if any([category_channel, text_channel, voice_channel]):
            return
        if channel_id != voice_channel.id:
            return
        await self._rename_user_autochannels(member, guild)


    async def _remove_user_autochannels(self, member: discord.Member, before: discord.VoiceState) -> None:
        before_channel = before.channel
        guild = before_channel.guild
        member_id = str(member.id)

        with Session(engine) as session:
            self.logger.debug("Getting autochannel voice")
            result = session.query(Channel).where(Channel.guild_id == guild.id, Channel.type == "autochannel", Channel.name == f"{member_id} voice")
            if db_voice_channel := result.first():
                self.logger.debug(f"Found {db_voice_channel=}")
                voice_channel = self.bot.get_channel(db_voice_channel.id)

            if before_channel.id != db_voice_channel.id or len(before_channel.members) > 0:
                # Early return when channel not empty, or isn't a known auto channel voice channel.
                return

            self.logger.debug("Getting autochannel category")
            result = session.query(Channel).where(Channel.guild_id == guild.id, Channel.type == "autochannel", Channel.name == f"{member_id} category")
            if db_category_channel := result.first():
                self.logger.debug(f"Found {db_category_channel=}")
                category_channel = self.bot.get_channel(db_category_channel.id)

            self.logger.debug("Getting autochannel text")
            result = session.query(Channel).where(
                Channel.guild_id == guild.id, Channel.type == "autochannel", Channel.name == f"{member_id} text"
            )
            if db_text_channel := result.first():
                self.logger.debug(f"Found {db_text_channel=}")
                autochannel_text = self.bot.get_channel(db_text_channel.id)

        empty_reason = "Autochannel is empty"
        await voice_channel.delete(reason=empty_reason)
        await autochannel_text.delete(reason=empty_reason)
        await category_channel.delete(reason=empty_reason)
        with Session(engine) as session:
            session.delete(db_category_channel)
            session.delete(db_text_channel)
            session.delete(db_voice_channel)
            session.commit()


    async def _rename_user_autochannels(self, member: discord.Member, guild: discord.Guild, overwrites) -> str:
        overwrites = self._create_overwrites(member)
        member_id = str(member.id)
        category_channel = await self._get_autochannel_category(guild, overwrites, category_name=member_id)
        voice_channel = await self._get_autochannel_voice(guild, category_channel, voice_channel_name=member_id)
        text_channel = await self._get_autochannel_text(guild, category_channel, text_channel_name=member_id)
        await member.move_to(voice_channel)
        renamed_reason = "Autochannel Renamed to username"
        if category_channel.name == member_id:
            await category_channel.edit(name=f"{member.name}'s Channels", reason=renamed_reason)
        if voice_channel.name == member_id:
            await voice_channel.edit(name=f"{member.name}'s Voice", reason=renamed_reason)
        if text_channel.name == member_id:
            await text_channel.edit(name=f"{member.name}'s Text", reason=renamed_reason)


    async def _create_overwrites(self, member: discord.Member) -> None:
        default_overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(),
            member.guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none()),
            member: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
        }
        overwrites = default_overwrites.copy()

        with Session(engine) as session:
            whitelist = session.query(AAW).where(AAW.id == member.id).all()
            blacklist = session.query(AAB).where(AAB.id == member.id).all()

            for i in blacklist:
                dc_user = discord.utils.get(member.guild.members, i.user_id)
                permissions = discord.Permissions.none()
                overwrites += {dc_user: permissions}

            for i in whitelist:
                dc_user = discord.utils.get(member.guild.members, i.user_id)
                permissions = discord.Permissions.voice() and discord.Permissions.text()
                try:
                    overwrites += {dc_user: permissions}
                except KeyError as e:
                    self.logger.warning(f"Cannot add whitelist on top of blacklist for {i.user_id}, {e}")
            session.commit()
        return overwrites


    whitelist = app_commands.Group(name="whitelist", description="add or remove members from your personal whitelist")

    @whitelist.command(name="add", description="add user to your whitelist")
    async def slash_whitelist_add(self, interaction: discord.Interaction, member: discord.Member) -> None:
        with Session(engine) as session:
            session.add(AAW(
                id = interaction.user.id,
                user_id = member.id
            ))
            session.commit()
        await interaction.response.send_message(f"Added {member.mention} to whitelist")


    @whitelist.command(name="remove", description="remove user to your whitelist")
    async def slash_whitelist_remove(self, interaction: discord.Interaction, member: discord.Member) -> None:
        with Session(engine) as session:
            black_user = session.query(AAW).where(AAW.id == interaction.user.id, AAW.user_id == member.id).first()
            session.delete(black_user)
            session.commit()
        await interaction.response.send_message(f"Removed {member.mention} from whitelist")


    blacklist = app_commands.Group(name="blacklist", description="add or remove members from your personal blacklist")

    @blacklist.command(name="add", description="add user to your blacklist")
    async def slash_blacklist_add(self, interaction: discord.Interaction, member: discord.Member) -> None:
        with Session(engine) as session:
            session.add(AAB(
                id = interaction.user.id,
                user_id = member.id
            ))
            session.commit()
        await interaction.response.send_message(f"Added {member.mention} to blacklist")


    @blacklist.command(name="remove", description="remove user to your blacklist")
    async def slash_blacklist_remove(self, interaction: discord.Interaction, member: discord.Member) -> None:
        with Session(engine) as session:
            black_user = session.query(AAB).where(AAB.id == interaction.user.id, AAB.user_id == member.id).first()
            session.delete(black_user)
            session.commit()
        await interaction.response.send_message(f"Removed {member.mention} from blacklist")



async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Autochannel(bot))