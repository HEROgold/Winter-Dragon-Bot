"""Module to notify users of steam sales."""

import asyncio
from datetime import UTC, datetime

from confkit.data_types import Hex
from discord import Interaction, app_commands
from sqlmodel import select

from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.extensions.user.steam.steam_sales_menu import create_sales_paginator
from winter_dragon.config import Config
from winter_dragon.database.tables.steamsale import SteamSale
from winter_dragon.database.tables.steamuser import SteamUsers
from winter_dragon.database.tables.user import Users
from winter_dragon.redis.queue import TaskQueue
from winter_dragon.workers.tasks.steam_scraper import scrape_steam_sales


STEAM_SEND_PERIOD = 3600 * 3  # 3 hour cooldown on updates in seconds
OUTDATED_DELTA = STEAM_SEND_PERIOD * 10  # 30 hours.


class SteamSales(GroupCog, auto_load=True):
    """Steam Sales cog for Discord bot."""

    steam_sales_update_interval = Config(STEAM_SEND_PERIOD)
    """How often to check for new steam sales in seconds."""
    outdated_delta = Config(OUTDATED_DELTA)
    """When a sale is considered outdated in seconds."""
    embed_color = Config(Hex(0x094D7F))

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the Steam Sales cog."""
        super().__init__(bot=bot)

    async def cog_load(self) -> None:
        """Load the cog."""
        await super().cog_load()
        self.loop = asyncio.get_event_loop()
        # Configure loop interval from config
        self.update.change_interval(seconds=self.steam_sales_update_interval)
        self.update.start()

    @loop()  # Interval is set in cog_load
    async def update(self) -> None:
        """Queue Steam sales scraping work for workers to process.

        This method acts as a job dispatcher, enqueuing scraping tasks
        to Redis for workers to pick up and execute asynchronously.
        Workers handle scraping, database updates, and user notifications.
        """
        self.logger.info("Queueing Steam sales scraping task")

        ttl = self.steam_sales_update_interval + self.steam_sales_update_interval / 10

        job = TaskQueue.enqueue_task(
            scrape_steam_sales,
            percent=100,
            outdated_delta=self.outdated_delta,
            queue_name=TaskQueue.LOW_PRIORITY_QUEUE,
            job_timeout=1800,  # 30 minutes max
            result_ttl=int(ttl),  # Keep results 10% longer than the update interval
            job_id=f"steam_scrape_{datetime.now(UTC).timestamp()}",
        )

        self.logger.info(
            f"Steam scraping task enqueued: job_id={job.id}",
            extra={"job_id": job.id, "queue": TaskQueue.LOW_PRIORITY_QUEUE},
        )

    @update.before_loop
    async def before_update(self) -> None:
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

    @app_commands.command(name="add", description="Get notified automatically about free steam games")
    async def slash_add(self, interaction: Interaction) -> None:
        """Add a user to the list of recipients for free steam games."""
        if self.session.exec(select(Users).where(Users.id == interaction.user.id)).first() is None:
            self.session.add(Users(id=interaction.user.id))
            self.session.commit()

        result = self.session.exec(select(SteamUsers).where(SteamUsers.user_id == interaction.user.id))
        if result.first():
            await interaction.response.send_message("Already in the list of recipients", ephemeral=True)
            return
        self.session.add(SteamUsers(user_id=interaction.user.id, last_notification=datetime.now(UTC)))
        self.session.commit()
        sub_mention = self.get_command_mention(self.slash_show)
        msg = f"I will notify you of new steam games!\nUse {sub_mention} to view current sales."
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name="percentage", description="Get notified of steam games on sale for the given percentage or higher"
    )
    async def slash_set_percentage(self, interaction: Interaction, percent: int) -> None:
        """Set the percentage for steam sale notifications."""
        query = select(SteamUsers).where(SteamUsers.user_id == interaction.user.id).with_for_update()
        user = self.session.exec(query).first()
        if not user:
            await interaction.response.send_message(
                f"You are not in the list of recipients. Use {self.get_command_mention(self.slash_add)} to subscribe.",
                ephemeral=True,
            )
            return
        user.sale_threshold = percent
        self.session.add(user)
        self.session.commit()
        await interaction.response.send_message(f"Changed your sale notification threshold to {percent}%.", ephemeral=True)

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
        description="Get a list of steam games that are on sale for the given percentage or higher",
    )
    async def slash_show(self, interaction: Interaction, percent: int = 100) -> None:
        """Get a list of steam games that are on sale for the given percentage or higher."""
        sales = [s for s in SteamSale.get_all() if s.sale_percent >= percent]

        if not sales:
            await interaction.response.send_message(
                f"No steam games found with sales {percent}% or higher.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        paginator = await create_sales_paginator(
            sales=sales,
            session=self.session,
            color=self.embed_color,
            items_per_page=5,
        )
        await paginator.start(interaction)
