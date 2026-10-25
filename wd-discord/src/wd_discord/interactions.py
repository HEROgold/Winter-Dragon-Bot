"""Discord application commands (https://docs.discord.com/developers/interactions/application-commands)."""

from __future__ import annotations

lazy from typing import Annotated, Self

lazy from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter, model_validator
lazy from wd_core.client import JsonPayload

from wd_discord.open_enum import OpenIntEnum, OpenStrEnum

# eager: pydantic needs the real classes, not lazy proxies, for the model fields below
from wd_discord.permissions import ChannelType, Permissions, PermissionsField
from wd_discord.snowflake import Snowflake
lazy from wd_discord.models import DiscordModel


class ApplicationCommandType(OpenIntEnum):
    """Represents the type of an application command.

    https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-types
    """

    CHAT_INPUT = 1
    USER = 2
    MESSAGE = 3
    PRIMARY_ENTRY_POINT = 4


class ApplicationCommandOptionType(OpenIntEnum):
    """Represents the type of an application command option (distinct from the command's own type).

    https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-type
    """

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


class InteractionContextType(OpenIntEnum):
    """Where an application command can be used.

    https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object-interaction-context-types
    """

    GUILD = 0
    BOT_DM = 1
    PRIVATE_CHANNEL = 2


class ApplicationIntegrationType(OpenIntEnum):
    """Where an app can be installed, and so where its commands are available.

    https://docs.discord.com/developers/resources/application#application-object-application-integration-types
    """

    GUILD_INSTALL = 0
    USER_INSTALL = 1


class EntryPointCommandHandlerType(OpenIntEnum):
    """Who handles a PRIMARY_ENTRY_POINT command's interaction.

    https://docs.discord.com/developers/interactions/application-commands#application-command-object-entry-point-command-handler-types
    """

    APP_HANDLER = 1
    """The app handles the interaction using an interaction token"""
    DISCORD_LAUNCH_ACTIVITY = 2
    """Discord handles the interaction by launching an Activity and sending a follow-up message, without the app"""


class Locale(OpenStrEnum):
    """A Discord locale code (https://docs.discord.com/developers/reference#locales)."""

    INDONESIAN = "id"
    DANISH = "da"
    GERMAN = "de"
    ENGLISH_UK = "en-GB"
    ENGLISH_US = "en-US"
    SPANISH = "es-ES"
    SPANISH_LATAM = "es-419"
    FRENCH = "fr"
    CROATIAN = "hr"
    ITALIAN = "it"
    LITHUANIAN = "lt"
    HUNGARIAN = "hu"
    DUTCH = "nl"
    NORWEGIAN = "no"
    POLISH = "pl"
    PORTUGUESE_BRAZIL = "pt-BR"
    ROMANIAN = "ro"
    FINNISH = "fi"
    SWEDISH = "sv-SE"
    VIETNAMESE = "vi"
    TURKISH = "tr"
    CZECH = "cs"
    GREEK = "el"
    BULGARIAN = "bg"
    RUSSIAN = "ru"
    UKRAINIAN = "uk"
    HINDI = "hi"
    THAI = "th"
    CHINESE_CHINA = "zh-CN"
    JAPANESE = "ja"
    CHINESE_TAIWAN = "zh-TW"
    KOREAN = "ko"


