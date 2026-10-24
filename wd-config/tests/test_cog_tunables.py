"""Pin the cogs' former hardcoded values: settings in cogs.ini, with today's values as defaults."""

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


TUNABLES = """
from winter_dragon.cogs.fuel import FuelSettings
from winter_dragon.cogs.heartbeat import HeartbeatSettings
from winter_dragon.cogs.invite import InviteSettings
from winter_dragon.cogs.percentage import PercentageSettings
from winter_dragon.cogs.reminder import ReminderSettings
from winter_dragon.cogs.stats import StatsSettings
from winter_dragon.cogs.tournament.cog import TournamentSettings
from winter_dragon.cogs.urban import UrbanSettings
result = {
    "heartbeat_interval": HeartbeatSettings.interval,
    "support_invite_max_age": InviteSettings.support_invite_max_age,
    "max_delay_days": ReminderSettings.max_delay_days,
    "max_content_length": ReminderSettings.max_content_length,
    "max_name_length": TournamentSettings.max_name_length,
    "max_team_size": TournamentSettings.max_team_size,
    "category_name": StatsSettings.category_name,
    "love_color": int(PercentageSettings.love_color),
    "graph_width": FuelSettings.graph_width_inches,
    "graph_height": FuelSettings.graph_height_inches,
    "graph_filename": FuelSettings.graph_filename,
    "request_timeout": UrbanSettings.request_timeout,
}
"""

DEFAULTS = {
    "heartbeat_interval": 60,
    "support_invite_max_age": 60,
    "max_delay_days": 3650,
    "max_content_length": 1000,
    "max_name_length": 100,
    "max_team_size": 25,
    "category_name": "Stats",
    "love_color": 0xFF0000,
    "graph_width": 10,
    "graph_height": 6,
    "graph_filename": "fuel_efficiency.png",
    "request_timeout": 10.0,
}


def test_cog_tunables_default_to_todays_values(boot_config: BootConfig) -> None:
    """With no cogs.ini, each former constant resolves to its old value and is written to its cog's section."""
    boot = boot_config(TUNABLES)

    assert boot.values == DEFAULTS
    cogs = boot.files["cogs.ini"]
    assert cogs["HeartbeatSettings"]["interval"] == "60"
    assert cogs["InviteSettings"]["support_invite_max_age"] == "60"
    assert cogs["TournamentSettings"]["max_team_size"] == "25"
    assert cogs["PercentageSettings"]["love_color"].lower() == "0xff0000"
    assert cogs["FuelSettings"]["graph_filename"] == "fuel_efficiency.png"


def test_prewritten_cog_tunables_win(boot_config: BootConfig) -> None:
    """Values already in cogs.ini win over the defaults."""
    boot = boot_config(
        TUNABLES,
        files={
            "cogs.ini": (
                "[HeartbeatSettings]\ninterval = 5\n"
                "[InviteSettings]\nsupport_invite_max_age = 120\n"
                "[ReminderSettings]\nmax_delay_days = 30\nmax_content_length = 200\n"
                "[TournamentSettings]\nmax_name_length = 50\nmax_team_size = 4\n"
                "[StatsSettings]\ncategory_name = Numbers\n"
                "[PercentageSettings]\nlove_color = 0x00ff00\n"
                "[FuelSettings]\ngraph_width_inches = 8\ngraph_height_inches = 4\ngraph_filename = fuel.png\n"
                "[UrbanSettings]\nrequest_timeout = 2.5\n"
            ),
        },
    )

    assert boot.values == {
        "heartbeat_interval": 5,
        "support_invite_max_age": 120,
        "max_delay_days": 30,
        "max_content_length": 200,
        "max_name_length": 50,
        "max_team_size": 4,
        "category_name": "Numbers",
        "love_color": 0x00FF00,
        "graph_width": 8,
        "graph_height": 4,
        "graph_filename": "fuel.png",
        "request_timeout": 2.5,
    }
