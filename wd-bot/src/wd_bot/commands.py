"""Application commands: the shared :class:`AppCommand` base, plain :class:`Command` and :class:`CommandGroup`."""

from dataclasses import dataclass
lazy import annotationlib
lazy import operator
lazy from abc import ABC, abstractmethod
lazy from functools import reduce
lazy from inspect import Parameter
lazy from inspect import signature as inspect_signature
lazy from itertools import islice
lazy from string.templatelib import Template
lazy from types import LazyImportType, NoneType, UnionType
lazy from typing import TYPE_CHECKING, Annotated, Self, get_args, get_origin

lazy from herogold.log import LoggerMixin
lazy from wd_discord import Channel, Role, User
lazy from wd_discord.authenticate import render
lazy from wd_discord.entities import Resolved
lazy from wd_discord.interactions import (
    MAX_CHOICES,
    MAX_DESCRIPTION_LENGTH,
    ApplicationCommandOption,
    ApplicationCommandOptionType,
    ApplicationCommandParams,
    InteractionContextType,
)
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.guild import Role as RoleModel
lazy from wd_discord.resources.user import User as UserModel
lazy from wd_discord.snowflake import Snowflake
lazy from wd_errors import Refused

lazy from wd_bot.checks import answer_refusal, require_guild, require_permissions
lazy from wd_bot.cogs import Cog
lazy from wd_bot.registry import GLOBAL, Scope
lazy from wd_bot.signature import command_signature


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator, Iterable, Sequence

    lazy from wd_discord import AutocompleteInteraction, CommandInteraction
    lazy from wd_discord.gateway.events import InteractionDataOption
    lazy from wd_discord.interactions import ApplicationCommandOptionChoice
    lazy from wd_discord.permissions import ChannelType, Permissions
    lazy from wd_discord.snowflake import SnowflakeLike


_OPTION_TYPE_MAP: dict[type, ApplicationCommandOptionType] = {
    str: ApplicationCommandOptionType.STRING,
    int: ApplicationCommandOptionType.INTEGER,
    float: ApplicationCommandOptionType.NUMBER,
    bool: ApplicationCommandOptionType.BOOLEAN,
    User: ApplicationCommandOptionType.USER,
    UserModel: ApplicationCommandOptionType.USER,
    Channel: ApplicationCommandOptionType.CHANNEL,
    ChannelModel: ApplicationCommandOptionType.CHANNEL,
    Role: ApplicationCommandOptionType.ROLE,
    RoleModel: ApplicationCommandOptionType.ROLE,
}
_MENTIONABLES = frozenset(frozenset({user, role}) for user in (User, UserModel) for role in (Role, RoleModel))
"""The unions a parameter is annotated with to take a MENTIONABLE option: a user or a role, entity or model."""


class ChannelTypes:
    """Limit a channel option to some kinds of channel: ``category: Annotated[Channel, ChannelTypes(GUILD_CATEGORY)]``."""

    __slots__ = ("types",)

    def __init__(self, *types: ChannelType) -> None:
        """Only let channels of ``types`` be picked."""
        self.types = list(types)


