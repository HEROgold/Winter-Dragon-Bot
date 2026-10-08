"""Application commands: the shared :class:`AppCommand` base, plain :class:`Command` and :class:`CommandGroup`."""

from __future__ import annotations

lazy import annotationlib
lazy from abc import ABC, abstractmethod
lazy from inspect import Parameter
lazy from inspect import signature as inspect_signature
lazy from itertools import islice
lazy from types import LazyImportType, NoneType, UnionType
lazy from typing import TYPE_CHECKING, Self, get_args

lazy from herogold.log import LoggerMixin
lazy from wd_discord import User
lazy from wd_discord.interactions import (
    MAX_CHOICES,
    ApplicationCommandOption,
    ApplicationCommandOptionType,
    ApplicationCommandParams,
)
lazy from wd_discord.resources.user import User as UserModel

lazy from wd_bot.signature import command_signature


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator, Iterable, Sequence

    lazy from wd_discord import AutocompleteInteraction, CommandInteraction
    lazy from wd_discord.gateway.events import InteractionDataOption
    lazy from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType
    lazy from wd_discord.permissions import Permissions

    lazy from wd_bot.cogs import Cog


_OPTION_TYPE_MAP: dict[type, ApplicationCommandOptionType] = {
    str: ApplicationCommandOptionType.STRING,
    int: ApplicationCommandOptionType.INTEGER,
    float: ApplicationCommandOptionType.NUMBER,
    bool: ApplicationCommandOptionType.BOOLEAN,
    User: ApplicationCommandOptionType.USER,
    UserModel: ApplicationCommandOptionType.USER,
}


