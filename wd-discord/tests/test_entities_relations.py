"""Unit tests: entity relations come back full when the data in hand has them, else partial; and the new actions."""

from __future__ import annotations

from datetime import UTC, datetime

from wd_discord import (
    Application,
    Channel,
    Emoji,
    GatewayGuild,
    Guild,
    Invite,
    Member,
    Message,
    PartialChannel,
    PartialGuild,
    PartialMember,
    PartialMessage,
    PartialRole,
    PartialUser,
    Role,
    User,
    VoiceState,
    bind,
    is_network_error,
)
from wd_discord.entities import CommandInteraction, ComponentInteraction, Entitlement, PartialGuildCommand
from wd_discord.gateway import EventName, parse_dispatch
from wd_discord.interactions import ApplicationCommandParams
from wd_discord.partial_emoji import PartialEmoji
from wd_discord.resources.application import Application as ApplicationModel
from wd_discord.resources.channel import Channel as ChannelModel
from wd_discord.resources.entitlement import Entitlement as EntitlementModel
from wd_discord.resources.guild import Guild as GuildModel
from wd_discord.resources.invite import Invite as InviteModel
from wd_discord.resources.voice import VoiceState as VoiceStateModel
from wd_discord.snowflake import Snowflake
from wd_discord.testing import GUILD_JSON, RecordingClient


USER_JSON = {"id": "9", "username": "owner", "discriminator": "0"}
MEMBER_JSON = {"user": USER_JSON, "roles": ["5"], "joined_at": None, "deaf": False, "mute": False}
ROLE_JSON = {
    "id": "5",
    "name": "Mods",
    "color": 0,
    "hoist": False,
    "position": 1,
    "permissions": "8",
    "managed": False,
    "mentionable": True,
    "flags": 0,
}
EVERYONE_JSON = {**ROLE_JSON, "id": "1", "name": "@everyone", "position": 0}
AFK_JSON = {"id": "20", "type": 2, "name": "AFK"}
GUILD_WITH_RELATIONS = {**GUILD_JSON, "afk_channel_id": "20", "roles": [EVERYONE_JSON, ROLE_JSON]}
MESSAGE_JSON = {
    "id": "50",
    "channel_id": "6",
    "author": USER_JSON,
    "content": "hi",
    "timestamp": "2026-10-10T00:00:00+00:00",
    "tts": False,
    "mention_everyone": False,
}
COMMAND_JSON = {"id": "77", "application_id": "2", "guild_id": "1", "name": "ping", "description": "Pong", "version": "1"}
VOICE_JSON = {
    "channel_id": "20",
    "user_id": "9",
    "session_id": "s",
    "deaf": False,
    "mute": False,
    "self_deaf": False,
    "self_mute": False,
    "self_video": False,
    "suppress": False,
    "request_to_speak_timestamp": None,
}


def _gateway_guild(client: RecordingClient) -> GatewayGuild:
    payload = {**GUILD_WITH_RELATIONS, "channels": [AFK_JSON], "members": [MEMBER_JSON], "voice_states": [VOICE_JSON]}
    guild = bind(client, parse_dispatch(EventName.GUILD_CREATE, payload))
    assert isinstance(guild, GatewayGuild)
    return guild


def test_fetched_guild_relations_are_partial_without_the_data() -> None:
    client = RecordingClient()
    guild = Guild(client, GuildModel.model_validate(GUILD_WITH_RELATIONS))

    assert guild.owner == PartialMember(client, Snowflake(9), Snowflake(1))
    assert guild.afk_channel == PartialChannel(client, Snowflake(20))
    assert guild.system_channel is None


def test_guild_roles_come_in_full_from_its_own_data() -> None:
    guild = Guild(RecordingClient(), GuildModel.model_validate(GUILD_WITH_RELATIONS))

    assert [role.name for role in guild.roles] == ["@everyone", "Mods"]
    assert isinstance(guild.default_role, Role)
    assert guild.default_role.mention == "@everyone"
    mods = guild.get_role(5)
    assert mods is not None
    assert (mods.mention, mods.guild_id) == ("<@&5>", Snowflake(1))
    assert guild.get_role(6) is None


def test_gateway_guild_resolves_relations_from_what_it_carries() -> None:
    guild = _gateway_guild(RecordingClient())

    assert isinstance(guild.owner, Member)
    assert guild.owner.display_name == "owner"
    assert isinstance(guild.afk_channel, Channel)
    assert guild.afk_channel.name == "AFK"


