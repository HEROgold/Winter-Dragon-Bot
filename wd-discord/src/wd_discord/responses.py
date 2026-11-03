"""Interaction responses (https://docs.discord.com/developers/interactions/receiving-and-responding).

Discord expects an initial response within 3 seconds of the interaction. The token in that interaction
stays valid for 15 minutes afterwards, for editing the original response or sending follow-ups.
"""

from typing import TypedDict
lazy from enum import IntEnum, IntFlag
lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import components_payload, is_layout
lazy from wd_discord.files import attachments_payload


if TYPE_CHECKING:
    lazy from collections.abc import Sequence

    lazy from wd_discord.components import MessageComponent
    lazy from wd_discord.embed import Embed
    lazy from wd_discord.files import File


class InteractionCallbackType(IntEnum):
    """The kind of initial response sent to an interaction.

    https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-response-object-interaction-callback-type
    """

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
    """Message flags an app can set when sending a message (subset).

    https://docs.discord.com/developers/resources/message#message-object-message-flags
    """

    SUPPRESS_EMBEDS = 1 << 2
    EPHEMERAL = 1 << 6
    """Only the invoking user sees the message (interaction responses only)."""
    SUPPRESS_NOTIFICATIONS = 1 << 12
    IS_COMPONENTS_V2 = 1 << 15
    """The message is laid out with components v2; it can't have ``content`` or ``embeds``, and keeps the flag for good."""


class MessageData(TypedDict, total=False):
    """The body of a response to an interaction (object -> API)."""

    content: str | None
    embeds: list[Embed]
    components: list[MessageComponent]
    flags: MessageFlags
    attachments: list[dict[str, object]]
    """The partial attachment object of each uploaded file; see :mod:`wd_discord.files`."""
    choices: list[dict[str, object]]
    """Autocomplete suggestions (APPLICATION_COMMAND_AUTOCOMPLETE_RESULT only), as dumped choices."""


class ModalData(TypedDict):
    """The body of a MODAL response to an interaction (object -> API)."""

    custom_id: str
    title: str
    components: list[dict[str, object]]


def message_data(
    *,
    content: str | None = None,
    embeds: Sequence[Embed] | None = None,
    components: Sequence[MessageComponent] | None = None,
    flags: MessageFlags | None = None,
    files: Sequence[File] = (),
) -> MessageData:
    """Build a message body for sending or editing a message (object -> API).

    A ``None`` argument is left out of the body, so an edit keeps that part of the message unchanged; pass
    an empty sequence to clear the embeds or components instead. ``files`` only adds their ``attachments``; the
    files themselves go in the request body (see :func:`wd_discord.files.request_body`).

    Components laid out with components v2 (see :func:`~wd_discord.components.is_layout`) set the
    ``IS_COMPONENTS_V2`` flag, and raise :class:`ValueError` next to any ``content`` or ``embeds``. Their body
    resets ``content`` and ``embeds``, which Discord requires when an edit turns a legacy message into v2.
    """
    data: MessageData = {}
    if components is not None and is_layout(components):
        if content or embeds:
            msg = "A components v2 message can't have content or embeds"
            raise ValueError(msg)
        flags = (flags or MessageFlags(0)) | MessageFlags.IS_COMPONENTS_V2
        data["content"] = None
        embeds = []
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
