from __future__ import annotations

lazy from enum import StrEnum


class OAuthScopes(StrEnum):
    """OAuth2 Scopes for the User Object."""

    IDENTIFY = "identify"
    EMAIL = "email"
    PREMIUM = "premium"

    def __or__(self, other: OAuthScopes | str) -> str:
        """Return the combination of two AuthScopes."""
        match other:
            case OAuthScopes():
                return f"{self.value}.{other.value}"
            case str():
                return f"{self.value}.{other}"
