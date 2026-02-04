"""Incremental game cog for the Winter Dragon bot."""

from datetime import UTC, datetime
from typing import Any

import discord
from discord import Interaction, app_commands
from sqlmodel import Session, select

from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.extensions.games.incremental_ui import GeneratorShopMenu, ProgressMenu
from winter_dragon.database.tables.incremental.currency import UserMoney
from winter_dragon.database.tables.incremental.generators import Generators
from winter_dragon.database.tables.incremental.player import Players
from winter_dragon.database.tables.incremental.rates import GeneratorRates


class PlayerManager:
    """Manages player-related database operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the player manager."""
        self.session = session

    def ensure_player_exists(self, user_id: int) -> Players:
        """Ensure a player exists in the database, creating if necessary."""
        player = self.session.exec(select(Players).where(Players.user_id == user_id)).first()
        if not player:
            player = Players(user_id=user_id, last_collection=datetime.now(tz=UTC))
            self.session.add(player)
            self.session.commit()
        return player


class GeneratorManager:
    """Manages generator-related database operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the generator manager."""
        self.session = session

    def get_by_name(self, name: str) -> Generators | None:
        """Get a generator by name."""
        return self.session.exec(select(Generators).where(Generators.name == name)).first()

    def create(
        self,
        name: str,
        description: str,
        cost_currency: str,
        cost_amount: int,
        base_per_second: float,
    ) -> Generators:
        """Create and save a new generator."""
        generator = Generators(
            name=name,
            description=description,
            cost_currency=cost_currency,
            cost_amount=cost_amount,
            base_per_second=base_per_second,
        )
        self.session.add(generator)
        self.session.commit()
        return generator

    def update(
        self,
        generator: Generators,
        cost_currency: str | None = None,
        cost_amount: int | None = None,
        base_per_second: float | None = None,
        description: str | None = None,
    ) -> None:
        """Update generator properties."""
        if cost_currency is not None:
            generator.cost_currency = cost_currency
        if cost_amount is not None:
            generator.cost_amount = cost_amount
        if base_per_second is not None:
            generator.base_per_second = base_per_second
        if description is not None:
            generator.description = description
        self.session.commit()

    def get_all(self) -> list[Generators]:
        """Get all generators."""
        return list(self.session.exec(select(Generators)).all())


class CurrencyManager:
    """Manages currency-related database operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the currency manager."""
        self.session = session

    def get_balance(self, user_id: int, currency: str) -> int:
        """Get a user's currency balance."""
        user_money = self.session.exec(
            select(UserMoney).where(
                UserMoney.user_id == user_id,
                UserMoney.currency == currency,
            )
        ).first()
        return user_money.value if user_money else 0

    def add_currency(self, user_id: int, currency: str, amount: int) -> UserMoney:
        """Add currency to a user."""
        user_money = self.session.exec(
            select(UserMoney).where(
                UserMoney.user_id == user_id,
                UserMoney.currency == currency,
            )
        ).first()

        if user_money:
            user_money.value += amount
        else:
            user_money = UserMoney(user_id=user_id, currency=currency, value=amount)
            self.session.add(user_money)

        self.session.commit()
        return user_money


class RateManager:
    """Manages generator rate-related database operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the rate manager."""
        self.session = session

    def get_or_create_rate(self, generator_id: int, currency: str, per_second: float) -> GeneratorRates:
        """Get or create a rate for a generator."""
        rate = self.session.exec(
            select(GeneratorRates).where(
                GeneratorRates.generator_id == generator_id,
                GeneratorRates.currency == currency,
            )
        ).first()

        if rate:
            rate.per_second = per_second
        else:
            rate = GeneratorRates(generator_id=generator_id, currency=currency, per_second=per_second)
            self.session.add(rate)

        self.session.commit()
        return rate


