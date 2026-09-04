"""A minimal emoji reference carried by other Discord objects.

Several Discord objects (welcome-screen channels, forum tags, default reactions) reference an
emoji not as a full :class:`~wd_discord.guild.emoji.Emoji` resource object but as a bare
``emoji_id`` / ``emoji_name`` pair - a *partial* emoji. :class:`PartialEmoji` turns that pair into
a single object so callers get one value instead of two loose primitives. It lives at the package
root (like :mod:`~wd_discord.snowflake` / :mod:`~wd_discord.image`) so both the ``channel`` and
``guild`` subpackages can use it without importing one another.
"""
from __future__ import annotations

lazy from wd_discord.models import DiscordModel
lazy from wd_discord.snowflake import Snowflake


class PartialEmoji(DiscordModel):
    """A minimal emoji reference: a custom emoji ``id`` or a unicode ``name``.

    https://docs.discord.com/developers/resources/emoji#emoji-object-emoji-structure (the partial
    form used by welcome-screen channels, forum tags and default reactions).
    """

    id: Snowflake | None = None
    """The custom emoji's id, or ``None`` for a standard unicode emoji."""
    name: str | None = None
    """The custom emoji's name, or the unicode character for a standard emoji."""
    animated: bool | None = None
    """Whether the custom emoji is animated."""

    @property
    def is_custom(self) -> bool:
        """Whether this references a custom guild emoji (i.e. it has an ``id``)."""
        return self.id is not None

    @property
    def is_unicode(self) -> bool:
        """Whether this references a standard unicode emoji (a ``name`` but no ``id``)."""
        return self.id is None and self.name is not None

    @classmethod
    def from_fields(cls, emoji_id: Snowflake | None, emoji_name: str | None) -> PartialEmoji | None:
        """Build from a raw ``emoji_id`` / ``emoji_name`` pair; ``None`` when no emoji is set."""
        if emoji_id is None and emoji_name is None:
            return None
        return cls(id=emoji_id, name=emoji_name)
