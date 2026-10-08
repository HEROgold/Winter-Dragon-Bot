"""Interaction responses (https://docs.discord.com/developers/interactions/receiving-and-responding).

Discord expects an initial response within 3 seconds of the interaction. The token in that interaction
stays valid for 15 minutes afterwards, for editing the original response or sending follow-ups.
"""

from __future__ import annotations

from typing import TypedDict
lazy from enum import IntEnum, IntFlag
lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import components_payload
lazy from wd_discord.files import attachments_payload


if TYPE_CHECKING:
    lazy from collections.abc import Sequence

    lazy from wd_discord.components import ActionRow
    lazy from wd_discord.embed import Embed
    lazy from wd_discord.files import File


class InteractionCallbackType(IntEnum):
    """The kind of initial response sent to an interaction."""

    PONG = 1
    """Acknowledge a PING."""
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    """Respond with a message."""
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    """Acknowledge now and show a loading state; edit the original response later."""
    DEFERRED_UPDATE_MESSAGE = 6
    """Components only: acknowledge now and edit the component's message later, with no loading state."""
    UPDATE_MESSAGE = 7
    """Components only: edit the message the component is attached to."""
    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8
    MODAL = 9
    LAUNCH_ACTIVITY = 12


class MessageFlags(IntFlag):
    """Message flags an app can set when sending a message (subset)."""

    SUPPRESS_EMBEDS = 1 << 2
    EPHEMERAL = 1 << 6
    """Only the invoking user sees the message (interaction responses only)."""
    SUPPRESS_NOTIFICATIONS = 1 << 12


class MessageData(TypedDict, total=False):
    """The body of a response to an interaction (object -> API)."""

    content: str
    embeds: list[Embed]
    components: list[ActionRow]
    flags: MessageFlags
    attachments: list[dict[str, object]]
    """The partial attachment object of each uploaded file; see :mod:`wd_discord.files`."""
    choices: list[dict[str, object]]
    """Autocomplete suggestions (APPLICATION_COMMAND_AUTOCOMPLETE_RESULT only), as dumped choices."""


def message_data(
    *,
    content: str | None = None,
    embeds: Sequence[Embed] | None = None,
    components: Sequence[ActionRow] | None = None,
    flags: MessageFlags | None = None,
    files: Sequence[File] = (),
) -> MessageData:
    """Build a message body for sending or editing a message (object -> API).

    A ``None`` argument is left out of the body, so an edit keeps that part of the message unchanged; pass
    an empty sequence to clear the embeds or components instead. ``files`` only adds their ``attachments``; the
    files themselves go in the request body (see :func:`wd_discord.files.request_body`).
    """
    data: MessageData = {}
    if content is not None:
        data["content"] = content
    if embeds is not None:
        data["embeds"] = [embed.model_dump(mode="json", exclude_none=True) for embed in embeds]
    if components is not None:
        data["components"] = components_payload(components)
    if flags:
        data["flags"] = int(flags)
    if files:
        data["attachments"] = list(attachments_payload(files))
    return data
