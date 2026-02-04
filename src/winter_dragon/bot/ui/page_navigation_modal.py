"""Page navigation modal for paginators."""

import discord
from discord import ui

from .modal import Modal


class PageNavigationModal(Modal):
    """Modal for navigating to a specific page in a paginator."""

    def __init__(self, total_pages: int) -> None:
        """Initialize the page navigation modal."""
        super().__init__(
            title="Go to Page",
            custom_id="page_navigation_modal",
        )
        self.total_pages = total_pages
        self.selected_page: int | None = None

        # Add text input for page number
        self.page_input = ui.TextInput(
            label="Page Number",
            placeholder=f"Enter page 1-{total_pages}",
            min_length=1,
            max_length=len(str(total_pages)),
            required=True,
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        try:
            page_num = int(self.page_input.value)

            # Validate page number
            if not 1 <= page_num <= self.total_pages:
                await interaction.response.send_message(
                    f"Please enter a valid page number between 1 and {self.total_pages}.",
                    ephemeral=True,
                )
                return

            # Convert to 0-indexed
            self.selected_page = page_num - 1
            await interaction.response.defer()

        except ValueError:
            await interaction.response.send_message(
                "Please enter a valid number.",
                ephemeral=True,
            )
        finally:
            self._submitted.set()
