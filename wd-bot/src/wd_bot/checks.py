"""Checks a command makes before acting: whether the invoker holds some permissions, or owns the bot.

Discord enforces ``default_member_permissions`` per top-level command only, so a group whose subcommands need
different permissions checks them itself with :func:`member_has`. The bot's owners are the application's owner, or
the members of the team that owns it (https://docs.discord.com/developers/topics/teams).
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord import is_network_error
lazy from wd_discord.permissions import Permissions
lazy from wd_discord.resources.application import MembershipState
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from wd_discord import AnyInteraction, Client
    lazy from wd_discord.entities import Application
    lazy from wd_discord.snowflake import SnowflakeLike


def member_has(interaction: AnyInteraction, permissions: Permissions) -> bool:
    """Whether the guild member invoking ``interaction`` holds every one of ``permissions`` in its channel.

    Administrators hold every permission; outside a guild nobody does.
    """
    member = interaction.member
    if member is None or member.permissions is None:
        return False
    return Permissions.ADMINISTRATOR in member.permissions or permissions in member.permissions


def owner_ids(application: Application) -> Generator[Snowflake]:
    """Yield the IDs of the users owning ``application``: its team's accepted members, or else its owner."""
    if application.team is not None:
        yield application.team.owner.id
        for member in application.team.members:
            if member.membership_state is MembershipState.ACCEPTED:
                yield member.user.id
    elif application.owner is not None:
        yield application.owner.id


async def is_owner(client: Client, user_id: SnowflakeLike) -> bool:
    """Whether the user ``user_id`` owns the bot; ``False`` when the application can't be read.

    Fetches the application each time, so it suits the occasional admin command, not a hot path.
    """
    application = await client.application.fetch()
    if is_network_error(application):
        return False
    return Snowflake.coerce(user_id) in set(owner_ids(application))
