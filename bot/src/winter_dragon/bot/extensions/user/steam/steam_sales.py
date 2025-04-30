"""Module to notify users of steam sales."""
import asyncio

from discord import Embed, Interaction, app_commands
from discord.errors import NotFound
from sqlmodel import select
from winter_dragon.bot.constants import STEAM_PERIOD, STEAM_SEND_PERIOD
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.extensions.user.steam.sale_repository import SteamSaleRepository
from winter_dragon.bot.extensions.user.steam.sale_scraper import SteamScraper
from winter_dragon.bot.extensions.user.steam.user_notifier import SteamSaleNotifier
from winter_dragon.database.tables.steamsale import SteamSale
from winter_dragon.database.tables.steamuser import SteamUsers
from winter_dragon.database.tables.user import Users


class SteamSales(GroupCog):
    """Steam Sales cog for Discord bot."""

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the Steam Sales cog."""
        super().__init__(bot)
        self.repository = SteamSaleRepository(bot)
        self.scraper = SteamScraper()

    async def cog_load(self) -> None:
        """Load the cog."""
        self.update.start()
        self.loop = asyncio.get_event_loop()

    async def get_new_steam_sales(self, percent: int) -> list[SteamSale]:
        """Get only unknown/new sales.

        Args:
        ----
            percent (int): Percentage to check for

        Returns:
        -------
            list[Sale]: List of TypedDict Sale

        """
        known_sales = self.repository.get_saved_sales()
        steam_sales = self.scraper.get_sales_from_steam(percent=percent)

        async for sale in steam_sales:
            if sale is None:
                self.logger.debug("Got None sale, skipping")
                continue
            self.repository.update_sale(sale)

        self.logger.debug(f"checking for new sales, {known_sales=}, {steam_sales=}")

        outdated = [
            i
            for i in known_sales
            if self.repository.is_outdated(i, STEAM_PERIOD)
        ]

        return [
            sale
            async for sale in steam_sales
            if sale and sale in outdated
        ]


    @loop(seconds=STEAM_SEND_PERIOD)
    async def update(self) -> None:
        """Create a discord Embed object to send and notify users of new 100% sales.

        Expected amount of sales should be low enough it'll never reach embed size limit.
        """
        self.logger.info("updating sales")

        embed = Embed(title="Free Steam Game's", description="New free Steam Games have been found!", color=0x094d7f)
        new_sales = await self.get_new_steam_sales(percent=100)
        self.logger.debug(f"{new_sales=}")

        notifier = SteamSaleNotifier()
        embed = notifier.populate_embed(embed, new_sales)

        if len(embed.fields) == 0:
            self.logger.warning("Got no populated embed, skipping sale sending.")
            return

        sub_mention_remove = self.get_command_mention(self.slash_remove)
        sub_mention_show = self.get_command_mention(self.slash_show)
        disable_message = f"You can disable this message by using {sub_mention_remove}"
        all_sale_message = f"You can see other sales by using {sub_mention_show}, followed by a percentage"

        with self.session as session:
            users = session.exec(select(SteamUsers)).all()
            self.logger.debug(f"Got embed with sales, {embed}, to send to {users=}")

            for db_user in users:
                self.logger.debug(f"Trying to show new sales to {db_user.id=}")
                try:
                    user = self.bot.get_user(db_user.id) or await self.bot.fetch_user(db_user.id)
                except NotFound:
                    self.logger.warning(f"Not showing {db_user.id=} sales, discord.errors.NotFound")
                    continue

                if len(embed.fields) > 0:
                    self.logger.debug(f"Showing {user}, {embed}")
                    await user.send(content=f"{disable_message}\n{all_sale_message}", embed=embed)
                else:
                    self.logger.debug(f"Not showing sales, empty embed fields: {user}, {embed}")


    @update.before_loop
    async def before_update(self) -> None:
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

    @app_commands.command(name="add", description="Get notified automatically about free steam games")
    async def slash_add(self, interaction: Interaction) -> None:
        """Add a user to the list of recipients for free steam games."""
        with self.session as session:
            if session.exec(select(Users).where(Users.id == interaction.user.id)).first() is None:
                session.add(Users(id = interaction.user.id))
                session.commit()

            result = session.exec(select(SteamUsers).where(SteamUsers.id == interaction.user.id))
            if result.first():
                await interaction.response.send_message("Already in the list of recipients", ephemeral=True)
                return
            session.add(SteamUsers(id = interaction.user.id))
            session.commit()
        sub_mention = self.get_command_mention(self.slash_show)
        msg = f"I will notify you of new steam games!\nUse {sub_mention} to view current sales."
        await interaction.response.send_message(msg, ephemeral=True)


    @app_commands.command(name="remove", description="No longer get notified of free steam games")
    async def slash_remove(self, interaction: Interaction) -> None:
        """Remove a user from the list of recipients for free steam games."""
        with self.session as session:
            result = session.exec(select(SteamUsers).where(SteamUsers.id == interaction.user.id))
            user = result.first()
            if not user:
                await interaction.response.send_message("Not in the list of recipients", ephemeral=True)
                return
            session.delete(user)
            session.commit()
        await interaction.response.send_message("I not notify you of new free steam games anymore.", ephemeral=True)


    # @app_commands.checks.cooldown(1, UPDATE_PERIOD)
    @app_commands.command(
        name="show",
        description="Get a list of steam games that are on sale for the given percentage or higher")
    async def slash_show(self, interaction: Interaction, percent: int = 100) -> None:
        """Get a list of steam games that are on sale for the given percentage or higher."""
        await interaction.response.defer()

        notifier = SteamSaleNotifier()
        embed = Embed(title="Steam Games", description=f"Steam Games with sales {percent}% or higher", color=0x094d7f)
        sales = [i async for i in self.scraper.get_sales_from_steam(percent=percent) if i is not None]
        embed = notifier.populate_embed(embed, sales)
        self.logger.debug(f"{embed.to_dict()}")

        if len(embed.fields) > 0:
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"No steam games found with {percent} or higher sales.", ephemeral=True)



async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(SteamSales(bot))