def test_gateway_guild_fills_in_the_guild_its_children_left_out() -> None:
    guild = _gateway_guild(RecordingClient())

    [channel] = guild.channels
    [state] = guild.voice_states
    assert channel.guild == PartialGuild(guild.client, Snowflake(1))
    assert state.guild == PartialGuild(guild.client, Snowflake(1))
    assert state.channel == PartialChannel(guild.client, Snowflake(20))


def test_member_relations() -> None:
    client = RecordingClient()
    guild = _gateway_guild(client)
    member = guild.get_member(9)

    assert member is not None
    assert isinstance(member.user, User)
    assert member.guild == PartialGuild(client, Snowflake(1))
    assert list(member.roles) == [PartialRole(client, Snowflake(5), Snowflake(1))]
    assert guild.member(9).user == PartialUser(client, Snowflake(9))


async def test_member_moderation_routes() -> None:
    client = RecordingClient()
    member = client.guilds.partial(1).member(9)
    until = datetime(2026, 10, 11, tzinfo=UTC)

    await member.add_role(client.guilds.partial(1).role(5), reason="promoted")
    await member.remove_role(client.guilds.partial(1).role(5))
    await member.timeout(until)
    await member.set_nick("Boss")
    await member.ban(delete_message_seconds=60)
    await member.unban()
    await member.kick()

    assert [(sent.method, sent.path) for sent in client.sent] == [
        ("PUT", "/guilds/1/members/9/roles/5"),
        ("DELETE", "/guilds/1/members/9/roles/5"),
        ("PATCH", "/guilds/1/members/9"),
        ("PATCH", "/guilds/1/members/9"),
        ("PUT", "/guilds/1/bans/9"),
        ("DELETE", "/guilds/1/bans/9"),
        ("DELETE", "/guilds/1/members/9"),
    ]
    assert client.sent[2].json == {"communication_disabled_until": "2026-10-11T00:00:00+00:00"}
    assert client.sent[3].json == {"nick": "Boss"}
    assert client.sent[4].json == {"delete_message_seconds": 60}


async def test_role_fetch_and_delete() -> None:
    client = RecordingClient()
    client.reply("GET", "/guilds/1/roles/5", ROLE_JSON)
    client.reply("GET", "/guilds/1/roles", [EVERYONE_JSON, ROLE_JSON])
    role = client.guilds.partial(1).role(5)

    fetched = await role.fetch()
    roles = await client.guilds.partial(1).fetch_roles()
    await role.delete()

    assert isinstance(fetched, Role)
    assert fetched.permissions.value == 8
    assert not is_network_error(roles)
    assert [role.id for role in roles] == [Snowflake(1), Snowflake(5)]
    assert client.sent[-1].path == "/guilds/1/roles/5"


def test_channel_relations() -> None:
    client = RecordingClient()
    channel = Channel(
        client,
        ChannelModel.model_validate(
            {
                "id": "6",
                "type": 0,
                "guild_id": "1",
                "parent_id": "10",
                "last_message_id": "50",
                "permission_overwrites": [
                    {"id": "5", "type": 0, "allow": "0", "deny": "2048"},
                    {"id": "9", "type": 1, "allow": "2048", "deny": "0"},
                ],
            },
        ),
    )

    assert channel.guild == PartialGuild(client, Snowflake(1))
    assert channel.parent == PartialChannel(client, Snowflake(10))
    assert channel.last_message == PartialMessage(client, Snowflake(50), Snowflake(6))
    assert [overwrite.target for overwrite in channel.overwrites] == [
        PartialRole(client, Snowflake(5), Snowflake(1)),
        PartialMember(client, Snowflake(9), Snowflake(1)),
    ]


async def test_channel_message_history_and_bulk_delete() -> None:
    client = RecordingClient()
    client.reply("GET", "/channels/6/messages", [MESSAGE_JSON])
    channel = client.channels.partial(6)

    messages = await channel.fetch_messages(before=channel.message(60), limit=10)
    await channel.delete_messages([channel.message(50), channel.message(51)])
    await channel.trigger_typing()

    assert not is_network_error(messages)
    assert [message.id for message in messages] == [Snowflake(50)]
    assert client.sent[0].params == {"limit": "10", "before": "60"}
    assert client.sent[1].json == {"messages": ["50", "51"]}
    assert client.sent[2].path == "/channels/6/typing"


