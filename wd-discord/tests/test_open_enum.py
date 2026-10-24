"""Unit tests: enums of Discord's values accept a value Discord adds later, and report it once."""

from __future__ import annotations

lazy import pytest
lazy from pydantic import ValidationError
lazy from wd_discord import open_enum
lazy from wd_discord.permissions import ChannelType
lazy from wd_discord.resources.channel.channel import Channel
lazy from wd_discord.resources.guild.features import GuildFeature
lazy from wd_discord.resources.user.profile import NamePlateBackgroundColor


def test_an_unknown_int_becomes_its_own_member() -> None:
    channel = Channel.model_validate({"id": "1", "type": 99})
    assert channel.type == 99
    assert channel.type.name == "UNKNOWN_99"
    assert ChannelType(99) is channel.type


def test_an_unknown_string_becomes_its_own_member() -> None:
    assert NamePlateBackgroundColor("black").name == "BLACK"
    assert GuildFeature("SOMETHING_NEW") == "SOMETHING_NEW"


def test_unknown_values_are_not_listed_as_members() -> None:
    ChannelType(98)
    assert 98 not in [member.value for member in ChannelType]


def test_a_value_of_the_wrong_type_is_still_refused() -> None:
    with pytest.raises(ValidationError):
        Channel.model_validate({"id": "1", "type": "text"})


def test_an_unknown_value_is_reported_once(monkeypatch: pytest.MonkeyPatch) -> None:
    warnings: list[object] = []

    class Logger:
        def warning(self, message: object) -> None:
            warnings.append(message)

    monkeypatch.setattr(open_enum, "_reported", set())
    monkeypatch.setattr(open_enum, "getLogger", lambda _name: Logger())
    ChannelType(97)
    ChannelType(97)
    assert len(warnings) == 1