MAX_OPTIONS = 25
"""A command or subcommand holds up to 25 options (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""
MAX_CHOICES = 25
"""An option offers up to 25 choices (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""
MAX_CHOICE_NAME_LENGTH = 100
"""A command option choice name, autocomplete results included, holds up to 100 characters (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-choice-structure)."""
MAX_DESCRIPTION_LENGTH = 100
"""A command or option description holds 1 to 100 characters (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""
CHAT_INPUT_NAME_PATTERN = r"^[-_\u02BC\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$"
"""What a slash command or option name may hold (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-naming)."""


def _require_lowercase(name: str) -> str:
    """Reject ``name`` if any of its letters has a lowercase variant that wasn't used."""
    if name != name.lower():
        msg = f"Name {name!r} must be lowercase"
        raise ValueError(msg)
    return name


type Name = Annotated[str, StringConstraints(min_length=1, max_length=32)]
type ChatInputName = Annotated[str, StringConstraints(pattern=CHAT_INPUT_NAME_PATTERN), AfterValidator(_require_lowercase)]
"""A CHAT_INPUT command or option name: Discord's name regex, lowercase where a lowercase variant exists."""
type Description = Annotated[str, StringConstraints(min_length=1, max_length=MAX_DESCRIPTION_LENGTH)]
type Localizations = dict[Locale, str]

_chat_input_name: TypeAdapter[str] = TypeAdapter(ChatInputName)


class ApplicationCommandOptionChoice(DiscordModel):
    """One predefined value for a STRING, INTEGER or NUMBER option."""

    name: Description
    name_localizations: Localizations | None = None
    value: Annotated[str, StringConstraints(max_length=100)] | int | float


class ApplicationCommandOption(DiscordModel):
    """A parameter of an application command, or one of its subcommands."""

    type: ApplicationCommandOptionType
    name: ChatInputName
    name_localizations: Localizations | None = None
    description: Description
    description_localizations: Localizations | None = None
    required: bool = False
    choices: Annotated[list[ApplicationCommandOptionChoice], Field(max_length=MAX_CHOICES)] | None = None
    options: Annotated[list[ApplicationCommandOption], Field(max_length=MAX_OPTIONS)] | None = None
    channel_types: list[ChannelType] | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    min_length: Annotated[int, Field(ge=0, le=6000)] | None = None
    max_length: Annotated[int, Field(ge=1, le=6000)] | None = None
    autocomplete: bool | None = None
    file_types: Annotated[list[str], Field(max_length=10)] | None = None


class ApplicationCommand(DiscordModel):
    """An application command as Discord returns it (list/create/edit response)."""

    id: Snowflake
    type: ApplicationCommandType = ApplicationCommandType.CHAT_INPUT
    application_id: Snowflake
    guild_id: Snowflake | None = None
    name: Name
    name_localizations: Localizations | None = None
    description: Annotated[str, StringConstraints(max_length=100)]
    description_localizations: Localizations | None = None
    options: Annotated[list[ApplicationCommandOption], Field(max_length=MAX_OPTIONS)] = Field(
        default_factory=list[ApplicationCommandOption],
    )
    default_member_permissions: PermissionsField | None = None
    dm_permission: bool = True
    default_permission: bool | None = None
    nsfw: bool = False
    integration_types: list[ApplicationIntegrationType] | None = None
    contexts: list[InteractionContextType] | None = None
    version: Snowflake
    handler: EntryPointCommandHandlerType | None = None

    def to_params(self) -> ApplicationCommandParams:
        """Return the create/edit body that defines this command, without the fields only Discord sets.

        Drops ``id``, ``application_id``, ``guild_id``, ``version`` and the deprecated ``dm_permission`` /
        ``default_permission``, so the result compares equal to the params the command was registered with.
        """
        return ApplicationCommandParams(
            name=self.name,
            name_localizations=self.name_localizations,
            description=self.description,
            description_localizations=self.description_localizations,
            options=self.options,
            default_member_permissions=self.default_member_permissions,
            integration_types=self.integration_types,
            contexts=self.contexts,
            type=self.type,
            nsfw=self.nsfw,
            handler=self.handler,
        )


class ApplicationCommandParams(BaseModel):
    """The JSON body for creating or editing an application command.

    Leaves out the deprecated ``dm_permission`` and ``default_permission``; ``contexts`` and
    ``default_member_permissions`` replace them.
    """

    model_config = ConfigDict(extra="forbid")

    name: Name
    name_localizations: Localizations | None = None
    description: Annotated[str, StringConstraints(max_length=100)] = ""
    description_localizations: Localizations | None = None
    options: Annotated[list[ApplicationCommandOption], Field(max_length=MAX_OPTIONS)] | None = None
    default_member_permissions: Permissions | None = None
    integration_types: list[ApplicationIntegrationType] | None = None
    contexts: list[InteractionContextType] | None = None
    type: ApplicationCommandType = ApplicationCommandType.CHAT_INPUT
    nsfw: bool | None = None
    handler: EntryPointCommandHandlerType | None = None

    @model_validator(mode="after")
    def _check_type_rules(self) -> Self:
        """Enforce the fields Discord only accepts on some command types."""
        if self.type is ApplicationCommandType.CHAT_INPUT:
            _chat_input_name.validate_python(self.name)
        if self.options and self.type is not ApplicationCommandType.CHAT_INPUT:
            msg = "options are only valid on CHAT_INPUT commands"
            raise ValueError(msg)
        needs_description = self.type in {ApplicationCommandType.CHAT_INPUT, ApplicationCommandType.PRIMARY_ENTRY_POINT}
        if needs_description != bool(self.description):
            msg = f"description must be {'1-100 characters' if needs_description else 'empty'} on {self.type.name} commands"
            raise ValueError(msg)
        if self.handler is not None and self.type is not ApplicationCommandType.PRIMARY_ENTRY_POINT:
            msg = "handler is only valid on PRIMARY_ENTRY_POINT commands"
            raise ValueError(msg)
        return self

    def to_json(self) -> JsonPayload:
        """Return the request body.

        ``default_member_permissions`` is always sent, as a decimal string or JSON null, so a PATCH
        can clear permissions a previous sync set.
        """
        permissions = self.default_member_permissions
        payload = self.model_dump(mode="json", exclude_none=True)
        payload["default_member_permissions"] = None if permissions is None else str(int(permissions))
        return payload