class Describe:
    """Give an option the description Discord shows under it: ``reason: Annotated[str, Describe("Why")]``.

    ``text`` is a plain string or a t-string; a t-string's interpolations take their values when wd-bot reads the
    handler's annotations, so ``Describe(t"At most {MAX_ITEMS}")`` names the constant instead of repeating it. Raises
    ``ValueError`` unless the rendered text is 1 to 100 characters, Discord's limit.
    """

    __slots__ = ("template", "text")

    def __init__(self, text: str | Template) -> None:
        """Describe the option with ``text``."""
        self.template = text if isinstance(text, Template) else None
        """The t-string ``text`` was given as, kept for its literal parts; ``None`` for a plain string."""
        self.text = text if isinstance(text, str) else render(text)
        """The description Discord shows."""
        if not 1 <= len(self.text) <= MAX_DESCRIPTION_LENGTH:
            msg = f"Option description {self.text!r} must be 1 to {MAX_DESCRIPTION_LENGTH} characters"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class OptionSpec:
    """A handler parameter as a Discord option: what Discord asks for, and what the handler gets."""

    name: str
    param_type: object
    """The handler's type for it: a ``_OPTION_TYPE_MAP`` key, or a mentionable union."""
    option_type: ApplicationCommandOptionType
    required: bool
    channel_types: list[ChannelType] | None = None
    """The kinds of channel a channel option may name; ``None`` allows any."""
    description: str | None = None
    """The text from the parameter's :class:`Describe`; ``None`` shows the parameter name instead."""

    def definition(self, *, autocomplete: bool) -> ApplicationCommandOption:
        """Return the option as Discord defines it."""
        return ApplicationCommandOption(
            type=self.option_type,
            name=self.name,
            description=self.description or self.name,
            required=self.required,
            channel_types=self.channel_types,
            autocomplete=True if autocomplete else None,
        )

    def argument(self, interaction: CommandInteraction, value: object) -> object:
        """Return the handler argument for the submitted ``value``; ``None`` when the object it names wasn't sent along.

        A parameter annotated with a bound entity gets one bound to the interaction's client; one annotated with the
        data model gets the model.
        """
        resolvers = _RESOLVERS.get(self.option_type)
        if resolvers is not None:
            resolved = interaction.resolved
            found = None if resolved is None else next(filter(None, (find(resolved, str(value)) for find in resolvers)), None)
            if found is None or type(found) in (get_args(self.param_type) or (self.param_type,)):
                return found
            return found.model
        if self.param_type is float and isinstance(value, int):
            return float(value)  # Discord sends a whole NUMBER as an integer
        return value


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
        guild_ids: Iterable[SnowflakeLike] | None = None,
    ) -> None:
        """Set the definition Discord sees.

        ``default_member_permissions`` is the permission bitfield Discord requires by default to use the
        command; ``contexts`` limits where it shows up (``None`` keeps Discord's default). ``guild_ids``
        registers the command in just those guilds instead of globally.
        """
        self.name = name
        self.description = description
        self.default_member_permissions = default_member_permissions
        self.contexts = None if contexts is None else list(contexts)
        self.guild_only = self.contexts == [InteractionContextType.GUILD]
        """Whether Discord offers the command in guilds only, so its handler gets a guild interaction."""
        self.scopes: frozenset[Scope] = (
            frozenset({GLOBAL}) if guild_ids is None else frozenset(Scope(Snowflake.coerce(guild)) for guild in guild_ids)
        )
        """The scopes this command declares it is registered in; a :class:`~wd_bot.registry.Placement` may differ."""

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
        # TODO(Herogold): send every field Discord would otherwise default, so a fetched command  # noqa: FIX002
        # https://github.com/HEROgold/Winter-Dragon-Bot/issues/205
        # compares equal to ``params()`` without the special-casing in ``registry.definition_matches``.
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

    def __init__(  # noqa: PLR0913 - each keyword is part of the command's Discord definition
        self,
        func: Callable[..., Awaitable[None]],
        *,
        name: str,
        description: str,
        default_member_permissions: Permissions | None = None,
        contexts: Iterable[InteractionContextType] | None = None,
        guild_ids: Iterable[SnowflakeLike] | None = None,
        requires: Permissions | None = None,
    ) -> None:
        """Wrap ``func`` as a command named ``name`` with the given ``description``.

        ``requires`` is checked by wd-bot before ``func`` runs; unlike ``default_member_permissions`` it works on a
        subcommand too.
        """
        super().__init__(
            name=name,
            description=description,
            default_member_permissions=default_member_permissions,
            contexts=contexts,
            guild_ids=guild_ids,
        )
        self.func = func
        self.requires = requires
        self.wants_guild = wants_guild_interaction(func)
        """Whether the handler's ``interaction`` is annotated as a guild interaction; it must then be guild-only."""
        self.owner: type[Cog] | None = None
        """The cog class this command was defined on; set when that class is created."""
        self._autocompletes: dict[str, AutocompleteHandler] = {}
        annotations = annotationlib.get_annotations(func, format=annotationlib.Format.FORWARDREF)
        parameters = inspect_signature(func, annotation_format=annotationlib.Format.STRING).parameters
        self._options = {
            name: self._option_of(param, annotations.get(name, Parameter.empty))
            for name, param in parameters.items()
            if name not in ("self", "interaction")
        }
        """The handler's parameters as Discord options, by name."""

    def _option_of(self, param: Parameter, annotation: object) -> OptionSpec:
        """Return handler parameter ``param`` as an option: its type, metadata, and whether it's required.

        A default value or a ``T | None`` annotation makes the option optional. ``Annotated`` metadata, inside or
        outside the ``| None``, configures it: :class:`ChannelTypes` limits a channel option and :class:`Describe`
        sets its description. ``User | Role`` takes a MENTIONABLE. Raises ``TypeError`` if the type has no Discord
        option type or the metadata doesn't fit it.
        """
        param_type, metadata = self._unwrap(self._resolve(annotation, self.func))
        required = param.default is Parameter.empty
        if isinstance(param_type, UnionType) and NoneType in get_args(param_type):
            non_none = [self._reify(arg) for arg in get_args(param_type) if arg is not NoneType]
            param_type, inner = self._unwrap(non_none[0] if len(non_none) == 1 else _union(non_none))
            metadata += inner
            required = False
        channel_types = [kind for item in metadata if isinstance(item, ChannelTypes) for kind in item.types]
        descriptions = [item.text for item in metadata if isinstance(item, Describe)]
        if len(descriptions) > 1:
            msg = f"Command {self.name!r}: parameter {param.name!r} has more than one Describe"
            raise TypeError(msg)
        if isinstance(param_type, UnionType) and frozenset(map(self._reify, get_args(param_type))) in _MENTIONABLES:
            option_type = ApplicationCommandOptionType.MENTIONABLE
        elif isinstance(param_type, type) and param_type in _OPTION_TYPE_MAP:
            option_type = _OPTION_TYPE_MAP[param_type]
        else:
            msg = f"Command {self.name!r}: unsupported option type {param_type!r} for parameter {param.name!r}"
            raise TypeError(msg)
        if channel_types and option_type is not ApplicationCommandOptionType.CHANNEL:
            msg = f"Command {self.name!r}: ChannelTypes only applies to a channel parameter, not {param.name!r}"
            raise TypeError(msg)
        return OptionSpec(
            param.name,
            param_type,
            option_type,
            required,
            channel_types or None,
            next(iter(descriptions), None),
        )

    @staticmethod
    def _unwrap(annotation: object) -> tuple[object, list[object]]:
        """Split ``Annotated[T, *metadata]`` into ``T`` and its metadata; any other annotation has none."""
        if get_origin(annotation) is not Annotated:
            return annotation, []
        param_type, *metadata = get_args(annotation)
        return Command._reify(param_type), metadata

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
        for name, option in self._options.items():
            yield option.definition(autocomplete=name in self._autocompletes)

    def _own_signature(self) -> Generator[str]:
        """Yield the handler's parameter signature, then its option descriptions and autocompletes when it has any.

        The descriptions are rendered: the signature only holds an annotation's source, which doesn't change when a
        constant a ``Describe`` names does.
        """
        yield command_signature(self.func)
        if descriptions := {name: spec.description for name, spec in self._options.items() if spec.description}:
            yield f"descriptions: {descriptions}"
        if self._autocompletes:
            yield f"autocomplete: {sorted(self._autocompletes)}"

    def autocomplete(self, option: str) -> Callable[[AutocompleteHandler], AutocompleteHandler]:
        """Tag a Cog method as the handler suggesting values for this command's ``option`` while it's typed.

        The handler gets the interaction and the text typed so far, and returns the choices to suggest; Discord
        shows at most the first :data:`~wd_discord.interactions.MAX_CHOICES`. Only STRING, INTEGER and NUMBER
        options autocomplete. Use it right below the command, like ``@remove.autocomplete("reminder")``.
        """
        spec = self._options.get(option)
        if spec is None or spec.param_type not in (str, int, float):
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
            if self.guild_only or (self.owner is not None and self.owner.guild_only()):
                interaction = require_guild(interaction)
            if self.requires is not None:
                require_permissions(interaction, self.requires)
            await self.func(cog, interaction, **kwargs)
        except Refused as refused:
            self.logger.debug(t"Command '{self.name}' refused: {refused.message} ({refused.cause})")
            await answer_refusal(interaction, refused)
        except Exception:
            self.logger.exception(t"Unhandled exception in command '{self.name}' (interaction {interaction.id})")
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
        """Map each submitted option to a handler argument, resolving user, channel, role and mentionable options.

        Options the handler doesn't declare, and objects missing from the interaction's resolved data, are skipped with
        a warning.
        """
        kwargs: dict[str, object] = {}
        for option in options:
            spec = self._options.get(option.name)
            if spec is None:
                self.logger.warning(t"Unknown option '{option.name}' for command '{self.name}', skipping it")
                continue
            value = spec.argument(interaction, option.value)
            if value is None:
                self.logger.warning(t"Unresolved '{option.value}' for option '{option.name}' in command '{self.name}'")
                continue
            kwargs[option.name] = value
        return kwargs

    def __get__(self, instance: object, owner: type) -> Self:
        """Allow a Command to be accessed as a plain attribute on a Cog instance without binding it like a method."""
        return self

    def __set_name__(self, owner: type, name: str) -> None:
        """Remember the cog class this command is defined on, so a mention from any cog can find its path."""
        if issubclass(owner, Cog):
            self.owner = owner


