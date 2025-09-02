"""Module that contains the enums for the bot's activity and status."""

from discord import ActivityType, Status


STATUS_TYPES = [
    Status.dnd,
    Status.do_not_disturb,
    Status.idle,
    Status.invisible,
    Status.offline,
    Status.online,
]
ACTIVITY_TYPES = [
    ActivityType.competing,
    ActivityType.custom,
    ActivityType.listening,
    ActivityType.playing,
    ActivityType.streaming,
    ActivityType.watching,
    # ActivityType.unknown,
]

VALID_RNG_STATUS = [
    Status.dnd,
    Status.do_not_disturb,
    Status.idle,
    Status.online,
]
VALID_RNG_ACTIVITY = [
    ActivityType.competing,
    ActivityType.listening,
    ActivityType.playing,
    ActivityType.streaming,
    ActivityType.watching,
]
