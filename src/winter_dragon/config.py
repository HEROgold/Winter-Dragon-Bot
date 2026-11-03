"""The app's own config scopes: app-wide settings in ``config.ini``, cog settings in ``cogs.ini``."""

lazy import logging

lazy from confkit.data_types import Hex, List
lazy from wd_config import Config as BaseConfig
lazy from wd_config.constants import APP_CONFIG_FILE, COGS_CONFIG_FILE


class Config[T](BaseConfig[T]):
    """Config descriptor scoped to the app-wide settings file."""


Config.bind(APP_CONFIG_FILE, operator=True)


class CogConfig[T](BaseConfig[T]):
    """Config descriptor scoped to the cog settings file; every cog shares it, one section per settings class."""


CogConfig.bind(COGS_CONFIG_FILE, operator=True)


class Settings:
    """Application-wide settings."""

    bot_name = Config("WinterDragon")
    """The bot's name."""
    support_guild_id = Config(0)
    """The official support guild that /invite guild invites to; ``0`` when there is none."""
    # TODO(Herogold, confkit#96): have DashboardSettings.public_url read this value, not keep a copy.  # noqa: FIX002
    dashboard_url = Config("")
    """The address people open the dashboard on, as ``public_url`` in ``dashboard.ini``; empty hides links to it."""
    log_level = Config(logging.DEBUG)
    """The lowest level logged, as a :mod:`logging` level number."""
    created_color = Config(Hex(0x00FF00))
    """The embed color for something created."""
    changed_color = Config(Hex(0xFFFF00))
    """The embed color for something changed."""
    deleted_color = Config(Hex(0xFF0000))
    """The embed color for something deleted."""
    act_color = Config(Hex(0x1E5AA0))
    """A card's bar while it needs someone to act now: sign-up open, a match being played, a vote open."""
    wait_color = Config(Hex(0x5E6B74))
    """A card's bar while it waits, or once it's done."""
    stop_color = Config(Hex(0xB83A2B))
    """A card's bar once it's called off or forfeited."""
    step_done_mark = Config("●")
    """Marks a step already taken; a custom emoji as ``<:name:id>``, or any text."""
    step_here_mark = Config("◉")
    """Marks the step being taken now; a custom emoji as ``<:name:id>``, or any text."""
    step_next_mark = Config("○")
    """Marks a step still to come; a custom emoji as ``<:name:id>``, or any text."""
    winner_mark = Config("⚑")
    """Marks a winner or a full team; a custom emoji as ``<:name:id>``, or any text."""
    bot_status_messages = Config(
        List(
            [
                "Licking a wedding cake",
                "Eating a wedding cake",
                "Comparing wedding cakes",
                "Taste testing a wedding cake",
                "Crashing a wedding to eat their cake",
                "Getting married to eat a cake",
                "Throwing a wedding cake",
                "Devouring a wedding cake",
                "Sniffing wedding cakes",
                "Touching a wedding cake",
                "Magically spawning a wedding cake",
                "Wanting to eat a wedding cake and have one too",
            ],
        ),
    )
    """The status messages the bot picks from."""
