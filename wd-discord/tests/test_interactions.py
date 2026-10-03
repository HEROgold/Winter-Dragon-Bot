"""Unit tests: application-command models and their documented limits."""

from __future__ import annotations

from wd_discord.interactions import (
    ApplicationCommand,
    ApplicationCommandOption,
    ApplicationCommandOptionChoice,
    ApplicationCommandOptionType,
    ApplicationCommandParams,
    ApplicationCommandType,
    ApplicationIntegrationType,
    EntryPointCommandHandlerType,
    InteractionContextType,
    Locale,
)
from wd_discord.permissions import ChannelType, Permissions
lazy import pytest
lazy from pydantic import ValidationError


def test_application_command_type_values() -> None:
    assert ApplicationCommandType.CHAT_INPUT == 1
    assert ApplicationCommandType.USER == 2
    assert ApplicationCommandType.MESSAGE == 3
    assert ApplicationCommandType.PRIMARY_ENTRY_POINT == 4


def test_application_command_option_type_values() -> None:
    assert ApplicationCommandOptionType.STRING == 3
    assert ApplicationCommandOptionType.USER == 6
    assert ApplicationCommandOptionType.SUB_COMMAND == 1


def test_context_integration_and_handler_values() -> None:
    assert InteractionContextType.GUILD == 0
    assert InteractionContextType.BOT_DM == 1
    assert ApplicationIntegrationType.USER_INSTALL == 1
    assert EntryPointCommandHandlerType.APP_HANDLER == 1


def test_locale_values_are_discord_codes() -> None:
    assert Locale.ENGLISH_US == "en-US"
    assert Locale.DUTCH == "nl"


def test_option_validates_from_dict() -> None:
    option = ApplicationCommandOption.model_validate(
        {"type": 6, "name": "user", "description": "The user to check", "required": True},
    )
    assert option.type is ApplicationCommandOptionType.USER
    assert option.required is True


def test_option_parses_channel_types_and_autocomplete() -> None:
    option = ApplicationCommandOption.model_validate(
        {"type": 7, "name": "channel", "description": "A channel", "channel_types": [0], "autocomplete": False},
    )
    assert option.channel_types == [ChannelType(0)]
    assert option.model_extra == {}


def test_option_choices_parse_into_models() -> None:
    option = ApplicationCommandOption.model_validate(
        {"type": 3, "name": "color", "description": "Pick one", "choices": [{"name": "Red", "value": "red"}]},
    )
    assert option.choices == [ApplicationCommandOptionChoice(name="Red", value="red")]


@pytest.mark.parametrize("name", ["has space", "Upper", "x" * 33, ""])
def test_option_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValidationError):
        ApplicationCommandOption(type=ApplicationCommandOptionType.STRING, name=name, description="d")


def test_option_rejects_more_than_25_choices() -> None:
    choices = [ApplicationCommandOptionChoice(name=str(i), value=i) for i in range(26)]
    with pytest.raises(ValidationError):
        ApplicationCommandOption(type=ApplicationCommandOptionType.INTEGER, name="n", description="d", choices=choices)


def test_command_validates_discord_payload() -> None:
    payload = {
        "id": "111",
        "application_id": "222",
        "version": "333",
        "name": "percentage",
        "description": "Calculate a random compatibility percentage with another user",
        "options": [{"type": 6, "name": "user", "description": "The user to check", "required": True}],
        "contexts": [0, 1, 2],
        "integration_types": [0],
    }
    command = ApplicationCommand.model_validate(payload)
    assert command.type is ApplicationCommandType.CHAT_INPUT
    assert command.options[0].name == "user"
    assert command.contexts == [
        InteractionContextType.GUILD,
        InteractionContextType.BOT_DM,
        InteractionContextType.PRIVATE_CHANNEL,
    ]
    assert command.guild_id is None


def test_params_payload_includes_options() -> None:
    option = ApplicationCommandOption(
        type=ApplicationCommandOptionType.USER, name="user", description="Target user", required=True
    )
    params = ApplicationCommandParams(name="percentage", description="Calculate a percentage", options=[option])
    assert params.to_json() == {
        "name": "percentage",
        "description": "Calculate a percentage",
        "type": 1,
        "options": [{"type": 6, "name": "user", "description": "Target user", "required": True}],
        "default_member_permissions": None,
    }


def test_params_payload_sends_permissions_as_decimal_string() -> None:
    params = ApplicationCommandParams(name="ping", description="Ping", default_member_permissions=Permissions.MANAGE_GUILD)
    assert params.to_json()["default_member_permissions"] == str(int(Permissions.MANAGE_GUILD))


def test_params_payload_sends_contexts_as_ints() -> None:
    params = ApplicationCommandParams(name="ping", description="Ping", contexts=[InteractionContextType.GUILD])
    assert params.to_json()["contexts"] == [0]


def test_params_rejects_invalid_chat_input_name() -> None:
    with pytest.raises(ValidationError):
        ApplicationCommandParams(name="Has Space", description="d")


def test_params_allows_spaces_in_user_command_name() -> None:
    params = ApplicationCommandParams(name="Show Avatar", type=ApplicationCommandType.USER)
    assert params.name == "Show Avatar"


def test_params_requires_description_on_chat_input() -> None:
    with pytest.raises(ValidationError):
        ApplicationCommandParams(name="ping")


def test_params_rejects_description_on_message_command() -> None:
    with pytest.raises(ValidationError):
        ApplicationCommandParams(name="Quote", description="d", type=ApplicationCommandType.MESSAGE)


def test_params_rejects_options_on_user_command() -> None:
    option = ApplicationCommandOption(type=ApplicationCommandOptionType.STRING, name="s", description="d")
    with pytest.raises(ValidationError):
        ApplicationCommandParams(name="Show", type=ApplicationCommandType.USER, options=[option])


def test_params_rejects_handler_outside_entry_point() -> None:
    with pytest.raises(ValidationError):
        ApplicationCommandParams(name="ping", description="d", handler=EntryPointCommandHandlerType.APP_HANDLER)
