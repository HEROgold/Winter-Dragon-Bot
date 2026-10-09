"""Keeps the commands Discord has equal to the :class:`~wd_bot.registry.CommandRegistry`, one scope at a time.

Per scope: if Discord hasn't reported the scope since startup, GET its commands (that recovers their IDs). If they
already match what the registry wants, stop there; otherwise PUT the scope's full command list (a bulk overwrite)
and record Discord's answer. A restart without command changes therefore costs one GET per scope and no writes.
"""

from __future__ import annotations

lazy import asyncio
lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin
lazy from wd_discord import is_network_error


if TYPE_CHECKING:
    lazy from collections.abc import Iterable

    lazy from wd_discord import Client
    lazy from wd_discord.entities import GlobalCommandStore, GuildCommandStore

    lazy from wd_bot.registry import CommandRegistry, Scope


class CommandSyncer(LoggerMixin):
    """Brings Discord's commands in line with a :class:`~wd_bot.registry.CommandRegistry`."""

    def __init__(self, registry: CommandRegistry) -> None:
        """Sync the scopes of ``registry``."""
        self.registry = registry
        self._lock = asyncio.Lock()
        self._pending: set[Scope] = set()

    async def sync(self, client: Client, scopes: Iterable[Scope], *, allow_writes: bool = True) -> None:
        """Sync each of ``scopes``; with ``allow_writes`` False, only read them (recovering IDs), never PUT.

        Calls overlapping a running sync queue their scopes onto it, so several hot reloads in a row end in
        one PUT per scope.
        """
        self._pending.update(scopes)
        async with self._lock:
            while self._pending:
                await self._sync_scope(client, self._pending.pop(), allow_writes=allow_writes)

    async def _sync_scope(self, client: Client, scope: Scope, *, allow_writes: bool) -> None:
        """Read ``scope`` from Discord if it is unknown, then PUT its commands if they differ."""
        store = self._store(client, scope)
        if not self.registry.is_known(scope):
            fetched = await store.fetch_all()
            if is_network_error(fetched):
                self.logger.warning(t"Failed to fetch the commands in {scope}: {fetched}")
                return
            self.registry.apply(scope, (command.model for command in fetched))
        if self.registry.in_sync(scope):
            return
        if not allow_writes:
            self.logger.warning(t"Commands in {scope} differ from Discord; skipping the write")
            return
        written = await store.overwrite(self.registry.params(scope))
        if is_network_error(written):
            self.logger.warning(t"Failed to write the commands in {scope}: {written}")
            return
        self.registry.apply(scope, (command.model for command in written))
        self.logger.info(t"Synced the commands in {scope}")

    @staticmethod
    def _store(client: Client, scope: Scope) -> GlobalCommandStore | GuildCommandStore:
        """Return the command store behind ``scope``."""
        if scope.guild_id is None:
            return client.application.commands
        return client.application.guild_commands(scope.guild_id)
