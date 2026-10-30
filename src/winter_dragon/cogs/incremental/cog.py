"""The /incremental command: show your save, refresh it, and buy generators, all on one message."""

lazy from typing import TYPE_CHECKING, override

lazy from sqlmodel import Session
lazy from wd_bot.cogs import Cog
lazy from wd_discord.snowflake import Snowflake
lazy from wd_errors import Refused

lazy from winter_dragon.cogs.incremental import game
lazy from winter_dragon.cogs.incremental.catalogue import catalogue
lazy from winter_dragon.cogs.incremental.models import INCREMENTAL_TABLES
lazy from winter_dragon.cogs.incremental.view import build_buttons, build_embed


if TYPE_CHECKING:
    lazy from wd_discord import CommandInteraction, ComponentInteraction
    lazy from wd_discord.components import ActionRow

    lazy from winter_dragon.cogs.incremental.game import SaveView


class Incremental(Cog):
    """Plays the Incremental game: one save per member, whatever guild they are in."""

    @override
    async def load(self) -> None:
        """Parse the catalogue, so an invalid file stops startup, then create the tables if missing."""
        catalogue()
        self.create_tables(*INCREMENTAL_TABLES)

    @Cog.command(name="incremental", description="Show your Incremental game save")
    async def incremental(self, interaction: CommandInteraction) -> None:
        """Show the invoking user's save, creating it on first use."""
        user = interaction.user
        if user is None:
            return
        with Session(self.bind) as session:
            view = game.open_save(session, user.id)
        await interaction.respond(embeds=[build_embed(view)], components=self._buttons(view))

    @Cog.component("incremental-refresh")
    async def refresh(self, interaction: ComponentInteraction, owner_id: str) -> None:
        """Bring the save up to date in the same message; only its owner may."""
        self._check_owner(interaction, owner_id)
        with Session(self.bind) as session:
            view = game.open_save(session, Snowflake.coerce(owner_id))
        await interaction.update(embeds=[build_embed(view)], components=self._buttons(view))

    @Cog.component("incremental-buy")
    async def buy(self, interaction: ComponentInteraction, owner_id: str, generator: str) -> None:
        """Buy one ``generator`` and update the same message; only the save's owner may, and they must afford it."""
        self._check_owner(interaction, owner_id)
        with Session(self.bind) as session:
            view = game.buy(session, Snowflake.coerce(owner_id), generator)
        await interaction.update(embeds=[build_embed(view)], components=self._buttons(view))

    def _buttons(self, view: SaveView) -> list[ActionRow]:
        """Return the Refresh and Buy buttons under ``view``."""
        return build_buttons(view, refresh=self.refresh, buy=self.buy)

    def _check_owner(self, interaction: ComponentInteraction, owner_id: str) -> None:
        """Refuse unless the clicker owns the save."""
        user = interaction.user
        if user is None or str(user.id) != owner_id:
            msg = f"This is not your save. Use {self.mention(self.incremental)} for your own."
            raise Refused(msg)
