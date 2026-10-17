"""Pin how wd-config boots today: which ini files appear, what they hold, and what settings resolve to."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


DISCORD_SETTINGS = """
from wd_config.discord import URLS, RateLimit, RestCache, UserAgent
result = {
    "base": URLS.base,
    "version": URLS.version,
    "gateway": URLS.gateway,
    "cdn": URLS.cdn,
    "web": URLS.web,
    "invite": URLS.invite,
    "ttl": RestCache.ttl,
    "max_retries": RateLimit.max_retries,
    "user_agent_url": UserAgent.url,
    "user_agent_version": UserAgent.version,
}
"""

DISCORD_DEFAULTS = {
    "base": "https://discord.com/api",
    "version": 10,
    "gateway": "wss://gateway.discord.gg",
    "cdn": "https://cdn.discordapp.com",
    "web": "https://discord.com",
    "invite": "https://discord.gg",
    "ttl": 30.0,
    "max_retries": 5,
    "user_agent_url": "https://github.com/HEROgold/WinterDragon",
    "user_agent_version": "0.1.0",
}


def test_empty_dir_writes_config_ini_but_not_discord_ini(boot_config: BootConfig) -> None:
    """Booting the app writes its config.ini; discord.ini is internal-only, so it isn't created."""
    boot = boot_config(DISCORD_SETTINGS + "import winter_dragon.config\n")

    assert "Settings" in boot.files["config.ini"]
    assert "discord.ini" not in boot.files


def test_absent_discord_ini_resolves_in_code_defaults(boot_config: BootConfig) -> None:
    """Without discord.ini every discord setting resolves to its in-code default."""
    boot = boot_config(DISCORD_SETTINGS)

    assert boot.values == DISCORD_DEFAULTS
    assert "discord.ini" not in boot.files


def test_empty_discord_ini_is_filled_with_defaults(boot_config: BootConfig) -> None:
    """An existing, empty discord.ini exposes the scope: every default is written into it."""
    boot = boot_config(DISCORD_SETTINGS, files={"discord.ini": ""})

    assert boot.values == DISCORD_DEFAULTS
    assert boot.files["discord.ini"] == {
        "URLS": {
            "base": "https://discord.com/api",
            "version": "10",
            "gateway": "wss://gateway.discord.gg",
            "cdn": "https://cdn.discordapp.com",
            "web": "https://discord.com",
            "invite": "https://discord.gg",
        },
        "RestCache": {"ttl": "30.0"},
        "RateLimit": {"max_retries": "5"},
        "UserAgent": {"url": "https://github.com/HEROgold/WinterDragon", "version": "0.1.0"},
    }


def test_discord_settings_stay_out_of_config_ini(boot_config: BootConfig) -> None:
    """Discord-scoped settings are never written to config.ini."""
    boot = boot_config(DISCORD_SETTINGS + "import winter_dragon.config\n", files={"discord.ini": ""})

    for section in ("URLS", "RestCache", "RateLimit", "UserAgent"):
        assert section not in boot.files["config.ini"]


def test_prewritten_value_is_the_resolved_setting(boot_config: BootConfig) -> None:
    """A value already in discord.ini wins over the default and is left on disk unchanged."""
    boot = boot_config(DISCORD_SETTINGS, files={"discord.ini": "[RestCache]\nttl = 5.5\n[RateLimit]\nmax_retries = 2\n"})

    assert boot.values["ttl"] == 5.5
    assert boot.values["max_retries"] == 2
    assert boot.files["discord.ini"]["RestCache"] == {"ttl": "5.5"}
    assert boot.files["discord.ini"]["RateLimit"] == {"max_retries": "2"}


FIRST_LAUNCH = """
from pathlib import Path
from wd_config.errors import FirstTimeLaunchError
from wd_config.parser import OperatorFiles
for name in ("a.ini", "b.ini"):
    OperatorFiles.register(Path(name))
try:
    OperatorFiles.check()
except FirstTimeLaunchError as e:
    result = {"raised": True, "message": str(e)}
else:
    result = {"raised": False}
result["unset"] = list(OperatorFiles.unset())
"""


