"""Unit tests: message components, legacy and components v2, and their message-wide limits."""

import pytest
from pydantic import ValidationError
from wd_discord.color import Color
from wd_discord.components import (
    ActionRow,
    Button,
    ButtonStyle,
    Container,
    MediaGallery,
    MediaGalleryItem,
    Section,
    SelectOption,
    Separator,
    SeparatorSpacing,
    StringSelect,
    TextDisplay,
    Thumbnail,
    UnfurledMediaItem,
    UserSelect,
    components_payload,
    is_layout,
    walk,
)
from wd_discord.limits import MAX_MESSAGE_COMPONENTS, MAX_TEXT_DISPLAY_CHARACTERS
from wd_discord.partial_emoji import PartialEmoji


def _button(custom_id: str) -> Button:
    return Button(style=ButtonStyle.PRIMARY, label="x", custom_id=custom_id)


def test_button_serializes_as_type_2() -> None:
    dumped = _button("a").model_dump(mode="json", exclude_none=True)
    assert dumped == {"type": 2, "style": 1, "label": "x", "custom_id": "a", "disabled": False}


def test_interactive_button_requires_custom_id() -> None:
    with pytest.raises(ValidationError, match="need a custom_id"):
        Button(style=ButtonStyle.PRIMARY, label="x")


def test_link_button_requires_url_and_rejects_custom_id() -> None:
    assert Button(style=ButtonStyle.LINK, label="docs", url="https://example.com").url == "https://example.com"
    with pytest.raises(ValidationError, match="LINK buttons"):
        Button(style=ButtonStyle.LINK, label="docs", url="https://example.com", custom_id="a")


def test_premium_button_takes_only_sku_id() -> None:
    assert Button(style=ButtonStyle.PREMIUM, sku_id=1).sku_id is not None
    with pytest.raises(ValidationError, match="PREMIUM buttons"):
        Button(style=ButtonStyle.PREMIUM, sku_id=1, label="buy")


def test_custom_id_is_limited_to_100_characters() -> None:
    _button("a" * 100)
    with pytest.raises(ValidationError):
        _button("a" * 101)


def test_label_is_limited_to_80_characters() -> None:
    with pytest.raises(ValidationError):
        Button(style=ButtonStyle.PRIMARY, label="a" * 81, custom_id="a")


def test_action_row_holds_one_to_five_buttons() -> None:
    ActionRow(components=[_button(str(index)) for index in range(5)])
    with pytest.raises(ValidationError):
        ActionRow(components=[_button(str(index)) for index in range(6)])
    with pytest.raises(ValidationError):
        ActionRow(components=[])


def test_user_select_serializes_as_type_5() -> None:
    dumped = UserSelect(custom_id="pick", placeholder="Members", max_values=25).model_dump(mode="json", exclude_none=True)
    assert dumped == {"type": 5, "custom_id": "pick", "placeholder": "Members", "max_values": 25, "disabled": False}


def test_a_select_must_be_alone_in_its_action_row() -> None:
    select = UserSelect(custom_id="pick")
    assert ActionRow(components=[select]).components == [select]
    with pytest.raises(ValidationError, match="A select menu must be alone in its action row"):
        ActionRow(components=[select, _button("a")])


def test_components_payload_serializes_rows() -> None:
    payload = components_payload([ActionRow(components=[_button("a")])])
    assert payload == [{"type": 1, "components": [{"type": 2, "style": 1, "label": "x", "custom_id": "a", "disabled": False}]}]


def test_components_payload_rejects_duplicate_custom_ids() -> None:
    rows = [ActionRow(components=[_button("same")]), ActionRow(components=[_button("same")])]
    with pytest.raises(ValueError, match="duplicated: \\['same'\\]"):
        components_payload(rows)


def test_components_payload_rejects_more_than_40_components() -> None:
    # 7 rows of 5 buttons = 7 + 35 = 42 components.
    rows = [ActionRow(components=[_button(f"{row}-{index}") for index in range(5)]) for row in range(7)]
    with pytest.raises(ValueError, match=str(MAX_MESSAGE_COMPONENTS)):
        components_payload(rows)


