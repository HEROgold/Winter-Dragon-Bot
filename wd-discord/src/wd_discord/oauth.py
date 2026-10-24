lazy from enum import StrEnum


class OAuthScopes(StrEnum):
    """OAuth2 Scopes for the User Object.

    https://docs.discord.com/developers/topics/oauth2#shared-resources-oauth2-scopes
    """

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
