"""Unit tests: stores and entities for commands, users, channels, guilds and messages (no network)."""

from __future__ import annotations

from wd_discord import (
    Channel,
    CurrentUser,
    GlobalCommand,
    GuildCommand,
    Message,
    PartialGlobalCommand,
    User,
    is_network_error,
)
from wd_discord.components import ActionRow, Button, ButtonStyle
from wd_discord.embed import Embed
from wd_discord.errors.api import ApiResponseError
from wd_discord.interactions import ApplicationCommand, ApplicationCommandParams
from wd_discord.resources.invite import Invite
from wd_discord.snowflake import Snowflake
from wd_discord.testing import RecordingClient


COMMANDS = "/applications/2/commands"
COMMAND_JSON = {"id": "77", "application_id": "2", "name": "ping", "description": "Pong", "version": "1"}
USER_JSON = {"id": "7", "username": "someone", "discriminator": "0", "global_name": "Someone"}
DM_JSON = {"id": "6", "type": 1}
MESSAGE_JSON = {
    "id": "5",
    "channel_id": "6",
    "author": {"id": "2", "username": "bot", "discriminator": "0"},
    "content": "hello",
    "timestamp": "2026-10-08T00:00:00+00:00",
    "tts": False,
    "mention_everyone": False,
}
ROW = ActionRow(components=[Button(style=ButtonStyle.SECONDARY, label="Next", custom_id="next")])
PARAMS = ApplicationCommandParams(name="ping", description="Pong")


async def test_create_global_command_returns_a_bound_command() -> None:
    client = RecordingClient()
    client.reply("POST", COMMANDS, COMMAND_JSON)

    command = await client.application.commands.create(PARAMS)

    assert isinstance(command, GlobalCommand)
    assert command.name == "ping"
    assert command.mention == "</ping:77>"
    assert client.sent[0].json == PARAMS.to_json()


async def test_global_command_edit_and_delete_by_id() -> None:
    client = RecordingClient()
    client.reply("PATCH", f"{COMMANDS}/77", COMMAND_JSON)
    command = client.application.commands.partial("77")

    edited = await command.edit(PARAMS)
    deleted = await command.delete()

    assert isinstance(command, PartialGlobalCommand)
    assert isinstance(edited, GlobalCommand)
    assert deleted is None
    assert [(sent.method, sent.path) for sent in client.sent] == [("PATCH", f"{COMMANDS}/77"), ("DELETE", f"{COMMANDS}/77")]


async def test_global_command_failure_is_a_value() -> None:
    client = RecordingClient()
    client.fail("DELETE", f"{COMMANDS}/77", ApiResponseError(code=10063, message="Unknown application command"))

    result = await client.application.commands.partial(77).delete()

    assert isinstance(result, ApiResponseError)
    assert result.code == 10063


async def test_fetch_all_global_commands() -> None:
    client = RecordingClient()
    client.reply("GET", COMMANDS, [COMMAND_JSON, {**COMMAND_JSON, "id": "78", "name": "pong"}])

    commands = await client.application.commands.fetch_all()

    assert not is_network_error(commands)
    assert [command.name for command in commands] == ["ping", "pong"]


async def test_overwrite_global_commands_puts_every_definition() -> None:
    client = RecordingClient()
    client.reply("PUT", COMMANDS, [COMMAND_JSON])

    commands = await client.application.commands.overwrite([PARAMS])

    assert not is_network_error(commands)
    assert [command.id for command in commands] == [Snowflake(77)]
    assert client.sent[0].json == [PARAMS.to_json()]


async def test_guild_commands_are_listed_and_overwritten_under_the_guild_route() -> None:
    client = RecordingClient()
    guild_route = "/applications/2/guilds/9/commands"
    client.reply("GET", guild_route, [{**COMMAND_JSON, "guild_id": "9"}])
    client.reply("PUT", guild_route, [{**COMMAND_JSON, "guild_id": "9"}])
    store = client.application.guild_commands(9)

    fetched = await store.fetch_all()
    overwritten = await store.overwrite([PARAMS])

    assert not is_network_error(fetched)
    assert not is_network_error(overwritten)
    assert [command.mention for command in fetched] == ["</ping:77>"]
    assert all(isinstance(command, GuildCommand) for command in overwritten)
    assert [(sent.method, sent.path) for sent in client.sent] == [("GET", guild_route), ("PUT", guild_route)]