async def test_thread_membership_routes() -> None:
    client = RecordingClient()
    thread = client.channels.partial(30)

    await thread.join_thread()
    await thread.add_thread_member(client.users.partial(9))
    await thread.remove_thread_member(client.guilds.partial(1).member(9))
    await thread.leave_thread()

    assert [(sent.method, sent.path) for sent in client.sent] == [
        ("PUT", "/channels/30/thread-members/@me"),
        ("PUT", "/channels/30/thread-members/9"),
        ("DELETE", "/channels/30/thread-members/9"),
        ("DELETE", "/channels/30/thread-members/@me"),
    ]


async def test_partial_message_reactions_and_pins() -> None:
    client = RecordingClient()
    client.reply("GET", "/channels/6/messages/50", MESSAGE_JSON)
    message = client.channels.partial(6).message(50)

    fetched = await message.fetch()
    await message.add_reaction(PartialEmoji(id=Snowflake(7), name="wave"))
    await message.remove_reaction("👍", client.users.partial(9))
    await message.remove_reaction("👍")
    await message.clear_reactions()
    await message.pin()
    await message.unpin()

    assert isinstance(fetched, Message)
    assert fetched.jump_url == "https://discord.com/channels/@me/6/50"
    assert [(sent.method, sent.path) for sent in client.sent[1:]] == [
        ("PUT", "/channels/6/messages/50/reactions/wave%3A7/@me"),
        ("DELETE", "/channels/6/messages/50/reactions/%F0%9F%91%8D/9"),
        ("DELETE", "/channels/6/messages/50/reactions/%F0%9F%91%8D/@me"),
        ("DELETE", "/channels/6/messages/50/reactions"),
        ("PUT", "/channels/6/messages/pins/50"),
        ("DELETE", "/channels/6/messages/pins/50"),
    ]


def test_guild_emoji_relations() -> None:
    client = RecordingClient()
    emoji_json = {"id": "7", "name": "wave", "roles": ["5"], "user": USER_JSON, "animated": True}
    guild = Guild(client, GuildModel.model_validate({**GUILD_JSON, "emojis": [emoji_json]}))

    [emoji] = guild.emojis
    assert isinstance(emoji, Emoji)
    assert emoji.mention == "<a:wave:7>"
    assert list(emoji.roles) == [PartialRole(client, Snowflake(5), Snowflake(1))]
    assert isinstance(emoji.user, User)


async def test_invite_relations_and_delete() -> None:
    client = RecordingClient()
    invite = Invite(
        client,
        InviteModel.model_validate({"code": "abc", "guild": {"id": "1"}, "channel": {"id": "6"}, "inviter": USER_JSON}),
    )

    await invite.delete()

    assert invite.guild == PartialGuild(client, Snowflake(1))
    assert invite.channel == PartialChannel(client, Snowflake(6))
    assert isinstance(invite.inviter, User)
    assert client.sent[0].path == "/invites/abc"


def test_interaction_member_and_channel_are_entities() -> None:
    client = RecordingClient()
    payload = {
        "id": "1",
        "application_id": "2",
        "type": 2,
        "token": "tok",
        "version": 1,
        "guild_id": "1",
        "channel_id": "6",
        "member": MEMBER_JSON,
        "channel": {"id": "6", "type": 0, "name": "general"},
        "data": {
            "id": "10",
            "name": "c",
            "type": 1,
            "resolved": {"users": {"9": USER_JSON}, "roles": {"5": ROLE_JSON}},
        },
    }
    interaction = bind(client, parse_dispatch(EventName.INTERACTION_CREATE, payload))

    assert isinstance(interaction, CommandInteraction)
    assert isinstance(interaction.member, Member)
    assert interaction.member.guild_id == Snowflake(1)
    assert isinstance(interaction.channel, Channel)
    assert interaction.channel.guild == PartialGuild(client, Snowflake(1))
    assert interaction.resolved is not None
    assert isinstance(interaction.resolved.user(9), User)
    role = interaction.resolved.role("5")
    assert isinstance(role, Role)
    assert role.guild_id == Snowflake(1)


def test_component_interaction_message_is_an_entity() -> None:
    client = RecordingClient()
    payload = {
        "id": "1",
        "application_id": "2",
        "type": 3,
        "token": "tok",
        "version": 1,
        "user": USER_JSON,
        "channel_id": "6",
        "message": MESSAGE_JSON,
        "data": {"custom_id": "next", "component_type": 2},
    }
    interaction = bind(client, parse_dispatch(EventName.INTERACTION_CREATE, payload))

    assert isinstance(interaction, ComponentInteraction)
    assert isinstance(interaction.message, Message)
    assert interaction.message.author.username == "owner"


