"""Utility helpers for parsing Steam store URLs."""

import re

from herogold.log import LoggerMixin


# TODO(Herogold, #7): Handle multi-id strings returned by Steam (e.g. "357070,366420,546090").  # noqa: FIX002
class SteamURL(LoggerMixin):
    """Class to handle Steam URLs."""

    def __init__(self, url: str) -> None:
        """Initialize the SteamURL class.

        Args:
        ----
            url (str): Url to extract the id from

        """
        self.url = url
        self._id = None

    @property
    def app_id(self) -> int:
        """Get an id from a steam game url.

        Args:
        ----
            url (str): Url to extract the id from

        Returns:
        -------
            int: The found id of a game

        """
        if self._id:
            return self._id
        # example: https://store.steampowered.com/app/1168660/Barro_2020/
        regex_game_id = r"(?:https?:\/\/)?store\.steampowered\.com\/app\/(\d+)\/[a-zA-Z0-9_\/]+"
        matches = re.findall(regex_game_id, self.url)
        self.logger.debug(f"game id: {matches=}, {matches=}")
        self._id = int(matches[0]) if matches else 0
        return self._id

    def is_valid_game_url(self) -> bool:
        """Find out if a url is for a valid game.

        Args:
        ----
            url (str): Url to check for

        """
        return bool(self.app_id)

    def __repr__(self) -> str:
        """Return the url as a string."""
        return self.url

    def __str__(self) -> str:
        """Return the url as a string."""
        return self.url
