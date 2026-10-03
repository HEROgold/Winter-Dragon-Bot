"""Admin command group for inspecting and forcing the application-command sync state."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from sqlmodel import Session
lazy from wd_bot.auto_sync import GlobalSyncedCommand, SyncedCommands
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_db.constants import engine
lazy from wd_discord.embed import Embed
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.permissions import Permissions


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Sequence

    lazy from wd_discord.gateway.events import Interaction


def describe_sync_status(session: Session, commands: Sequence[tuple[str, str]]) -> Generator[str]:
    """Yield one "name: synced|pending" line per (name, signature) pair in ``commands``."""
    synced = SyncedCommands.load(session, GlobalSyncedCommand)
    for name, current_signature in commands:
        yield f"{name}: {'synced' if synced.is_synced(name, current_signature) else 'pending'}"


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
    async def list_commands(self, interaction: Interaction) -> None:
        """Show every registered command's synced/pending state."""
        commands = [(command.name, command.signature()) for command in self.bot.commands]
        with Session(engine) as session:
            lines = list(describe_sync_status(session, commands))
        embed = Embed(title="Registered commands", description="\n".join(lines) or "No commands registered.")
        await self.bot.client.create_interaction_response(interaction, embeds=[embed])

    @Cog.command(  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUntypedFunctionDecorator]
        name="resync",
        description="Push pending command changes to Discord",
    )
    async def resync(self, interaction: Interaction) -> None:
        """Acknowledge within Discord's 3s window, then force the diff-and-push sync."""
        await self.bot.client.create_interaction_response(interaction, content="Resyncing commands…")
        await self.bot.sync_commands(self.bot.client)
        self.logger.info(t"Command resync finished")
