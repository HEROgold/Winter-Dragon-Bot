"""Checks made before a command or component acts, and answering the user when one refuses.

Discord enforces ``default_member_permissions`` per top-level command only, so a subcommand that needs more says so
with ``@Cog.command(..., requires=...)`` and wd-bot checks it with :func:`require_permissions`. A guild-only command
gets its interaction through :func:`require_guild`. The bot's owners are the application's owner, or the members of
the team that owns it (https://docs.discord.com/developers/topics/teams).
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, overload

lazy from wd_discord import is_network_error, narrow_to_guild
lazy from wd_discord.permissions import Permissions
lazy from wd_discord.resources.application import MembershipState
lazy from wd_discord.snowflake import Snowflake
lazy from wd_errors import Refused


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from wd_discord import (
        AnyInteraction,
        Client,
        CommandInteraction,
        ComponentInteraction,
        GuildCommandInteraction,
        GuildComponentInteraction,
    )
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


def permission_names(permissions: Permissions) -> str:
    """Return ``permissions`` as Discord shows them: ``Manage Channels and Manage Guild``."""
    return " and ".join((flag.name or "").replace("_", " ").title() for flag in permissions)


def require_permissions(interaction: AnyInteraction, permissions: Permissions) -> None:
    """Refuse unless the member invoking ``interaction`` holds every one of ``permissions``."""
    if not member_has(interaction, permissions):
        member = interaction.member
        granted = Permissions(0) if member is None or member.permissions is None else member.permissions
        missing = permissions & ~granted
        msg = f"You need the {permission_names(missing or permissions)} permission for that."
        raise Refused(msg)


@overload
def require_guild(interaction: CommandInteraction) -> GuildCommandInteraction: ...
@overload
def require_guild(interaction: ComponentInteraction) -> GuildComponentInteraction: ...
def require_guild(
    interaction: CommandInteraction | ComponentInteraction,
) -> GuildCommandInteraction | GuildComponentInteraction:
    """Return ``interaction`` as sent from a guild, or refuse when it wasn't."""
    narrowed = narrow_to_guild(interaction)
    if narrowed is None:
        msg = "This only works in a server."
        raise Refused(msg)
    return narrowed


async def answer_refusal(interaction: AnyInteraction, refused: Refused) -> None:
    """Tell the user behind ``interaction``, privately, why their action was refused.

    Answers in a follow-up when the interaction got its initial response (or was deferred) already.
    """
    await interaction.respond(refused.message, ephemeral=True)


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
