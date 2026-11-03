"""Draw a tournament's bracket as a PNG: each round a column of match boxes, joined to the next, climbing to the champion.

The image uses the dashboard's look: Archivo on snow, ice lines, the winner of each match marked with the route
marker, and the matches being played outlined in route blue.
"""

lazy import io
lazy from dataclasses import dataclass
lazy from functools import cache
lazy from pathlib import Path
lazy from typing import TYPE_CHECKING

lazy from PIL import Image, ImageDraw, ImageFont
lazy from wd_discord.color import Color

lazy from winter_dragon.config import Settings

lazy from .bracket import BracketSlot, round_name
lazy from .models import MatchPhase


if TYPE_CHECKING:
    lazy from collections.abc import Mapping, Sequence

    lazy from .models import TournamentMatch


FONT = Path(__file__).parents[2] / "ui" / "fonts" / "Archivo[wdth,wght].ttf"
"""Archivo, a variable font with a weight and a width axis, cut down to Latin with ``pyftsubset`` to stay small.

It is under the SIL Open Font License (``OFL.txt`` beside it). Names in other scripts draw as empty boxes.
"""

SCALE = 2
"""Pixels per layout unit; drawing at twice the size keeps the text sharp once Discord scales the image down."""

SNOW = (0xF4, 0xF7, 0xF9)
WHITE = (0xFF, 0xFF, 0xFF)
ICE = (0xDC, 0xE8, 0xEF)
SLATE = (0x5E, 0x6B, 0x74)
GRANITE = (0x26, 0x32, 0x3B)

BOX_WIDTH = 170
BOX_HEIGHT = 52
ROW_GAP = 16
LINK = 26
"""The horizontal room between a round's boxes and the next round's, where the connecting lines run."""
MARGIN = 16
HEADER = 36
SUMMIT_WIDTH = 120
PLAYING = {MatchPhase.BAN, MatchPhase.PICK, MatchPhase.LIVE}


@cache
def _font(size: int, weight: int, width: int = 100) -> ImageFont.FreeTypeFont:
    """Return Archivo at ``size`` layout units, ``weight`` (100-900) and ``width`` (62-125)."""
    font = ImageFont.truetype(str(FONT), size * SCALE)
    font.set_variation_by_axes([weight, width])
    return font


