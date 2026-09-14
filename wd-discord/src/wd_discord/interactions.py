"""Discord Interactions."""
from __future__ import annotations

from collections.abc import Mapping

lazy from dataclasses import dataclass, field
lazy from enum import Enum, IntEnum, StrEnum, auto
lazy from typing import TYPE_CHECKING, Annotated, get_type_hints

lazy from wd_discord.utils.strings import LimitedString
lazy from wd_errors.size import TooLongError

from pydantic import Field
from wd_discord.models import DiscordModel
from wd_discord.permissions import PermissionsField
from wd_discord.snowflake import Snowflake

if TYPE_CHECKING:
    lazy from collections.abc import Callable

    lazy from wd_discord.permissions import Permissions


class ApplicationCommandType(IntEnum):
    """Represents the type of an application command."""

    chat_input = 1
    user = 2
    message = 3
    primary_entry_point = 4

class ApplicationCommandOptionType(IntEnum):
    """Represents the type of an application command option (distinct from the command's own type)."""

    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10
    ATTACHMENT = 11

@dataclass
class Locale:
    """Represents a locale."""

    locale: str
    english_name: str
    native_name: str

class Locales(Enum):
    """Represents the different locales for Discord."""

    Indonesian = Locale("id", "Indonesian", "Bahasа Indonesia")
    Danish = Locale("da", "Danish", "Dansk")
    German = Locale("de", "German", "Deutsch")
    English_UK = Locale("en-GB", "English, UK", "English, UK")
    English_US = Locale("en-US", "English, US", "English, US")
    Spanish = Locale("es-ES", "Spanish", "Español")
    Spanish_LATAM = Locale("es-419", "Spanish, LATAM", "Español, LATAM")
    French = Locale("fr", "French", "Français")
    Croatian = Locale("hr", "Croatian", "Hrvatski")
    Italian = Locale("it", "Italian", "Italiano")
    Lithuanian = Locale("lt", "Lithuanian", "Lietuviškai")
    Hungarian = Locale("hu", "Hungarian", "Magyar")
    Dutch = Locale("nl", "Dutch", "Nederlands")
    Norwegian = Locale("no", "Norwegian", "Norsk")
    Polish = Locale("pl", "Polish", "Polski")
    Portuguese_Brazil = Locale("pt-BR", "Portuguese, Brazilian", "Português do Brasil")
    Romanian = Locale("ro", "Romanian, Romania", "Română")
    Finnish = Locale("fi", "Finnish", "Suomi")
    Swedish = Locale("sv-SE", "Swedish", "Svenska")
    Vietnamese = Locale("vi", "Vietnamese", "Tiếng Việt")
    Turkish = Locale("tr", "Turkish", "Türkçe")
    Czech = Locale("cs", "Czech", "Čeština")
    Greek = Locale("el", "Greek", "Ελληνικά")
    Bulgarian = Locale("bg", "Bulgarian", "български")
    Russian = Locale("ru", "Russian", "Pусский")
    Ukrainian = Locale("uk", "Ukrainian", "Українська")
    Hindi = Locale("hi", "Hindi", "हिन्दी")
    Thai = Locale("th", "Thai", "ไทย")
    Chinese_China = Locale("zh-CN", "Chinese, China", "中文")
    Japanese = Locale("ja", "Japanese", "日本語")
    Chinese_Taiwan = Locale("zh-TW", "Chinese, Taiwan", "繁體中文")
    Korean = Locale("ko", "Korean", "한국어")


def required_if(dependent_field: str, required_state: object) -> Callable[[object, object], tuple[bool, Exception | None]]:
    """Check if a field is required based on the state of another field."""

    def validator(instance: object, current_value: object) -> tuple[bool, Exception | None]:
        """Validate the field."""
        actual_state = getattr(instance, dependent_field)
        if isinstance(current_value, AttributeError):
            current_value = ""
        if actual_state == required_state and not bool(current_value):
            return False, ValueError(f"Description must be provided for {required_state} commands.")
        return True, None

    return validator

def absent_if(dependent_field: str, absent_state: object = None) -> Callable[[object, object], tuple[bool, Exception | None]]:
    """Check if a field must be absent based on the state of another field."""

    def validator(instance: object, current_value: object) -> tuple[bool, Exception | None]:
        """Validate the field."""
        actual_state = getattr(instance, dependent_field)
        if actual_state == absent_state and bool(current_value):
            return False, ValueError(f"Choices cannot be provided for {absent_state} commands.")
        return True, None

    return validator

