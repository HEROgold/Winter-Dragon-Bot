"""Module containing the automatic channel cog."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, cast

import discord
from winter_dragon.bot.config import Config
from discord import (
    VoiceChannel,
    app_commands,
)
from sqlmodel import select
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.bot.errors import NoneTypeError
from winter_dragon.database.tables import AutoChannels as AC  # noqa: N817
from winter_dragon.database.tables import AutoChannelSettings as ACS  # noqa: N817
from winter_dragon.database.tables.channel import Channels


if TYPE_CHECKING:

    from winter_dragon.bot._types.aliases import VocalGuildChannel
    from winter_dragon.bot.core.bot import WinterDragon


@app_commands.guild_only()
class AutomaticChannels(GroupCog):
    """Automatic channels for users to create their own (temporary) channels."""

    create_reason = Config("Creating AutomaticChannel")

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """When a user joins a voice channel, create a new channel for them."""
        self.logger.debug(f"{member} moved from {before} to {after}")
        if voice_create := self.session.exec(select(AC).where(AC.id == member.guild.id)).first():
            self.logger.debug(f"{voice_create}")

            # Handle before.channel things
            if before.channel is None:
                pass
            elif before.channel.id == voice_create.channel_id:
                # ignore when already moved from "Join Me"
                return
            elif len(before.channel.members) == 0:  # noqa: SIM102
                if db_channel := self.session.exec(select(AC).where(AC.channel_id == before.channel.id)).first():
                    if dc_channel := member.guild.get_channel(db_channel.channel_id):
                        await dc_channel.delete(reason="removing empty voice")
                    self.session.delete(db_channel)

            if (
                after.channel is not None and
                after.channel.id == voice_create.channel_id
            ):
                await self.create_user_channel(member, after, after.channel.guild)
            self.session.commit()

    async def create_user_channel(
        self,
        member: discord.Member,
        after: discord.VoiceState,
        guild: discord.Guild,
    ) -> None:
        """Create a automatic channel for a user."""
        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            member.guild.me: discord.PermissionOverwrite.from_pair(
                discord.Permissions.all_channel(),
                discord.Permissions.none(),
            ),
            member: discord.PermissionOverwrite.from_pair(
                discord.Permissions.all_channel(),
                discord.Permissions.none(),
            ),
        }

        if after.channel is None:
            return

        if user_channel := self.session.exec(select(AC).where(AC.id == member.id)).first():  # noqa: SIM102
            if dc_channel := member.guild.get_channel(user_channel.channel_id):
                await member.send(f"You already have a channel at {dc_channel.mention}")
                return

        # check if user that joined "Create Vc" channel is in db
        if self.session.exec(select(AC).where(AC.channel_id == after.channel.id)).first():
            name, limit = self.get_final_settings(
                member,
                self.session.exec(select(ACS).where(ACS.user_id == member.id)).first(),
                self.session.exec(select(ACS).where(ACS.user_id == guild.id)).first(),
            )

            # Set a default name if no custom one is set in settings
            name = member.activity.name if member.activity and member.activity.name else f"{member.name}'s channel"

            db_auto_channel = self.session.exec(select(AC).where(AC.id == guild.id)).first()
            if db_auto_channel is None:
                await member.send("You are not setup yet, please use `/setup` to create your channel")
                return
            channel_id = db_auto_channel.channel_id
            voice_channel = guild.get_channel(channel_id)
            if voice_channel is None:
                await member.send("The category for your channel does not exist, please use `/setup` to create your channel")
                return
            category = voice_channel.category

            voice_channel = await member.guild.create_voice_channel(
                name,
                category=category,
                overwrites=overwrites, # type: ignore[reportUnknownArgumentType]
                reason=self.create_reason,
            )

            await member.move_to(voice_channel)
            await voice_channel.set_permissions(self.bot.user, connect=True, read_messages=True) # type: ignore  # noqa: PGH003
            await voice_channel.set_permissions(member, connect=True, read_messages=True)
            await voice_channel.edit(name=name, user_limit=limit)
            self.session.add(AC(
                id=member.id,
                channel_id=voice_channel.id,
            ))
            self.session.commit()


    def get_final_settings(
            self,
            member: discord.Member,
            setting: ACS | None,
            guild_setting: ACS | None,
        ) -> tuple[str | None, int]:
        """Get the final settings for the channel. returning the most restrictive settings where possible."""
        self.logger.debug(f"transform settings: {member}, {setting=}, {guild_setting=}")
        name = None if setting is None else setting.channel_name
        if (  # noqa: SIM108
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
        """Set up the AutoChannel system for this guild."""
        guild = interaction.guild
        if guild is None:
            msg = "Guild is None when setting up AutoChannel"
            raise NoneTypeError(msg)

        if self.session.exec(select(AC).where(AC.id == guild.id)).first() is not None:
            await interaction.response.send_message("You are already set up", ephemeral=True)
            return

        channel = await guild.create_voice_channel(
            voice_channel_name,
            category=(
                await guild.create_category(category_name)
            ),
            reason=self.create_reason,
        )

        self.session.add_all([
            Channels(
                id=channel.id,
                name=channel.name,
                guild_id=guild.id,
            ),
            AC(
                id = guild.id,
                channel_id = channel.id,
            ),
        ])
        self.session.commit()
        await interaction.response.send_message("**You are all setup and ready to go!**", ephemeral=True)


    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.command(name="mark", description="Mark the current channel or a given channel to be the main AutoChannel")
    async def slash_mark(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel | None=None,
    ) -> None:
        """Mark the current channel or a given channel to be the main AutoChannel."""
        if channel is None or interaction.guild is None:
            msg = "Incorrect channel type, please use this command in a guild channel"
            await interaction.response.send_message(msg, ephemeral=True)
            return

        if channel != VoiceChannel:
            await interaction.response.send_message(dedent(f"""{channel.mention} is not a voice channel!
                use {self.get_command_mention(self.slash_mark)} with the `channel` option to mark another channel""",
            ))
            return

        self.session.add(AC(
            id = interaction.guild.id,
            channel_id = channel.id,
        ))
        self.session.commit()
        await interaction.response.send_message(f"Successfully set {channel.mention} as this guild's creation channel")

    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.command(name="guild_limit", description="Set a limit for AutoChannels")
    async def slash_set_guild_limit(self, interaction: discord.Interaction, limit: int) -> None:
        """Set a limit for AutoChannels."""
        if autochannel_settings := self.session.exec(select(ACS).where(ACS.user_id == interaction.user.id)).first():
            autochannel_settings.channel_limit = limit
        else:
            self.session.add(ACS(
                user_id = interaction.user.id,
                channel_name = interaction.user.name,
                channel_limit = 0,
            ))
        self.session.commit()
        await interaction.response.send_message(
            f"You have changed the channel limit for your guild to `{limit}`!",
            ephemeral=True,
        )


    @app_commands.command(name="limit", description="Set a limit for your channel")
    async def slash_limit(self, interaction: discord.Interaction, limit: int) -> None:
        """Set a limit for your channel."""
        if autochannel_settings := self.session.exec(select(ACS).where(ACS.user_id == interaction.user.id)).first():
            autochannel_settings.channel_limit = limit
        else:
            self.session.add(ACS(
                user_id = interaction.user.id,
                channel_name = interaction.user.name,
                channel_limit = 0,
            ))

        if autochannel := self.session.exec(select(AC).where(AC.id == interaction.user.id)).first():
            channel = self.bot.get_channel(autochannel.channel_id)
            if channel is not None:
                channel = cast("VocalGuildChannel", channel)
                await channel.edit(user_limit=limit)

            await interaction.response.send_message(
                f"{interaction.user.mention} You have set the channel limit to be `{limit}`!, settings are saved",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"{interaction.user.mention} You don't own a channel, settings are saved.",
                ephemeral=True,
            )
        self.session.commit()


    @slash_setup.error
    async def info_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle errors for the setup command."""
        self.logger.exception(error)
        await interaction.response.send_message(
            "An error occurred while setting up the AutoChannel.",
            ephemeral=True,
        )

    @app_commands.command(name="name", description="Change the name of your channels")
    async def slash_name(self, interaction: discord.Interaction, *, name: str) -> None:
        """Change the name of a users channels."""
        if autochannel := self.session.exec(select(AC).where(AC.id == interaction.user.id)).first():
            channel = self.bot.get_channel(autochannel.channel_id)
            if channel is not None and isinstance(channel, VoiceChannel):
                await channel.edit(name=name)

        await interaction.response.send_message(
            f"{interaction.user.mention} You have changed your channel name to `{name}`!",
            ephemeral=True,
        )

        if voice_settings := self.session.exec(select(ACS).where(ACS.user_id == interaction.user.id)).first():
            voice_settings.channel_name = name
        else:
            self.session.add(ACS(
                user_id = interaction.user.id,
                channel_name = name,
                channel_limit = 0,
            ))
        self.session.commit()


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(AutomaticChannels(bot=bot))
