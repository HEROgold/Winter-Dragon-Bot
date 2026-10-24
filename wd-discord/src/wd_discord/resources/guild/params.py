"""Request bodies for modifying guild members (https://docs.discord.com/developers/resources/guild#modify-guild-member)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
lazy from wd_core.client import MemberPayload

from wd_discord.resources.guild.member import GuildMemberFlags
from wd_discord.snowflake import Snowflake


class MemberParams(BaseModel):
    """The member attributes to change; the rest stay as they are.

    Discord takes each field as optional and nullable, so a field passed as ``None`` is sent as ``null``: that clears
    the nickname, lifts a timeout (``communication_disabled_until``) or disconnects from voice (``channel_id``). A
    field not passed isn't sent. Each needs its own permission, named on the field.
    """

    model_config = ConfigDict(extra="forbid")

    nick: Annotated[str, Field(max_length=32)] | None = None
    """The member's nickname; needs MANAGE_NICKNAMES."""
    roles: list[Snowflake] | None = None
    """Every role the member is to have, replacing their current roles; needs MANAGE_ROLES."""
    mute: bool | None = None
    """Server-mute them in voice; needs MUTE_MEMBERS, and fails when they aren't in a voice channel."""
    deaf: bool | None = None
    """Server-deafen them in voice; needs DEAFEN_MEMBERS, and fails when they aren't in a voice channel."""
    channel_id: Snowflake | None = None
    """The voice channel to move them to; ``None`` disconnects them. Needs MOVE_MEMBERS."""
    communication_disabled_until: datetime | None = None
    """When their timeout ends, at most 28 days ahead; ``None`` lifts it. Needs MODERATE_MEMBERS."""
    flags: GuildMemberFlags | None = None
    """The member's flags; needs MANAGE_GUILD, MANAGE_ROLES, or MODERATE_MEMBERS with KICK_ and BAN_MEMBERS."""

    def to_json(self) -> MemberPayload:
        """Return the request body: the fields passed, ``None`` as ``null``."""
        return MemberPayload(**self.model_dump(mode="json", exclude_unset=True))
