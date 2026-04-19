"""Tournament signup Cog for Discord scheduled events."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ui import Button, View
from sqlmodel import select

from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.bot.core.tasks import loop
from winter_dragon.database.tables import (
    TournamentSignupConfig,
    TournamentSignupEvent,
    TournamentSignupParticipant,
)


class TournamentJoinButton(Button):
    """Button that allows users to join a tournament signup."""

    def __init__(self, event_id: int) -> None:
        super().__init__(style=discord.ButtonStyle.success, label="I join", custom_id=f"tournament_join:{event_id}")
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.view or not isinstance(self.view, TournamentJoinView):
            await interaction.response.send_message("Unable to process this signup.", ephemeral=True)
            return

        await self.view.handle_join(interaction)


class TournamentJoinView(View):
    """Persistent view for tournament signup buttons."""

    def __init__(self, cog: TournamentSignup, event_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.event_id = event_id
        self.add_item(TournamentJoinButton(event_id=event_id))

    async def handle_join(self, interaction: discord.Interaction) -> None:
        """Handle a join button press."""
        event_record = self.cog.get_signup_event(self.event_id)
        if event_record is None:
            await interaction.response.send_message("This tournament signup is no longer active.", ephemeral=True)
            return

        if self.cog.is_user_registered(event_record.id, interaction.user.id):
            await interaction.response.send_message("You have already joined this tournament.", ephemeral=True)
            return

        self.cog.session.add(
            TournamentSignupParticipant(
                event_id=event_record.id,
                user_id=interaction.user.id,
            )
        )
        self.cog.session.commit()

        embed = self.cog.build_signup_embed(event_record, interaction.guild)
        await interaction.response.send_message(
            f"✅ {interaction.user.mention}, you are now registered for this tournament.",
            ephemeral=True,
        )

        if interaction.message is not None:
            await interaction.message.edit(embed=embed, view=self)


@app_commands.guild_only()
class TournamentSignup(GroupCog, auto_load=True):
    """Cog to manage tournament signup announcements for scheduled events."""

    tournament = app_commands.Group(name="tournament", description="Tournament signup commands")

    def __init__(self, **kwargs: dict) -> None:
        super().__init__(**kwargs)
        self.logger.info("TournamentSignup cog initialized")

    async def cog_load(self) -> None:
        await super().cog_load()
        self.restore_signup_views()
        self.signup_reminder_loop.start()

    async def cog_unload(self) -> None:
        if self.signup_reminder_loop.is_running():
            self.signup_reminder_loop.stop()
        await super().cog_unload()

    def restore_signup_views(self) -> None:
        """Restore persistent views for existing announcement messages."""
        signup_events = self.session.exec(
            select(TournamentSignupEvent).where(TournamentSignupEvent.announce_message_id is not None)
        ).all()
        for signup_event in signup_events:
            if signup_event.announce_message_id is None:
                continue
            try:
                self.bot.add_view(TournamentJoinView(self, signup_event.id), message_id=signup_event.announce_message_id)
            except Exception:
                self.logger.exception("Failed to restore tournament signup view for event %s", signup_event.id)

    @Cog.listener()
    async def on_guild_scheduled_event_create(self, event: discord.ScheduledEvent) -> None:
        """Announce tournament signups when a matching scheduled event is created."""
        guild = event.guild
        if guild is None:
            return

        config = self.get_config(guild.id)
        if config is None or config.announcement_channel_id is None or config.tournament_voice_channel_id is None:
            return

        event_channel_id = getattr(event, "channel_id", None)
        if event_channel_id != config.tournament_voice_channel_id:
            return

        announcement_channel = guild.get_channel(config.announcement_channel_id)
        if not isinstance(announcement_channel, discord.abc.Messageable):
            return

        event_record = TournamentSignupEvent(
            guild_id=guild.id,
            scheduled_event_id=event.id,
            location_id=event_channel_id,
            event_name=event.name,
            event_description=event.description,
            start_time=self.get_event_start_time(event),
        )
        self.session.add(event_record)
        self.session.commit()

        embed = self.build_signup_embed(event_record, guild)
        view = TournamentJoinView(self, event_record.id)

        try:
            message = await announcement_channel.send(embed=embed, view=view)
            event_record.announce_message_id = message.id
            self.session.add(event_record)
            self.session.commit()
            self.bot.add_view(view, message_id=message.id)
        except discord.DiscordException:
            self.logger.exception("Failed to send tournament signup announcement for %s", event.name)

    @Cog.listener()
    async def on_guild_scheduled_event_delete(self, event: discord.ScheduledEvent) -> None:
        """Remove signup records when a scheduled event is deleted."""
        signup_event = self.session.exec(
            select(TournamentSignupEvent).where(TournamentSignupEvent.scheduled_event_id == event.id)
        ).first()
        if signup_event is not None:
            self.session.delete(signup_event)
            self.session.commit()

    def get_config(self, guild_id: int) -> TournamentSignupConfig | None:
        """Load the guild signup configuration."""
        return self.session.exec(select(TournamentSignupConfig).where(TournamentSignupConfig.id == guild_id)).first()

    def get_signup_event(self, event_id: int) -> TournamentSignupEvent | None:
        """Load a signup event record by primary key."""
        return self.session.exec(select(TournamentSignupEvent).where(TournamentSignupEvent.id == event_id)).first()

    def get_participant_ids(self, event_id: int) -> list[int]:
        """Return the list of registered participant user IDs for a signup event."""
        participants = self.session.exec(
            select(TournamentSignupParticipant.user_id).where(TournamentSignupParticipant.event_id == event_id)
        ).all()
        return list(participants)

    def is_user_registered(self, event_id: int, user_id: int) -> bool:
        """Determine whether the user is already registered."""
        return (
            self.session.exec(
                select(TournamentSignupParticipant).where(
                    TournamentSignupParticipant.event_id == event_id,
                    TournamentSignupParticipant.user_id == user_id,
                )
            ).first()
            is not None
        )

    def build_signup_embed(self, event_record: TournamentSignupEvent, guild: discord.Guild | None) -> discord.Embed:
        """Create or refresh the signup announcement embed."""
        start_time = event_record.start_time
        embed = discord.Embed(
            title=event_record.event_name or "Tournament Signup",
            description=event_record.event_description or "Click the button below to join the tournament.",
            color=discord.Color.blurple(),
            timestamp=start_time,
        )

        if start_time is not None:
            embed.add_field(
                name="Starts",
                value=discord.utils.format_dt(start_time, style="F"),
                inline=False,
            )

        if guild is not None and event_record.location_id is not None:
            location_channel = guild.get_channel(event_record.location_id)
            if location_channel is not None:
                embed.add_field(
                    name="Location",
                    value=location_channel.mention,
                    inline=False,
                )

        participants = self.get_participant_ids(event_record.id)
        if participants:
            member_mentions = [
                guild.get_member(user_id).mention if guild and guild.get_member(user_id) else f"<@{user_id}>"
                for user_id in participants[:25]
            ]
            embed.add_field(
                name=f"Registered Players ({len(participants)})",
                value="\n".join(member_mentions),
                inline=False,
            )
        else:
            embed.add_field(
                name="Registered Players",
                value="No players have joined yet.",
                inline=False,
            )

        embed.set_footer(text="Use the button below to join the tournament.")
        return embed

    def get_event_start_time(self, event: discord.ScheduledEvent) -> datetime | None:
        """Get the start time from a scheduled event object."""
        return getattr(event, "scheduled_start_time", None) or getattr(event, "start_time", None)

    @app_commands.checks.has_permissions(manage_guild=True)
    @tournament.command(name="mark_location", description="Mark the tournament voice channel location")
    async def mark_location(
        self,
        interaction: discord.Interaction,
        voice_channel: discord.VoiceChannel | None = None,
    ) -> None:
        """Mark a voice channel as the tournament location."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command must be used in a guild.", ephemeral=True)
            return

        if voice_channel is None:
            if not interaction.user.voice or interaction.user.voice.channel is None:
                await interaction.response.send_message(
                    "Please join a voice channel or provide a voice channel.",
                    ephemeral=True,
                )
                return
            voice_channel = interaction.user.voice.channel

        config = self.get_config(guild.id) or TournamentSignupConfig(id=guild.id)
        config.tournament_voice_channel_id = voice_channel.id
        self.session.add(config)
        self.session.commit()

        await interaction.response.send_message(
            f"✅ {voice_channel.mention} has been set as the tournament location.",
            ephemeral=True,
        )

    @app_commands.checks.has_permissions(manage_guild=True)
    @tournament.command(name="set_chat", description="Set the announcement channel for tournament signups")
    async def set_chat(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        """Set the text channel used for tournament signup announcements."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command must be used in a guild.", ephemeral=True)
            return

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                await interaction.response.send_message(
                    "Please use this command in a text channel or specify a text channel.",
                    ephemeral=True,
                )
                return
            channel = interaction.channel

        config = self.get_config(guild.id) or TournamentSignupConfig(id=guild.id)
        config.announcement_channel_id = channel.id
        self.session.add(config)
        self.session.commit()

        await interaction.response.send_message(
            f"✅ {channel.mention} has been set as the tournament signup announcement channel.",
            ephemeral=True,
        )

    @tournament.command(name="status", description="Show the current tournament signup configuration")
    async def status(self, interaction: discord.Interaction) -> None:
        """Show the current tournament signup setup for this guild."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command must be used in a guild.", ephemeral=True)
            return

        config = self.get_config(guild.id)
        if config is None:
            await interaction.response.send_message("No tournament signup configuration is set.", ephemeral=True)
            return

        location = guild.get_channel(config.tournament_voice_channel_id) if config.tournament_voice_channel_id else None
        announcement = guild.get_channel(config.announcement_channel_id) if config.announcement_channel_id else None
        active_signups = self.session.exec(
            select(TournamentSignupEvent).where(TournamentSignupEvent.guild_id == guild.id)
        ).all()

        embed = discord.Embed(
            title="Tournament Signup Status",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Tournament voice location",
            value=location.mention if location else "Not set",
            inline=False,
        )
        embed.add_field(
            name="Announcement channel",
            value=announcement.mention if announcement else "Not set",
            inline=False,
        )
        embed.add_field(
            name="Active signups",
            value=str(len(active_signups)),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @loop(hours=1)
    async def signup_reminder_loop(self) -> None:
        """Send reminders for upcoming tournament signups."""
        now = datetime.now(UTC)
        signup_events = self.session.exec(
            select(TournamentSignupEvent).where(TournamentSignupEvent.start_time is not None)
        ).all()

        for signup_event in signup_events:
            if signup_event.start_time is None:
                continue

            lead_time = signup_event.start_time - now
            if signup_event.reminder_one_day_sent is False and timedelta(hours=23) < lead_time <= timedelta(days=1):
                await self.send_reminder(signup_event, "1 day")
                signup_event.reminder_one_day_sent = True
                self.session.add(signup_event)
            elif signup_event.reminder_two_hour_sent is False and timedelta(hours=1) < lead_time <= timedelta(hours=2):
                await self.send_reminder(signup_event, "2 hours")
                signup_event.reminder_two_hour_sent = True
                self.session.add(signup_event)

        self.session.commit()

    async def send_reminder(self, signup_event: TournamentSignupEvent, window_label: str) -> None:
        """Send a reminder message for an upcoming tournament."""
        guild = self.bot.get_guild(signup_event.guild_id)
        if guild is None or signup_event.announce_message_id is None:
            return

        config = self.get_config(guild.id)
        if config is None or config.announcement_channel_id is None:
            return

        announcement_channel = guild.get_channel(config.announcement_channel_id)
        if announcement_channel is None or not isinstance(announcement_channel, discord.abc.Messageable):
            return

        embed = discord.Embed(
            title=f"Tournament Reminder — {window_label}",
            description=f"The tournament **{signup_event.event_name or 'Unnamed event'}** starts in {window_label}.",
            color=discord.Color.gold(),
        )
        if signup_event.start_time is not None:
            embed.add_field(
                name="Starts",
                value=discord.utils.format_dt(signup_event.start_time, style="F"),
                inline=False,
            )

        participants = self.get_participant_ids(signup_event.id)
        embed.add_field(
            name="Registered players",
            value=str(len(participants)),
            inline=False,
        )

        await announcement_channel.send(embed=embed)