type AutocompleteHandler = Callable[..., Awaitable[Iterable[ApplicationCommandOptionChoice]]]
"""A cog method suggesting values for an option: ``(self, interaction, current) -> choices``."""


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
    async def invoke(self, cog: Cog, interaction: CommandInteraction) -> bool:
        """Handle ``interaction``; return ``False`` if the handler failed or nothing could be dispatched."""

    @abstractmethod
    async def complete(self, cog: Cog, interaction: AutocompleteInteraction) -> bool:
        """Suggest values for the option being typed; return ``False`` if the handler failed or none was found."""

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
        self._autocompletes: dict[str, AutocompleteHandler] = {}
        self._param_types: dict[str, type] = {}
        self._param_required: dict[str, bool] = {}
        annotations = annotationlib.get_annotations(func, format=annotationlib.Format.FORWARDREF)
        parameters = inspect_signature(func, annotation_format=annotationlib.Format.STRING).parameters
        for param_name, param in parameters.items():
            if param_name in ("self", "interaction"):
                continue
            option_type, required = self._parse_parameter(param, annotations.get(param_name, Parameter.empty))
            self._param_types[param_name] = option_type
            self._param_required[param_name] = required

    def _parse_parameter(self, param: Parameter, annotation: object) -> tuple[type, bool]:
        """Return the option type for handler parameter ``param`` and whether the option is required.

        A default value or a ``T | None`` annotation makes the option optional. Raises ``TypeError`` if
        the type has no Discord option type.
        """
        option_type = self._resolve(annotation, self.func)
        required = param.default is Parameter.empty
        if isinstance(option_type, UnionType) and NoneType in get_args(option_type):
            non_none = [arg for arg in get_args(option_type) if arg is not NoneType]
            option_type = self._reify(non_none[0]) if len(non_none) == 1 else option_type
            required = False
        if not isinstance(option_type, type) or option_type not in _OPTION_TYPE_MAP:
            msg = f"Command {self.name!r}: unsupported option type {option_type!r} for parameter {param.name!r}"
            raise TypeError(msg)
        return option_type, required

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
                autocomplete=True if param_name in self._autocompletes else None,
            )

    def _own_signature(self) -> Generator[str]:
        """Yield the handler's parameter signature, and which options autocomplete when any do."""
        yield command_signature(self.func)
        if self._autocompletes:
            yield f"autocomplete: {sorted(self._autocompletes)}"

    def autocomplete(self, option: str) -> Callable[[AutocompleteHandler], AutocompleteHandler]:
        """Tag a Cog method as the handler suggesting values for this command's ``option`` while it's typed.

        The handler gets the interaction and the text typed so far, and returns the choices to suggest; Discord
        shows at most the first :data:`~wd_discord.interactions.MAX_CHOICES`. Only STRING, INTEGER and NUMBER
        options autocomplete. Use it right below the command, like ``@remove.autocomplete("reminder")``.
        """
        if self._param_types.get(option) not in (str, int, float):
            msg = f"Command {self.name!r}: option {option!r} isn't a str, int or float parameter, so it can't autocomplete"
            raise TypeError(msg)

        def decorator(func: AutocompleteHandler) -> AutocompleteHandler:
            self._autocompletes[option] = func
            return func

        return decorator

    async def invoke(
        self,
        cog: Cog,
        interaction: CommandInteraction,
        options: Sequence[InteractionDataOption] | None = None,
    ) -> bool:
        """Resolve option values into kwargs and call the wrapped handler.

        ``options`` defaults to ``interaction``'s top-level options; a :class:`CommandGroup` passes the
        chosen subcommand's nested options instead. Returns ``True`` if the handler completed, ``False``
        if it raised (the exception is logged).
        """
        if options is None:
            options = interaction.options
        kwargs = self._build_kwargs(interaction, options)
        try:
            await self.func(cog, interaction, **kwargs)
        except Exception:
            self.logger.exception(t"Unhandled exception in command '{self.name}'")
            return False
        return True

    async def complete(
        self,
        cog: Cog,
        interaction: AutocompleteInteraction,
        options: Sequence[InteractionDataOption] | None = None,
    ) -> bool:
        """Answer ``interaction`` with the focused option's suggestions.

        ``options`` defaults to ``interaction``'s top-level options, like :meth:`invoke`. Returns ``False`` (after
        logging) when no handler is registered for the focused option, or the handler raised.
        """
        if options is None:
            options = interaction.options
        focused = next((option for option in options if option.focused), None)
        handler = self._autocompletes.get(focused.name) if focused else None
        if focused is None or handler is None:
            self.logger.warning(t"No autocomplete handler for the focused option of command '{self.name}'")
            return False
        current = "" if focused.value is None else str(focused.value)
        try:
            choices = list(islice(await handler(cog, interaction, current), MAX_CHOICES))
        except Exception:
            self.logger.exception(t"Unhandled exception autocompleting '{focused.name}' of command '{self.name}'")
            return False
        await interaction.suggest(choices)
        return True

    def _build_kwargs(self, interaction: CommandInteraction, options: Sequence[InteractionDataOption]) -> dict[str, object]:
        """Map each submitted option to a handler argument, resolving USER options to users.

        A parameter annotated with the bound :class:`wd_discord.User` gets one bound to the interaction's client; one
        annotated with the data model gets the model. Options the handler doesn't declare, and users missing from the
        interaction's resolved data, are skipped with a warning.
        """
        resolved = interaction.resolved
        kwargs: dict[str, object] = {}
        for option in options:
            param_type = self._param_types.get(option.name)
            if param_type is None:
                self.logger.warning(t"Unknown option '{option.name}' for command '{self.name}', skipping it")
                continue
            if param_type is User or param_type is UserModel:
                user = resolved.users.get(str(option.value)) if resolved and resolved.users else None
                if user is None:
                    self.logger.warning(t"Unresolved user '{option.value}' for option '{option.name}' in command '{self.name}'")
                    continue
                kwargs[option.name] = User(interaction.client, user) if param_type is User else user
            elif param_type is float and isinstance(option.value, int):
                kwargs[option.name] = float(option.value)  # Discord sends a whole NUMBER as an integer
            else:
                kwargs[option.name] = option.value
        return kwargs

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

    def _chosen(self, options: Sequence[InteractionDataOption]) -> tuple[Command, Sequence[InteractionDataOption]] | None:
        """Return the chosen subcommand and its own option values, or ``None`` (after logging) if none is known."""
        chosen = next((option for option in options if option.type == ApplicationCommandOptionType.SUB_COMMAND), None)
        subcommand = self.subcommands.get(chosen.name) if chosen else None
        if chosen is None or subcommand is None:
            self.logger.warning(t"No known subcommand chosen for command group '{self.name}'")
            return None
        return subcommand, chosen.options or []

    async def invoke(self, cog: Cog, interaction: CommandInteraction) -> bool:
        """Route ``interaction`` to the chosen subcommand, passing it that subcommand's option values.

        Returns ``False`` (after logging) if no known subcommand was chosen.
        """
        if (chosen := self._chosen(interaction.options)) is None:
            return False
        subcommand, options = chosen
        return await subcommand.invoke(cog, interaction, options)

    async def complete(self, cog: Cog, interaction: AutocompleteInteraction) -> bool:
        """Route ``interaction`` to the chosen subcommand's autocomplete, like :meth:`invoke`."""
        if (chosen := self._chosen(interaction.options)) is None:
            return False
        subcommand, options = chosen
        return await subcommand.complete(cog, interaction, options)