def validate[T](cls: type[T]) -> type[T]:
    """Class decorator to validate dataclass fields based on their type annotations and metadata."""
    original_post_init: Callable[..., None] = getattr(cls, "__post_init__", lambda _self, *_args, **_kwargs: None)

    def new_post_init[**P](inst: object, *args: P.args, **kwargs: P.kwargs) -> None:
        if original_post_init:
            original_post_init(inst, *args, **kwargs)

        hints = get_type_hints(cls, include_extras=True)
        errors: list[Exception] = []

        for field_name, field_type in hints.items():
            if hasattr(field_type, "__metadata__"):
                validators = field_type.__metadata__
                current_value = getattr(inst, field_name)

                for validator in validators:
                    is_valid, error = validator(inst, current_value)
                    if not is_valid:
                        errors.append(error)

        if errors:
            msg = "Invalid application command."
            raise ExceptionGroup(msg, errors)

    cls.__post_init__ = new_post_init  # ty:ignore[unresolved-attribute]
    return cls

class CommandOption(DiscordModel):
    """An option for an application command (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""

    type: ApplicationCommandOptionType
    name: str
    description: str
    required: bool = False
    choices: list[Mapping[str, object]] | None = None
    options: list[CommandOption] | None = None


class RegisteredCommand(DiscordModel):
    """A chat-input application command as Discord's REST API returns it (list/create/edit response)."""

    id: Snowflake
    application_id: Snowflake
    guild_id: Snowflake | None = None
    version: Snowflake
    name: str
    description: str
    options: list[CommandOption] = Field(default_factory=list)
    default_member_permissions: PermissionsField | None = None
    dm_permission: bool = True
    nsfw: bool = False

class CommandHandlerType(Enum):
    """Represents the type of handler for an application command."""

    APP_HANDLER = 1
    """The app handles the interaction using an interaction token"""
    DISCORD_LAUNCH_ACTIVITY = 2
    """Discord handles the interaction by launching an Activity and sending a follow-up message without coordinating with the app"""

class InteractionContextType(Enum):
    """Represents the context in which an application command can be used."""

    GUILD = 0
    BOT_DM = 1
    PRIVATE_CHANNEL = 2

class IntegrationType(StrEnum):
    """Represents the type of integration for an application command."""

    twitch = auto()
    youtube = auto()
    discord = auto()
    guild_subscription = auto()

@validate
@dataclass
class ApplicationCommand:
    """Represents an application command."""

    id: Snowflake
    type_: ApplicationCommandType | None
    application_id: Snowflake
    guild_id: Snowflake | None
    version: Snowflake
    name = LimitedString(32)
    name_localizations: dict[Locale, str] | None = None
    description: Annotated[str, required_if("type_", ApplicationCommandType.chat_input)] = LimitedString(100)
    description_localizations: dict[Locale, str] | None = None
    options: Annotated[list[CommandOption] | None, absent_if("type_", ApplicationCommandType.chat_input)] = None
    default_member_permissions: Permissions | None = None
    dm_permission: bool = True # If true, allows use of command in DM with bot. Use contexts instead!
    default_permission: bool = True
    nsfw: bool = False
    integration_types: list[IntegrationType] | None = None
    contexts: list[InteractionContextType] | None = None
    handler: Annotated[CommandHandlerType, required_if("type_", ApplicationCommandType.primary_entry_point)] = CommandHandlerType.APP_HANDLER

@dataclass
class ChatInputApplicationCommand(ApplicationCommand):
    """Represents a chat input application command."""

    description = LimitedString(100)
    options: list[CommandOption] = field(default_factory=list)

@dataclass
class UserApplicationCommand(ApplicationCommand):
    """Represents a user application command."""

    description = LimitedString(0)
    options: None = None

@dataclass
class MessageApplicationCommand(ApplicationCommand):
    """Represents a message application command."""

    description = LimitedString(0)
    options: None = None

@dataclass
class PrimaryEntryPointApplicationCommand(ApplicationCommand):
    """Represents a primary entry point application command."""

    description = LimitedString(0)
    options: None = None
