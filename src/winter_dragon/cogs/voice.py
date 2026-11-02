"""The /voice command group: split a voice channel into teams that each get a voice channel of their own."""

lazy import asyncio
lazy from random import Random
lazy from typing import TYPE_CHECKING, Annotated, ClassVar, Unpack, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session
from wd_bot.commands import Describe, Range
from wd_db.extension.lifecycle import DiscordKeyedModel, Ownership
lazy from wd_bot.cogs import BotArgs, Cog, GroupCog
lazy from wd_db.extension.lifecycle import alive, alive_by_id

# Command resolves option annotations from module globals at runtime, so these types must be available here.
lazy from wd_discord import (
    ChannelType,
    GuildCommandInteraction,
    GuildComponentInteraction,
    is_network_error,
)
lazy from wd_discord.gateway import EventName
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.resources.channel import GuildChannelParams
lazy from wd_errors import Refused, unwrap
lazy from wd_types.clock import utc_now

lazy from winter_dragon.cogs.team.cards import split_post
lazy from winter_dragon.cogs.team.cog import Teams
lazy from winter_dragon.cogs.team.models import Team, TeamOrigin
lazy from winter_dragon.cogs.team.service import create_temporary_teams, end_team, membership
lazy from winter_dragon.cogs.team.split import split_into
lazy from winter_dragon.stored import stored
lazy from winter_dragon.voice_channels import EmptiedChannels, VoiceOccupancy


if TYPE_CHECKING:
    lazy from wd_discord import GatewayGuild, VoiceState


class TeamVoiceChannel(DiscordKeyedModel, table=True):
    """A voice channel made for a team of a voice split; ``id`` is the channel's, deleted once empty."""

    ownership: ClassVar[Ownership] = Ownership(guild="guild_id")

    guild_id: int = Field(sa_type=BigInteger, index=True)
    team_id: int = Field(index=True)


VOICE_TABLES = (TeamVoiceChannel,)
CHANNEL_REFUSAL = "I couldn't create your team's channel; do I have the Manage Channels permission?"
"""What a member hears when their team's voice channel can't be made."""


