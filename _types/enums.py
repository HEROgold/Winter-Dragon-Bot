from enum import Enum, auto
from typing import Self

from discord import AuditLogAction


class ChannelTypes(Enum):
    STATS = auto()
    LOGS = auto()
    TICKETS = auto()
    TEAM_VOICE = auto()
    TEAM_CATEGORY = auto()
    TEAM_LOBBY = auto()


class Generators(Enum):
    Candy = auto()
    Ferrari = auto()
    Peru = auto()
    Mystic = auto()
    Gamboge = auto()
    Chrome = auto()
    Selective = auto()
    Tangerine = auto()
    Golden = auto()
    Canary = auto()
    Chartreuse = auto()
    Lime = auto()
    Bitter = auto()
    Spring = auto()
    Mango = auto()
    Lawn = auto()
    Chlorophyll = auto()
    Harlequin = auto()
    Ultramarine = auto()
    Phlox = auto()
    Cerulean = auto()
    Fuchsia = auto()
    Guppy = auto()
    Crimson = auto()
    Cornflower = auto()

    @classmethod
    def generation_rate(cls, generator: Self) -> float:
        val = generator.value / 2 if generator.value >> 2 == 0 else generator.value >> 2
        return val / 2


class SuggestionTypes(Enum):
    NEVER_HAVE_I_EVER = auto()
    WOULD_YOU_RATHER = auto()


class LogCategories(Enum):
    GLOBAL = "ALL_CATEGORIES"

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
        return self.__class__[action.name.upper()]


class StatusTypes(Enum):
    DND = auto()
    DO_NOT_DISTURB = auto()
    IDLE = auto()
    INVISIBLE = auto()
    OFFLINE = auto()
    ONLINE = auto()
    RANDOM = auto()


class ActivityTypes(Enum):
    COMPETING = auto()
    CUSTOM = auto()
    LISTENING = auto()
    PLAYING = auto()
    STREAMING = auto()
    WATCHING = auto()
    RANDOM = auto()
