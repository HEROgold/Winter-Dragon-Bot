"""Application commands: the shared :class:`AppCommand` base, plain :class:`Command` and :class:`CommandGroup`."""

from __future__ import annotations

lazy import annotationlib
lazy from abc import ABC, abstractmethod
lazy from inspect import Parameter
lazy from inspect import signature as inspect_signature
lazy from types import LazyImportType, NoneType, UnionType
lazy from typing import TYPE_CHECKING, Self, get_args

lazy from herogold.log import LoggerMixin
lazy from wd_discord.interactions import ApplicationCommandOption, ApplicationCommandOptionType, ApplicationCommandParams
lazy from wd_discord.resources.user import User

lazy from wd_bot.signature import command_signature


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator, Iterable, Sequence

    lazy from wd_discord.gateway.events import Interaction, InteractionDataOption
    lazy from wd_discord.interactions import InteractionContextType
    lazy from wd_discord.permissions import Permissions

    lazy from wd_bot.cogs import Cog


_OPTION_TYPE_MAP: dict[type, ApplicationCommandOptionType] = {
    str: ApplicationCommandOptionType.STRING,
    int: ApplicationCommandOptionType.INTEGER,
    bool: ApplicationCommandOptionType.BOOLEAN,
    User: ApplicationCommandOptionType.USER,
}


