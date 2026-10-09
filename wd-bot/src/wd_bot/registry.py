"""Which application commands the bot registers where, and the IDs Discord gave them.

For each :class:`Scope` (global, or one guild) the :class:`CommandRegistry` holds two views:

- **local**: the commands the bot's cogs want registered there, placed by a :class:`Placement`.
- **remote**: the commands Discord last reported there, from a sync's GET or PUT.

Discord's answer is the only source of command IDs, so a mention never shows a stale one; nothing is persisted.
"""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Final, Protocol

lazy from herogold.log import LoggerMixin


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Iterable, Sequence

    lazy from wd_discord.interactions import ApplicationCommand, ApplicationCommandOption, ApplicationCommandParams
    lazy from wd_discord.snowflake import Snowflake

    lazy from wd_bot.cogs import Cog
    lazy from wd_bot.commands import AppCommand


@dataclass(frozen=True)
class Scope:
    """Where a command is registered: globally (``guild_id=None``) or in one guild."""

    guild_id: Snowflake | None = None

    def __str__(self) -> str:
        """Return ``global`` or ``guild <id>``, for logs and listings."""
        return "global" if self.guild_id is None else f"guild {self.guild_id}"


GLOBAL: Final = Scope()
"""The global scope: commands every guild (and DM) sees."""


@dataclass(frozen=True)
class CommandPath:
    """The full name a user types: ``/root`` or ``/root sub``."""

    root: str
    sub: str | None = None

    def __str__(self) -> str:
        """Return the path as typed, without the slash: ``steam show``."""
        return self.root if self.sub is None else f"{self.root} {self.sub}"


class Placement(Protocol):
    """Decides which scopes a top-level command is registered in."""

    def __call__(self, command: AppCommand, /) -> frozenset[Scope]:
        """Return the scopes ``command`` belongs in."""
        ...


def declared_scopes(command: AppCommand) -> frozenset[Scope]:
    """Place ``command`` in the scopes it declares (global unless it names guilds); the default :class:`Placement`."""
    return command.scopes


@dataclass(frozen=True)
class Entry:
    """A registered top-level command and the cog whose methods handle it."""

    cog: Cog
    command: AppCommand


@dataclass(frozen=True)
class CommandMention:
    """A mention of a command, resolved to its current Discord ID when rendered (``str()`` or an f-string).

    Renders the clickable ``</steam show:id>`` once Discord has reported the command, and a plain
    ``/steam show`` until then.
    """

    registry: CommandRegistry
    path: CommandPath
    guild_id: Snowflake | None = None

    def __str__(self) -> str:
        """Return the mention markup for the command's current ID."""
        command_id = self.registry.command_id(self.path.root, self.guild_id)
        return f"`/{self.path}`" if command_id is None else f"</{self.path}:{command_id}>"