def test_voice_state_user_is_full_only_with_its_member() -> None:
    client = RecordingClient()
    bare = VoiceState(client, VoiceStateModel.model_validate({**VOICE_JSON, "guild_id": "1"}))
    with_member = VoiceState(client, VoiceStateModel.model_validate({**VOICE_JSON, "guild_id": "1", "member": MEMBER_JSON}))

    assert bare.user == PartialUser(client, Snowflake(9))
    assert isinstance(with_member.user, User)
    assert bare.guild == PartialGuild(client, Snowflake(1))


def test_application_team_owner_is_full_when_a_member() -> None:
    client = RecordingClient()
    team = {
        "id": "40",
        "name": "Team",
        "icon": None,
        "owner_user_id": "9",
        "members": [{"membership_state": 2, "team_id": "40", "user": USER_JSON, "role": "admin"}],
    }
    base = {"id": "2", "name": "app", "icon": None, "description": "", "bot_public": True}
    base |= {"bot_require_code_grant": False, "verify_key": "k", "guild_id": "1"}
    application = Application(client, ApplicationModel.model_validate({**base, "team": team}))
    stranger_owned = Application(client, ApplicationModel.model_validate({**base, "team": {**team, "owner_user_id": "8"}}))

    assert application.team is not None
    assert isinstance(application.team.owner, User)
    assert stranger_owned.team is not None
    assert stranger_owned.team.owner == PartialUser(client, Snowflake(8))
    assert application.guild == PartialGuild(client, Snowflake(1))


async def test_entitlement_consume_and_delete() -> None:
    client = RecordingClient()
    entitlement = Entitlement(
        client,
        EntitlementModel.model_validate(
            {
                "id": "60",
                "sku_id": "61",
                "application_id": "2",
                "user_id": "9",
                "type": 8,
                "deleted": False,
                "starts_at": None,
                "ends_at": None,
            },
        ),
    )

    await entitlement.consume()
    await entitlement.delete()

    assert entitlement.user == PartialUser(client, Snowflake(9))
    assert [(sent.method, sent.path) for sent in client.sent] == [
        ("POST", "/applications/2/entitlements/60/consume"),
        ("DELETE", "/applications/2/entitlements/60"),
    ]


async def test_guild_command_by_id() -> None:
    client = RecordingClient()
    route = "/applications/2/guilds/1/commands"
    client.reply("POST", route, COMMAND_JSON)
    client.reply("PATCH", f"{route}/77", COMMAND_JSON)
    store = client.application.guild_commands(client.guilds.partial(1))

    created = await store.create(ApplicationCommandParams(name="ping", description="Pong"))
    partial = store.partial(77)
    edited = await partial.edit(ApplicationCommandParams(name="ping", description="Pong"))
    await partial.delete()

    assert not is_network_error(created)
    assert created.guild == PartialGuild(client, Snowflake(1))
    assert isinstance(partial, PartialGuildCommand)
    assert not is_network_error(edited)
    assert edited.mention == "</ping:77>"
    assert client.sent[-1].method == "DELETE"
    assert client.sent[-1].path == f"{route}/77"


async def test_welcome_screen_channels_are_handles() -> None:
    client = RecordingClient()
    screen_json = {
        "description": "Hi",
        "welcome_channels": [{"channel_id": "6", "description": "Chat", "emoji_id": None, "emoji_name": "👋"}],
    }
    client.reply("GET", "/guilds/1/welcome-screen", screen_json)

    screen = await client.guilds.partial(1).fetch_welcome_screen()

    assert not is_network_error(screen)
    [channel] = screen.channels
    assert channel.channel == PartialChannel(client, Snowflake(6))
    assert channel.emoji is not None
    assert channel.emoji.name == "👋"


async def test_lookups_by_entity_send_their_ids() -> None:
    client = RecordingClient()
    client.reply("GET", "/guilds/1/voice-states/9", {**VOICE_JSON, "guild_id": "1"})
    client.reply("GET", "/applications/2/entitlements", [])
    guild = client.guilds.partial(1)

    state = await guild.fetch_voice_state(guild.member(9))
    await guild.fetch_voice_state()
    await client.application.fetch_entitlements(user=client.users.partial(9), guild=guild)

    assert isinstance(state, VoiceState)
    assert client.sent[1].path == "/guilds/1/voice-states/@me"
    assert client.sent[2].params == {"user_id": "9", "guild_id": "1"}
