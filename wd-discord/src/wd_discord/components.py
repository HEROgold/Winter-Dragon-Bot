"""Legacy message components: action rows and buttons (https://docs.discord.com/developers/components/reference).

Only the legacy layout is modeled: action rows holding buttons, sent next to ``content``/``embeds``.
The ``IS_COMPONENTS_V2`` flag would disable ``content`` and ``embeds`` entirely, so it isn't supported here.
"""

from __future__ import annotations

lazy from collections import Counter
lazy from enum import IntEnum
lazy from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    lazy from collections.abc import Sequence


MAX_ACTION_ROW_BUTTONS = 5
"""An action row holds up to 5 buttons."""
MAX_MESSAGE_COMPONENTS = 40
"""A message holds up to 40 components in total, counting nested ones."""
MAX_CUSTOM_ID_LENGTH = 100


class ComponentType(IntEnum):
    """The type of a component."""

    ACTION_ROW = 1
    BUTTON = 2
    STRING_SELECT = 3
    TEXT_INPUT = 4
    USER_SELECT = 5
    ROLE_SELECT = 6
    MENTIONABLE_SELECT = 7
    CHANNEL_SELECT = 8
    SECTION = 9
    TEXT_DISPLAY = 10
    THUMBNAIL = 11
    MEDIA_GALLERY = 12
    FILE = 13
    SEPARATOR = 14
    CONTAINER = 17
    LABEL = 18
    FILE_UPLOAD = 19
    RADIO_GROUP = 21
    CHECKBOX_GROUP = 22
    CHECKBOX = 23


class ButtonStyle(IntEnum):
    """How a button looks, and what clicking it does."""

    PRIMARY = 1
    SECONDARY = 2
    SUCCESS = 3
    DANGER = 4
    LINK = 5
    """Opens ``url``; sends no interaction."""
    PREMIUM = 6
    """Opens the purchase flow for ``sku_id``; sends no interaction."""


type CustomId = Annotated[str, StringConstraints(min_length=1, max_length=MAX_CUSTOM_ID_LENGTH)]
"""A developer-defined identifier, sent back in the interaction when the component is used."""


class Button(BaseModel):
    """A clickable button; must sit inside an :class:`ActionRow`."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.BUTTON] = ComponentType.BUTTON
    style: ButtonStyle
    label: Annotated[str, StringConstraints(max_length=80)] | None = None
    custom_id: CustomId | None = None
    sku_id: Snowflake | None = None
    url: Annotated[str, StringConstraints(max_length=512)] | None = None
    disabled: bool = False

    @model_validator(mode="after")
    def _check_style_rules(self) -> Self:
        """Enforce which of ``custom_id``/``url``/``sku_id``/``label`` each style takes."""
        match self.style:
            case ButtonStyle.LINK:
                if self.url is None or self.custom_id is not None or self.sku_id is not None:
                    msg = "LINK buttons need a url, and take no custom_id or sku_id"
                    raise ValueError(msg)
            case ButtonStyle.PREMIUM:
                if self.sku_id is None or self.custom_id is not None or self.url is not None or self.label is not None:
                    msg = "PREMIUM buttons need a sku_id, and take no custom_id, url or label"
                    raise ValueError(msg)
            case _:
                if self.custom_id is None or self.url is not None or self.sku_id is not None:
                    msg = f"{self.style.name} buttons need a custom_id, and take no url or sku_id"
                    raise ValueError(msg)
        return self


class ActionRow(BaseModel):
    """A row of up to 5 buttons at the bottom of a message."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.ACTION_ROW] = ComponentType.ACTION_ROW
    components: Annotated[list[Button], Field(min_length=1, max_length=MAX_ACTION_ROW_BUTTONS)]


def components_payload(rows: Sequence[ActionRow]) -> list[ActionRow]:
    """Return the ``components`` JSON for a message, checking the message-wide limits.

    Raises :class:`ValueError` when the message has more than 40 components or reuses a ``custom_id``,
    both of which Discord rejects.
    """
    total = sum(1 + len(row.components) for row in rows)
    if total > MAX_MESSAGE_COMPONENTS:
        msg = f"A message holds at most {MAX_MESSAGE_COMPONENTS} components, got {total}"
        raise ValueError(msg)
    custom_ids = Counter(button.custom_id for row in rows for button in row.components if button.custom_id is not None)
    if duplicates := sorted(custom_id for custom_id, count in custom_ids.items() if count > 1):
        msg = f"custom_id must be unique within a message, duplicated: {duplicates}"
        raise ValueError(msg)
    return [row.model_dump(mode="json", exclude_none=True) for row in rows]
