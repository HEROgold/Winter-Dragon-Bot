import discord
from discord import app_commands

from tools.database_tables import Session, engine
from tools.database_tables import AutoChannel as AC
from tools.database_tables import AutoChannelSettings as ACS
from _types.cogs import Cog, GroupCog
from _types.bot import WinterDragon

CREATE_REASON = "Creating AutomaticChannel"

class AutomaticChannels(GroupCog):
    # FIXME: weird behavior sometimes on join/leave
    # TODO: add automatic naming, when a name is not specified in settings > get current activity name
    # see https://discordpy.readthedocs.io/en/stable/api.html?highlight=voice_state_update#discord.on_voice_state_update
    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        self.logger.debug(f"{member} moved from {before} to {after}")
        with Session(engine) as session:
            if voice_create := session.query(AC).where(AC.id == member.guild.id).first():
                self.logger.debug(f"{voice_create}")

                # Handle before.channel things
                if before.channel is None:
                    pass
                elif before.channel.id == voice_create.channel_id:
                    # ignore when already moved from "Join Me"
                    return
                elif len(before.channel.members) == 0:
                    if db_channel := session.query(AC).where(AC.channel_id == before.channel.id).first():
                        if dc_channel := member.guild.get_channel(db_channel.channel_id):
                            await dc_channel.delete(reason="removing empty voice")
                        session.delete(db_channel)

                if (
                    after.channel is not None and
                    after.channel.id == voice_create.channel_id
                ):
                    await self.create_user_channel(member, after, session, after.channel.guild)
                session.commit()


    async def create_user_channel(
        self,
        member: discord.Member,
        after: discord.VoiceState,
        session: Session,
        guild: discord.Guild
    ) -> None:
        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            member.guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none()),
            member: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.none())
        }

        if after.channel is None:
            return

        if user_channel := session.query(AC).where(AC.id == member.id).first():
            if dc_channel := member.guild.get_channel(user_channel.channel_id):
                await member.send(f"You already have a channel at {dc_channel.mention}")
                return

        # check if user that joined "Create Vc" channel is in db
        if session.query(AC).where(AC.channel_id == after.channel.id).first():
            name, limit = self.get_final_settings(
                member,
                session.query(ACS).where(ACS.id == member.id).first(),
                session.query(ACS).where(ACS.id == guild.id).first()
            )

            # Set a default name if no custom one is set in settings
            if name is None:
                name = member.activity.name or f"{member.name}'s channel"

            voice_channel = await member.guild.create_voice_channel(
                name,
                category=guild.get_channel(session.query(AC).where(AC.id == guild.id).first().channel_id).category,
                overwrites=overwrites,
                reason=CREATE_REASON
            )

            await member.move_to(voice_channel)
            # await voice_channel.set_permissions(self.bot.user, connect=True, read_messages=True)
            # await voice_channel.set_permissions(member, connect=True, read_messages=True)
            await voice_channel.edit(name=name, user_limit=limit)
            session.add(AC(
                id=member.id,
                channel_id=voice_channel.id
            ))
            session.commit()


    def get_final_settings(
            self,
            member: discord.Member,
            setting: ACS,
            guild_setting: ACS
        ) -> tuple[str, int]:
        self.logger.debug(f"transform settings: {member}, {setting=}, {guild_setting=}")
        name = None if setting is None else setting.channel_name
        if (
            setting is None 
            or guild_setting is None 
            or setting.channel_limit == 0
        ):
            limit = 0
        else:
            limit = setting.channel_limit
        return name, limit


    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.command(name="setup", description="Start the AutoChannel setup")
    async def slash_setup(self, interaction: discord.Interaction, category_name: str, voice_channel_name: str) -> None:
        with Session(engine) as session:
            if session.query(AC).where(AC.id == interaction.guild.id).first() is not None:
                await interaction.response.send_message("You are already set up", ephemeral=True)
                return

            channel = await interaction.guild.create_voice_channel(
                voice_channel_name,
                category=(
                    await interaction.guild.create_category(category_name)
                ),
                reason=CREATE_REASON
            )

            session.add(AC(
                id = interaction.guild.id,
                channel_id = channel.id
            ))
            session.commit()
        await interaction.response.send_message("**You are all setup and ready to go!**", ephemeral=True)


    # FIXME: both limits seem to lock db!?
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.command(name="guild_limit", description="Set a limit for AutoChannels")
    async def slash_set_guild_limit(self, interaction: discord.Interaction, limit: int) -> None:
        await interaction.response.send_message("Disabled due to a bug", ephemeral=True)
        return
        with Session(engine) as session:
            if autochannel_settings := session.query(ACS).where(ACS.id == interaction.user.id).first():
                autochannel_settings.channel_limit = limit
            else:
                session.add(ACS(
                    id = interaction.user.id,
                    channel_name = interaction.user.name,
                    channel_limit = 0
                ))
            session.commit()
        await interaction.response.send_message(f"You have changed the channel limit for your server to `{limit}`!", ephemeral=True)


    @app_commands.command(name="limit", description="Set a limit for your channel")
    async def slash_limit(self, interaction: discord.Interaction, limit: int) -> None:
        await interaction.response.send_message("Disabled due to a bug", ephemeral=True)
        return
        with Session(engine) as session:
            if autochannel_settings := session.query(ACS).where(ACS.id == interaction.user.id).first():
                autochannel_settings.channel_limit = limit
            else:
                session.add(ACS(
                    id = interaction.user.id,
                    channel_name = interaction.user.name,
                    channel_limit = 0
                ))

            if autochannel := session.query(AC).where(AC.id == interaction.user.id).first():
                channel = self.bot.get_channel(autochannel.channel_id)
                if channel is not None:
                    await channel.edit(user_limit=limit)

                await interaction.response.send_message(
                    f"{interaction.user.mention} You have set the channel limit to be `{limit}`!, settings are saved",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(f"{interaction.user.mention} You don't own a channel, settings are saved.", ephemeral=True)
            session.commit()


    @slash_setup.error
    async def info_error(self, interaction: discord.Interaction, error: Exception) -> None:
        self.logger.exception(error)


    @app_commands.command(name="name", description="Change the name of your channels")
    async def slash_name(self, interaction: discord.Interaction, *, name: str) -> None:
        with Session(engine) as session:
            if autochannel := session.query(AC).where(AC.id == interaction.user.id).first():
                channel = self.bot.get_channel(autochannel.channel_id)
                if channel is not None:
                    await channel.edit(name=name)

            await interaction.response.send_message(f"{interaction.user.mention} You have changed your channel name to `{name}`!", ephemeral=True)

            if voice_settings := session.query(ACS).where(ACS.id == interaction.user.id).first():
                voice_settings.channel_name = name
            else:
                session.add(ACS(
                    id = interaction.user.id,
                    channel_name = name,
                    channel_limit = 0
                ))
            session.commit()


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(AutomaticChannels(bot))