def test_fetched_command_round_trips_to_the_params_it_was_registered_with() -> None:
    fetched = ApplicationCommand.model_validate({**COMMAND_JSON, "dm_permission": True, "guild_id": "9"})

    assert fetched.to_params() == ApplicationCommandParams(name="ping", description="Pong", options=[], nsfw=False)


async def test_users_me_returns_an_editable_current_user() -> None:
    client = RecordingClient()
    client.reply("GET", "/users/@me", USER_JSON)
    client.reply("PATCH", "/users/@me", {**USER_JSON, "username": "renamed"})

    me = await client.users.me()
    assert isinstance(me, CurrentUser)
    renamed = await me.edit(username="renamed")

    assert isinstance(renamed, CurrentUser)
    assert renamed.username == "renamed"
    assert client.sent[1].json == {"username": "renamed"}


async def test_user_send_opens_a_dm_then_sends() -> None:
    client = RecordingClient()
    client.reply("POST", "/users/@me/channels", DM_JSON)
    client.reply("POST", "/channels/6/messages", MESSAGE_JSON)

    message = await client.users.partial(7).send("hello", embeds=[Embed(title="sales")], components=[ROW])

    assert isinstance(message, Message)
    assert message.content == "hello"
    assert client.sent[0].json == {"recipient_id": "7"}
    assert client.sent[1].json["embeds"] == [{"title": "sales"}]


async def test_user_send_stops_when_the_dm_fails() -> None:
    client = RecordingClient()
    client.fail("POST", "/users/@me/channels", ApiResponseError(code=50007, message="Cannot send messages to this user"))

    result = await client.users.partial(7).send("hello")

    assert isinstance(result, ApiResponseError)
    assert len(client.sent) == 1


async def test_fetched_user_is_bound() -> None:
    client = RecordingClient()
    client.reply("GET", "/users/7", USER_JSON)

    user = await client.users.fetch(7)

    assert isinstance(user, User)
    assert user.display_name == "Someone"
    assert user.mention == "<@7>"


async def test_channel_send_and_invite() -> None:
    client = RecordingClient()
    client.reply("POST", "/channels/6/messages", MESSAGE_JSON)
    client.reply("POST", "/channels/6/invites", {"code": "abc"})
    channel = client.channels.partial("6")

    await channel.send("hello", components=[ROW])
    invite = await channel.create_invite()

    assert client.sent[0].json["content"] == "hello"
    assert isinstance(invite, Invite)
    assert invite.url == "https://discord.gg/abc"
    assert client.sent[1].json == {"max_age": 86400, "max_uses": 1, "temporary": False, "unique": True}


async def test_message_edit_and_delete_target_its_channel() -> None:
    client = RecordingClient()
    client.reply("POST", "/channels/6/messages", MESSAGE_JSON)
    client.reply("PATCH", "/channels/6/messages/5", {**MESSAGE_JSON, "content": "edited"})
    message = await client.channels.partial(6).send("hello")
    assert isinstance(message, Message)

    edited = await message.edit("edited")
    await message.delete()

    assert isinstance(edited, Message)
    assert edited.content == "edited"
    assert client.sent[2].method == "DELETE"
    assert client.sent[2].path == "/channels/6/messages/5"


async def test_guild_channels_and_leave() -> None:
    client = RecordingClient()
    client.reply("GET", "/guilds/8/channels", [{"id": "6", "type": 0, "name": "general"}])
    guild = client.guilds.partial(8)

    channels = await guild.channels()
    left = await guild.leave()

    assert not is_network_error(channels)
    assert [(type(channel), channel.name) for channel in channels] == [(Channel, "general")]
    assert left is None
    assert client.sent[1].path == "/users/@me/guilds/8"