def test_button_emoji_serializes_as_a_partial_emoji() -> None:
    button = Button(style=ButtonStyle.SECONDARY, custom_id="a", emoji=PartialEmoji(id=5, name="route"))
    assert button.model_dump(mode="json", exclude_none=True)["emoji"] == {"id": "5", "name": "route"}


def test_string_select_serializes_as_type_3_with_its_options() -> None:
    select = StringSelect(custom_id="team", options=[SelectOption(label="Frostbite", value="7", description="4 members")])
    assert select.model_dump(mode="json", exclude_none=True) == {
        "type": 3,
        "custom_id": "team",
        "options": [{"label": "Frostbite", "value": "7", "description": "4 members"}],
        "disabled": False,
    }


def test_a_string_select_must_be_alone_and_needs_an_option() -> None:
    select = StringSelect(custom_id="team", options=[SelectOption(label="a", value="a")])
    with pytest.raises(ValidationError, match="alone in its action row"):
        ActionRow(components=[select, _button("b")])
    with pytest.raises(ValidationError):
        StringSelect(custom_id="team", options=[])


def _text(content: str = "hi") -> TextDisplay:
    return TextDisplay(content=content)


def test_section_holds_one_to_three_texts_and_an_accessory() -> None:
    thumbnail = Thumbnail(media=UnfurledMediaItem(url="attachment://a.png"))
    Section(components=[_text()] * 3, accessory=thumbnail)
    with pytest.raises(ValidationError):
        Section(components=[_text()] * 4, accessory=thumbnail)
    with pytest.raises(ValidationError):
        Section(components=[], accessory=_button("a"))


def test_container_serializes_its_children_and_accent_color() -> None:
    container = Container(
        components=[_text("## Spring Cup"), Separator(spacing=SeparatorSpacing.LARGE)],
        accent_color=Color(0x1E5AA0),
    )
    assert components_payload([container]) == [
        {
            "type": 17,
            "components": [
                {"type": 10, "content": "## Spring Cup"},
                {"type": 14, "divider": True, "spacing": 2},
            ],
            "accent_color": 0x1E5AA0,
            "spoiler": False,
        },
    ]


def test_media_gallery_holds_one_to_ten_items() -> None:
    item = MediaGalleryItem(media=UnfurledMediaItem(url="attachment://bracket.png"))
    MediaGallery(items=[item] * 10)
    with pytest.raises(ValidationError):
        MediaGallery(items=[item] * 11)


def test_walk_yields_nested_components() -> None:
    accessory = _button("join")
    section = Section(components=[_text()], accessory=accessory)
    row = ActionRow(components=[_button("leave")])
    container = Container(components=[section, row])
    assert [type(component).__name__ for component in walk([container])] == [
        "Container",
        "Section",
        "TextDisplay",
        "Button",
        "ActionRow",
        "Button",
    ]


def test_is_layout_only_for_components_beyond_action_rows() -> None:
    assert not is_layout([ActionRow(components=[_button("a")])])
    assert is_layout([_text()])


def test_components_payload_counts_nested_components() -> None:
    # A container of 39 text displays is 40 components; one more is too many.
    components_payload([Container(components=[_text()] * 39)])
    with pytest.raises(ValueError, match=str(MAX_MESSAGE_COMPONENTS)):
        components_payload([Container(components=[_text()] * 40)])


def test_components_payload_finds_duplicate_custom_ids_in_sections() -> None:
    section = Section(components=[_text()], accessory=_button("same"))
    with pytest.raises(ValueError, match="duplicated"):
        components_payload([Container(components=[section, ActionRow(components=[_button("same")])])])


def test_components_payload_limits_the_text_of_all_text_displays() -> None:
    half = _text("a" * (MAX_TEXT_DISPLAY_CHARACTERS // 2))
    components_payload([half, half])
    with pytest.raises(ValueError, match=str(MAX_TEXT_DISPLAY_CHARACTERS)):
        components_payload([half, half, _text("a")])
