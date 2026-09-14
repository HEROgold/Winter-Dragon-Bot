"""Unit tests: interaction/application-command concepts and validators."""
from __future__ import annotations

lazy import pytest

from wd_discord.utils.strings import LimitedString, TooLongError

# NOTE: wd_discord.interactions imports herogold.protocols, which currently fails to import
# on Python 3.15 (herogold 3.3.0 bug: "SupportsDelete is not a generic class"). Skip the
# whole module cleanly until that upstream issue is resolved.
try:
    from wd_discord.interactions import (
        ApplicationCommandOptionType,
        ApplicationCommandType,
        CommandHandlerType,
        CommandOption,
        IntegrationType,
        InteractionContextType,
        Locales,
        RegisteredCommand,
    )
except (ImportError, TypeError) as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"wd_discord.interactions is unimportable: {exc}", allow_module_level=True)


def test_application_command_type_values() -> None:
    assert ApplicationCommandType.chat_input == 1
    assert ApplicationCommandType.user == 2
    assert ApplicationCommandType.message == 3
    assert ApplicationCommandType.primary_entry_point == 4


def test_application_command_option_type_values() -> None:
    assert ApplicationCommandOptionType.STRING == 3
    assert ApplicationCommandOptionType.USER == 6
    assert ApplicationCommandOptionType.SUB_COMMAND == 1


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


def test_command_option_validates_from_dict() -> None:
    option = CommandOption.model_validate(
        {"type": 6, "name": "user", "description": "The user to check", "required": True},
    )
    assert option.type is ApplicationCommandOptionType.USER
    assert option.required is True


def test_registered_command_validates_discord_payload() -> None:
    payload = {
        "id": "111",
        "application_id": "222",
        "version": "333",
        "name": "percentage",
        "description": "Calculate a random compatibility percentage with another user",
        "options": [{"type": 6, "name": "user", "description": "The user to check", "required": True}],
    }
    command = RegisteredCommand.model_validate(payload)
    assert command.name == "percentage"
    assert command.options[0].name == "user"
    assert command.guild_id is None