class Voice(
    GroupCog,
    name="voice",
    description="Voice channel tools: split everyone in your channel into teams",
    contexts=[InteractionContextType.GUILD],
):
    """Splits the members of a voice channel into random teams, and gives each team a voice channel to move to."""

    rng = Random()  # noqa: S311 - drawing teams isn't cryptography
    """Draws the teams of a split; tests replace it with a seeded one."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Start without knowing who is in which voice channel; GUILD_CREATE fills that in."""
        super().__init__(**kwargs)
        self.voice = VoiceOccupancy()
        self._lock = asyncio.Lock()

    @property
    def channels(self) -> EmptiedChannels[TeamVoiceChannel]:
        """The team voice channels, deleted once empty."""
        return EmptiedChannels(
            TeamVoiceChannel,
            self.bind,
            self.bot.client,
            self.logger,
            "Team channel is empty",
            on_forgotten=self._channel_gone,
        )

    @override
    async def load(self) -> None:
        """Create the voice tables if missing."""
        self.create_tables(*VOICE_TABLES)

    @staticmethod
    def _channel_gone(session: Session, row: TeamVoiceChannel) -> None:
        """End the team of a deleted team channel, once the team has no channel left."""
        remaining = session.exec(alive(TeamVoiceChannel).where(TeamVoiceChannel.team_id == row.team_id)).first()
        if remaining is not None:
            return
        team = alive_by_id(session, Team, row.team_id)
        if team is not None:
            end_team(session, team, utc_now())

    @Cog.listener(EventName.GUILD_CREATE)
    async def on_guild_create(self, guild: GatewayGuild) -> None:
        """Learn who is in which voice channel, then delete the team channels that emptied while offline."""
        guild_id = guild.id
        self.voice.reset(guild_id, guild.voice_states)
        await self.channels.sweep(self.voice, guild_id)

    @Cog.listener(EventName.VOICE_STATE_UPDATE)
    async def on_voice_state_update(self, state: VoiceState) -> None:
        """Track who joins and leaves voice, and delete a team channel the member left empty."""
        if state.guild is None:
            return
        guild_id, user_id = state.guild.id, state.user.id
        async with self._lock:
            after = None if state.channel is None else state.channel.id
            before = self.voice.move(guild_id, user_id, after)
            await self.channels.left(self.voice, guild_id, before, after)

    @Cog.command(name="split", description="Split everyone in your voice channel into random teams")
    async def split(
        self,
        interaction: GuildCommandInteraction,
        teams: Annotated[int, Describe("How many teams to split into"), Range(min_value=2, max_value=10)] = 2,
        move: Annotated[bool, Describe("Give each team a voice channel to move to")] = True,  # noqa: FBT002 - a boolean command option, as in tournament/cog.py
    ) -> None:
        """Draw temporary teams from the members of the caller's voice channel and post them in its chat."""
        channel_id = self.voice.channel_of(interaction.guild_id, interaction.user.id)
        if channel_id is None:
            msg = "Join a voice channel first."
            raise Refused(msg)
        members = self.voice.members_in(interaction.guild_id, channel_id)
        if len(members) < teams:
            msg = f"There aren't enough people in your voice channel for {teams} teams."
            raise Refused(msg)
        groups = split_into([int(member) for member in members], teams, self.rng)
        with Session(self.bind) as session:
            stored_teams = create_temporary_teams(session, groups, TeamOrigin.VOICE_SPLIT)
            session.commit()
            embed, rows = split_post(
                list(zip(stored_teams, groups, strict=True)),
                Teams.keep_button,
                move=(lambda team: self.move_button.custom_id(team.id or 0, channel_id)) if move else None,
            )
        sent = await self.bot.client.channels.partial(channel_id).send(embeds=[embed], components=rows)
        unwrap(sent, "I couldn't post in your voice channel's chat.")
        await interaction.respond(content=f"Posted the teams in <#{channel_id}>.", ephemeral=True)

    @Cog.component("team-move")
    async def move_button(self, interaction: GuildComponentInteraction, team_id: str, split_channel_id: str) -> None:
        """Move the presser to their team's voice channel, creating it on the team's first press."""
        user_id = int(interaction.user.id)
        with Session(self.bind) as session:
            team = stored(session, Team, int(team_id), "That team is gone.")
            if membership(session, team, user_id) is None:
                msg = "Only this team's members can move to its channel."
                raise Refused(msg)
            if team.ended_at is not None:
                msg = "That team has ended."
                raise Refused(msg)
            label = team.name
        async with self._lock:
            channel_id = await self._team_channel(interaction, int(team_id), label, split_channel_id)
        moved = await interaction.member.move_to(self.bot.client.channels.partial(channel_id), reason="Voice split")
        if is_network_error(moved):
            await interaction.respond(
                content="I couldn't move you; are you in a voice channel, and may I move members there?",
                ephemeral=True,
            )
            return
        await interaction.respond(content=f"Moved you to <#{channel_id}>.", ephemeral=True)

    async def _team_channel(
        self,
        interaction: GuildComponentInteraction,
        team_id: int,
        label: str,
        split_channel_id: str,
    ) -> int:
        """Return the ID of the team's voice channel, creating it next to the split channel when it has none."""
        with Session(self.bind) as session:
            existing = session.exec(alive(TeamVoiceChannel).where(TeamVoiceChannel.team_id == team_id)).first()
        if existing is not None:
            return int(existing.id)
        client = self.bot.client
        guild_id = int(interaction.guild_id)
        split_channel = await client.channels.partial(int(split_channel_id)).fetch()
        if is_network_error(split_channel):
            raise Refused(CHANNEL_REFUSAL)
        parent_id = None if split_channel.parent is None else split_channel.parent.id
        created = await client.guilds.partial(guild_id).create_channel(
            GuildChannelParams(name=label, type=ChannelType.GUILD_VOICE, parent_id=parent_id),
            reason="Voice split",
        )
        if is_network_error(created):
            raise Refused(CHANNEL_REFUSAL)
        with Session(self.bind) as session:
            session.add(TeamVoiceChannel(id=int(created.id), guild_id=guild_id, team_id=team_id))
            session.commit()
        return int(created.id)
