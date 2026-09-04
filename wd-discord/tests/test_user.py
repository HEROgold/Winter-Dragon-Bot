"""Unit tests: user profile models and scope validation."""
from __future__ import annotations

lazy from wd_discord.oauth import OAuthScopes
lazy from wd_discord.user.collectibles import Collectibles
lazy from wd_discord.user.profile import NamePlate, NamePlateBackgroundColor
lazy from wd_discord.user.user import User


def test_nameplate_background_color_values() -> None:
    assert NamePlateBackgroundColor.CRIMSON == "crimson"
    assert NamePlateBackgroundColor.BUBBLE_GUM == "bubble_gum"
    assert NamePlateBackgroundColor.WHITE == "white"


def test_nameplate_and_collectibles_construct() -> None:
    plate = NamePlate.model_validate(
        {
            "sku_id": "123",
            "asset": "nameplates/nameplates/twilight/",
            "label": "",
            "palette": NamePlateBackgroundColor.COBALT,
        },
    )
    collectibles = Collectibles(nameplate=plate)
    assert collectibles.nameplate is plate
    assert collectibles.nameplate.palette == NamePlateBackgroundColor.COBALT


def _user() -> User:
    """A fully-populated :class:`User` (values are placeholders); ``id`` is coerced to a Snowflake."""
    return User.model_validate(
        {
            "id": "123",
            "username": "user",
            "discriminator": "0001",
            "global_name": "User",
            "verified": True,
            "email": "user@example.com",
        },
    )


def test_validate_scopes_passes_with_all_scopes() -> None:
    allowed = {OAuthScopes.IDENTIFY, OAuthScopes.EMAIL, OAuthScopes.PREMIUM}
    assert _user().validate_scopes(allowed) is True


def test_validate_scopes_fails_when_required_scope_missing() -> None:
    # `email`/`verified` require the EMAIL scope; without it validation should fail.
    assert _user().validate_scopes({OAuthScopes.IDENTIFY}) is False
