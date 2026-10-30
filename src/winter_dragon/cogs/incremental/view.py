"""The Discord side of the Incremental game: the save embed and its buttons."""

lazy from typing import TYPE_CHECKING

lazy from confkit.data_types import Hex
lazy from wd_discord.components import ActionRow, Button, ButtonStyle
lazy from wd_discord.embed import Embed, EmbedField, EmbedFooter
lazy from wd_discord.limits import MAX_ACTION_ROW_BUTTONS

lazy from winter_dragon.cogs.incremental.catalogue import catalogue
lazy from winter_dragon.config import CogConfig


if TYPE_CHECKING:
    lazy from collections.abc import Iterable

    lazy from wd_bot.components import ComponentHandler

    lazy from winter_dragon.cogs.incremental.catalogue import Quantity
    lazy from winter_dragon.cogs.incremental.game import Offer, SaveView


class IncrementalSettings:
    """Settings for /incremental, in its ``cogs.ini`` section."""

    embed_color = CogConfig(Hex(0xC9A227))
    """The color of the save embed."""


def format_amount(amount: float) -> str:
    """Format ``amount`` with thousands separators and one decimal."""
    return f"{amount:,.1f}"


def format_quantities(quantities: Iterable[Quantity]) -> str:
    """Describe ``quantities`` as amounts with their currency labels, separated by commas."""
    game = catalogue()
    parts: list[str] = []
    for quantity in quantities:
        currency = game.currency(quantity.currency)
        parts.append(f"{format_amount(quantity.amount)} {currency.label if currency is not None else quantity.currency}")
    return ", ".join(parts)


def _offer_field(offer: Offer) -> EmbedField:
    status = "" if offer.affordable else " (can't afford)"
    produces = format_quantities(offer.generator.produces)
    price = format_quantities(offer.price)
    return EmbedField(
        name=f"{offer.generator.name} x{offer.owned}",
        value=f"{offer.generator.description}\nMakes {produces} per second each.\nNext costs {price}{status}",
    )


def build_embed(view: SaveView) -> Embed:
    """Build the embed showing ``view``: amounts and rates per currency, then each generator with its next price."""
    holdings = "\n".join(
        f"{holding.currency.label}: {format_amount(holding.amount)} (+{format_amount(holding.per_second)}/s)"
        for holding in view.holdings
    )
    return Embed(
        title="Incremental",
        description=holdings,
        color=IncrementalSettings.embed_color,
        fields=[_offer_field(offer) for offer in view.offers],
        footer=EmbedFooter(text="Production continues while you are away."),
    )


def build_buttons(view: SaveView, *, refresh: ComponentHandler, buy: ComponentHandler) -> list[ActionRow]:
    """Build the Refresh button and one Buy button per generator, disabled when the save can't pay for it.

    Each ``custom_id`` carries the save's owner, so a click is checked against them without stored state.
    """
    buttons = [
        Button(style=ButtonStyle.SECONDARY, label="Refresh", custom_id=refresh.custom_id(view.member_id)),
        *(
            Button(
                style=ButtonStyle.SUCCESS if offer.affordable else ButtonStyle.SECONDARY,
                label=f"Buy {offer.generator.name}",
                custom_id=buy.custom_id(view.member_id, offer.generator.key),
                disabled=not offer.affordable,
            )
            for offer in view.offers
        ),
    ]
    return [
        ActionRow(components=buttons[start : start + MAX_ACTION_ROW_BUTTONS])
        for start in range(0, len(buttons), MAX_ACTION_ROW_BUTTONS)
    ]
