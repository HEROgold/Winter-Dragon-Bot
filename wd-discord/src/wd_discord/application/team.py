"""Discord Team object and its members."""

from __future__ import annotations

lazy from enum import IntEnum

lazy from wd_discord.image import ImageHash
lazy from wd_discord.models import DiscordModel
lazy from wd_discord.snowflake import Snowflake
lazy from wd_discord.user import User


class MembershipState(IntEnum):
    """State of a team member's invitation."""

    INVITED = 1
    """The member has been invited to the team but has not yet accepted."""
    ACCEPTED = 2
    """The member has accepted the team invitation."""


class TeamMember(DiscordModel):
    """https://docs.discord.com/developers/topics/teams#data-models-team-member-object."""

    membership_state: MembershipState
    """The user's membership state on the team."""
    team_id: Snowflake
    """The id of the parent team of which they are a member."""
    user: User
    """The avatar, discriminator, id, and username of the user."""
    role: str
    """The role of the team member."""


class Team(DiscordModel):
    """https://docs.discord.com/developers/topics/teams#data-models-team-object."""

    icon: ImageHash | None
    """A hash of the image of the team's icon."""
    id: Snowflake
    """The unique id of the team."""
    members: list[TeamMember]
    """The members of the team."""
    name: str
    """The name of the team."""
    owner_user_id: Snowflake
    """The user id of the current team owner."""

    @property
    def owner(self) -> TeamMember | None:
        """Return the owner of the team, if they are a member."""
        for member in self.members:
            if member.user.id == self.owner_user_id:
                return member
        return None