class AppCommand(LoggerMixin, ABC):
    """What every application command shares: its name, description and where Discord lets it be used.

    Subclasses supply the options, the rest of the signature and the dispatch.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        default_member_permissions: Permissions | None = None,
        contexts: Iterable[InteractionContextType] | None = None,
    ) -> None:
        """Set the definition Discord sees.

        ``default_member_permissions`` is the permission bitfield Discord requires by default to use the
        command; ``contexts`` limits where it shows up (``None`` keeps Discord's default).
        """
        self.name = name
        self.description = description
        self.default_member_permissions = default_member_permissions
        self.contexts = None if contexts is None else list(contexts)

    @abstractmethod
    def options(self) -> Generator[ApplicationCommandOption]:
        """Yield this command's Discord option definitions."""

    @abstractmethod
    def _own_signature(self) -> Generator[str]:
        """Yield the signature parts specific to the subclass."""

    @abstractmethod
    async def invoke(self, cog: Cog, interaction: Interaction) -> bool:
        """Handle ``interaction``; return ``False`` if the handler failed or nothing could be dispatched."""

    def signature(self) -> str:
        """Return the signature of the full registered definition, used to detect drift for sync."""
        permissions = None if self.default_member_permissions is None else int(self.default_member_permissions)
        contexts = None if self.contexts is None else [int(context) for context in self.contexts]
        return " | ".join((self.description, str(permissions), str(contexts), *self._own_signature()))

    def params(self) -> ApplicationCommandParams:
        """Return the create/edit request body for this command."""
        return ApplicationCommandParams(
            name=self.name,
            description=self.description,
            options=list(self.options()),
            default_member_permissions=self.default_member_permissions,
            contexts=self.contexts,
        )


class Command(AppCommand):
    """Encapsulates one chat-input application command: its Discord definition and its handler.

    Built by :meth:`wd_bot.cogs.Cog.command`. ``func``'s parameters (after ``self``/``interaction``)
    define the command's options via their type annotations.
    """

    def __init__(
        self,
        func: Callable[..., Awaitable[None]],
        *,
        name: str,
        description: str,
        default_member_permissions: Permissions | None = None,
        contexts: Iterable[InteractionContextType] | None = None,
    ) -> None:
        """Wrap ``func`` as a command named ``name`` with the given ``description``."""
        super().__init__(
            name=name,
            description=description,
            default_member_permissions=default_member_permissions,
            contexts=contexts,
        )
        self.func = func
        self._param_types: dict[str, type] = {}
        self._param_required: dict[str, bool] = {}
        annotations = annotationlib.get_annotations(func, format=annotationlib.Format.FORWARDREF)
        parameters = inspect_signature(func, annotation_format=annotationlib.Format.STRING).parameters
        for param_name, param in parameters.items():
            if param_name in ("self", "interaction"):
                continue
            annotation: object = self._resolve(annotations.get(param_name, Parameter.empty), func)
            required = param.default is Parameter.empty
            if isinstance(annotation, UnionType) and NoneType in get_args(annotation):
                non_none = [arg for arg in get_args(annotation) if arg is not NoneType]
                annotation = self._reify(non_none[0]) if len(non_none) == 1 else annotation
                required = False
            if not isinstance(annotation, type) or annotation not in _OPTION_TYPE_MAP:
                msg = f"Command {name!r}: unsupported option type {annotation!r} for parameter {param_name!r}"
                raise TypeError(msg)
            self._param_types[param_name] = annotation
            self._param_required[param_name] = required

    @staticmethod
    def _resolve(annotation: object, func: Callable[..., object]) -> object:
        """Resolve a string or forward-ref annotation of ``func`` to a real type, if possible."""
        if isinstance(annotation, str):
            annotation = annotationlib.ForwardRef(annotation, owner=func)
        if isinstance(annotation, annotationlib.ForwardRef):
            annotation = annotation.evaluate()
        return Command._reify(annotation)

    @staticmethod
    def _reify(annotation: object) -> object:
        """Resolve ``annotation`` if it is a not-yet-reified lazy-import proxy."""
        return annotation.resolve() if isinstance(annotation, LazyImportType) else annotation

    def options(self) -> Generator[ApplicationCommandOption]:
        """Yield this command's Discord option definitions, derived from its handler's parameters."""
        for param_name, param_type in self._param_types.items():
            yield ApplicationCommandOption(
                type=_OPTION_TYPE_MAP[param_type],
                name=param_name,
                description=param_name,
                required=self._param_required[param_name],
            )

    def _own_signature(self) -> Generator[str]:
        """Yield the handler's parameter signature."""
        yield command_signature(self.func)

    async def invoke(
        self,
        cog: Cog,
        interaction: Interaction,
        options: Sequence[InteractionDataOption] | None = None,
    ) -> bool:
        """Resolve option values into kwargs and call the wrapped handler.

        ``options`` defaults to ``interaction``'s top-level options; a :class:`CommandGroup` passes the
        chosen subcommand's nested options instead. Returns ``True`` if the handler completed, ``False``
        if it raised (the exception is logged).
        """
        kwargs: dict[str, object] = {}
        data = interaction.data
        if options is None:
            options = data.options if data else []
        resolved = data.resolved if data else None
        for option in options:
            if option.name not in self._param_types:
                self.logger.warning(t"Unknown option '{option.name}' for command '{self.name}', skipping it")
                continue
            if self._param_types[option.name] is User:
                user = resolved.users.get(str(option.value)) if resolved and resolved.users else None
                if user is None:
                    self.logger.warning(t"Unresolved user '{option.value}' for option '{option.name}' in command '{self.name}'")
                    continue
                kwargs[option.name] = user
            else:
                kwargs[option.name] = option.value
        try:
            await self.func(cog, interaction, **kwargs)
        except Exception:
            self.logger.exception(t"Unhandled exception in command '{self.name}'")
            return False
        return True

    def __get__(self, instance: object, owner: type) -> Self:
        """Allow a Command to be accessed as a plain attribute on a Cog instance without binding it like a method."""
        return self


class CommandGroup(AppCommand):
    """A chat-input command whose options are subcommands, built from a :class:`~wd_bot.cogs.GroupCog`.

    Discord registers the group as one command (``/name sub ...``), so the group is what gets synced
    and dispatched. Only the group carries ``default_member_permissions`` and ``contexts``; Discord has
    neither per subcommand.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        subcommands: Iterable[Command],
        default_member_permissions: Permissions | None = None,
        contexts: Iterable[InteractionContextType] | None = None,
    ) -> None:
        """Group ``subcommands`` under the command ``name``."""
        super().__init__(
            name=name,
            description=description,
            default_member_permissions=default_member_permissions,
            contexts=contexts,
        )
        self.subcommands = {subcommand.name: subcommand for subcommand in subcommands}
        for subcommand in self.subcommands.values():
            if subcommand.default_member_permissions is not None or subcommand.contexts is not None:
                self.logger.warning(
                    t"Subcommand '{name} {subcommand.name}' sets default_member_permissions or contexts; Discord ignores them",
                )

    def options(self) -> Generator[ApplicationCommandOption]:
        """Yield one SUB_COMMAND option per subcommand, nesting that subcommand's own options."""
        for subcommand in self.subcommands.values():
            yield ApplicationCommandOption(
                type=ApplicationCommandOptionType.SUB_COMMAND,
                name=subcommand.name,
                description=subcommand.description,
                options=list(subcommand.options()) or None,
            )

    def _own_signature(self) -> Generator[str]:
        """Yield each subcommand's signature, in name order."""
        for name in sorted(self.subcommands):
            yield f"{name}: {self.subcommands[name].signature()}"

    async def invoke(self, cog: Cog, interaction: Interaction) -> bool:
        """Route ``interaction`` to the chosen subcommand, passing it that subcommand's option values.

        Returns ``False`` (after logging) if no known subcommand was chosen.
        """
        options = interaction.data.options if interaction.data else []
        chosen = next((option for option in options if option.type == ApplicationCommandOptionType.SUB_COMMAND), None)
        subcommand = self.subcommands.get(chosen.name) if chosen else None
        if chosen is None or subcommand is None:
            self.logger.warning(t"No known subcommand chosen for command group '{self.name}'")
            return False
        return await subcommand.invoke(cog, interaction, chosen.options or [])
