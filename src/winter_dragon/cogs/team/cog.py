"""The /team command group: create a lasting team, split members into temporary ones, invite, manage and leave teams."""

from random import Random
from typing import Annotated
lazy from datetime import timedelta
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session
from wd_bot.commands import Describe, Length, Lookup, Range
lazy from wd_bot.cogs import Cog, GroupCog

# Command resolves option annotations from module globals at runtime, so these types must be available here.
lazy from wd_discord import (
    GuildCommandInteraction,
    GuildComponentInteraction,
    User,
)
lazy from wd_discord.components import ActionRow, Button, ButtonStyle, Label, Modal, TextInput, UserSelect
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType
lazy from wd_discord.snowflake import Snowflake
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

from winter_dragon.config import CogConfig
lazy from winter_dragon.stored import stored
lazy from winter_dragon.ui import ChangedEmbed, CreatedEmbed, DeletedEmbed, mentions

lazy from .cards import split_post
lazy from .models import TEAM_TABLES, Team, TeamOrigin
lazy from .service import (
    create_team,
    create_temporary_teams,
    disband,
    end_expired,
    hand_over,
    join,
    keep,
    kick,
    leave,
    members_of,
    membership,
    require_captain,
    require_keepable,
    teams_of,
)
lazy from .split import split_into


if TYPE_CHECKING:
    lazy from wd_discord import AutocompleteInteraction, ModalSubmitInteraction


KEEP_NAME_INPUT = "name"
"""The ``custom_id`` of the text input in the Keep modal."""


class TeamSettings:
    """Settings for /team, in its ``cogs.ini`` section."""

    max_name_length = CogConfig(100)
    """The longest team name accepted."""
    temporary_lifetime_hours = CogConfig(24)
    """How long a temporary team nobody keeps lasts."""


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
    """Lasting teams: create one, see who is in it, and leave it. Temporary teams come from a split and can be kept.

    Every action refuses with :class:`~wd_errors.Refused` from inside its session, which drops the session's changes.
    """

    rng = Random()  # noqa: S311 - drawing teams isn't cryptography
    """Draws the teams of a split; tests replace it with a seeded one."""

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
            teams = list(teams_of(session, user.id))
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
            team = create_team(session, name, interaction.user.id)
            session.commit()
            label = team.name
        await interaction.respond(
            embeds=[CreatedEmbed(description=f"Created **{label}**; you're its captain.")],
            ephemeral=True,
        )

    @Cog.command(name="split", description="Split members into random temporary teams")
    async def split(
        self,
        interaction: GuildCommandInteraction,
        teams: Annotated[int, Describe("How many teams to split into"), Range(min_value=2, max_value=10)] = 2,
    ) -> None:
        """Ask for the members to split, with a user select menu taking at least ``teams`` and at most 25 of them."""
        select = UserSelect(
            custom_id=self.split_select.custom_id(teams),
            placeholder="Members",
            min_values=teams,
            max_values=25,
        )
        await interaction.respond(
            content=f"Pick the members to split into {teams} teams.",
            components=[ActionRow(components=[select])],
            ephemeral=True,
        )

    @Cog.component("team-split")
    async def split_select(self, interaction: GuildComponentInteraction, teams: str) -> None:
        """Draw temporary teams from the picked members and post them publicly, each with a Keep button."""
        count = int(teams)
        member_ids = [Snowflake.coerce(value) for value in interaction.values]
        if len(member_ids) < count:
            msg = f"Pick at least {count} members for {count} teams."
            raise Refused(msg)
        groups = split_into(member_ids, count, self.rng)
        with Session(self.bind) as session:
            stored_teams = create_temporary_teams(session, groups, TeamOrigin.TEXT_SPLIT)
            session.commit()
            embed, rows = split_post(list(zip(stored_teams, groups, strict=True)), self.keep_button)
        await interaction.respond(embeds=[embed], components=rows)

    @Cog.component("team-keep")
    async def keep_button(self, interaction: GuildComponentInteraction, team_id: str) -> None:
        """Open the modal asking for a name, when the presser may keep the temporary team."""
        with Session(self.bind) as session:
            current = stored(session, Team, int(team_id), "That team is gone.")
            require_keepable(session, current, interaction.user.id)
        modal = Modal(
            custom_id=self.keep_modal.custom_id(team_id),
            title="Keep this team",
            components=[
                Label(
                    label="Team name",
                    component=TextInput(custom_id=KEEP_NAME_INPUT, min_length=1, max_length=100),
                ),
            ],
        )
        await interaction.show_modal(modal)

    @Cog.modal("team-keep-name")
    async def keep_modal(self, interaction: ModalSubmitInteraction, team_id: str) -> None:
        """Make the temporary team lasting under the submitted name, with the presser as captain."""
        user = interaction.user
        if user is None:
            return
        with Session(self.bind) as session:
            current = stored(session, Team, int(team_id), "That team is gone.")
            keep(session, current, user.id, interaction.values.get(KEEP_NAME_INPUT, ""))
            session.commit()
            label = current.name
        await interaction.respond(
            embeds=[CreatedEmbed(description=f"Kept as **{label}**; you're its captain.")],
            ephemeral=True,
        )

    @Cog.periodic(seconds=600)
    async def end_expired_teams(self) -> None:
        """End the temporary teams nobody kept within ``temporary_lifetime_hours``."""
        with Session(self.bind) as session:
            end_expired(session, utc_now(), timedelta(hours=TeamSettings.temporary_lifetime_hours))
            session.commit()

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
            member_ids = [Snowflake(member.user_id) for member in members_of(session, current)]
            captain = [] if current.captain_id is None else [Snowflake(current.captain_id)]
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
            leave(session, current, interaction.user.id)
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
        captain_id = interaction.user.id
        invitee_id = member.id
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
        invitee = Snowflake.coerce(invitee_id)
        if interaction.user.id != invitee:
            msg = "This invite isn't for you."
            raise Refused(msg)
        with Session(self.bind) as session:
            current = stored(session, Team, int(team_id), "That team is gone.")
            _unended(current)
            join(session, current, invitee)
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
            kick(session, current, interaction.user.id, member.id)
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
            hand_over(session, current, interaction.user.id, member.id)
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
            disband(session, current, interaction.user.id)
            session.commit()
            label = current.name
        await interaction.respond(embeds=[DeletedEmbed(description=f"Disbanded **{label}**.")], ephemeral=True)
