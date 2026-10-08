"""A minimal Discord embed model.

Only the fields existing commands need are modeled
(https://docs.discord.com/developers/resources/message#embed-object). Every embed
field is optional per Discord's docs; the ones not modeled yet are: ``type``, ``url``,
``timestamp``, ``image``, ``thumbnail``, ``video``, ``provider``, ``author``,
``flags`` - add them here as a future command actually needs them.
"""

from __future__ import annotations

from wd_discord.models import DiscordModel


MAX_EMBED_FIELDS = 25
"""An embed holds up to 25 fields."""
MAX_EMBED_CHARACTERS = 6000
"""The combined length of an embed's title, description, field names/values and footer text."""


class EmbedField(DiscordModel):
    """One entry in an embed's ``fields`` array."""

    name: str
    value: str
    inline: bool = False


class EmbedFooter(DiscordModel):
    """The footer shown under an embed."""

    text: str
    icon_url: str | None = None


class Embed(DiscordModel):
    """A Discord message embed (minimal subset - see module docstring for what's missing)."""

    title: str | None = None
    description: str | None = None
    color: int | None = None
    fields: list[EmbedField] | None = None
    footer: EmbedFooter | None = None

    def character_count(self) -> int:
        """Return how many characters count towards Discord's :data:`MAX_EMBED_CHARACTERS` limit."""
        parts = [self.title or "", self.description or "", self.footer.text if self.footer else ""]
        parts += [part for field in self.fields or [] for part in (field.name, field.value)]
        return sum(len(part) for part in parts)
