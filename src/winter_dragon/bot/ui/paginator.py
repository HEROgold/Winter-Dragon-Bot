"""Pagination components for navigating through large datasets."""

from typing import TYPE_CHECKING

import discord
from herogold.log import LoggerMixin

from .page_navigation_modal import PageNavigationModal
from .view import View


if TYPE_CHECKING:
    from collections.abc import Callable

    from discord.interactions import InteractionMessage


class PageSource[T](LoggerMixin):
    """Abstract base class for pagination sources."""

    async def get_page(self, page_number: int) -> T:
        """Get a specific page."""
        raise NotImplementedError

    async def get_page_count(self) -> int | None:
        """Get the total number of pages."""
        raise NotImplementedError

    async def format_page(self, page_data: T, page_number: int) -> tuple[str, discord.Embed]:
        """Format the page for display."""
        raise NotImplementedError


class ListPageSource(PageSource[list[str]]):
    """Page source for displaying lists of items."""

    def __init__(
        self,
        items: list[str],
        items_per_page: int = 10,
        title: str = "Results",
    ) -> None:
        """Initialize the list page source."""
        self.items = items
        self.items_per_page = items_per_page
        self.title = title

    async def get_page(self, page_number: int) -> list[str]:
        """Get a page of items."""
        start = page_number * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]

    async def get_page_count(self) -> int:
        """Get total page count."""
        return (len(self.items) + self.items_per_page - 1) // self.items_per_page

    async def format_page(self, page_data: list[str], page_number: int) -> tuple[str, discord.Embed]:
        """Format the page as an embed."""
        total_pages = await self.get_page_count()
        content = "\n".join(page_data)

        embed = discord.Embed(
            title=self.title,
            description=content,
            colour=discord.Colour.blurple(),
        )
        embed.set_footer(text=f"Page {page_number + 1}/{total_pages}")

        return "", embed


class EmbedPageSource(PageSource[discord.Embed]):
    """Page source for displaying pre-made embeds."""

    def __init__(self, embeds: list[discord.Embed]) -> None:
        """Initialize the embed page source."""
        self.embeds = embeds

    async def get_page(self, page_number: int) -> discord.Embed:
        """Get a page embed."""
        return self.embeds[page_number]

    async def get_page_count(self) -> int:
        """Get total page count."""
        return len(self.embeds)

    async def format_page(self, page_data: discord.Embed, page_number: int) -> tuple[str, discord.Embed]:
        """Format the page."""
        total_pages = await self.get_page_count()

        if not page_data.footer.text:
            page_data.set_footer(text=f"Page {page_number + 1}/{total_pages}")

        return "", page_data


class Paginator(View, LoggerMixin):
    """Interactive paginator for navigating through pages."""

    def __init__(
        self,
        source: PageSource,
        timeout: float = 180.0,
        on_page_change: Callable | None = None,
    ) -> None:
        """Initialize the paginator."""
        super().__init__(timeout=timeout)
        self.source = source
        self.current_page = 0
        self.total_pages: int | None = None
        self.on_page_change_callback = on_page_change

    async def start(self, interaction: discord.Interaction) -> InteractionMessage:
        """Start the paginator."""
        self.total_pages = await self.source.get_page_count()
        page_data = await self.source.get_page(self.current_page)
        content, embed = await self.source.format_page(page_data, self.current_page)

        await self._update_buttons()

        if interaction.response.is_done():
            # Interaction has already been responded to (e.g., deferred), use followup
            await interaction.followup.send(content or "\u200b", embed=embed, view=self, ephemeral=False)
            self.message = await interaction.original_response()
        else:
            # Normal response to interaction
            await interaction.response.send_message(content or "\u200b", embed=embed, view=self, ephemeral=False)
            self.message = await interaction.original_response()
        return self.message

    async def _update_buttons(self) -> None:
        """Update button states based on current page."""
        if self.total_pages is None or self.total_pages <= 1:
            self._children = []
            return

        # Clear existing buttons
        self.clear_items()

        # Add previous button
        prev_button = discord.ui.Button(
            label="◀",
            custom_id="paginator_prev",
            disabled=self.current_page == 0,
            style=discord.ButtonStyle.secondary,
        )
        prev_button.callback = self._prev_button_callback  # ty:ignore[invalid-assignment]
        self.add_item(prev_button)

        # Add go to page button
        go_to_button = discord.ui.Button(
            label="⋯",
            custom_id="paginator_goto",
            style=discord.ButtonStyle.secondary,
        )
        go_to_button.callback = self._goto_page_callback  # ty:ignore[invalid-assignment]
        self.add_item(go_to_button)

        # Add info button
        info_button = discord.ui.Button(
            label=f"{self.current_page + 1}/{self.total_pages}",
            custom_id="paginator_info",
            disabled=True,
            style=discord.ButtonStyle.secondary,
        )
        info_button.callback = self._info_button_callback  # ty:ignore[invalid-assignment]
        self.add_item(info_button)

        # Add next button
        next_button = discord.ui.Button(
            label="▶",
            custom_id="paginator_next",
            disabled=self.current_page >= self.total_pages - 1,
            style=discord.ButtonStyle.secondary,
        )
        next_button.callback = self._next_button_callback  # ty:ignore[invalid-assignment]
        self.add_item(next_button)

    async def show_page(self, interaction: discord.Interaction, page_number: int) -> None:
        """Show a specific page."""
        if self.total_pages is None:
            return

        if not 0 <= page_number < self.total_pages:
            return

        self.current_page = page_number
        page_data = await self.source.get_page(self.current_page)
        content, embed = await self.source.format_page(page_data, self.current_page)

        await self._update_buttons()

        if self.on_page_change_callback:
            await self.on_page_change_callback(self.current_page)
        await interaction.response.edit_message(content=content or "\u200b", embed=embed, view=self)

    async def _prev_button_callback(self, interaction: discord.Interaction) -> None:
        """Previous page button callback."""
        if self.current_page > 0:
            await self.show_page(interaction, self.current_page - 1)
        else:
            await interaction.response.defer()

    async def _goto_page_callback(self, interaction: discord.Interaction) -> None:
        """Go to page button callback."""
        if self.total_pages is None:
            await interaction.response.defer()
            return

        modal = PageNavigationModal(self.total_pages)
        await interaction.response.send_modal(modal)

        # Wait for modal submission
        await modal.wait()

        if modal.selected_page is not None and self.message:
            page_data = await self.source.get_page(modal.selected_page)
            content, embed = await self.source.format_page(page_data, modal.selected_page)

            self.current_page = modal.selected_page
            await self._update_buttons()

            if self.on_page_change_callback:
                await self.on_page_change_callback(self.current_page)

            await self.message.edit(content=content or "\u200b", embed=embed, view=self)

    async def _info_button_callback(self, interaction: discord.Interaction) -> None:
        """Info button callback."""
        await interaction.response.defer()

    async def _next_button_callback(self, interaction: discord.Interaction) -> None:
        """Next page button callback."""
        if self.total_pages and self.current_page < self.total_pages - 1:
            await self.show_page(interaction, self.current_page + 1)
        else:
            await interaction.response.defer()
