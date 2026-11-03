"""Components v2 cards: one colored container per message, and the marks that steps and winners share.

A card's color says whether it needs someone now (:attr:`Tone.ACT`), waits or is done (:attr:`Tone.WAIT`), or was
called off (:attr:`Tone.STOP`). Colors and marks are read from ``config.ini`` each time, so a change shows on the
next edit without a restart.
"""

lazy from enum import Enum, auto
lazy from typing import TYPE_CHECKING

lazy from wd_discord.color import Color
lazy from wd_discord.components import Container, TextDisplay

lazy from winter_dragon.config import Settings


if TYPE_CHECKING:
    lazy from wd_discord.components import ActionRow, FileDisplay, MediaGallery, Section, Separator


class Tone(Enum):
    """What a card asks of whoever reads it, shown as the color of its bar."""

    ACT = auto()
    """Someone needs to act now."""
    WAIT = auto()
    """Nothing to do yet, or nothing left to do."""
    STOP = auto()
    """Called off or forfeited."""

    @property
    def color(self) -> Color:
        """The bar color set for this tone in ``config.ini``."""
        match self:
            case Tone.ACT:
                return Color(Settings.act_color)
            case Tone.WAIT:
                return Color(Settings.wait_color)
            case Tone.STOP:
                return Color(Settings.stop_color)


class Mark(Enum):
    """A mark put before text: where a sequence of steps stands, or who won."""

    DONE = auto()
    HERE = auto()
    NEXT = auto()
    WINNER = auto()

    def __str__(self) -> str:
        """Return the mark set in ``config.ini``: text, or a custom emoji as ``<:name:id>``."""
        match self:
            case Mark.DONE:
                return Settings.step_done_mark
            case Mark.HERE:
                return Settings.step_here_mark
            case Mark.NEXT:
                return Settings.step_next_mark
            case Mark.WINNER:
                return Settings.winner_mark


def steps(names: list[str], current: int) -> str:
    """Return ``names`` as one line of steps, marking those before ``current`` done and ``current`` itself in bold."""
    marked = []
    for index, name in enumerate(names):
        if index < current:
            marked.append(f"{Mark.DONE} {name}")
        elif index == current:
            marked.append(f"{Mark.HERE} **{name}**")
        else:
            marked.append(f"{Mark.NEXT} {name}")
    return "   ".join(marked)


def card(tone: Tone, *components: ActionRow | TextDisplay | Section | MediaGallery | Separator | FileDisplay) -> Container:
    """Return ``components`` in one container, its bar colored for ``tone``."""
    return Container(components=list(components), accent_color=tone.color)


def block(*lines: str) -> TextDisplay:
    """Return ``lines`` as one text display, one per line; empty lines are left out."""
    return TextDisplay(content="\n".join(line for line in lines if line))
