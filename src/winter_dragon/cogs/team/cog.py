"""The /team command group: create a lasting team, see its captain and members, and leave it."""

from typing import Annotated
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session
from wd_bot.commands import Describe, Length, Lookup
lazy from wd_bot.cogs import Cog, GroupCog

# Command resolves option annotations from module globals at runtime, so GuildCommandInteraction must be available here.
lazy from wd_discord import (  # noqa: TC002 - wd_bot reads the handler's interaction type at runtime
    GuildCommandInteraction,
)
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType
lazy from wd_errors import Refused

lazy from winter_dragon.config import CogConfig
lazy from winter_dragon.stored import stored
lazy from winter_dragon.ui import CreatedEmbed, DeletedEmbed, mentions

lazy from .models import TEAM_TABLES, Team
lazy from .service import create_team, leave, members_of, teams_of


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
