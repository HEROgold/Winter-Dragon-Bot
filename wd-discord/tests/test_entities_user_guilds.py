"""Unit tests: GET /users/@me/guilds through the user store (no network)."""

from wd_discord import is_network_error
from wd_discord.entities.user import MAX_GUILDS_PER_PAGE, UserGuild
from wd_discord.testing import RecordingClient


GUILDS = "/users/@me/guilds"


def guild_json(guild_id: int, *, owner: bool = False) -> dict[str, object]:
    return {"id": str(guild_id), "name": f"guild {guild_id}", "owner": owner, "permissions": "8", "features": []}


async def test_guilds_returns_bound_entities() -> None:
    client = RecordingClient()
    client.reply("GET", GUILDS, [guild_json(10, owner=True), guild_json(11)])

    guilds = await client.users.guilds()

    assert not is_network_error(guilds)
    found = list(guilds)
    assert all(isinstance(guild, UserGuild) for guild in found)
    assert [(int(guild.id), guild.name, guild.is_owner) for guild in found] == [(10, "guild 10", True), (11, "guild 11", False)]
    assert client.requests_to("GET", GUILDS)[0].params == {"limit": str(MAX_GUILDS_PER_PAGE)}


async def test_guilds_reads_every_page() -> None:
    client = RecordingClient()
    first = [guild_json(number) for number in range(1, MAX_GUILDS_PER_PAGE + 1)]
    second = [guild_json(MAX_GUILDS_PER_PAGE + 1)]
    client.reply_each("GET", GUILDS, first, second)  # type: ignore[arg-type] - a JSON array, not an object

    guilds = await client.users.guilds()

    assert not is_network_error(guilds)
    assert len(list(guilds)) == MAX_GUILDS_PER_PAGE + 1
    sent = client.requests_to("GET", GUILDS)
    assert sent[1].params == {"limit": str(MAX_GUILDS_PER_PAGE), "after": str(MAX_GUILDS_PER_PAGE)}


async def test_guilds_returns_the_failure_of_a_page() -> None:
    client = RecordingClient()
    client.reply("GET", GUILDS, {"message": "401: Unauthorized", "code": 0}, status=401)

    assert is_network_error(await client.users.guilds())
