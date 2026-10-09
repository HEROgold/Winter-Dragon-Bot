"""Admin command group for inspecting and forcing the application-command sync state."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_discord.embed import Embed
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.permissions import Permissions


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from wd_bot.registry import CommandRegistry
    lazy from wd_discord import CommandInteraction


def describe_sync_status(registry: CommandRegistry) -> Generator[str]:
    """Yield one "name (scope): synced|pending" line per registered command, scope by scope."""
    for scope in sorted(registry.scopes(), key=str):
        for entry in registry.entries(scope):
            status = "synced" if registry.is_synced(scope, entry.command.name) else "pending"
            yield f"{entry.command.name} ({scope}): {status}"


class BotCommands(
    GroupCog,
    name="bot-commands",
    description="Inspect and push the bot's application commands",
    default_member_permissions=Permissions.MANAGE_GUILD,
    contexts=[InteractionContextType.GUILD],
):
    """Admin ``/bot-commands`` group for inspecting/forcing application-command sync.

    Guild-only: Discord doesn't enforce ``default_member_permissions`` in DMs, so the group must not
    show up there.
    """

    @Cog.command(  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUntypedFunctionDecorator]
        name="list",
        description="List registered commands and their sync status",
    )
    async def list_commands(self, interaction: CommandInteraction) -> None:
        """Show every registered command's synced/pending state."""
        lines = list(describe_sync_status(self.bot.registry))
        embed = Embed(title="Registered commands", description="\n".join(lines) or "No commands registered.")
        await interaction.respond(embeds=[embed])

    @Cog.command(  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUntypedFunctionDecorator]
        name="resync",
        description="Re-read the commands from Discord and push any differences",
    )
    async def resync(self, interaction: CommandInteraction) -> None:
        """Acknowledge within Discord's 3s window, then re-read every scope from Discord and sync it."""
        await interaction.respond("Resyncing commands…")
        self.bot.registry.forget()
        await self.bot.sync_commands(self.bot.client)
        self.logger.info(t"Command resync finished")
