"""UI primitives built on top of discord.py modals."""

from discord.ui import Modal as DiscordModal
from discord.utils import MISSING
from herogold.log import LoggerMixin


class Modal(DiscordModal, LoggerMixin):
    """Custom modal class for the bot."""

    def __init__(self, *, title: str = MISSING, timeout: float | None = None, custom_id: str = MISSING) -> None:
        """Initialize the modal with a title, timeout, and custom ID."""
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
