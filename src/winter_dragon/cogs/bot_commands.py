"""Admin command group for inspecting and forcing the application-command sync state."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from sqlmodel import Session, select
lazy from wd_bot.auto_sync import CommandRecord, GlobalSyncedCommand
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
    records_by_name = {record.name: record for record in session.exec(select(CommandRecord)).all()}
    synced_by_command_id = {row.command_id: row for row in session.exec(select(GlobalSyncedCommand)).all()}

    for name, current_signature in commands:
        record = records_by_name.get(name)
        row = synced_by_command_id.get(record.id) if record and record.id is not None else None
        state = "synced" if row is not None and row.signature == current_signature else "pending"
        yield f"{name}: {state}"


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
