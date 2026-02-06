"""UI components for the incremental game."""

from typing import TYPE_CHECKING

import discord
from discord import Interaction
from sqlmodel import select

from winter_dragon.bot.ui import Menu
from winter_dragon.bot.ui.button import Button
from winter_dragon.database.constants import SessionMixin
from winter_dragon.database.tables.incremental.currency import UserMoney
from winter_dragon.database.tables.incremental.generators import Generators
from winter_dragon.database.tables.incremental.user_generator import AssociationUserGenerator


if TYPE_CHECKING:
    from winter_dragon.bot.extensions.games.incremental import CurrencyManager, GeneratorManager


class GeneratorShopMenu(Menu, SessionMixin):
    """Menu for buying generators in the incremental game."""

    def __init__(
        self,
        interaction: Interaction,
        user_id: int,
        generator_manager: "GeneratorManager",
        currency_manager: "CurrencyManager",
        timeout: float = 300.0,
    ) -> None:
        """Initialize the generator shop menu."""
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.user_id = user_id
        self.generator_manager = generator_manager
        self.currency_manager = currency_manager
        self.selected_generator: Generators | None = None

        # Fetch all generators using manager
        generators = self.generator_manager.get_all()

        for idx, generator in enumerate(generators):

            async def on_select_generator(
                interaction: Interaction,
                gen: Generators = generator,
            ) -> None:
                self.selected_generator = gen
                await self._show_purchase_confirmation(interaction, gen)

            button = Button(
                label=generator.name,
                style=discord.ButtonStyle.primary,
                on_interact=on_select_generator,
                row=idx // 3,
            )
            self.add_item(button)

    async def _show_purchase_confirmation(self, interaction: Interaction, generator: Generators) -> None:
        """Show a confirmation dialog for purchasing a generator."""
        currency_name = generator.cost_currency
        current_balance = self.currency_manager.get_balance(self.user_id, currency_name)
        can_afford = current_balance >= generator.cost_amount

        generation_rate = generator.base_per_second

        embed = discord.Embed(
            title=f"Purchase {generator.name}?",
            description=generator.description,
            colour=discord.Colour.green() if can_afford else discord.Colour.red(),
        )
        embed.add_field(name="Cost", value=f"{generator.cost_amount} {currency_name}", inline=False)
        embed.add_field(name="Your Balance", value=f"{current_balance} {currency_name}", inline=False)
        embed.add_field(
            name="Generation Rate",
            value=f"{generation_rate:.6f} per second",
            inline=False,
        )

        async def on_confirm(interaction: Interaction) -> None:
            if not can_afford:
                await interaction.response.send_message("You cannot afford this generator!", ephemeral=True)
                return

            # Deduct currency using manager
            currency_name = generator.cost_currency
            self.currency_manager.add_currency(self.user_id, currency_name, -generator.cost_amount)

            # Add or increment user generator
            user_gen = self.session.exec(
                select(AssociationUserGenerator).where(
                    AssociationUserGenerator.user_id == self.user_id,
                    AssociationUserGenerator.generator_id == generator.id,
                )
            ).first()

            if user_gen:
                user_gen.count += 1
            else:
                user_gen = AssociationUserGenerator(
                    user_id=self.user_id,
                    generator_id=generator.id,  # pyright: ignore[reportArgumentType]
                    count=1,
                )
                self.session.add(user_gen)

            self.session.commit()

            await interaction.response.send_message(
                f"✅ Successfully purchased {generator.name}!",
                ephemeral=True,
            )

        async def on_cancel(interaction: Interaction) -> None:
            await interaction.response.send_message("Purchase cancelled.", ephemeral=True)

        confirm_button = Button(
            label="Confirm",
            style=discord.ButtonStyle.success,
            emoji="✅",
            on_interact=on_confirm,
            disabled=not can_afford,
            row=1,
        )
        cancel_button = Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            on_interact=on_cancel,
            row=1,
        )

        view = discord.ui.View()
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ProgressMenu(Menu, SessionMixin):
    """Menu for viewing player progress in the incremental game."""

    def __init__(
        self,
        interaction: Interaction,
        user_id: int,
        generator_manager: "GeneratorManager",
        timeout: float = 300.0,
    ) -> None:
        """Initialize the progress menu.

        Args:
            interaction: Discord interaction
            user_id: ID of the user
            generator_manager: Manager for generator operations
            timeout: Button timeout

        """
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.user_id = user_id
        self.generator_manager = generator_manager

        async def on_refresh(interaction: Interaction) -> None:
            embed = self._build_embed()
            await interaction.response.edit_message(embed=embed)

        refresh_button = Button(
            label="Refresh",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            on_interact=on_refresh,
        )
        self.add_item(refresh_button)

    def _build_embed(self) -> discord.Embed:
        """Build the progress embed."""
        embed = discord.Embed(
            title="Your Incremental Game Progress",
            colour=discord.Colour.blurple(),
        )

        # Get user's generators
        user_generators = self.session.exec(
            select(AssociationUserGenerator).where(AssociationUserGenerator.user_id == self.user_id)
        ).all()

        if not user_generators:
            embed.add_field(name="Generators", value="You don't have any generators yet.", inline=False)
        else:
            for user_gen in user_generators:
                # Use generator manager to get generator details
                generator = self.generator_manager.session.get(Generators, user_gen.generator_id)
                if generator:
                    generation_rate = generator.base_per_second
                    embed.add_field(
                        name=generator.name,
                        value=f"Owned: {user_gen.count}\nRate: {generation_rate:.6f}/s",
                        inline=True,
                    )

        # Get user's currency
        user_monies = self.session.exec(select(UserMoney).where(UserMoney.user_id == self.user_id)).all()
        if user_monies:
            currency_field = "\n".join(f"{m.currency}: {m.value}" for m in user_monies)
            embed.add_field(name="Currency", value=currency_field, inline=False)
        else:
            embed.add_field(name="Currency", value="No currency yet.", inline=False)

        return embed

    def embed(self) -> discord.Embed:
        """Build the progress settings embed."""
        return self._build_embed()
