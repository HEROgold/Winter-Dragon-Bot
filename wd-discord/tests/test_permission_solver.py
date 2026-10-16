"""Unit tests: PermissionSolver works out a member's guild and channel permissions like Discord does."""

from __future__ import annotations

from wd_discord.permission_solver import PermissionSolver
from wd_discord.permissions import Permissions
from wd_discord.resources.channel import Channel
from wd_discord.resources.guild import Guild, GuildMember, Role
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


def _ranked(
    role_id: str,
    position: int,
    permissions: Permissions = Permissions.none(),
    *,
    managed: bool = False,
) -> dict[str, object]:
    return {**_role(role_id, permissions), "position": position, "managed": managed}


def _giver(*own_roles: str, user_id: str = "7") -> PermissionSolver:
    """A member of a guild whose roles, highest first: 30 (position 5), 40 (4, admin), 31 and 32 (both 3), 33 (managed).

    30, 31 and 32 grant MANAGE_ROLES.
    """
    roles = [
        _role("1", Permissions.none()),
        _ranked("30", 5, Permissions.MANAGE_ROLES),
        _ranked("31", 3, Permissions.MANAGE_ROLES),
        _ranked("32", 3, Permissions.MANAGE_ROLES),
        _ranked("33", 1, managed=True),
        _ranked("40", 4, Permissions.ADMINISTRATOR),
    ]
    guild = Guild.model_validate({**GUILD_JSON, "id": "1", "roles": roles})
    member = GuildMember.model_validate(
        {"user": {"id": user_id, "username": "m", "discriminator": "0"}, "roles": list(own_roles), "joined_at": None, "deaf": False, "mute": False},
    )
    return PermissionSolver(guild, member)


def _role_of(solver: PermissionSolver, role_id: str) -> Role:
    return next(role for role in solver.guild.roles if str(role.id) == role_id)


def test_a_role_manager_gives_roles_below_their_highest() -> None:
    solver = _giver("30")
    assert solver.can_give_role(_role_of(solver, "31"))
    assert not solver.can_give_role(_role_of(solver, "30"))  # their own highest isn't below itself
    assert solver.can_give_role(_role_of(solver, "40"))  # an admin role, but ranked below theirs


def test_equal_positions_rank_the_lower_id_higher() -> None:
    lower_id = _giver("31")
    higher_id = _giver("32")
    assert lower_id.can_give_role(_role_of(lower_id, "32"))
    assert not higher_id.can_give_role(_role_of(higher_id, "31"))


def test_administrator_still_needs_a_higher_role() -> None:
    admin = _giver("40")
    assert admin.can_give_role(_role_of(admin, "31"))
    assert not admin.can_give_role(_role_of(admin, "30"))


def test_a_member_without_manage_roles_gives_nothing() -> None:
    plain = _giver()
    assert not plain.can_give_role(_role_of(plain, "31"))


def test_nobody_gives_a_managed_role_or_everyone() -> None:
    owner = _giver(user_id="9")
    assert not owner.can_give_role(_role_of(owner, "33"))
    assert not owner.can_give_role(_role_of(owner, "1"))


def test_the_owner_gives_any_other_role() -> None:
    owner = _giver(user_id="9")
    assert owner.can_give_role(_role_of(owner, "40"))
    assert owner.can_give_role(_role_of(owner, "30"))
