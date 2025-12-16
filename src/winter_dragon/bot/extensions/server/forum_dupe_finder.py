"""Module for helping find duplicate forum posts."""

from difflib import SequenceMatcher

from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog


class ForumDupeFinder(GroupCog, auto_load=True):
    """A class to find duplicate forum posts based on their content."""

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the ForumDupeFinder with the bot instance."""
        super().__init__(bot=bot)
        self.forum_posts: list[str] = []  # TODO: replace with actual forum posts titles, preferably from database.

    def get_ratio(self, a: str, b: str) -> float:
        """Calculate the similarity ratio between two strings."""
        return SequenceMatcher(None, a, b).ratio()

    def find_duplicates(self, post_title: str, *, ratio: float = 0.8) -> list[str]:
        """Find duplicate forum posts based on their content."""
        duplicates: list[str] = []
        duplicates.extend(post for post in self.forum_posts if self.get_ratio(post_title, post) > ratio)
        return duplicates