def test_first_launch_lists_every_unset_value_and_raises(boot_config: BootConfig) -> None:
    """Each `!!` value in a registered file is reported as `file:section:key`, and the check raises."""
    boot = boot_config(
        FIRST_LAUNCH,
        files={
            "a.ini": "[Tokens]\ndiscord_token = !!\nother = set\n",
            "b.ini": "[Db]\npassword = !!\n",
        },
    )

    assert boot.values["raised"] is True
    assert boot.values["unset"] == ["a.ini:Tokens:discord_token", "b.ini:Db:password"]
    assert "a.ini:Tokens:discord_token" in boot.values["message"]
    assert "b.ini:Db:password" in boot.values["message"]


def test_filled_in_operator_files_pass(boot_config: BootConfig) -> None:
    """Registered files without `!!` values, or not written yet, pass the check."""
    boot = boot_config(FIRST_LAUNCH, files={"a.ini": "[Tokens]\ndiscord_token = abc\n"})

    assert boot.values == {"raised": False, "unset": []}


def test_unregistered_files_are_not_checked(boot_config: BootConfig) -> None:
    """A `!!` in a file no scope registered (such as discord.ini) is not an operator value."""
    boot = boot_config(FIRST_LAUNCH, files={"discord.ini": "[URLS]\nbase = !!\n"})

    assert boot.values == {"raised": False, "unset": []}


DISCORD_URLS = """
from wd_config.discord import URLS
from wd_discord.client import Client
from wd_discord.entities.message import PartialMessage
from wd_discord.gateway import Gateway, parse_gateway_bot
from wd_discord.image import ImageHash
from wd_discord.resources.invite import Invite
from wd_discord.snowflake import Snowflake

client = Client("token")
info = parse_gateway_bot(
    {
        "url": "wss://gw.example",
        "shards": 1,
        "session_start_limit": {"total": 1, "remaining": 1, "reset_after": 0, "max_concurrency": 1},
    },
)
result = {
    "api": client.base_url,
    "gateway": Gateway("token").url,
    "shard_gateway": info.connect_url,
    "jump": PartialMessage(client, Snowflake(2), Snowflake(1)).jump_url,
    "image": ImageHash("abc").url("avatars/7"),
    "invite": Invite(code="xyz").url,
    "authorize": URLS().oauth2_authorize,
}
"""


def test_discord_urls_follow_defaults(boot_config: BootConfig) -> None:
    """Without discord.ini every Discord URL uses today's hosts and API v10."""
    boot = boot_config(DISCORD_URLS)

    assert boot.values == {
        "api": "https://discord.com/api/v10",
        "gateway": "wss://gateway.discord.gg/?v=10&encoding=json",
        "shard_gateway": "wss://gw.example?v=10&encoding=json",
        "jump": "https://discord.com/channels/@me/1/2",
        "image": "https://cdn.discordapp.com/avatars/7/abc.png",
        "invite": "https://discord.gg/xyz",
        "authorize": "https://discord.com/oauth2/authorize",
    }


def test_configured_version_moves_gateway_and_api_together(boot_config: BootConfig) -> None:
    """Changing the API version in discord.ini changes the REST base and every gateway query at once."""
    boot = boot_config(DISCORD_URLS, files={"discord.ini": "[URLS]\nversion = 9\n"})

    assert boot.values["api"] == "https://discord.com/api/v9"
    assert boot.values["gateway"] == "wss://gateway.discord.gg/?v=9&encoding=json"
    assert boot.values["shard_gateway"] == "wss://gw.example?v=9&encoding=json"


def test_configured_hosts_flow_into_urls(boot_config: BootConfig) -> None:
    """Custom hosts in discord.ini are used for the gateway, CDN images, jump links, invites and OAuth2."""
    hosts = (
        "[URLS]\nbase = https://api.example/api\ngateway = wss://gateway.example\n"
        "cdn = https://cdn.example\nweb = https://web.example\ninvite = https://inv.example\n"
    )
    boot = boot_config(DISCORD_URLS, files={"discord.ini": hosts})

    assert boot.values == {
        "api": "https://api.example/api/v10",
        "gateway": "wss://gateway.example/?v=10&encoding=json",
        "shard_gateway": "wss://gw.example?v=10&encoding=json",
        "jump": "https://web.example/channels/@me/1/2",
        "image": "https://cdn.example/avatars/7/abc.png",
        "invite": "https://inv.example/xyz",
        "authorize": "https://web.example/oauth2/authorize",
    }