class IncrementalGame(Cog, auto_load=True):
    """Cog for managing the incremental game system."""

    def __init__(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the cog with manager instances."""
        super().__init__(**kwargs)
        self.player_manager = PlayerManager(self.session)
        self.generator_manager = GeneratorManager(self.session)
        self.currency_manager = CurrencyManager(self.session)
        self.rate_manager = RateManager(self.session)

    @app_commands.command(name="buy", description="Buy a generator for the incremental game")
    @app_commands.guild_only()
    async def buy(self, interaction: Interaction) -> None:
        """Open the generator shop menu."""
        user_id = interaction.user.id
        self.player_manager.ensure_player_exists(user_id)

        menu = GeneratorShopMenu(
            interaction,
            user_id,
            self.generator_manager,
            self.currency_manager,
        )
        embed = discord.Embed(
            title="Generator Shop",
            description="Select a generator to purchase",
            colour=discord.Colour.gold(),
        )
        await interaction.response.send_message(embed=embed, view=menu, ephemeral=True)

    @app_commands.command(name="progress", description="View your incremental game progress")
    @app_commands.guild_only()
    async def progress(self, interaction: Interaction) -> None:
        """View player's game progress."""
        user_id = interaction.user.id
        self.player_manager.ensure_player_exists(user_id)

        menu = ProgressMenu(interaction, user_id, self.generator_manager)
        embed = menu.embed()
        embed.set_footer(text="Use the buttons below to refresh")
        await interaction.response.send_message(embed=embed, view=menu, ephemeral=True)

    # Admin command group
    admin = app_commands.Group(
        name="admin",
        description="Admin commands for managing the incremental game",
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True),
    )

    @admin.command(name="generator-add", description="Add a new generator")
    async def admin_generator_add(  # noqa: PLR0913
        self,
        interaction: Interaction,
        name: str,
        cost_currency: str,
        cost_amount: int,
        base_per_second: float,
        description: str = "A new generator",
    ) -> None:
        """Add a new generator to the game."""
        if self.generator_manager.get_by_name(name):
            await interaction.response.send_message(f"Generator '{name}' already exists!", ephemeral=True)
            return

        generator = self.generator_manager.create(
            name=name,
            description=description,
            cost_currency=cost_currency,
            cost_amount=cost_amount,
            base_per_second=base_per_second,
        )

        self.logger.info(f"Added generator '{name}' with {base_per_second} per second rate")
        embed = self._build_generator_embed(generator, "Generator Added", discord.Colour.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin.command(name="generator-update", description="Update an existing generator")
    async def admin_generator_update(  # noqa: PLR0913
        self,
        interaction: Interaction,
        name: str,
        cost_currency: str | None = None,
        cost_amount: int | None = None,
        base_per_second: float | None = None,
        description: str | None = None,
    ) -> None:
        """Update an existing generator."""
        generator = self.generator_manager.get_by_name(name)
        if not generator:
            await interaction.response.send_message(f"Generator '{name}' not found!", ephemeral=True)
            return

        self.generator_manager.update(
            generator,
            cost_currency=cost_currency,
            cost_amount=cost_amount,
            base_per_second=base_per_second,
            description=description,
        )

        self.logger.info(f"Updated generator '{name}'")
        embed = self._build_generator_embed(generator, "Generator Updated", discord.Colour.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin.command(name="generator-list", description="List all generators")
    async def admin_generator_list(self, interaction: Interaction) -> None:
        """List all generators in the game."""
        generators = self.generator_manager.get_all()

        if not generators:
            await interaction.response.send_message("No generators found!", ephemeral=True)
            return

        embed = discord.Embed(title="All Generators", colour=discord.Colour.blurple())
        for generator in generators:
            self._add_generator_field(embed, generator)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Currency subgroup
    currency = app_commands.Group(
        name="currency",
        description="Manage player currency",
        parent=admin,
    )

    @currency.command(name="add", description="Add currency to a user")
    async def admin_currency_add(
        self,
        interaction: Interaction,
        user: discord.User,
        currency: str,
        amount: int,
    ) -> None:
        """Add currency to a user."""
        self.player_manager.ensure_player_exists(user.id)
        self.currency_manager.add_currency(user.id, currency, amount)

        self.logger.info(f"Added {amount} {currency} to {user}")

        embed = discord.Embed(
            title="Currency Added",
            description=f"Added {amount} {currency} to {user.mention}",
            colour=discord.Colour.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Rates subgroup
    rate = app_commands.Group(
        name="rate",
        description="Manage generator production rates",
        parent=admin,
    )

    @rate.command(name="add", description="Add/update generation rate for a generator")
    async def admin_rate_add(
        self,
        interaction: Interaction,
        generator_name: str,
        currency: str,
        per_second: float,
    ) -> None:
        """Add or update a generation rate for a generator and currency combination."""
        generator = self.generator_manager.get_by_name(generator_name)
        if not generator or generator.id is None:
            await interaction.response.send_message(f"Generator '{generator_name}' not found!", ephemeral=True)
            return

        self.rate_manager.get_or_create_rate(generator.id, currency, per_second)
        self.logger.info(f"Updated rate for '{generator_name}': {per_second} {currency}/s")

        embed = discord.Embed(
            title="Rate Added/Updated",
            description=f"Generator: {generator_name}\nCurrency: {currency}\nRate: {per_second} per second",
            colour=discord.Colour.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Helper methods
    def _build_generator_embed(self, generator: Generators, title: str, colour: discord.Colour) -> discord.Embed:
        """Build a generator info embed."""
        embed = discord.Embed(
            title=title,
            description=f"Successfully {'added' if 'Added' in title else 'updated'} generator '{generator.name}'",
            colour=colour,
        )
        embed.add_field(name="Description", value=generator.description, inline=False)
        embed.add_field(name="Cost", value=f"{generator.cost_amount} {generator.cost_currency}", inline=True)
        embed.add_field(
            name="Generation Rate",
            value=f"{generator.base_per_second:.6f} per second",
            inline=True,
        )
        return embed

    def _add_generator_field(self, embed: discord.Embed, generator: Generators) -> None:
        """Add a generator field to an embed."""
        embed.add_field(
            name=generator.name,
            value=(
                f"Cost: {generator.cost_amount} {generator.cost_currency}\n"
                f"Rate: {generator.base_per_second:.6f} per second\n"
                f"Description: {generator.description}"
            ),
            inline=False,
        )
