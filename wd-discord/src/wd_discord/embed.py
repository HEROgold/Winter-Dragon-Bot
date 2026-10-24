"""A minimal Discord embed model.

Only the fields existing commands need are modeled
(https://docs.discord.com/developers/resources/message#embed-object). Every embed
field is optional per Discord's docs; the ones not modeled yet are: ``type``, ``url``,
``timestamp``, ``image``, ``thumbnail``, ``video``, ``provider``, ``author``,
``flags`` - add them here as a future command actually needs them.
"""

from wd_discord.color import Color
from wd_discord.models import DiscordModel


MAX_EMBED_FIELDS = 25
"""An embed holds up to 25 fields (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_CHARACTERS = 6000
"""The combined length of an embed's title, description, field names/values and footer text (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_TITLE_LENGTH = 256
"""An embed title holds up to 256 characters (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_DESCRIPTION_LENGTH = 4096
"""An embed description holds up to 4096 characters (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_FIELD_NAME_LENGTH = 256
"""An embed field name holds up to 256 characters (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_FIELD_VALUE_LENGTH = 1024
"""An embed field value holds up to 1024 characters (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""


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
    color: Color | None = None
    fields: list[EmbedField] | None = None
    footer: EmbedFooter | None = None

    def character_count(self) -> int:
        """Return how many characters count towards Discord's :data:`MAX_EMBED_CHARACTERS` limit."""
        parts = [self.title or "", self.description or "", self.footer.text if self.footer else ""]
        parts += [part for field in self.fields or [] for part in (field.name, field.value)]
        return sum(len(part) for part in parts)
