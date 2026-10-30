"""Discord's documented limits, and :func:`truncate` to fit text into one of them.

Import a limit from here rather than writing its number: Discord owns these values.
"""

ELLIPSIS = "…"
"""What :func:`truncate` ends cut text with."""

MAX_ACTION_ROWS = 5
"""A message without the components v2 flag holds up to 5 action rows (https://docs.discord.com/developers/components/reference#action-row)."""
MAX_ACTION_ROW_BUTTONS = 5
"""An action row holds up to 5 buttons (https://docs.discord.com/developers/components/reference#action-row)."""
MAX_MESSAGE_COMPONENTS = 40
"""A message holds up to 40 components in total, counting nested ones (https://docs.discord.com/developers/components/reference)."""
MAX_CUSTOM_ID_LENGTH = 100
"""A component's ``custom_id`` holds up to 100 characters (https://docs.discord.com/developers/components/reference#anatomy-of-a-component-custom-id)."""
MAX_BUTTON_LABEL_LENGTH = 80
"""A button label holds up to 80 characters (https://docs.discord.com/developers/components/reference#button)."""
MAX_MODAL_TITLE_LENGTH = 45
"""A modal title holds up to 45 characters (https://docs.discord.com/developers/interactions/receiving-and-responding#modal)."""
MAX_LABEL_LENGTH = 45
"""A label holds up to 45 characters (https://docs.discord.com/developers/components/reference#label)."""
MAX_TEXT_INPUT_LENGTH = 4000
"""A text input accepts up to 4000 characters (https://docs.discord.com/developers/components/reference#text-input)."""

MAX_EMBED_FIELDS = 25
"""An embed holds up to 25 fields (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_CHARACTERS = 6000
"""The combined length of an embed's title, description, field names/values and footer text (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_TITLE_LENGTH = 256
"""An embed title holds up to 256 characters (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_DESCRIPTION_LENGTH = 4096
"""An embed description holds up to 4096 characters (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_FIELD_NAME_LENGTH = 256
"""An embed field name holds up to 256 characters (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""
MAX_EMBED_FIELD_VALUE_LENGTH = 1024
"""An embed field value holds up to 1024 characters (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""

MAX_OPTIONS = 25
"""A command or subcommand holds up to 25 options (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""
MAX_CHOICES = 25
"""An option offers up to 25 choices (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""
MAX_CHOICE_NAME_LENGTH = 100
"""A command option choice name, autocomplete results included, holds up to 100 characters (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-choice-structure)."""
MAX_DESCRIPTION_LENGTH = 100
"""A command or option description holds 1 to 100 characters (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""
MAX_OPTION_VALUE_LENGTH = 6000
"""A STRING option's ``min_length`` and ``max_length`` are at most 6000 (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""

MAX_REASON_LENGTH = 512
"""The longest audit log reason Discord keeps (https://docs.discord.com/developers/resources/audit-log#audit-log-entry-object)."""

MAX_USER_LIMIT = 99
"""The most users a voice channel can be limited to; 0 means no limit (https://docs.discord.com/developers/resources/channel#modify-channel-json-params-guild-channel)."""
MAX_CHANNEL_NAME_LENGTH = 100
"""A channel name holds 1 to 100 characters (https://docs.discord.com/developers/resources/channel#channel-object-channel-structure)."""
MIN_GUILD_NAME_LENGTH = 2
"""A guild name holds at least 2 characters (https://docs.discord.com/developers/resources/guild#guild-object-guild-structure)."""
MAX_GUILD_NAME_LENGTH = 100
"""A guild name holds up to 100 characters (https://docs.discord.com/developers/resources/guild#guild-object-guild-structure)."""

MAX_MESSAGES_PER_PAGE = 100
"""The most messages ``GET /channels/{channel_id}/messages`` returns at once (https://docs.discord.com/developers/resources/message#get-channel-messages)."""
MAX_MEMBERS_PER_PAGE = 1000
"""The most members ``GET /guilds/{guild_id}/members`` returns at once (https://docs.discord.com/developers/resources/guild#list-guild-members)."""


def truncate(text: str, limit: int) -> str:
    """Return ``text``, or when it's longer than ``limit`` characters, its start cut to fit ``limit`` with :data:`ELLIPSIS`."""
    return text if len(text) <= limit else text[: limit - len(ELLIPSIS)] + ELLIPSIS