GUILD_INTERACTIONS = frozenset({"GuildCommandInteraction", "GuildComponentInteraction"})


def wants_guild_interaction(func: Callable[..., object]) -> bool:
    """Whether ``func``'s ``interaction`` parameter is annotated as a guild interaction.

    Reads the annotation's name: cogs import interaction types for type checking only, so it often can't be resolved.
    """
    parameters = inspect_signature(func, annotation_format=annotationlib.Format.STRING).parameters
    annotation = parameters["interaction"].annotation if "interaction" in parameters else Parameter.empty
    return isinstance(annotation, str) and annotation.rpartition(".")[2] in GUILD_INTERACTIONS


def _union(types: Iterable[object]) -> object:
    """Return the union of ``types``, as ``A | B`` would."""
    return reduce(operator.or_, types)


type _Resolver = Callable[[Resolved, str], User | Role | Channel | None]

_RESOLVERS: dict[ApplicationCommandOptionType, tuple[_Resolver, ...]] = {
    ApplicationCommandOptionType.USER: (Resolved.user,),
    ApplicationCommandOptionType.ROLE: (Resolved.role,),
    ApplicationCommandOptionType.MENTIONABLE: (Resolved.user, Resolved.role),
    ApplicationCommandOptionType.CHANNEL: (Resolved.channel,),
}
"""How to find the object an ID option names in the interaction's resolved data, tried in order."""