def _rgb(color: int) -> tuple[int, int, int]:
    return (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF


@dataclass(frozen=True)
class _Box:
    """Where one match is drawn, in layout units."""

    left: int
    top: int

    @property
    def right(self) -> int:
        return self.left + BOX_WIDTH

    @property
    def middle(self) -> int:
        return self.top + BOX_HEIGHT // 2


def _boxes(rounds: int) -> dict[BracketSlot, _Box]:
    """Lay out every match: the first round evenly down the image, each later match level with the two feeding it."""
    boxes: dict[BracketSlot, _Box] = {}
    for slot in range(2 ** (rounds - 1)):
        boxes[BracketSlot(0, slot)] = _Box(MARGIN, HEADER + slot * (BOX_HEIGHT + ROW_GAP))
    for round_ in range(1, rounds):
        left = MARGIN + round_ * (BOX_WIDTH + LINK)
        for slot in range(2 ** (rounds - round_ - 1)):
            upper, lower = boxes[BracketSlot(round_ - 1, 2 * slot)], boxes[BracketSlot(round_ - 1, 2 * slot + 1)]
            boxes[BracketSlot(round_, slot)] = _Box(left, (upper.middle + lower.middle) // 2 - BOX_HEIGHT // 2)
    return boxes


class _Canvas:
    """An image drawn on in layout units."""

    def __init__(self, width: int, height: int) -> None:
        self.image = Image.new("RGB", (width * SCALE, height * SCALE), SNOW)
        self.draw = ImageDraw.Draw(self.image)

    def line(self, points: list[tuple[int, int]], color: tuple[int, int, int], width: int = 2) -> None:
        self.draw.line([(x * SCALE, y * SCALE) for x, y in points], fill=color, width=width * SCALE, joint="curve")

    def box(self, box: _Box, outline: tuple[int, int, int], width: int) -> None:
        corners = (box.left * SCALE, box.top * SCALE, box.right * SCALE, (box.top + BOX_HEIGHT) * SCALE)
        self.draw.rounded_rectangle(corners, radius=4 * SCALE, fill=WHITE, outline=outline, width=width * SCALE)

    def text(  # noqa: PLR0913 - where, what, and how it looks
        self,
        x: int,
        y: int,
        content: str,
        font: ImageFont.FreeTypeFont,
        color: tuple[int, int, int],
        *,
        anchor: str = "ls",
        max_width: int | None = None,
    ) -> None:
        """Write ``content`` with its baseline at ``y``; cut it with an ellipsis to fit ``max_width`` units."""
        if max_width is not None:
            while len(content) > 1 and self.draw.textlength(content, font=font) > max_width * SCALE:
                content = content[:-2] + "…"
        self.draw.text((x * SCALE, y * SCALE), content, font=font, fill=color, anchor=anchor)

    def marker(self, x: int, y: int, accent: tuple[int, int, int]) -> None:
        """Draw the route marker, white, blue, white, with its left edge at ``x`` and centred on ``y``."""
        outer = (x * SCALE, (y - 5) * SCALE, (x + 16) * SCALE, (y + 5) * SCALE)
        self.draw.rounded_rectangle(outer, radius=2 * SCALE, fill=SNOW, outline=SLATE, width=1)
        self.draw.rectangle((x * SCALE, (y - 1.5) * SCALE, (x + 16) * SCALE, (y + 1.5) * SCALE), fill=accent)

    def png(self) -> bytes:
        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()


def _side_name(match: TournamentMatch, names: Mapping[int, str], ids: Mapping[BracketSlot, int], *, side_b: bool) -> str:
    entry_id = match.entry_b_id if side_b else match.entry_a_id
    if entry_id is not None:
        return names.get(entry_id, f"Team {entry_id}")
    if match.round == 0:
        return "bye"
    feeder = ids.get(BracketSlot(match.round - 1, 2 * match.slot + int(side_b)))
    return "To be decided" if feeder is None else f"Winner of {feeder}"


def _tag(match: TournamentMatch) -> str:
    if match.phase in PLAYING:
        return f"Match {match.id}, {'live' if match.phase is MatchPhase.LIVE else match.phase.value + 's'}"
    if match.phase is MatchPhase.FORFEIT:
        return f"Match {match.id}, forfeit"
    return f"Match {match.id}"


def bracket_png(matches: Sequence[TournamentMatch], names: Mapping[int, str], champion: int | None) -> bytes:
    """Return the bracket of ``matches`` as a PNG, with the champion's name at its summit once there is one."""
    rounds = max((match.round for match in matches), default=0) + 1
    boxes = _boxes(rounds)
    ids = {BracketSlot(match.round, match.slot): match.id for match in matches if match.id is not None}
    accent = _rgb(Color(Settings.act_color))
    final = boxes[BracketSlot(rounds - 1, 0)]
    width = final.right + LINK + SUMMIT_WIDTH + MARGIN
    height = max(box.top for box in boxes.values()) + BOX_HEIGHT + MARGIN
    canvas = _Canvas(width, height)

    heading = _font(11, 600)
    for round_ in range(rounds):
        canvas.text(MARGIN + round_ * (BOX_WIDTH + LINK), 22, round_name(round_, rounds), heading, SLATE)

    for round_ in range(1, rounds):
        for slot in range(2 ** (rounds - round_ - 1)):
            upper, lower = boxes[BracketSlot(round_ - 1, 2 * slot)], boxes[BracketSlot(round_ - 1, 2 * slot + 1)]
            target = boxes[BracketSlot(round_, slot)]
            elbow = upper.right + LINK // 2
            canvas.line(
                [(upper.right, upper.middle), (elbow, upper.middle), (elbow, lower.middle), (lower.right, lower.middle)],
                ICE,
            )
            canvas.line([(elbow, target.middle), (target.left, target.middle)], ICE)

    team, decided, waiting, tag = _font(13, 650, 85), _font(13, 400, 85), _font(13, 400, 85), _font(10, 600)
    for match in matches:
        box = boxes[BracketSlot(match.round, match.slot)]
        playing = match.phase in PLAYING
        canvas.box(box, accent if playing else ICE, 3 if playing else 2)
        canvas.text(box.right, box.top - 4, _tag(match), tag, accent if playing else SLATE, anchor="rs")
        for row, side_b in enumerate((False, True)):
            entry_id = match.entry_b_id if side_b else match.entry_a_id
            baseline = box.top + 21 + row * 21
            label = _side_name(match, names, ids, side_b=side_b)
            won = match.phase.decided and entry_id is not None and entry_id == match.winner_id
            lost = match.phase.decided and not won
            font = decided if lost else (waiting if entry_id is None else team)
            color = SLATE if lost or entry_id is None else GRANITE
            canvas.text(box.left + 10, baseline, label, font, color, max_width=BOX_WIDTH - 44)
            if won:
                canvas.marker(box.right - 26, baseline - 4, accent)

    summit_x = final.right + LINK
    canvas.line([(final.right, final.middle), (summit_x, final.middle)], ICE)
    peak = summit_x + SUMMIT_WIDTH // 2
    base = final.middle + 34
    canvas.draw.polygon(
        [((peak - 30) * SCALE, base * SCALE), (peak * SCALE, (base - 48) * SCALE), ((peak + 30) * SCALE, base * SCALE)],
        fill=ICE,
    )
    canvas.draw.polygon(
        [
            ((peak - 9) * SCALE, (base - 34) * SCALE),
            (peak * SCALE, (base - 48) * SCALE),
            ((peak + 9) * SCALE, (base - 34) * SCALE),
        ],
        fill=WHITE,
        outline=SLATE,
        width=SCALE,
    )
    if champion is None:
        canvas.text(peak, base - 56, "Champion", heading, SLATE, anchor="ms")
    else:
        canvas.line([(peak, base - 48), (peak, base - 74)], SLATE, 1)
        canvas.marker(peak, base - 69, accent)
        canvas.text(peak, base + 18, names.get(champion, "?"), _font(15, 750, 75), GRANITE, anchor="ms", max_width=SUMMIT_WIDTH)
    return canvas.png()
