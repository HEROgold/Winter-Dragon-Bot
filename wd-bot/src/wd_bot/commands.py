"""wd_bot.commands.Command: encapsulates one application command's definition and dispatch."""

from __future__ import annotations

lazy import annotationlib
lazy from inspect import Parameter
lazy from inspect import signature as inspect_signature
lazy from types import LazyImportType, NoneType, UnionType
lazy from typing import TYPE_CHECKING, Self, get_args

lazy from herogold.log import LoggerMixin
lazy from wd_discord.interactions import ApplicationCommandOptionType, CommandOption
lazy from wd_discord.resources.user import User

lazy from wd_bot.signature import command_signature


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator

    lazy from wd_discord.gateway.events import Interaction

    lazy from wd_bot.cogs import Cog


_OPTION_TYPE_MAP: dict[type, ApplicationCommandOptionType] = {
    str: ApplicationCommandOptionType.STRING,
    int: ApplicationCommandOptionType.INTEGER,
    bool: ApplicationCommandOptionType.BOOLEAN,
    User: ApplicationCommandOptionType.USER,
}


class Command(LoggerMixin):
    """Encapsulates one chat-input application command: its Discord definition and its handler.

    Built by :meth:`wd_bot.cogs.Cog.command`. ``func``'s parameters (after ``self``/``interaction``)
    define the command's options via their type annotations.
    """

    def __init__(self, func: Callable[..., Awaitable[None]], *, name: str, description: str) -> None:
        """Wrap ``func`` as a command named ``name`` with the given ``description``."""
        self.func = func
        self.name = name
        self.description = description
        self._param_types: dict[str, type] = {}
        self._param_required: dict[str, bool] = {}
        annotations = annotationlib.get_annotations(func, format=annotationlib.Format.FORWARDREF)
        for param_name, param in inspect_signature(func).parameters.items():
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

    def options(self) -> Generator[CommandOption]:
        """Yield this command's Discord option definitions, derived from its handler's parameters."""
        for param_name, param_type in self._param_types.items():
            yield CommandOption(
                type=_OPTION_TYPE_MAP[param_type],
                name=param_name,
                description=param_name,
                required=self._param_required[param_name],
            )

    def signature(self) -> str:
        """Return this command's current signature, used to detect definition drift for sync."""
        return command_signature(self.func)

    async def invoke(self, cog: Cog, interaction: Interaction) -> None:
        """Resolve ``interaction``'s option values into kwargs and call the wrapped handler."""
        kwargs: dict[str, object] = {}
        data = interaction.data
        options = data.options if data else []
        resolved = data.resolved if data else None
        for option in options:
            if self._param_types.get(option.name) is User:
                user = resolved.users.get(str(option.value)) if resolved and resolved.users else None
                if user is None:
                    self.logger.warning("Unresolved user %r for option %r in command %r", option.value, option.name, self.name)  # pyright: ignore[reportArgumentType]
                    continue
                kwargs[option.name] = user
            else:
                kwargs[option.name] = option.value
        try:
            await self.func(cog, interaction, **kwargs)
        except Exception:
            self.logger.exception("Unhandled exception in command %r", self.name)  # pyright: ignore[reportArgumentType]  # herogold types msg as Template; t-strings render as reprs

    def __get__(self, instance: object, owner: type) -> Self:
        """Allow a Command to be accessed as a plain attribute on a Cog instance without binding it like a method."""
        return self