class CommandGroup(AppCommand):
    """A chat-input command whose options are subcommands, built from a :class:`~wd_bot.cogs.GroupCog`.

    Discord registers the group as one command (``/name sub ...``), so the group is what gets synced
    and dispatched. Only the group carries ``default_member_permissions`` and ``contexts``; Discord has
    neither per subcommand.
    """

    def __init__(  # noqa: PLR0913 - each keyword is part of the group's Discord definition
        self,
        *,
        name: str,
        description: str,
        subcommands: Iterable[Command],
        default_member_permissions: Permissions | None = None,
        contexts: Iterable[InteractionContextType] | None = None,
        guild_ids: Iterable[SnowflakeLike] | None = None,
    ) -> None:
        """Group ``subcommands`` under the command ``name``."""
        super().__init__(
            name=name,
            description=description,
            default_member_permissions=default_member_permissions,
            contexts=contexts,
            guild_ids=guild_ids,
        )
        self.subcommands = {subcommand.name: subcommand for subcommand in subcommands}
        for subcommand in self.subcommands.values():
            if subcommand.default_member_permissions is not None or subcommand.contexts is not None:
                self.logger.warning(
                    t"Subcommand '{name} {subcommand.name}' sets default_member_permissions or contexts; Discord ignores them",
                )
            if subcommand.scopes != {GLOBAL}:
                self.logger.warning(t"Subcommand '{name} {subcommand.name}' sets guild_ids; the group's scopes apply")

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
