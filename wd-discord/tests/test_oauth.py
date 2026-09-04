"""Unit tests: OAuth2 scope enum and combination operator."""
from __future__ import annotations

lazy import pytest
lazy from wd_discord.oauth import OAuthScopes


def test_scope_values() -> None:
    assert OAuthScopes.IDENTIFY == "identify"
    assert OAuthScopes.EMAIL == "email"
    assert OAuthScopes.PREMIUM == "premium"


def test_or_combines_two_scopes() -> None:
    assert OAuthScopes.IDENTIFY | OAuthScopes.EMAIL == "identify.email"


def test_or_combines_scope_and_str() -> None:
    assert OAuthScopes.IDENTIFY | "email" == "identify.email"


@pytest.mark.xfail(
    reason="__or__ has no default case: unknown types fall through to None instead of raising.",
    strict=True,
)
def test_or_rejects_unknown_type() -> None:
    with pytest.raises(TypeError):
        _ = OAuthScopes.IDENTIFY | 123  # type: ignore[operator]
