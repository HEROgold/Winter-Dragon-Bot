"""Gateway Intents values: combined intents and aliases map to the documented bits."""

lazy import pytest
lazy from wd_discord.intents import Intents


# Bits from https://docs.discord.com/developers/events/gateway#list-of-intents
GUILDS = 1 << 0
GUILD_MEMBERS = 1 << 1
GUILD_MESSAGES = 1 << 9
GUILD_MESSAGE_REACTIONS = 1 << 10
GUILD_MESSAGE_TYPING = 1 << 11
DIRECT_MESSAGES = 1 << 12
DIRECT_MESSAGE_REACTIONS = 1 << 13
DIRECT_MESSAGE_TYPING = 1 << 14
AUTO_MODERATION_CONFIGURATION = 1 << 20
AUTO_MODERATION_EXECUTION = 1 << 21
GUILD_MESSAGE_POLLS = 1 << 24
DIRECT_MESSAGE_POLLS = 1 << 25


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("messages", GUILD_MESSAGES | DIRECT_MESSAGES),
        ("reactions", GUILD_MESSAGE_REACTIONS | DIRECT_MESSAGE_REACTIONS),
        ("typing", GUILD_MESSAGE_TYPING | DIRECT_MESSAGE_TYPING),
        ("polls", GUILD_MESSAGE_POLLS | DIRECT_MESSAGE_POLLS),
        ("auto_moderation", AUTO_MODERATION_CONFIGURATION | AUTO_MODERATION_EXECUTION),
        ("THREAD_MEMBERS_UPDATE", GUILDS | GUILD_MEMBERS),
        ("MESSAGE_CREATE", GUILD_MESSAGES | DIRECT_MESSAGES),
        ("MESSAGE_UPDATES", GUILD_MESSAGES | DIRECT_MESSAGES),
        ("MESSAGE_DELETE", GUILD_MESSAGES | DIRECT_MESSAGES),
        ("CHANNEL_PINS_UPDATE", GUILDS | DIRECT_MESSAGES),
        ("MESSAGE_REACTION_ADD", GUILD_MESSAGE_REACTIONS | DIRECT_MESSAGE_REACTIONS),
        ("MESSAGE_REACTION_REMOVE", GUILD_MESSAGE_REACTIONS | DIRECT_MESSAGE_REACTIONS),
        ("MESSAGE_REACTION_REMOVE_ALL", GUILD_MESSAGE_REACTIONS | DIRECT_MESSAGE_REACTIONS),
        ("MESSAGE_REACTION_REMOVE_EMOJI", GUILD_MESSAGE_REACTIONS | DIRECT_MESSAGE_REACTIONS),
        ("TYPING_START", GUILD_MESSAGE_TYPING | DIRECT_MESSAGE_TYPING),
        ("MESSAGE_POLL_VOTE_ADD", GUILD_MESSAGE_POLLS | DIRECT_MESSAGE_POLLS),
        ("MESSAGE_POLL_VOTE_REMOVE", GUILD_MESSAGE_POLLS | DIRECT_MESSAGE_POLLS),
    ],
)
def test_combined_intent_is_union_of_its_parts(name: str, expected: int) -> None:
    """A combined intent requests every intent it is made of."""
    intent = Intents[name]

    assert intent != 0
    assert intent == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("guild_polls", GUILD_MESSAGE_POLLS),
        ("dm_polls", DIRECT_MESSAGE_POLLS),
    ],
)
def test_poll_alias_maps_to_its_own_bit(name: str, expected: int) -> None:
    """The guild and direct-message poll aliases name the matching intent."""
    assert Intents[name] == expected


def test_all_includes_every_combined_intent() -> None:
    """``all()`` requests every intent, combined ones included."""
    everything = Intents.all()

    assert everything & Intents.messages == Intents.messages
    assert everything & Intents.polls == Intents.polls


def test_only_one_all_intents_constructor() -> None:
    """The asserting ``all2`` variant is gone; ``all()`` is the single way to request every intent."""
    assert not hasattr(Intents, "all2")
