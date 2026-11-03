"""Message components (https://docs.discord.com/developers/components/reference).

A message lays out its components one of two ways. Legacy messages hold only action rows of buttons and selects,
sent next to ``content`` and ``embeds``. Components v2 messages are built from layout components instead
(:class:`Container`, :class:`Section`, :class:`TextDisplay`, :class:`MediaGallery`, :class:`Separator`,
:class:`FileDisplay`) and can't have ``content`` or ``embeds``. :func:`wd_discord.responses.message_data` picks
the layout from the components it's given: any top-level component other than an :class:`ActionRow` makes it v2.
"""

lazy from collections import Counter
lazy from enum import IntEnum
lazy from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from wd_discord.color import Color
from wd_discord.open_enum import OpenIntEnum
from wd_discord.partial_emoji import PartialEmoji
from wd_discord.snowflake import Snowflake
lazy from wd_discord.limits import (
    MAX_ACTION_ROW_BUTTONS,
    MAX_BUTTON_LABEL_LENGTH,
    MAX_CUSTOM_ID_LENGTH,
    MAX_LABEL_LENGTH,
    MAX_MEDIA_DESCRIPTION_LENGTH,
    MAX_MEDIA_GALLERY_ITEMS,
    MAX_MESSAGE_COMPONENTS,
    MAX_MODAL_TITLE_LENGTH,
    MAX_SECTION_TEXT_DISPLAYS,
    MAX_SELECT_OPTION_LENGTH,
    MAX_SELECT_OPTIONS,
    MAX_TEXT_DISPLAY_CHARACTERS,
    MAX_TEXT_INPUT_LENGTH,
)


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Sequence


class ComponentType(OpenIntEnum):
    """The type of a component.

    https://docs.discord.com/developers/components/reference#component-object-component-types
    """

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


class ButtonStyle(OpenIntEnum):
    """How a button looks, and what clicking it does.

    https://docs.discord.com/developers/components/reference#button-button-styles
    """

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
    label: Annotated[str, StringConstraints(max_length=MAX_BUTTON_LABEL_LENGTH)] | None = None
    custom_id: CustomId | None = None
    sku_id: Snowflake | None = None
    url: Annotated[str, StringConstraints(max_length=512)] | None = None
    emoji: PartialEmoji | None = None
    """Shown before the label; a custom emoji needs its ``id`` and ``name``."""
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


class UserSelect(BaseModel):
    """A menu picking users; must sit alone inside an :class:`ActionRow`."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.USER_SELECT] = ComponentType.USER_SELECT
    custom_id: CustomId
    placeholder: Annotated[str, StringConstraints(max_length=150)] | None = None
    min_values: Annotated[int, Field(ge=0, le=25)] | None = None
    max_values: Annotated[int, Field(ge=1, le=25)] | None = None
    disabled: bool = False


type SelectText = Annotated[str, StringConstraints(min_length=1, max_length=MAX_SELECT_OPTION_LENGTH)]


class SelectOption(BaseModel):
    """One choice of a :class:`StringSelect`."""

    model_config = ConfigDict(extra="forbid")

    label: SelectText
    """What the user sees."""
    value: SelectText
    """What the interaction sends back when this option is chosen."""
    description: Annotated[str, StringConstraints(max_length=MAX_SELECT_OPTION_LENGTH)] | None = None
    emoji: PartialEmoji | None = None
    default: bool | None = None
    """Show this option as chosen when the menu appears."""


class StringSelect(BaseModel):
    """A menu of developer-defined options; must sit alone inside an :class:`ActionRow`."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.STRING_SELECT] = ComponentType.STRING_SELECT
    custom_id: CustomId
    options: Annotated[list[SelectOption], Field(min_length=1, max_length=MAX_SELECT_OPTIONS)]
    placeholder: Annotated[str, StringConstraints(max_length=150)] | None = None
    min_values: Annotated[int, Field(ge=0, le=MAX_SELECT_OPTIONS)] | None = None
    max_values: Annotated[int, Field(ge=1, le=MAX_SELECT_OPTIONS)] | None = None
    disabled: bool = False


class ActionRow(BaseModel):
    """A row of up to 5 buttons, or one select menu."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.ACTION_ROW] = ComponentType.ACTION_ROW
    components: Annotated[list[Button | UserSelect | StringSelect], Field(min_length=1, max_length=MAX_ACTION_ROW_BUTTONS)]

    @model_validator(mode="after")
    def _check_select_alone(self) -> Self:
        """Refuse a select menu sharing its row with any other component."""
        selects = [component for component in self.components if isinstance(component, UserSelect | StringSelect)]
        if selects and len(self.components) > 1:
            msg = "A select menu must be alone in its action row"
            raise ValueError(msg)
        return self


class UnfurledMediaItem(BaseModel):
    """An image or file a component shows: a web URL, or ``attachment://<filename>`` for a file sent with the message."""

    model_config = ConfigDict(extra="forbid")

    url: str


class TextDisplay(BaseModel):
    """Markdown text in a components v2 message; mentions in it ping like message content."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.TEXT_DISPLAY] = ComponentType.TEXT_DISPLAY
    content: Annotated[str, StringConstraints(min_length=1, max_length=MAX_TEXT_DISPLAY_CHARACTERS)]


class Thumbnail(BaseModel):
    """A small image beside a :class:`Section`'s text."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.THUMBNAIL] = ComponentType.THUMBNAIL
    media: UnfurledMediaItem
    description: Annotated[str, StringConstraints(max_length=MAX_MEDIA_DESCRIPTION_LENGTH)] | None = None
    """Alt text."""
    spoiler: bool = False


class Section(BaseModel):
    """One to three text displays with a button or thumbnail beside them."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.SECTION] = ComponentType.SECTION
    components: Annotated[list[TextDisplay], Field(min_length=1, max_length=MAX_SECTION_TEXT_DISPLAYS)]
    accessory: Button | Thumbnail


class MediaGalleryItem(BaseModel):
    """One image of a :class:`MediaGallery`."""

    model_config = ConfigDict(extra="forbid")

    media: UnfurledMediaItem
    description: Annotated[str, StringConstraints(max_length=MAX_MEDIA_DESCRIPTION_LENGTH)] | None = None
    """Alt text."""
    spoiler: bool = False


class MediaGallery(BaseModel):
    """One to ten images shown as a grid, at the full width of the message."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.MEDIA_GALLERY] = ComponentType.MEDIA_GALLERY
    items: Annotated[list[MediaGalleryItem], Field(min_length=1, max_length=MAX_MEDIA_GALLERY_ITEMS)]


class SeparatorSpacing(IntEnum):
    """How much room a :class:`Separator` leaves."""

    SMALL = 1
    LARGE = 2


class Separator(BaseModel):
    """Vertical space between components, with a dividing line unless ``divider`` is off."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.SEPARATOR] = ComponentType.SEPARATOR
    divider: bool = True
    spacing: SeparatorSpacing = SeparatorSpacing.SMALL


class FileDisplay(BaseModel):
    """A file sent with the message, shown as a download; ``file`` must be an ``attachment://`` reference."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.FILE] = ComponentType.FILE
    file: UnfurledMediaItem
    spoiler: bool = False


class Container(BaseModel):
    """A box around other components, with an optional colored bar on its left like an embed's."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.CONTAINER] = ComponentType.CONTAINER
    components: Annotated[
        list[ActionRow | TextDisplay | Section | MediaGallery | Separator | FileDisplay],
        Field(min_length=1),
    ]
    accent_color: Color | None = None
    spoiler: bool = False


type MessageComponent = ActionRow | TextDisplay | Section | MediaGallery | Separator | FileDisplay | Container
"""A component that can sit at the top level of a message."""

type AnyComponent = MessageComponent | Button | UserSelect | StringSelect | Thumbnail
"""Any component a message can hold, nested ones included."""


def is_layout(components: Sequence[MessageComponent]) -> bool:
    """Return whether ``components`` need the components v2 flag: any top-level component that isn't an action row."""
    return any(not isinstance(component, ActionRow) for component in components)


