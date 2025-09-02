"""Module to notify users of steam sales."""
import asyncio

from confkit.data_types import Hex
from discord import Embed, Interaction, app_commands
from sqlmodel import select
from winter_dragon.bot.config import Config
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.extensions.user.steam.sale_scraper import SteamScraper
from winter_dragon.bot.extensions.user.steam.user_notifier import SteamSaleNotifier
from winter_dragon.database.tables.steamsale import SteamSale
from winter_dragon.database.tables.steamuser import SteamUsers
from winter_dragon.database.tables.user import Users


STEAM_SEND_PERIOD = 3600 * 3 # 3 hour cooldown on updates in seconds
OUTDATED_DELTA = STEAM_SEND_PERIOD * 10 # 30 hours.

class SteamSales(GroupCog):
    """Steam Sales cog for Discord bot."""

    steam_sales_update_interval = Config(STEAM_SEND_PERIOD)
    embed_color = Config(Hex(0x094d7f))

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the Steam Sales cog."""
        super().__init__(bot=bot)
        self.scraper = SteamScraper()

    async def cog_load(self) -> None:
        """Load the cog."""
        await super().cog_load()
        self.loop = asyncio.get_event_loop()
        # Configure loop interval from config
        self.update.change_interval(seconds=self.steam_sales_update_interval)
        self.update.start()

    async def get_new_steam_sales(self, percent: int) -> list[SteamSale]:
        """Get only unknown/new sales.

        Args:
        ----
            percent (int): Percentage to check for 0 .. 100

        """
        known_sales = SteamSale.get_all()
        steam_sales = self.scraper.get_sales_from_steam(percent=percent)

        async for sale in steam_sales:
            if sale is None:
                self.logger.debug("Got None sale, skipping")
                continue
            sale.update()

        self.logger.debug(f"checking for new sales, {known_sales=}, {steam_sales=}")

        outdated = [
            i
            for i in known_sales
            if i.is_outdated(OUTDATED_DELTA)
        ]

        return [
            sale
            async for sale in steam_sales
            if sale and sale in outdated
        ]


    @loop()
    async def update(self) -> None:
        """Create a discord Embed object to send and notify users of new 100% sales.

        Expected amount of sales should be low enough it'll never reach embed size limit.
        """
        self.logger.info("updating sales")

        embed = Embed(title="Free Steam Game's", description="New free Steam Games have been found!", color=0x094d7f)
        new_sales = await self.get_new_steam_sales(percent=100)
        notifier = SteamSaleNotifier(self.bot, self.session, embed)
        self._setup_notifier_messages(notifier)
        embed = notifier.add_sales(new_sales)

    def _set_notify_messages(self) -> None:
        """Update the notify messages."""
        SteamSales.sub_mention_remove = self.get_command_mention(self.slash_remove)
        SteamSales.sub_mention_show = self.get_command_mention(self.slash_show)
        SteamSales.disable_message = f"You can disable this message by using {SteamSales.sub_mention_remove}"
        SteamSales.all_sale_message = f"You can see other sales by using {SteamSales.sub_mention_show}, followed by a percentage"  # noqa: E501

    def _setup_notifier_messages(self, notifier: SteamSaleNotifier) -> None:
        """Set up the notifier messages."""
        self._set_notify_messages()
        notifier.set_messages(
            SteamSales.sub_mention_remove,
            SteamSales.sub_mention_show,
            SteamSales.disable_message,
            SteamSales.all_sale_message,
        )


    @update.before_loop
    async def before_update(self) -> None:
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

    @app_commands.command(name="add", description="Get notified automatically about free steam games")
    async def slash_add(self, interaction: Interaction) -> None:
        """Add a user to the list of recipients for free steam games."""
        if self.session.exec(select(Users).where(Users.id == interaction.user.id)).first() is None:
            self.session.add(Users(id = interaction.user.id))
            self.session.commit()

        result = self.session.exec(select(SteamUsers).where(SteamUsers.user_id == interaction.user.id))
        if result.first():
            await interaction.response.send_message("Already in the list of recipients", ephemeral=True)
            return
        self.session.add(SteamUsers(user_id = interaction.user.id))
        self.session.commit()
        sub_mention = self.get_command_mention(self.slash_show)
        msg = f"I will notify you of new steam games!\nUse {sub_mention} to view current sales."
        await interaction.response.send_message(msg, ephemeral=True)


    @app_commands.command(name="remove", description="No longer get notified of free steam games")
    async def slash_remove(self, interaction: Interaction) -> None:
        """Remove a user from the list of recipients for free steam games."""
        result = self.session.exec(select(SteamUsers).where(SteamUsers.user_id == interaction.user.id))
        user = result.first()
        if not user:
            await interaction.response.send_message("Not in the list of recipients", ephemeral=True)
            return
        self.session.delete(user)
        self.session.commit()
        await interaction.response.send_message("I not notify you of new free steam games anymore.", ephemeral=True)


    @app_commands.command(
        name="show",
        description="Get a list of steam games that are on sale for the given percentage or higher")
    async def slash_show(self, interaction: Interaction, percent: int = 100) -> None:
        """Get a list of steam games that are on sale for the given percentage or higher."""
        await interaction.response.defer()

        embed = Embed(title="Steam Games", description=f"Steam Games with sales {percent}% or higher", color=self.embed_color)
        notifier = SteamSaleNotifier(self.bot, self.session, embed)

        sales = [i async for i in self.scraper.get_sales_from_steam(percent=percent) if i is not None]
        notifier.add_sales(sales)
        await interaction.followup.send(embed=notifier.embed)



async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(SteamSales(bot=bot))
