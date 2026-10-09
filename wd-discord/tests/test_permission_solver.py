"""Unit tests: PermissionSolver works out a member's guild and channel permissions like Discord does."""

from __future__ import annotations

from wd_discord.permission_solver import PermissionSolver
from wd_discord.permissions import Permissions
from wd_discord.resources.channel import Channel
from wd_discord.resources.guild import Guild, GuildMember
from wd_discord.testing import GUILD_JSON


VIEW = Permissions.VIEW_CHANNEL
MANAGE = Permissions.MANAGE_CHANNELS
SEND = Permissions.SEND_MESSAGES
MOD_ROLE = "5"


def _role(role_id: str, permissions: Permissions) -> dict[str, object]:
    return {
        "id": role_id,
        "name": role_id,
        "color": 0,
        "hoist": False,
        "position": 0,
        "permissions": str(int(permissions)),
        "managed": False,
        "mentionable": False,
        "flags": 0,
    }


def _solver(*roles: str, user_id: str = "7", mod: Permissions = MANAGE) -> PermissionSolver:
    guild = Guild.model_validate({**GUILD_JSON, "roles": [_role("1", VIEW | SEND), _role(MOD_ROLE, mod)]})
    member = GuildMember.model_validate(
        {
            "user": {"id": user_id, "username": "member", "discriminator": "0"},
            "roles": list(roles),
            "joined_at": None,
            "deaf": False,
            "mute": False,
        },
    )
    return PermissionSolver(guild, member)


def _channel(*overwrites: tuple[str, int, Permissions, Permissions]) -> Channel:
    return Channel.model_validate(
        {
            "id": "20",
            "type": 0,
            "permission_overwrites": [
                {"id": target, "type": kind, "allow": str(int(allow)), "deny": str(int(deny))}
                for target, kind, allow, deny in overwrites
            ],
        },
    )


def test_base_adds_everyone_and_the_members_roles() -> None:
    assert _solver().base() == VIEW | SEND
    assert _solver(MOD_ROLE).base() == VIEW | SEND | MANAGE


def test_the_owner_and_administrators_hold_everything() -> None:
    hidden = _channel(("1", 0, Permissions.none(), VIEW))
    assert _solver(user_id="9").in_channel(hidden) == Permissions.all()
    assert _solver(MOD_ROLE, mod=Permissions.ADMINISTRATOR).in_channel(hidden) == Permissions.all()


def test_overwrites_apply_everyone_then_roles_then_member() -> None:
    everyone_hidden = ("1", 0, Permissions.none(), VIEW)
    mods_see = ("5", 0, VIEW, Permissions.none())
    member_muted = ("7", 1, Permissions.none(), SEND)
    assert _solver(MOD_ROLE).in_channel(_channel(everyone_hidden)) == SEND | MANAGE
    assert _solver(MOD_ROLE).in_channel(_channel(everyone_hidden, mods_see)) == VIEW | SEND | MANAGE
    assert _solver(MOD_ROLE).in_channel(_channel(everyone_hidden, mods_see, member_muted)) == VIEW | MANAGE
    assert _solver().in_channel(_channel(everyone_hidden, mods_see)) == SEND


def test_a_member_overwrite_beats_a_role_denial() -> None:
    mods_hidden = ("5", 0, Permissions.none(), VIEW)
    member_sees = ("7", 1, VIEW, Permissions.none())
    assert VIEW in _solver(MOD_ROLE).in_channel(_channel(mods_hidden, member_sees))
    assert VIEW not in _solver(MOD_ROLE).in_channel(_channel(mods_hidden))