class CommandRegistry(LoggerMixin):
    """The bot's commands per scope, next to what Discord last reported for that scope."""

    def __init__(self, placement: Placement = declared_scopes) -> None:
        """Start empty, placing commands with ``placement``."""
        self.placement = placement
        self._local: dict[Scope, dict[str, Entry]] = {}
        self._remote: dict[Scope, dict[str, ApplicationCommand]] = {}

    def register(self, cog: Cog) -> set[Scope]:
        """Add ``cog``'s top-level commands to the scopes their placement picks; return those scopes.

        A command whose name another cog already registered in a scope replaces it there, with a warning.
        """
        touched: set[Scope] = set()
        for command in cog.app_commands():
            for scope in self.placement(command):
                commands = self._local.setdefault(scope, {})
                if (existing := commands.get(command.name)) is not None and existing.cog is not cog:
                    previous = existing.cog.__cog_name__
                    self.logger.warning(
                        t"Duplicate command '{command.name}' in {scope}: cog '{cog.__cog_name__}' replaces '{previous}'",
                    )
                commands[command.name] = Entry(cog, command)
                touched.add(scope)
        return touched

    def unregister(self, cog: Cog) -> set[Scope]:
        """Remove ``cog``'s commands from every scope; return the scopes that changed."""
        touched: set[Scope] = set()
        for scope, commands in self._local.items():
            for name in [name for name, entry in commands.items() if entry.cog is cog]:
                del commands[name]
                touched.add(scope)
        return touched

    def refresh(self) -> set[Scope]:
        """Place every registered command again, e.g. after :attr:`placement` changed; return the scopes that changed."""
        cogs = {id(entry.cog): entry.cog for commands in self._local.values() for entry in commands.values()}
        before = {scope: dict(commands) for scope, commands in self._local.items()}
        self._local.clear()
        for cog in cogs.values():
            self.register(cog)
        scopes = before.keys() | self._local.keys()
        return {scope for scope in scopes if before.get(scope, {}) != self._local.get(scope, {})}

    def scopes_of(self, cog: Cog) -> set[Scope]:
        """Return the scopes ``cog`` has commands registered in."""
        return {scope for scope, commands in self._local.items() if any(entry.cog is cog for entry in commands.values())}

    def entry(self, name: str, guild_id: Snowflake | None = None) -> Entry | None:
        """Return the command ``name`` an interaction from ``guild_id`` reaches: the guild's own first, then global."""
        if guild_id is not None and (entry := self._local.get(Scope(guild_id), {}).get(name)) is not None:
            return entry
        return self._local.get(GLOBAL, {}).get(name)

    def entries(self, scope: Scope) -> Generator[Entry]:
        """Yield the commands registered in ``scope``, by name."""
        commands = self._local.get(scope, {})
        for name in sorted(commands):
            yield commands[name]

    def commands(self) -> Generator[AppCommand]:
        """Yield every registered top-level command once, whichever scopes it is in."""
        seen: set[int] = set()
        for commands in self._local.values():
            for entry in commands.values():
                if id(entry.command) not in seen:
                    seen.add(id(entry.command))
                    yield entry.command

    def scopes(self) -> set[Scope]:
        """Return every scope that has commands locally or on Discord; a sync covers all of them."""
        return {scope for scope, commands in self._local.items() if commands} | self._remote.keys()

    def params(self, scope: Scope) -> list[ApplicationCommandParams]:
        """Return the definitions ``scope`` should have on Discord, by name."""
        return [entry.command.params() for entry in self.entries(scope)]

    def is_known(self, scope: Scope) -> bool:
        """Whether Discord has reported ``scope``'s commands since startup (or the last :meth:`forget`)."""
        return scope in self._remote

    def apply(self, scope: Scope, commands: Iterable[ApplicationCommand]) -> None:
        """Record ``commands`` as everything Discord has in ``scope`` now."""
        self._remote[scope] = {command.name: command for command in commands}

    def forget(self) -> None:
        """Drop what Discord reported, so the next sync reads every scope from Discord again."""
        self._remote.clear()

    def in_sync(self, scope: Scope) -> bool:
        """Whether Discord's last report for ``scope`` has exactly the commands and definitions the bot wants."""
        remote = self._remote.get(scope)
        if remote is None:
            return False
        local = {params.name: params for params in self.params(scope)}
        return local.keys() == remote.keys() and all(definition_matches(local[name], remote[name]) for name in local)

    def is_synced(self, scope: Scope, name: str) -> bool:
        """Whether the command ``name`` in ``scope`` is on Discord as currently defined."""
        local = self._local.get(scope, {}).get(name)
        remote = self._remote.get(scope, {}).get(name)
        return local is not None and remote is not None and definition_matches(local.command.params(), remote)

    def command_id(self, name: str, guild_id: Snowflake | None = None) -> Snowflake | None:
        """Return the Discord ID of the top-level command ``name``: the guild's own first, then the global one."""
        if guild_id is not None and (command := self._remote.get(Scope(guild_id), {}).get(name)) is not None:
            return command.id
        command = self._remote.get(GLOBAL, {}).get(name)
        return None if command is None else command.id

    def mention(self, path: CommandPath, guild_id: Snowflake | None = None) -> CommandMention:
        """Return a mention of the command at ``path``, as seen from ``guild_id``."""
        return CommandMention(self, path, guild_id)


def definition_matches(local: ApplicationCommandParams, remote: ApplicationCommand) -> bool:
    """Whether Discord's ``remote`` command has the definition ``local`` would register.

    Discord fills in fields a request leaves out, so an unset ``integration_types``, ``contexts`` or ``nsfw``
    matches whatever Discord chose, and an unset ``autocomplete`` matches ``False``.
    """
    # TODO(Herogold): drop this special-casing once params() sends every field  # noqa: FIX002
    # https://github.com/HEROgold/Winter-Dragon-Bot/issues/205
    fetched = remote.to_params()
    filled = local.model_copy(
        update={
            "integration_types": fetched.integration_types if local.integration_types is None else local.integration_types,
            "contexts": fetched.contexts if local.contexts is None else local.contexts,
            "nsfw": fetched.nsfw if local.nsfw is None else local.nsfw,
            "options": _normalized(local.options or []),
        },
    )
    return filled == fetched.model_copy(update={"options": _normalized(fetched.options or [])})


def _normalized(options: Sequence[ApplicationCommandOption]) -> list[ApplicationCommandOption]:
    """Return ``options`` with an unset ``autocomplete`` as ``False``, at every nesting level."""
    return [
        option.model_copy(
            update={
                "autocomplete": bool(option.autocomplete),
                "options": None if option.options is None else _normalized(option.options),
            },
        )
        for option in options
    ]
