"""Unit tests: bound interactions send the right callbacks and webhook requests (no network)."""

import json

from wd_discord import (
    AutocompleteInteraction,
    CommandInteraction,
    ComponentInteraction,
    Message,
    ModalSubmitInteraction,
    UnknownInteraction,
    User,
    bind,
)
from wd_discord.components import ActionRow, Button, ButtonStyle, ComponentType, Label, Modal, TextInput
from wd_discord.embed import Embed
from wd_discord.errors.api import ApiResponseError
from wd_discord.files import File
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import CommandInteraction as CommandInteractionModel
from wd_discord.gateway.events import ComponentInteraction as ComponentInteractionModel
from wd_discord.gateway.events import Interaction as InteractionModel
from wd_discord.gateway.events import InteractionData, InteractionType, MessageComponentData, ModalSubmitData
from wd_discord.gateway.events import ModalSubmitInteraction as ModalSubmitInteractionModel
from wd_discord.interactions import ApplicationCommandOptionChoice
from wd_discord.testing import RecordingClient, message_json, user_json


USER_JSON = user_json(username="asker")
COMMAND = CommandInteractionModel(
    id="1",
    application_id="2",
    type=InteractionType.APPLICATION_COMMAND,
    token="tok",  # noqa: S106
    version=1,
    guild_id="8",
    channel_id="6",
    user=USER_JSON,
    data=InteractionData(id="10", name="c", type=1),
)
COMPONENT = ComponentInteractionModel(
    id="1",
    application_id="2",
    type=InteractionType.MESSAGE_COMPONENT,
    token="tok",  # noqa: S106
    version=1,
    data=MessageComponentData(custom_id="page:2", component_type=ComponentType.BUTTON),
    message={"id": "11"},
)
AUTOCOMPLETE = AutocompleteInteractionModel(
    id="1",
    application_id="2",
    type=InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE,
    token="tok",  # noqa: S106
    version=1,
    data=InteractionData(id="10", name="c", type=1),
)
CALLBACK = "/interactions/1/tok/callback"
ORIGINAL = "/webhooks/2/tok/messages/@original"
FOLLOWUP = "/webhooks/2/tok"
ROW = ActionRow(components=[Button(style=ButtonStyle.SECONDARY, label="Next", custom_id="next")])
ROW_JSON = [{"type": 1, "components": [{"type": 2, "style": 2, "label": "Next", "custom_id": "next", "disabled": False}]}]


def _command(client: RecordingClient) -> CommandInteraction:
    return CommandInteraction(client, COMMAND)


def _component(client: RecordingClient) -> ComponentInteraction:
    return ComponentInteraction(client, COMPONENT)


def test_bind_picks_the_class_matching_the_model() -> None:
    client = RecordingClient()
    ping = InteractionModel.model_validate({"id": "1", "application_id": "2", "type": 1, "token": "tok", "version": 1})
    assert isinstance(bind(client, COMMAND), CommandInteraction)
    assert isinstance(bind(client, COMPONENT), ComponentInteraction)
    assert isinstance(bind(client, AUTOCOMPLETE), AutocompleteInteraction)
    assert isinstance(bind(client, ping), UnknownInteraction)


def test_exposes_the_model_through_bound_properties() -> None:
    client = RecordingClient()
    interaction = _command(client)
    assert interaction.command_name == "c"
    assert isinstance(interaction.user, User)
    assert interaction.user.username == "asker"
    assert interaction.channel is not None
    assert str(interaction.channel.id) == "6"
    assert interaction.guild is not None
    assert str(interaction.guild.id) == "8"
    assert interaction.model is COMMAND


async def test_respond_sends_a_type_4_callback() -> None:
    client = RecordingClient()
    interaction = _command(client)
    assert await interaction.respond("hi", components=[ROW]) is None
    assert client.requests_to("POST", CALLBACK)[0].json == {"type": 4, "data": {"content": "hi", "components": ROW_JSON}}
    assert interaction.responded


async def test_ephemeral_respond_sets_flag_64() -> None:
    client = RecordingClient()
    await _command(client).respond("hi", ephemeral=True)
    assert client.sent[0].json == {"type": 4, "data": {"content": "hi", "flags": 64}}


async def test_respond_after_answering_sends_a_followup() -> None:
    client = RecordingClient()
    client.reply("POST", FOLLOWUP, message_json())
    interaction = _command(client)
    await interaction.defer()
    await interaction.respond("oops", ephemeral=True)
    assert [sent.path for sent in client.sent] == [CALLBACK, FOLLOWUP]
    assert client.sent[1].json == {"content": "oops", "flags": 64}


async def test_respond_with_files_sends_multipart() -> None:
    client = RecordingClient()
    await _command(client).respond("graph", files=[File("graph.png", b"png", content_type="image/png", description="A graph")])
    sent = client.requests_to("POST", CALLBACK)[0]
    assert sent.json is None
    assert json.loads(sent.data["payload_json"]) == {
        "type": 4,
        "data": {"content": "graph", "attachments": [{"id": 0, "filename": "graph.png", "description": "A graph"}]},
    }
    assert sent.files == [("files[0]", ("graph.png", b"png", "image/png"))]


