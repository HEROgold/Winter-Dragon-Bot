"""Unit tests: legacy message components (buttons, action rows) and their message-wide limits."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from wd_discord.components import (
    MAX_MESSAGE_COMPONENTS,
    ActionRow,
    Button,
    ButtonStyle,
    components_payload,
)


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
