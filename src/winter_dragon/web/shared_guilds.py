"""The guilds each signed-in session shares with the bot, kept in memory for a while (ADR 0006).

Cards check these before they open. Nothing here reaches the cookie or the database: a restart forgets them, and the
next card a member opens sends them through a silent sign-in that reads their guilds again.
"""

from datetime import timedelta
lazy from typing import TYPE_CHECKING

lazy from wd_types.clock import utc_now


if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from wd_discord.snowflake import Snowflake


SHARED_GUILDS_LIFETIME = timedelta(minutes=15)
"""How long the guilds read at sign-in count as current."""
RETURN_PREFIXES = ("/cards/", "/profile", "/me")
"""Where signing in may send a member back to: the card pages and the member's own pages."""


def safe_return_path(path: str | None) -> str | None:
    """Return ``path`` when it is a page of this site that signing in may return to, else ``None``.

    Refuses anything that could leave the site: a scheme, a host (``//host``), a backslash or a control character.
    """
    if path is None or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return None
    if any(ord(character) < ord(" ") for character in path):
        return None
    return path if path.startswith(RETURN_PREFIXES) else None


class SharedGuilds:
    """Which guilds the bot and each session's member are both in, and when each session's were read."""

    def __init__(self, *, lifetime: timedelta = SHARED_GUILDS_LIFETIME, now: Callable[[], datetime] | None = None) -> None:
        """Count a session's guilds as current for ``lifetime``, as read from the clock ``now``."""
        self._lifetime = lifetime
        self._now = utc_now if now is None else now
        self._by_session: dict[str, tuple[datetime, frozenset[Snowflake]]] = {}

    def remember(self, session_id: str, guild_ids: frozenset[Snowflake]) -> None:
        """Keep ``guild_ids`` as the guilds the session's member shares with the bot, read just now."""
        self._by_session[session_id] = (self._now(), guild_ids)

    def current(self, session_id: str | None) -> frozenset[Snowflake] | None:
        """Return the session's shared guilds; ``None`` when there are none yet or they have gone stale."""
        if session_id is None or (kept := self._by_session.get(session_id)) is None:
            return None
        read_at, guild_ids = kept
        if self._now() - read_at >= self._lifetime:
            del self._by_session[session_id]
            return None
        return guild_ids

    def forget(self, session_id: str | None) -> None:
        """Drop the session's guilds, when it ends."""
        if session_id is not None:
            self._by_session.pop(session_id, None)
