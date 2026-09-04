"""Unit tests: interaction/application-command concepts and validators."""
from __future__ import annotations

lazy import pytest


# NOTE: wd_discord.interactions imports herogold.protocols, which currently fails to import
# on Python 3.15 (herogold 3.3.0 bug: "SupportsDelete is not a generic class"). Skip the
# whole module cleanly until that upstream issue is resolved.
try:
    from wd_discord.interactions import (
        ApplicationCommandType,
        CommandHandlerType,
        IntegrationType,
        InteractionContextType,
        LimitedString,
        Locales,
        TooLongError,
        absent_if,
        required_if,
    )
except (ImportError, TypeError) as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"wd_discord.interactions is unimportable: {exc}", allow_module_level=True)


def test_application_command_type_values() -> None:
    assert ApplicationCommandType.chat_input == 1
    assert ApplicationCommandType.user == 2
    assert ApplicationCommandType.message == 3
    assert ApplicationCommandType.primary_entry_point == 4


def test_integration_type_values() -> None:
    assert IntegrationType.twitch == "twitch"
    assert IntegrationType.discord == "discord"


def test_context_and_handler_values() -> None:
    assert InteractionContextType.GUILD.value == 0
    assert InteractionContextType.BOT_DM.value == 1
    assert CommandHandlerType.APP_HANDLER.value == 1


def test_locale_payload() -> None:
    assert Locales.English_US.value.locale == "en-US"
    assert Locales.Dutch.value.locale == "nl"


def test_limited_string_accepts_within_bounds() -> None:
    class Holder:
        name = LimitedString(5)

    holder = Holder()
    holder.name = "abc"
    assert holder.name == "abc"


def test_limited_string_rejects_too_long() -> None:
    class Holder:
        name = LimitedString(5)

    holder = Holder()
    with pytest.raises(TooLongError):
        holder.name = "way too long"


def test_required_if_validator() -> None:
    validator = required_if("type_", ApplicationCommandType.chat_input)

    class Cmd:
        type_ = ApplicationCommandType.chat_input

    invalid, error = validator(Cmd(), "")
    assert invalid is False
    assert isinstance(error, ValueError)

    valid, no_error = validator(Cmd(), "a description")
    assert valid is True
    assert no_error is None


def test_absent_if_validator() -> None:
    validator = absent_if("type_", ApplicationCommandType.chat_input)

    class Cmd:
        type_ = ApplicationCommandType.chat_input

    invalid, error = validator(Cmd(), ["a", "choice"])
    assert invalid is False
    assert isinstance(error, ValueError)
