"""Module that contains channel-related enums."""

from enum import Enum, auto
from typing import Self

from discord import AuditLogAction
from winter_dragon.database.channeltypes import ChannelTypes  # type: ignore[NotAccessed]


__all__ = ("ChannelTypes",)


class LogCategories(Enum):
    """Enum for the different categories of logs."""

    GLOBAL = -1 # "ALL_CATEGORIES"

    # Own Enums
    MEMBER_JOINED = auto()
    MEMBER_LEFT = auto()
    MESSAGE_EDITED = auto()

    # Reflected enums
    GUILD_UPDATE = auto()
    CHANNEL_CREATE = auto()
    CHANNEL_UPDATE = auto()
    CHANNEL_DELETE = auto()
    OVERWRITE_CREATE = auto()
    OVERWRITE_UPDATE = auto()
    OVERWRITE_DELETE = auto()
    KICK = auto()
    MEMBER_PRUNE = auto()
    BAN = auto()
    UNBAN = auto()
    MEMBER_UPDATE = auto()
    MEMBER_ROLE_UPDATE = auto()
    MEMBER_MOVE = auto()
    MEMBER_DISCONNECT = auto()
    BOT_ADD = auto()
    ROLE_CREATE = auto()
    ROLE_UPDATE = auto()
    ROLE_DELETE = auto()
    INVITE_CREATE = auto()
    INVITE_UPDATE = auto()
    INVITE_DELETE = auto()
    WEBHOOK_CREATE = auto()
    WEBHOOK_UPDATE = auto()
    WEBHOOK_DELETE = auto()
    EMOJI_CREATE = auto()
    EMOJI_UPDATE = auto()
    EMOJI_DELETE = auto()
    MESSAGE_DELETE = auto()
    MESSAGE_BULK_DELETE = auto()
    MESSAGE_PIN = auto()
    MESSAGE_UNPIN = auto()
    INTEGRATION_CREATE = auto()
    INTEGRATION_UPDATE = auto()
    INTEGRATION_DELETE = auto()
    STAGE_INSTANCE_CREATE = auto()
    STAGE_INSTANCE_UPDATE = auto()
    STAGE_INSTANCE_DELETE = auto()
    STICKER_CREATE = auto()
    STICKER_UPDATE = auto()
    STICKER_DELETE = auto()
    SCHEDULED_EVENT_CREATE = auto()
    SCHEDULED_EVENT_UPDATE = auto()
    SCHEDULED_EVENT_DELETE = auto()
    THREAD_CREATE = auto()
    THREAD_UPDATE = auto()
    THREAD_DELETE = auto()
    APP_COMMAND_PERMISSION_UPDATE = auto()
    AUTOMOD_RULE_CREATE = auto()
    AUTOMOD_RULE_UPDATE = auto()
    AUTOMOD_RULE_DELETE = auto()
    AUTOMOD_BLOCK_MESSAGE = auto()
    AUTOMOD_FLAG_MESSAGE = auto()
    AUTOMOD_TIMEOUT_MEMBER = auto()

    def from_AuditLogAction(self, action: AuditLogAction) -> Self:  # noqa: N802
        """Get the enum from an AuditLogAction."""
        return self.__class__[action.name.upper()]
