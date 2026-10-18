"""Confirmation embeds for something created, changed or deleted, in the colors set in ``config.ini``.

Only successful confirmations use them; a refusal or an error stays plain text. Each embed reads its color when
it's created, so a color changed in ``config.ini`` shows on the next reply without a restart.
"""

from __future__ import annotations

from pydantic import Field
from wd_discord.embed import Embed

lazy from winter_dragon.config import Settings


class CreatedEmbed(Embed):
    """Confirms that something was created, in ``Settings.created_color``."""

    color: int | None = Field(default_factory=lambda: int(Settings.created_color))


class ChangedEmbed(Embed):
    """Confirms that something was changed, in ``Settings.changed_color``."""

    color: int | None = Field(default_factory=lambda: int(Settings.changed_color))


class DeletedEmbed(Embed):
    """Confirms that something was deleted, in ``Settings.deleted_color``."""

    color: int | None = Field(default_factory=lambda: int(Settings.deleted_color))
