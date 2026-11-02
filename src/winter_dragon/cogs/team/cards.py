"""The messages the team features post: the split teams, with the buttons under them."""

lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import ActionRow, Button, ButtonStyle
lazy from wd_discord.embed import Embed, EmbedField

lazy from winter_dragon.ui import mentions


if TYPE_CHECKING:
    lazy from collections.abc import Callable, Sequence

    lazy from wd_bot.components import ComponentHandler

    lazy from .models import Team


BUTTONS_PER_ROW = 5
"""How many buttons Discord allows in one action row."""


def split_post(
    teams: Sequence[tuple[Team, Sequence[int]]],
    keep: ComponentHandler,
    move: Callable[[Team], str] | None = None,
) -> tuple[Embed, list[ActionRow]]:
    """Return the post showing freshly split teams: a field per team, with Keep buttons under it.

    Move buttons come first for each team when ``move`` gives their custom ids.
    """
    fields = [EmbedField(name=team.name, value=mentions(group)) for team, group in teams]
    buttons: list[Button] = []
    for team, _group in teams:
        if move is not None:
            buttons.append(
                Button(style=ButtonStyle.PRIMARY, label=f"Move to {team.name}", custom_id=move(team)),
            )
        buttons.append(
            Button(style=ButtonStyle.SECONDARY, label=f"Keep {team.name}", custom_id=keep.custom_id(team.id or 0)),
        )
    rows = [ActionRow(components=buttons[start : start + BUTTONS_PER_ROW]) for start in range(0, len(buttons), BUTTONS_PER_ROW)]
    return Embed(title="Teams", fields=fields), rows