def walk(components: Sequence[AnyComponent]) -> Generator[AnyComponent]:
    """Yield every component in ``components``, each followed by the ones nested inside it."""
    for component in components:
        yield component
        match component:
            case ActionRow() | Container():
                yield from walk(component.components)
            case Section():
                yield from walk([*component.components, component.accessory])
            case _:
                pass


def components_payload(components: Sequence[MessageComponent]) -> list[MessageComponent]:
    """Return the ``components`` JSON for a message, checking the message-wide limits.

    Raises :class:`ValueError` when the message has more than 40 components (nested ones included), reuses a
    ``custom_id``, or has more than 4000 characters of text displays, all of which Discord rejects.
    """
    every = list(walk(components))
    if len(every) > MAX_MESSAGE_COMPONENTS:
        msg = f"A message holds at most {MAX_MESSAGE_COMPONENTS} components, got {len(every)}"
        raise ValueError(msg)
    custom_ids = Counter(
        component.custom_id
        for component in every
        if isinstance(component, Button | UserSelect | StringSelect) and component.custom_id is not None
    )
    if duplicates := sorted(custom_id for custom_id, count in custom_ids.items() if count > 1):
        msg = f"custom_id must be unique within a message, duplicated: {duplicates}"
        raise ValueError(msg)
    text = sum(len(component.content) for component in every if isinstance(component, TextDisplay))
    if text > MAX_TEXT_DISPLAY_CHARACTERS:
        msg = f"A message's text displays hold at most {MAX_TEXT_DISPLAY_CHARACTERS} characters, got {text}"
        raise ValueError(msg)
    return [component.model_dump(mode="json", exclude_none=True) for component in components]


class TextInputStyle(OpenIntEnum):
    """How tall a text input is.

    https://docs.discord.com/developers/components/reference#text-input-text-input-styles
    """

    SHORT = 1
    """A single line."""
    PARAGRAPH = 2
    """Several lines."""


class TextInput(BaseModel):
    """A text field inside a :class:`Label` of a :class:`Modal`."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.TEXT_INPUT] = ComponentType.TEXT_INPUT
    custom_id: CustomId
    style: TextInputStyle = TextInputStyle.SHORT
    min_length: Annotated[int, Field(ge=0, le=MAX_TEXT_INPUT_LENGTH)] | None = None
    max_length: Annotated[int, Field(ge=1, le=MAX_TEXT_INPUT_LENGTH)] | None = None
    required: bool | None = None
    value: Annotated[str, StringConstraints(max_length=MAX_TEXT_INPUT_LENGTH)] | None = None
    """Text the field starts with."""
    placeholder: Annotated[str, StringConstraints(max_length=100)] | None = None


class Label(BaseModel):
    """A caption above one component of a :class:`Modal`."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[ComponentType.LABEL] = ComponentType.LABEL
    label: Annotated[str, StringConstraints(min_length=1, max_length=MAX_LABEL_LENGTH)]
    description: Annotated[str, StringConstraints(max_length=100)] | None = None
    component: TextInput


class Modal(BaseModel):
    """A pop-up form, shown as the response to an interaction.

    https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-response-object-modal
    The submit arrives as a MODAL_SUBMIT interaction carrying ``custom_id``.
    """

    model_config = ConfigDict(extra="forbid")

    custom_id: CustomId
    title: Annotated[str, StringConstraints(min_length=1, max_length=MAX_MODAL_TITLE_LENGTH)]
    components: Annotated[list[Label], Field(min_length=1, max_length=5)]