async def test_followup_with_files_sends_multipart() -> None:
    client = RecordingClient()
    client.reply("POST", FOLLOWUP, message_json())
    interaction = _command(client)
    await interaction.defer(ephemeral=True)
    await interaction.respond(files=[File("a.txt", b"a"), File("b.txt", b"b")], ephemeral=True)
    sent = client.requests_to("POST", FOLLOWUP)[0]
    assert json.loads(sent.data["payload_json"]) == {
        "flags": 64,
        "attachments": [{"id": 0, "filename": "a.txt"}, {"id": 1, "filename": "b.txt"}],
    }
    assert [name for name, _ in sent.files] == ["files[0]", "files[1]"]


async def test_failed_callback_does_not_count_as_answered() -> None:
    client = RecordingClient()
    client.fail("POST", CALLBACK, ApiResponseError(code=10062, message="Unknown interaction"))
    interaction = _command(client)
    assert isinstance(await interaction.respond("hi"), ApiResponseError)
    assert not interaction.responded


async def test_defer_sends_type_5_once() -> None:
    client = RecordingClient()
    interaction = _command(client)
    await interaction.defer()
    await interaction.defer()
    assert [sent.json for sent in client.sent] == [{"type": 5}]


async def test_ephemeral_defer_sets_flag_64() -> None:
    client = RecordingClient()
    await _command(client).defer(ephemeral=True)
    assert client.sent[0].json == {"type": 5, "data": {"flags": 64}}


async def test_edit_original_patches_the_webhook_message() -> None:
    client = RecordingClient()
    client.reply("PATCH", ORIGINAL, message_json())
    message = await _command(client).edit_original(embeds=[Embed(title="p1")])
    assert client.sent[0].json == {"embeds": [{"title": "p1"}]}
    assert isinstance(message, Message)
    assert str(message.id) == "5"


async def test_edit_original_with_empty_components_clears_them() -> None:
    client = RecordingClient()
    client.reply("PATCH", ORIGINAL, message_json())
    await _command(client).edit_original(components=[])
    assert client.sent[0].json == {"components": []}


async def test_delete_original() -> None:
    client = RecordingClient()
    assert await _command(client).delete_original() is None
    assert (client.sent[0].method, client.sent[0].path) == ("DELETE", ORIGINAL)


async def test_update_sends_type_7() -> None:
    client = RecordingClient()
    interaction = _component(client)
    assert interaction.custom_id == "page:2"
    await interaction.update(embeds=[Embed(title="p2")], components=[ROW])
    assert client.sent[0].json == {"type": 7, "data": {"embeds": [{"title": "p2"}], "components": ROW_JSON}}


async def test_update_after_defer_edits_the_original() -> None:
    client = RecordingClient()
    client.reply("PATCH", ORIGINAL, message_json())
    interaction = _component(client)
    await interaction.defer_update()
    await interaction.update("done")
    assert client.sent[0].json == {"type": 6}
    assert (client.sent[1].method, client.sent[1].path, client.sent[1].json) == ("PATCH", ORIGINAL, {"content": "done"})


async def test_suggest_sends_autocomplete_choices() -> None:
    client = RecordingClient()
    await AutocompleteInteraction(client, AUTOCOMPLETE).suggest([ApplicationCommandOptionChoice(name="Fifty", value=50)])
    assert client.sent[0].json == {"type": 8, "data": {"choices": [{"name": "Fifty", "value": 50}]}}


MODAL_SUBMIT = ModalSubmitInteractionModel(
    id="1",
    application_id="2",
    type=InteractionType.MODAL_SUBMIT,
    token="tok",  # noqa: S106
    version=1,
    data=ModalSubmitData(
        custom_id="guess:5",
        components=[
            {"type": 18, "id": 1, "component": {"type": 4, "id": 2, "custom_id": "letter", "value": "e"}},
            {"type": 1, "components": [{"type": 4, "custom_id": "other", "value": "x"}]},
        ],
    ),
    message=message_json(id="11"),
)


async def test_show_modal_sends_type_9_with_the_modal() -> None:
    client = RecordingClient()
    modal = Modal(
        custom_id="guess:5",
        title="Guess",
        components=[Label(label="Letter or word", component=TextInput(custom_id="guess", min_length=1, max_length=20))],
    )
    assert await _component(client).show_modal(modal) is None
    assert client.sent[0].json == {
        "type": 9,
        "data": {
            "custom_id": "guess:5",
            "title": "Guess",
            "components": [
                {
                    "type": 18,
                    "label": "Letter or word",
                    "component": {"type": 4, "custom_id": "guess", "style": 1, "min_length": 1, "max_length": 20},
                },
            ],
        },
    }


def test_modal_submit_parses_and_binds_with_its_values() -> None:
    interaction = bind(RecordingClient(), InteractionModel.model_validate(MODAL_SUBMIT.model_dump(mode="json")))
    assert isinstance(interaction, ModalSubmitInteraction)
    assert interaction.custom_id == "guess:5"
    assert interaction.values == {"letter": "e", "other": "x"}
    assert interaction.message is not None


async def test_modal_submit_update_edits_the_source_message() -> None:
    client = RecordingClient()
    interaction = ModalSubmitInteraction(client, MODAL_SUBMIT)
    await interaction.update("done")
    assert client.sent[0].json == {"type": 7, "data": {"content": "done"}}
