"""wd_bot.commands.Command: encapsulates one application command's definition and dispatch."""

from __future__ import annotations

lazy from inspect import Parameter
lazy from inspect import signature as inspect_signature
lazy from typing import TYPE_CHECKING, Self

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
        for param_name, param in inspect_signature(func, eval_str=True).parameters.items():
            if param_name in ("self", "interaction"):
                continue
            if param.annotation not in _OPTION_TYPE_MAP:
                msg = f"Command {name!r}: unsupported option type {param.annotation!r} for parameter {param_name!r}"
                raise TypeError(msg)
            self._param_types[param_name] = param.annotation
            self._param_required[param_name] = param.default is Parameter.empty

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
                user_id = str(option.value)
                kwargs[option.name] = resolved.users.get(user_id) if resolved and resolved.users else None
            else:
                kwargs[option.name] = option.value
        try:
            await self.func(cog, interaction, **kwargs)
        except Exception:
            self.logger.exception("Unhandled exception in command %r", self.name)  # pyright: ignore[reportArgumentType]  # herogold types msg as Template; t-strings render as reprs

    def __get__(self, instance: object, owner: type) -> Self:
        """Allow a Command to be accessed as a plain attribute on a Cog instance without binding it like a method."""
        return self
