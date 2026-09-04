"""Module that contains the Gateway Intents."""
from __future__ import annotations

lazy from enum import IntFlag
lazy from functools import wraps
lazy from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    lazy from collections.abc import Callable


class Intents(IntFlag):
    """Represents the Gateway Intents.

    This is a subclass of ``int`` that allows for bitwise operations to combine intents.
    https://docs.discord.com/developers/events/gateway#list-of-intents
    Marked with *, ** or ***, read the Discord docs for the meaning of those intents.
    """

    GUILDS = (1 << 0)
    GUILD_CREATE = GUILDS
    GUILD_UPDATE = GUILDS
    GUILD_DELETE = GUILDS
    GUILD_ROLE_CREATE = GUILDS
    GUILD_ROLE_UPDATE = GUILDS
    GUILD_ROLE_DELETE = GUILDS
    CHANNEL_CREATE = GUILDS
    CHANNEL_UPDATE = GUILDS
    CHANNEL_DELETE = GUILDS
    THREAD_CREATE = GUILDS
    THREAD_UPDATE = GUILDS
    THREAD_DELETE = GUILDS
    THREAD_LIST_SYNC = GUILDS
    THREAD_MEMBER_UPDATE = GUILDS
    STAGE_INSTANCE_CREATE = GUILDS
    STAGE_INSTANCE_UPDATE = GUILDS
    STAGE_INSTANCE_DELETE = GUILDS
    VOICE_CHANNEL_STATUS_UPDATE = GUILDS
    VOICE_CHANNEL_START_TIME_UPDATE = GUILDS
    guilds = GUILDS

    GUILD_MEMBERS = (1 << 1) # **
    GUILD_MEMBER_ADD = GUILD_MEMBERS
    GUILD_MEMBER_UPDATE = GUILD_MEMBERS
    GUILD_MEMBER_REMOVE = GUILD_MEMBERS
    members = GUILD_MEMBERS

    GUILD_MODERATION = (1 << 2)
    GUILD_AUDIT_LOG_ENTRY_CREATE = GUILD_MODERATION
    GUILD_BAN_ADD = GUILD_MODERATION
    GUILD_BAN_REMOVE = GUILD_MODERATION
    moderation = GUILD_MODERATION
    bans = GUILD_MODERATION

    GUILD_EXPRESSIONS = (1 << 3)
    GUILD_EMOJIS_UPDATE = GUILD_EXPRESSIONS
    GUILD_STICKERS_UPDATE = GUILD_EXPRESSIONS
    GUILD_SOUNDBOARD_SOUND_CREATE = GUILD_EXPRESSIONS
    GUILD_SOUNDBOARD_SOUND_UPDATE = GUILD_EXPRESSIONS
    GUILD_SOUNDBOARD_SOUND_DELETE = GUILD_EXPRESSIONS
    GUILD_SOUNDBOARD_SOUNDS_UPDATE = GUILD_EXPRESSIONS
    emojis = GUILD_EXPRESSIONS
    emojis_and_stickers = GUILD_EXPRESSIONS
    expressions = GUILD_EXPRESSIONS

    GUILD_INTEGRATIONS = (1 << 4)
    GUILD_INTEGRATIONS_UPDATE = GUILD_INTEGRATIONS
    INTEGRATION_CREATE = GUILD_INTEGRATIONS
    INTEGRATION_UPDATE = GUILD_INTEGRATIONS
    INTEGRATION_DELETE = GUILD_INTEGRATIONS
    integrations = GUILD_INTEGRATIONS

    GUILD_WEBHOOKS = (1 << 5)
    WEBHOOKS_UPDATE = GUILD_WEBHOOKS
    webhooks = GUILD_WEBHOOKS

    GUILD_INVITES = (1 << 6)
    INVITE_CREATE = GUILD_INVITES
    INVITE_DELETE = GUILD_INVITES
    invites = GUILD_INVITES

    GUILD_VOICE_STATES = (1 << 7)
    VOICE_CHANNEL_EFFECT_SEND = GUILD_VOICE_STATES
    VOICE_STATE_UPDATE = GUILD_VOICE_STATES
    voice_states = GUILD_VOICE_STATES

    GUILD_PRESENCES = (1 << 8) # **
    PRESENCE_UPDATE = GUILD_PRESENCES
    presences = GUILD_PRESENCES

    GUILD_MESSAGES = (1 << 9)
    MESSAGE_DELETE_BULK = GUILD_MESSAGES
    guild_messages = GUILD_MESSAGES

    GUILD_MESSAGE_REACTIONS = (1 << 10)
    guild_reactions = GUILD_MESSAGE_REACTIONS

    GUILD_MESSAGE_TYPING = (1 << 11)
    guild_typing = GUILD_MESSAGE_TYPING

    DIRECT_MESSAGES = (1 << 12)
    dm_messages = DIRECT_MESSAGES
    messages = GUILD_MESSAGES & DIRECT_MESSAGES

    DIRECT_MESSAGE_REACTIONS = (1 << 13)
    dm_reactions = DIRECT_MESSAGE_REACTIONS
    reactions = GUILD_MESSAGE_REACTIONS & DIRECT_MESSAGE_REACTIONS

    DIRECT_MESSAGE_TYPING = (1 << 14)
    dm_typing = DIRECT_MESSAGE_TYPING
    typing = GUILD_MESSAGE_TYPING & DIRECT_MESSAGE_TYPING

    MESSAGE_CONTENT = (1 << 15) # ***
    message_content = MESSAGE_CONTENT

    GUILD_SCHEDULED_EVENTS = (1 << 16)
    GUILD_SCHEDULED_EVENT_CREATE = GUILD_SCHEDULED_EVENTS
    GUILD_SCHEDULED_EVENT_UPDATE = GUILD_SCHEDULED_EVENTS
    GUILD_SCHEDULED_EVENT_DELETE = GUILD_SCHEDULED_EVENTS
    GUILD_SCHEDULED_EVENT_USER_ADD = GUILD_SCHEDULED_EVENTS
    GUILD_SCHEDULED_EVENT_USER_REMOVE = GUILD_SCHEDULED_EVENTS
    guild_scheduled_events = GUILD_SCHEDULED_EVENTS

    AUTO_MODERATION_CONFIGURATION = (1 << 20)
    AUTO_MODERATION_RULE_CREATE = AUTO_MODERATION_CONFIGURATION
    AUTO_MODERATION_RULE_UPDATE = AUTO_MODERATION_CONFIGURATION
    AUTO_MODERATION_RULE_DELETE = AUTO_MODERATION_CONFIGURATION
    auto_moderation_configuration = AUTO_MODERATION_CONFIGURATION

    AUTO_MODERATION_EXECUTION = (1 << 21)
    AUTO_MODERATION_ACTION_EXECUTION = AUTO_MODERATION_EXECUTION
    auto_moderation_execution = AUTO_MODERATION_EXECUTION
    auto_moderation = AUTO_MODERATION_CONFIGURATION & AUTO_MODERATION_EXECUTION

    GUILD_MESSAGE_POLLS = (1 << 24)
    dm_polls = GUILD_MESSAGE_POLLS

    DIRECT_MESSAGE_POLLS = (1 << 25)
    guild_polls = DIRECT_MESSAGE_POLLS
    polls = GUILD_MESSAGE_POLLS & DIRECT_MESSAGE_POLLS

    # Composite intents for convenience
    # Each of these are mentioned under their respective categories.
    # Some are mentioned multiple times, and will inherit all the intents they are mentioned under.
    THREAD_MEMBERS_UPDATE = GUILD_MEMBERS & GUILDS # *
    MESSAGE_CREATE = DIRECT_MESSAGES & GUILD_MESSAGES
    MESSAGE_UPDATES = DIRECT_MESSAGES & GUILD_MESSAGES
    MESSAGE_DELETE = DIRECT_MESSAGES & GUILD_MESSAGES
    CHANNEL_PINS_UPDATE = DIRECT_MESSAGE_TYPING & GUILDS
    MESSAGE_POLL_VOTE_REMOVE = DIRECT_MESSAGE_POLLS & GUILD_MESSAGE_POLLS
    MESSAGE_REACTION_ADD = DIRECT_MESSAGE_REACTIONS & GUILD_MESSAGE_REACTIONS
    MESSAGE_REACTION_REMOVE = DIRECT_MESSAGE_REACTIONS & GUILD_MESSAGE_REACTIONS
    MESSAGE_REACTION_REMOVE_ALL = DIRECT_MESSAGE_REACTIONS & GUILD_MESSAGE_REACTIONS
    MESSAGE_REACTION_REMOVE_EMOJI = DIRECT_MESSAGE_REACTIONS & GUILD_MESSAGE_REACTIONS
    TYPING_START = DIRECT_MESSAGE_TYPING & GUILD_MESSAGE_TYPING
    MESSAGE_POLL_VOTE_ADD = DIRECT_MESSAGE_POLLS & GUILD_MESSAGE_POLLS

    def none() -> Intents:
        """Return an Intents object with no intents set."""
        return Intents(0)

    def all() -> Intents:
        """Return an Intents object with all intents set."""
        all_intents = Intents.none()
        for intent in Intents:
            all_intents |= intent
        return all_intents

type Decorator[**P, R] = Callable[P, R]
type DecoratorFactory[**P, R] = Callable[[Callable[P, R]], Decorator[P, R]]

def requires_intents[**P, R](*required_intents: Intents, actual_intents: Intents | None = None) -> DecoratorFactory[P, R]:
    """Check if the required intents are enabled before executing the function.

    ```py
    @requires_intents(Intents.GUILDS, intents)
    def on_guild_join() -> None:
        ...
    ```

    """
    def decorator(func: Callable[P, R]) -> Decorator[P, R]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            if actual_intents is not None and not all((actual_intents & intent) == intent for intent in required_intents):
                    missing_intents = [intent for intent in required_intents if (actual_intents & intent) != intent]
                    msg = f"Missing required intents: {', '.join(intent.name for intent in missing_intents)}"
                    raise RuntimeError(msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator
