"""A minimal Discord embed model.

Only the fields needed to replicate ``wd_cogs/games/love_meter.py``'s presentation
(https://docs.discord.com/developers/resources/message#embed-object) are modeled. Every embed
field is optional per Discord's docs; the ones not modeled yet are: ``type``, ``url``,
``timestamp``, ``footer``, ``image``, ``thumbnail``, ``video``, ``provider``, ``author``,
``flags`` — add them here (and to :class:`EmbedField` for ``fields``' nested shape, already
covered) as a future command actually needs them.
"""
from __future__ import annotations

from wd_discord.models import DiscordModel


class EmbedField(DiscordModel):
    """One entry in an embed's ``fields`` array."""

    name: str
    value: str
    inline: bool = False


class Embed(DiscordModel):
    """A Discord message embed (minimal subset - see module docstring for what's missing)."""

    title: str | None = None
    description: str | None = None
    color: int | None = None
    fields: list[EmbedField] | None = None
