"""The /team command group: create a lasting team, invite and manage its members, and leave it."""

from typing import Annotated
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session
from wd_bot.commands import Describe, Length, Lookup
lazy from wd_bot.cogs import Cog, GroupCog

# Command resolves option annotations from module globals at runtime, so these types must be available here.
lazy from wd_discord import (  # noqa: TC002 - wd_bot reads the handler's interaction type at runtime
    GuildCommandInteraction,
    GuildComponentInteraction,
    User,
)
lazy from wd_discord.components import ActionRow, Button, ButtonStyle
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType
lazy from wd_errors import Refused

lazy from winter_dragon.config import CogConfig
lazy from winter_dragon.stored import stored
lazy from winter_dragon.ui import ChangedEmbed, CreatedEmbed, DeletedEmbed, mentions

lazy from .models import TEAM_TABLES, Team
lazy from .service import (
    create_team,
    disband,
    hand_over,
    join,
    kick,
    leave,
    members_of,
    membership,
    require_captain,
    teams_of,
)


if TYPE_CHECKING:
    lazy from wd_discord import AutocompleteInteraction


class TeamSettings:
    """Settings for /team, in its ``cogs.ini`` section."""

    max_name_length = CogConfig(100)
    """The longest team name accepted."""


def _unended(team: Team) -> None:
    """Refuse when ``team`` has ended."""
    if team.ended_at is not None:
        msg = "That team has ended."
        raise Refused(msg)


