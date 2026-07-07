"""Unit tests: user profile models and scope validation."""
from __future__ import annotations

import pytest


# NOTE: user.py imports from herogold (IsAnnotated) and wd_discord.utils.strings,
# which can fail to import on Python 3.15 (herogold 3.3.0). Skip cleanly if so.
try:
    from wd_discord.oauth import OAuthScopes
    from wd_discord.user.collectibles import Collectibles
    from wd_discord.user.profile import NamePlate, NamePlateBackgroundColor
    from wd_discord.user.user import Users
except (ImportError, TypeError) as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"wd_discord.user is unimportable: {exc}", allow_module_level=True)


def test_nameplate_background_color_values() -> None:
    assert NamePlateBackgroundColor.CRIMSON == "crimson"
    assert NamePlateBackgroundColor.BUBBLE_GUM == "bubble_gum"
    assert NamePlateBackgroundColor.WHITE == "white"


def test_nameplate_and_collectibles_construct() -> None:
    plate = NamePlate(
        sku_id="123",
        asset="nameplates/nameplates/twilight/",
        label="",
        palette=NamePlateBackgroundColor.COBALT,
    )
    collectibles = Collectibles(nameplate=plate)
    assert collectibles.nameplate is plate
    assert collectibles.nameplate.palette == NamePlateBackgroundColor.COBALT


def _users() -> Users:
    """A fully-populated Users instance (values are placeholders; no validation)."""
    return Users(
        id="123",
        username="user",
        discriminator="0001",
        global_name="User",
        avatar=None,
        bot=None,
        system=None,
        mfa_enabled=None,
        banner=None,
        accent_color=None,
        locale=None,
        verified=True,
        email="user@example.com",
        flags=None,
        premium_type=None,
        public_flags=None,
        avatar_decoration_data=None,
        collectibles=None,
        primary_guild=None,
    )


def test_validate_scopes_passes_with_all_scopes() -> None:
    allowed = {OAuthScopes.IDENTIFY, OAuthScopes.EMAIL, OAuthScopes.PREMIUM}
    assert _users().validate_scopes(allowed) is True


@pytest.mark.xfail(
    reason="validate_scopes checks isinstance against dataclasses.Field (never IsAnnotated), "
    "so it never inspects metadata and always returns True.",
    strict=True,
)
def test_validate_scopes_fails_when_required_scope_missing() -> None:
    # `email`/`verified` require the EMAIL scope; without it validation should fail.
    assert _users().validate_scopes({OAuthScopes.IDENTIFY}) is False
