from typing import Optional

import discord
from discord import app_commands

from tools.database_tables import Session, engine
from tools.database_tables import AutoChannel as AC
from tools.database_tables import AutoChannelSettings as ACS
from _types.cogs import Cog, GroupCog
from _types.bot import WinterDragon


class AutomaticChannels(GroupCog):
    # FIXME: doesn't display debug msg on channel join/leave
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
            if voice_create := session.query(AC).where(AC.id == after.channel.guild.id).first():
                self.logger.debug(f"{voice_create}")
                # ignore when already moved from "Join Me"
                if before.channel is not None:
                    if before.channel.id == voice_create.channel_id:
                        return

                    if len(before.channel.members > 0):
                        await before.channel.delete(reason="removing empty voice")
                        session.delete(session.query(AC).where(AC.channel_id == before.channel.id).first())

                if after.channel is not None and after.channel.id == voice_create.channel_id:
                    return await self.create_user_channel(member, after, session, after.channel.guild)
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

        if user_channel := session.query(AC).where(AC.channel_id == after.channel.id).first():
            name, limit = self.get_final_settings(
                member,
                session.query(ACS).where(ACS.id == member.id).first(),
                session.query(ACS).where(ACS.id == guild.id).first()
            )

            voice_channel = await member.guild.create_voice_channel(
                name,
                category=guild.get_channel(session.query(AC).where(AC.id == guild.id).first().id).category,
                overwrites=overwrites
            )
            channel_id = voice_channel.id
            await member.move_to(voice_channel)
            # await voice_channel.set_permissions(self.bot.user, connect=True, read_messages=True)
            # await voice_channel.set_permissions(member, connect=True, read_messages=True)
            await voice_channel.edit(name=name, user_limit=limit)
            session.add(AC(
                id=member.id,
                channel_id=channel_id
            ))
            session.commit()
        else:
            await member.send(f"You already have a channel at {self.bot.get_channel(user_channel[1]).mention}")
            return


    def get_final_settings(
            self,
            member: discord.Member,
            setting: Optional[tuple[str, int]],
            guild_setting: Optional[tuple[str, int]]
        ) -> tuple[str, int]:
        print(f"transform settings: {member}, {setting=}, {guild_setting=}")
        name = f"{member.name}'s channel" if setting is None else setting[0]
        if (
            setting is None 
            or guild_setting is None 
            or setting[1] == 0
        ):
            limit = 0
        else:
            limit = setting[1]
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
                )
            )

            session.add(AC(
                id = interaction.guild.id,
                channel_id = channel.id
            ))
            session.commit()
        await interaction.response.send_message("**You are all setup and ready to go!**", ephemeral=True)


    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.command(name="guild_limit", description="Set a default limit for AutoChannels")
    async def slash_set_guild_limit(self, interaction: discord.Interaction, limit: int) -> None:
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
        await interaction.response.send_message("You have changed the default channel limit for your server!", ephemeral=True)


    @app_commands.command(name="limit", description="Set a limit for your channel")
    async def slash_limit(self, interaction: discord.Interaction, limit: int) -> None:
        with Session(engine) as session:
            if autochannel := session.query(AC).where(AC.id == interaction.user.id).first():
                channel = self.bot.get_channel(autochannel.channel_id)
                await channel.edit(user_limit=limit)
                await interaction.response.send_message(f"{interaction.user.mention} You have set the channel limit to be {limit}!", ephemeral=True)
            else:
                await interaction.response.send_message(f"{interaction.user.mention} You don't own a channel.", ephemeral=True)

            if autochannel_settings := session.query(ACS).where(ACS.id == interaction.user.id).first():
                autochannel_settings.channel_limit = limit
            else:
                session.add(ACS(
                    id = interaction.user.id,
                    channel_name = interaction.user.name,
                    channel_limit = 0
                ))
            session.commit()


    @slash_setup.error
    async def info_error(self, interaction: discord.Interaction, error: Exception) -> None:
        print(error)


    # TODO: Remove lock, unlock, whitelist and blacklist commands,
    # since users should be able to edit their own channel permissions

    # @app_commands.command(name="lock", description="Lock your channel")
    # async def slash_lock(self, interaction: discord.Interaction) -> None:
    #     with Session(engine) as session:
    #         if autochannel := session.query(AC).where(AC.id == interaction.user.id).first():
    #             role = interaction.guild.default_role
    #             channel = self.bot.get_channel(autochannel.channel_id)
    #             await channel.set_permissions(role, connect=False)
    #             await interaction.channel.send(f"{interaction.user.mention} Voice chat locked! 🔒")
    #         else:
    #             await interaction.channel.send(f"{interaction.user.mention} You don't own a channel.")
    #         session.commit()

    # @app_commands.command(name="unlock", description="Unlock your channel")
    # async def slash_unlock(self, interaction: discord.Interaction) -> None:
    #     with Session(engine) as session:
    #         if autochannel := session.query(AC).where(AC.id == interaction.user.id).first():
    #             role = interaction.guild.default_role
    #             channel = self.bot.get_channel(autochannel.channel_id)
    #             await channel.set_permissions(role, connect=True)
    #             await interaction.channel.send(f"{interaction.user.mention} Voice chat unlocked! 🔓")
    #         else:
    #             await interaction.response.send_message(f"{interaction.user.mention} You don't own a channel.", ephemeral=True)
    #         session.commit()

    # @app_commands.command(name="whitelist", description="Allow a specific member to your channel")
    # async def permit(self, interaction: discord.Interaction, member: discord.Member) -> None:
    #     with Session(engine) as session:
    #         c = session.cursor()
    #         author_id = interaction.user.id
    #         voice = FromDatabase.get_voice_id_from_user(author_id, c)
    #         if voice is None:
    #             await interaction.channel.send(f"{interaction.user.mention} You don't own a channel.")
    #         else:
    #             channel_id = voice[0]
    #             channel = self.bot.get_channel(channel_id)
    #             await channel.set_permissions(member, connect=True)
    #             await interaction.channel.send(
    #                 f"{interaction.user.mention} You have permitted {member.name} to have access to the channel. ✅"
    #             )
    #         session.commit()

    # @app_commands.command(name="blacklist", description="Deny a specific member to your channel")
    # async def reject(self, interaction: discord.Interaction, member: discord.Member) -> None:
    #     with Session(engine) as session:
    #         c = session.cursor()
    #         author_id = interaction.user.id
    #         guild_id = interaction.guild.id
    #         voice = FromDatabase.get_voice_id_from_user(author_id, c)
    #         if voice is None:
    #             await interaction.channel.send(f"{interaction.user.mention} You don't own a channel.")
    #         else:
    #             channel_id = voice[0]
    #             channel = self.bot.get_channel(channel_id)
    #             for members in channel.members:
    #                 if members.id == member.id:
    #                     c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guild_id,))
    #                     voice = c.fetchone()
    #                     channel2 = self.bot.get_channel(voice[0])
    #                     await member.move_to(channel2)
    #             await channel.set_permissions(member, connect=False, read_messages=True)
    #             await interaction.channel.send(
    #                 f"{interaction.user.mention} You have rejected {member.name} from accessing the channel. ❌"
    #             )
    #         session.commit()


    @app_commands.command(name="name", description="Change the name of your channels")
    async def slash_name(self, interaction: discord.Interaction, *, name: str) -> None:
        with Session(engine) as session:
            if autochannel := session.query(AC).where(AC.id == interaction.user.id).first():
                channel = self.bot.get_channel(autochannel.channel_id)
                await channel.edit(name=name)

            await interaction.response.send_message(f"{interaction.user.mention} You have changed the channel name to {name}!", ephemeral=True)
            
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