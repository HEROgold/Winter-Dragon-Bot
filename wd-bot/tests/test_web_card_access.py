"""Unit tests: whether a member could see a channel in Discord, which decides who may open its card (no network)."""

from wd_discord.permissions import Permissions
from wd_discord.resources.channel import OverwriteType, PermissionOverwrite
from wd_discord.snowflake import Snowflake

from winter_dragon.web.card_access import GuildMember, can_view_channel


GUILD = Snowflake(10)
OWNER = Snowflake(11)
MEMBER = Snowflake(12)
STAFF = Snowflake(20)
ROLES = {GUILD: Permissions.VIEW_CHANNEL, STAFF: Permissions.MANAGE_MESSAGES}


def overwrite(kind: OverwriteType, target: Snowflake, *, allow: Permissions = Permissions(0), deny: Permissions = Permissions(0)) -> PermissionOverwrite:
    return PermissionOverwrite(id=target, type=kind, allow=allow, deny=deny)


def can_view(*, roles: tuple[Snowflake, ...] = (), overwrites: tuple[PermissionOverwrite, ...] = (), member: Snowflake = MEMBER, role_permissions: dict[Snowflake, Permissions] | None = None) -> bool:
    who = GuildMember(GUILD, OWNER, member, roles, ROLES if role_permissions is None else role_permissions)
    return can_view_channel(who, overwrites)


def test_everyone_sees_a_channel_with_no_overwrites() -> None:
    assert can_view()


def test_the_guild_owner_sees_everything() -> None:
    hidden = overwrite(OverwriteType.ROLE, GUILD, deny=Permissions.VIEW_CHANNEL)

    assert can_view(member=OWNER, overwrites=(hidden,))


def test_an_administrator_role_sees_everything() -> None:
    hidden = overwrite(OverwriteType.ROLE, GUILD, deny=Permissions.VIEW_CHANNEL)
    permissions = ROLES | {STAFF: Permissions.ADMINISTRATOR}

    assert can_view(roles=(STAFF,), overwrites=(hidden,), role_permissions=permissions)


def test_a_private_channel_hides_from_everyone_but_the_role_let_in() -> None:
    hidden = overwrite(OverwriteType.ROLE, GUILD, deny=Permissions.VIEW_CHANNEL)
    staff = overwrite(OverwriteType.ROLE, STAFF, allow=Permissions.VIEW_CHANNEL)

    assert not can_view(overwrites=(hidden, staff))
    assert can_view(roles=(STAFF,), overwrites=(hidden, staff))


def test_a_member_overwrite_beats_the_role_overwrites() -> None:
    hidden = overwrite(OverwriteType.ROLE, GUILD, deny=Permissions.VIEW_CHANNEL)
    invited = overwrite(OverwriteType.MEMBER, MEMBER, allow=Permissions.VIEW_CHANNEL)
    banned = overwrite(OverwriteType.MEMBER, MEMBER, deny=Permissions.VIEW_CHANNEL)

    assert can_view(overwrites=(hidden, invited))
    assert not can_view(overwrites=(banned,))


def test_an_overwrite_for_someone_else_changes_nothing() -> None:
    other = overwrite(OverwriteType.MEMBER, Snowflake(99), deny=Permissions.VIEW_CHANNEL)

    assert can_view(overwrites=(other,))