class Teams(
    GroupCog,
    name="team",
    description="Teams of members that outlast any one tournament",
    contexts=[InteractionContextType.GUILD],
):
    """Lasting teams: create one, see who is in it, and leave it.

    Every action refuses with :class:`~wd_errors.Refused` from inside its session, which drops the session's changes.
    """

    @override
    async def load(self) -> None:
        """Create the team tables if missing."""
        self.create_tables(*TEAM_TABLES)

    async def team_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        """Suggest the invoker's teams whose name contains what was typed."""
        user = interaction.user
        if user is None:
            return []
        with Session(self.bind) as session:
            teams = list(teams_of(session, int(user.id)))
        return [Lookup.choice(team, team.name) for team in teams if current.casefold() in team.name.casefold()]

    @Cog.command(name="create", description="Create a team, with you as its captain")
    async def create(
        self,
        interaction: GuildCommandInteraction,
        name: Annotated[
            str,
            Describe("The team's name"),
            Length(min_length=1, max_length=TeamSettings.max_name_length),
        ],
    ) -> None:
        """Create the lasting team ``name`` with the invoker as its captain."""
        with Session(self.bind) as session:
            team = create_team(session, name, int(interaction.user.id))
            session.commit()
            label = team.name
        await interaction.respond(
            embeds=[CreatedEmbed(description=f"Created **{label}**; you're its captain.")],
            ephemeral=True,
        )

    @Cog.command(name="show", description="Show a team's captain and members")
    async def show(
        self,
        interaction: GuildCommandInteraction,
        team: Annotated[Team, Lookup(team_choices), Describe("The team to show")],
    ) -> None:
        """Post the team's name, captain and members."""
        with Session(self.bind) as session:
            current = stored(session, Team, team.id or 0, "That team is gone.")
            _unended(current)
            member_ids = [member.user_id for member in members_of(session, current.id or 0)]
            captain = [] if current.captain_id is None else [current.captain_id]
            embed = Embed(
                title=current.name,
                fields=[
                    EmbedField(name="Captain", value=mentions(captain)),
                    EmbedField(name=f"Members ({len(member_ids)})", value=mentions(member_ids)),
                ],
            )
        await interaction.respond(embeds=[embed])

    @Cog.command(name="leave", description="Leave a team")
    async def leave_team(
        self,
        interaction: GuildCommandInteraction,
        team: Annotated[Team, Lookup(team_choices), Describe("The team to leave")],
    ) -> None:
        """Take the invoker out of the team."""
        with Session(self.bind) as session:
            current = stored(session, Team, team.id or 0, "That team is gone.")
            _unended(current)
            leave(session, current, int(interaction.user.id))
            session.commit()
            label = current.name
        await interaction.respond(embeds=[DeletedEmbed(description=f"You left **{label}**.")], ephemeral=True)

    @Cog.command(name="invite", description="Invite a member to a team you captain")
    async def invite(
        self,
        interaction: GuildCommandInteraction,
        team: Annotated[Team, Lookup(team_choices), Describe("The team to invite to")],
        member: Annotated[User, Describe("The member to invite")],
    ) -> None:
        """Post a public invite with a Join button that only ``member`` can press."""
        captain_id = int(interaction.user.id)
        invitee_id = int(member.id)
        with Session(self.bind) as session:
            current = stored(session, Team, team.id or 0, "That team is gone.")
            _unended(current)
            require_captain(current, captain_id)
            if member.bot:
                msg = "Bots can't join teams."
                raise Refused(msg)
            if membership(session, current, invitee_id) is not None:
                msg = "They're in that team already."
                raise Refused(msg)
            label = current.name
            team_id = current.id or 0
        join_button = Button(
            style=ButtonStyle.SUCCESS,
            label="Join",
            custom_id=self.accept_invite.custom_id(team_id, invitee_id),
        )
        await interaction.respond(
            embeds=[Embed(description=f"<@{invitee_id}>, <@{captain_id}> invites you to **{label}**.")],
            components=[ActionRow(components=[join_button])],
        )

    @Cog.component("team-invite")
    async def accept_invite(self, interaction: GuildComponentInteraction, team_id: str, invitee_id: str) -> None:
        """Join the invitee to the team when the invitee presses Join."""
        if int(interaction.user.id) != int(invitee_id):
            msg = "This invite isn't for you."
            raise Refused(msg)
        with Session(self.bind) as session:
            current = stored(session, Team, int(team_id), "That team is gone.")
            _unended(current)
            join(session, current, int(invitee_id))
            session.commit()
            label = current.name
        await interaction.update(
            embeds=[CreatedEmbed(description=f"<@{invitee_id}> joined **{label}**.")],
            components=[],
        )

    @Cog.command(name="kick", description="Take a member out of a team you captain")
    async def kick_member(
        self,
        interaction: GuildCommandInteraction,
        team: Annotated[Team, Lookup(team_choices), Describe("The team to remove the member from")],
        member: Annotated[User, Describe("The member to remove")],
    ) -> None:
        """Take ``member`` out of the team, for its captain."""
        with Session(self.bind) as session:
            current = stored(session, Team, team.id or 0, "That team is gone.")
            _unended(current)
            kick(session, current, int(interaction.user.id), int(member.id))
            session.commit()
            label = current.name
        await interaction.respond(
            embeds=[DeletedEmbed(description=f"Removed <@{member.id}> from **{label}**.")],
            ephemeral=True,
        )

    @Cog.command(name="captain", description="Hand a team's captaincy to a member")
    async def make_captain(
        self,
        interaction: GuildCommandInteraction,
        team: Annotated[Team, Lookup(team_choices), Describe("The team to hand over")],
        member: Annotated[User, Describe("The member to make captain")],
    ) -> None:
        """Make ``member`` the captain of the team, for its captain."""
        with Session(self.bind) as session:
            current = stored(session, Team, team.id or 0, "That team is gone.")
            _unended(current)
            hand_over(session, current, int(interaction.user.id), int(member.id))
            session.commit()
            label = current.name
        await interaction.respond(
            embeds=[ChangedEmbed(description=f"<@{member.id}> is now captain of **{label}**.")],
            ephemeral=True,
        )

    @Cog.command(name="disband", description="Disband a team you captain")
    async def disband_team(
        self,
        interaction: GuildCommandInteraction,
        team: Annotated[Team, Lookup(team_choices), Describe("The team to disband")],
    ) -> None:
        """Soft-delete the team and every membership, for its captain."""
        with Session(self.bind) as session:
            current = stored(session, Team, team.id or 0, "That team is gone.")
            _unended(current)
            disband(session, current, int(interaction.user.id))
            session.commit()
            label = current.name
        await interaction.respond(embeds=[DeletedEmbed(description=f"Disbanded **{label}**.")], ephemeral=True)
