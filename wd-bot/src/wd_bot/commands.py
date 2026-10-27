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
lazy from typing import TYPE_CHECKING, Annotated, Self, TypedDict, Unpack, get_args, get_origin

lazy from herogold.log import LoggerMixin
lazy from sqlmodel import Session
lazy from wd_db.extension.lifecycle import LifecycleModel, find_by_key, row_key
lazy from wd_discord import Channel, Role, User
lazy from wd_discord.authenticate import render
lazy from wd_discord.entities import InGuild, Resolved
lazy from wd_discord.interactions import (
    ApplicationCommandOption,
    ApplicationCommandOptionChoice,
    ApplicationCommandOptionType,
    ApplicationCommandParams,
    InteractionContextType,
)
lazy from wd_discord.limits import (
    MAX_CHOICE_NAME_LENGTH,
    MAX_CHOICES,
    MAX_DESCRIPTION_LENGTH,
    MAX_OPTION_VALUE_LENGTH,
    truncate,
)
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.guild import Role as RoleModel
lazy from wd_discord.resources.user import User as UserModel
lazy from wd_discord.snowflake import Snowflake
lazy from wd_errors import Refused

lazy from wd_bot.checks import require_guild, require_permissions
lazy from wd_bot.cogs import Cog
lazy from wd_bot.guard import dispatch_guard, error_embed
lazy from wd_bot.registry import GLOBAL, Scope
lazy from wd_bot.signature import command_signature


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator, Iterable, Sequence

    lazy from wd_discord import AutocompleteInteraction, CommandInteraction
    lazy from wd_discord.gateway.events import InteractionDataOption
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


class Length:
    """Limit a string option's length: ``name: Annotated[str, Length(min_length=2, max_length=32)]``.

    Discord enforces it before the command reaches the handler. Raises ``ValueError`` unless at least one limit is
    given, ``min_length`` is 0 to 6000, ``max_length`` is 1 to 6000
    (:data:`~wd_discord.limits.MAX_OPTION_VALUE_LENGTH`), and ``min_length`` is not above ``max_length``.
    """

    __slots__ = ("max_length", "min_length")

    def __init__(self, *, min_length: int | None = None, max_length: int | None = None) -> None:
        """Allow values of ``min_length`` to ``max_length`` characters; ``None`` leaves that end open."""
        if min_length is None and max_length is None:
            msg = "Length needs a min_length, a max_length, or both"
            raise ValueError(msg)
        if min_length is not None and not 0 <= min_length <= MAX_OPTION_VALUE_LENGTH:
            msg = f"Length min_length {min_length} must be 0 to {MAX_OPTION_VALUE_LENGTH}"
            raise ValueError(msg)
        if max_length is not None and not 1 <= max_length <= MAX_OPTION_VALUE_LENGTH:
            msg = f"Length max_length {max_length} must be 1 to {MAX_OPTION_VALUE_LENGTH}"
            raise ValueError(msg)
        if min_length is not None and max_length is not None and min_length > max_length:
            msg = f"Length min_length {min_length} is above its max_length {max_length}"
            raise ValueError(msg)
        self.min_length = min_length
        self.max_length = max_length

    def __repr__(self) -> str:
        """Show the limits, so a command's signature changes when they do."""
        return f"Length(min_length={self.min_length!r}, max_length={self.max_length!r})"


class Range:
    """Limit an ``int`` or ``float`` option's value: ``count: Annotated[int, Range(min_value=1, max_value=10)]``.

    Discord enforces both bounds, inclusive, before the command reaches the handler. On an ``int`` parameter the
    bounds must be ints. Raises ``ValueError`` unless at least one bound is given and ``min_value`` is not above
    ``max_value``.
    """

    __slots__ = ("max_value", "min_value")

    def __init__(self, *, min_value: float | None = None, max_value: float | None = None) -> None:
        """Allow values from ``min_value`` to ``max_value``; ``None`` leaves that end open."""
        if min_value is None and max_value is None:
            msg = "Range needs a min_value, a max_value, or both"
            raise ValueError(msg)
        if min_value is not None and max_value is not None and min_value > max_value:
            msg = f"Range min_value {min_value} is above its max_value {max_value}"
            raise ValueError(msg)
        self.min_value = min_value
        self.max_value = max_value

    def __repr__(self) -> str:
        """Show the bounds, so a command's signature changes when they do."""
        return f"Range(min_value={self.min_value!r}, max_value={self.max_value!r})"


class Lookup:
    """Suggest an option's values while it's typed: ``name: Annotated[str, Lookup(pet_names)]``.

    The only way to autocomplete an option. ``choices`` is the cog method that suggests values, an
    :data:`AutocompleteHandler`; define it above the command, so type checkers can resolve the name. Discord shows at
    most the first :data:`~wd_discord.limits.MAX_CHOICES`.

    On a ``str``, ``int`` or ``float`` parameter the handler gets the submitted value. On a
    :class:`~wd_db.extension.lifecycle.LifecycleModel` table class, or a union of them, the option is a STRING that
    picks a stored row: build each suggestion with :meth:`choice`, and the handler gets the alive row, detached from
    the session that loaded it (a handler that writes adds it to its own session). A value that doesn't parse, names
    a table outside the annotation, or names a row that is gone or soft-deleted is refused. Lookup only loads by ID,
    so ownership and scope checks (whose row it is, which guild it belongs to) stay in the handler.
    """

    __slots__ = ("choices",)

    def __init__(self, choices: AutocompleteHandler) -> None:
        """Suggest rows with the cog method ``choices``."""
        self.choices = choices

    @staticmethod
    def choice(row: LifecycleModel, name: str) -> ApplicationCommandOptionChoice:
        """Return the suggestion that picks ``row``, shown as ``name`` cut to Discord's length limit."""
        return ApplicationCommandOptionChoice(
            name=truncate(name, MAX_CHOICE_NAME_LENGTH),
            value=row_key(row),
        )

    def load(self, cog: Cog, models: tuple[type[LifecycleModel], ...], option: str, value: object) -> LifecycleModel:
        """Return the alive row ``value`` names, one of ``models``; raise ``Refused`` when there is none."""
        with Session(cog.bind) as session:
            row = find_by_key(session, models, str(value))
        if row is None:
            msg = f"I can't find that {option}; pick one from the list."
            raise Refused(msg)
        return row


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
    lookup: Lookup | None = None
    """The :class:`Lookup` of a stored-row option; ``None`` for any other."""
    models: tuple[type[LifecycleModel], ...] = ()
    """The table classes a :class:`Lookup` option may name."""
    length: Length | None = None
    """The :class:`Length` of a string option; ``None`` leaves its length to Discord."""
    range: Range | None = None
    """The :class:`Range` of a number option; ``None`` leaves it unbounded."""

    def definition(self, *, autocomplete: bool) -> ApplicationCommandOption:
        """Return the option as Discord defines it."""
        return ApplicationCommandOption(
            type=self.option_type,
            name=self.name,
            description=self.description or self.name,
            required=self.required,
            channel_types=self.channel_types,
            autocomplete=True if autocomplete else None,
            min_length=None if self.length is None else self.length.min_length,
            max_length=None if self.length is None else self.length.max_length,
            min_value=None if self.range is None else self.range.min_value,
            max_value=None if self.range is None else self.range.max_value,
        )

    def argument(self, interaction: CommandInteraction, value: object, cog: Cog) -> object:
        """Return the handler argument for the submitted ``value``; ``None`` when the object it names wasn't sent along.

        Raises :class:`~wd_errors.Refused` when a channel isn't one of the option's ``channel_types``, or a
        :class:`Lookup` value names no alive row.

        A parameter annotated with a bound entity gets one bound to the interaction's client; one annotated with the
        data model gets the model.
        """
        if self.lookup is not None and self.models:
            return self.lookup.load(cog, self.models, self.name, value)
        resolvers = _RESOLVERS.get(self.option_type)
        if resolvers is not None:
            resolved = interaction.resolved
            found = None if resolved is None else next(filter(None, (find(resolved, str(value)) for find in resolvers)), None)
            if self.channel_types and isinstance(found, Channel) and found.type not in self.channel_types:
                kinds = " or ".join(kind.name.removeprefix("GUILD_").replace("_", " ").lower() for kind in self.channel_types)
                msg = f"Pick a {kinds} channel for {self.name!r}."
                raise Refused(msg)
            if found is None or type(found) in (get_args(self.param_type) or (self.param_type,)):
                return found
            return found.model
        if self.param_type is float and isinstance(value, int):
            return float(value)  # Discord sends a whole NUMBER as an integer
        return value


type AutocompleteHandler = Callable[..., Awaitable[Iterable[ApplicationCommandOptionChoice]]]
"""A cog method suggesting values for an option: ``(self, interaction, current) -> choices``."""


class DefinitionOptions(TypedDict, total=False):
    """The optional parts of a :class:`CommandDefinition`, as keywords, in any iterable form."""

    default_member_permissions: Permissions | None
    contexts: Iterable[InteractionContextType] | None
    guild_ids: Iterable[SnowflakeLike] | None


@dataclass(frozen=True, slots=True)
class CommandDefinition:
    """What Discord is told about a command: its name, description, who may use it, where, and in which guilds.

    ``default_member_permissions`` is the permission bitfield Discord requires by default to use the command;
    ``contexts`` limits where it shows up (``None`` keeps Discord's default). ``guild_ids`` registers the command in
    just those guilds instead of globally (``None``). Build one from any iterables with :meth:`of`.
    """

    name: str
    description: str
    default_member_permissions: Permissions | None = None
    contexts: tuple[InteractionContextType, ...] | None = None
    guild_ids: tuple[Snowflake, ...] | None = None

    @classmethod
    def of(cls, name: str, description: str, **options: Unpack[DefinitionOptions]) -> Self:
        """Return the definition of ``name``, holding ``options``' iterables as tuples and its guild ids as snowflakes."""
        contexts = options.get("contexts")
        guild_ids = options.get("guild_ids")
        return cls(
            name,
            description,
            options.get("default_member_permissions"),
            None if contexts is None else tuple(contexts),
            None if guild_ids is None else tuple(map(Snowflake.coerce, guild_ids)),
        )


class AppCommand(LoggerMixin, ABC):
    """What every application command shares: its name, description and where Discord lets it be used.

    Subclasses supply the options, the rest of the signature and the dispatch.
    """

    def __init__(self, definition: CommandDefinition) -> None:
        """Set the definition Discord sees."""
        self.definition = definition
        self.name = definition.name
        self.description = definition.description
        self.default_member_permissions = definition.default_member_permissions
        self.contexts = None if definition.contexts is None else list(definition.contexts)
        self.guild_only = self.contexts == [InteractionContextType.GUILD]
        """Whether Discord offers the command in guilds only, so its handler gets a guild interaction."""
        guild_ids = definition.guild_ids
        self.scopes: frozenset[Scope] = frozenset({GLOBAL}) if guild_ids is None else frozenset(map(Scope, guild_ids))
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
    define the command's options via their type annotations, read when the cog class is created: a command is
    always a cog method, so its annotations may name anything in the class body.
    """

    def __init__(
        self,
        func: Callable[..., Awaitable[None]],
        definition: CommandDefinition,
        *,
        requires: Permissions | None = None,
    ) -> None:
        """Wrap ``func`` as the command ``definition`` describes.

        ``requires`` is checked by wd-bot before ``func`` runs; unlike ``default_member_permissions`` it works on a
        subcommand too.
        """
        super().__init__(definition)
        self.func = func
        self.requires = requires
        self.wants_guild = wants_guild_interaction(func)
        """Whether the handler's ``interaction`` is annotated as a guild interaction; it must then be guild-only."""
        self.owner: type[Cog] | None = None
        """The cog class this command was defined on; set when that class is created."""
        self._specs: dict[str, OptionSpec] | None = None

    @property
    def _options(self) -> dict[str, OptionSpec]:
        """The handler's parameters as Discord options, by name; raises ``TypeError`` before a cog class owns it."""
        if self._specs is None:
            msg = f"Command {self.name!r} isn't defined on a Cog, so it has no options"
            raise TypeError(msg)
        return self._specs

    def _read_options(self) -> dict[str, OptionSpec]:
        """Return the handler's parameters as options, reading its annotations now that its class body has run."""
        annotations = annotationlib.get_annotations(self.func, format=annotationlib.Format.FORWARDREF)
        parameters = inspect_signature(self.func, annotation_format=annotationlib.Format.STRING).parameters
        return {
            name: self._option_of(param, annotations.get(name, Parameter.empty))
            for name, param in parameters.items()
            if name not in ("self", "interaction")
        }

    def _option_of(self, param: Parameter, annotation: object) -> OptionSpec:
        """Return handler parameter ``param`` as an option: its type, metadata, and whether it's required.

        A default value or a ``T | None`` annotation makes the option optional. ``Annotated`` metadata, inside or
        outside the ``| None``, configures it: :class:`ChannelTypes` limits a channel option and :class:`Describe`
        sets its description. ``User | Role`` takes a MENTIONABLE. A :class:`Lookup` goes with a table class, or a
        union of them, and makes a STRING. Raises ``TypeError`` if the type has no Discord option type or the
        metadata doesn't fit it.
        """
        param_type, metadata = self._unwrap(self._resolve(annotation, self.func))
        required = param.default is Parameter.empty
        if isinstance(param_type, UnionType) and NoneType in get_args(param_type):
            non_none = [self._reify(arg) for arg in get_args(param_type) if arg is not NoneType]
            param_type, inner = self._unwrap(non_none[0] if len(non_none) == 1 else _union(non_none))
            metadata += inner
            required = False
        channel_types = [kind for item in metadata if isinstance(item, ChannelTypes) for kind in item.types]
        lookups = [item for item in metadata if isinstance(item, Lookup)]
        descriptions = [item.text for item in metadata if isinstance(item, Describe)]
        if len(descriptions) > 1:
            msg = f"Command {self.name!r}: parameter {param.name!r} has more than one Describe"
            raise TypeError(msg)
        if len(lookups) > 1:
            msg = f"Command {self.name!r}: parameter {param.name!r} has more than one Lookup"
            raise TypeError(msg)
        if lookups and not callable(lookups[0].choices):
            msg = f"Command {self.name!r}: the Lookup of {param.name!r} names {lookups[0].choices!r}, which isn't a function"
            raise TypeError(msg)
        members = tuple(map(self._reify, get_args(param_type))) if isinstance(param_type, UnionType) else (param_type,)
        tables = tuple(kind for kind in members if isinstance(kind, type) and issubclass(kind, LifecycleModel))
        models = tables if len(tables) == len(members) else ()
        if models and not lookups:
            msg = f"Command {self.name!r}: parameter {param.name!r} is a LifecycleModel, so it needs a Lookup"
            raise TypeError(msg)
        if lookups and not models and param_type not in (str, int, float):
            msg = f"Command {self.name!r}: a Lookup goes on a str, int, float or LifecycleModel parameter, not {param.name!r}"
            raise TypeError(msg)
        if models:
            option_type = ApplicationCommandOptionType.STRING
        elif isinstance(param_type, UnionType) and frozenset(map(self._reify, get_args(param_type))) in _MENTIONABLES:
            option_type = ApplicationCommandOptionType.MENTIONABLE
        elif isinstance(param_type, type) and param_type in _OPTION_TYPE_MAP:
            option_type = _OPTION_TYPE_MAP[param_type]
        else:
            msg = f"Command {self.name!r}: unsupported option type {param_type!r} for parameter {param.name!r}"
            raise TypeError(msg)
        if channel_types and option_type is not ApplicationCommandOptionType.CHANNEL:
            msg = f"Command {self.name!r}: ChannelTypes only applies to a channel parameter, not {param.name!r}"
            raise TypeError(msg)
        length, bounds = self._limits_of(param.name, param_type if not models else None, metadata)
        return OptionSpec(
            param.name,
            param_type,
            option_type,
            required,
            channel_types or None,
            next(iter(descriptions), None),
            next(iter(lookups), None),
            models,
            length,
            bounds,
        )

    def _limits_of(self, name: str, param_type: object, metadata: list[object]) -> tuple[Length | None, Range | None]:
        """Return parameter ``name``'s :class:`Length` and :class:`Range`, if it has them.

        ``param_type`` is the handler's type, or ``None`` for a stored-row option. Raises ``TypeError`` for a second
        one of either, a ``Length`` off a ``str``, a ``Range`` off an ``int`` or ``float``, or a ``Range`` with a
        non-int bound on an ``int``.
        """
        lengths = [item for item in metadata if isinstance(item, Length)]
        ranges = [item for item in metadata if isinstance(item, Range)]
        for kind, found in (("Length", lengths), ("Range", ranges)):
            if len(found) > 1:
                msg = f"Command {self.name!r}: parameter {name!r} has more than one {kind}"
                raise TypeError(msg)
        if lengths and param_type is not str:
            msg = f"Command {self.name!r}: Length only applies to a str parameter, not {name!r}"
            raise TypeError(msg)
        if ranges and param_type not in (int, float):
            msg = f"Command {self.name!r}: Range only applies to an int or float parameter, not {name!r}"
            raise TypeError(msg)
        if ranges and param_type is int and not all(
            isinstance(end, int | None) for end in (ranges[0].min_value, ranges[0].max_value)
        ):
            msg = f"Command {self.name!r}: the Range of int parameter {name!r} needs int bounds"
            raise TypeError(msg)
        return next(iter(lengths), None), next(iter(ranges), None)

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
            yield option.definition(autocomplete=option.lookup is not None)

    def _own_signature(self) -> Generator[str]:
        """Yield the handler's parameter signature, then its option descriptions and limits when it has any.

        Both are rendered: the signature only holds an annotation's source, which doesn't change when a constant a
        ``Describe``, ``Length`` or ``Range`` names does.
        """
        yield command_signature(self.func)
        if descriptions := {name: spec.description for name, spec in self._options.items() if spec.description}:
            yield f"descriptions: {descriptions}"
        if limits := {name: (spec.length, spec.range) for name, spec in self._options.items() if spec.length or spec.range}:
            yield f"limits: {limits}"

    async def invoke(
        self,
        cog: Cog,
        interaction: CommandInteraction,
        options: Sequence[InteractionDataOption] | None = None,
    ) -> bool:
        """Resolve option values into kwargs and call the wrapped handler.

        ``options`` defaults to ``interaction``'s top-level options; a :class:`CommandGroup` passes the
        chosen subcommand's nested options instead. Runs through :data:`~wd_bot.guard.dispatch_guard`, which answers
        a refusal or an exception. Returns ``True`` if the handler completed or refused, ``False`` if it raised.
        """
        if options is None:
            options = interaction.options
        async def call() -> None:
            kwargs = self._build_kwargs(cog, interaction, options)
            checked = interaction
            if self.guild_only or (self.owner is not None and self.owner.guild_only()):
                checked = require_guild(interaction)
            if self.requires is not None:
                require_permissions(checked, self.requires)
            await self.func(cog, checked, **kwargs)

        return await dispatch_guard.run(f"command '{self.name}'", call, interaction)

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
        spec = self._options.get(focused.name) if focused else None
        handler = spec.lookup.choices if spec is not None and spec.lookup is not None else None
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

    def _build_kwargs(
        self,
        cog: Cog,
        interaction: CommandInteraction,
        options: Sequence[InteractionDataOption],
    ) -> dict[str, object]:
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
            value = spec.argument(interaction, option.value, cog)
            if value is None:
                self.logger.warning(t"Unresolved '{option.value}' for option '{option.name}' in command '{self.name}'")
                continue
            kwargs[option.name] = value
        return kwargs

    def __get__(self, instance: object, owner: type) -> Self:
        """Allow a Command to be accessed as a plain attribute on a Cog instance without binding it like a method."""
        return self

    def __set_name__(self, owner: type, name: str) -> None:
        """Remember the cog class this command is defined on, and read its options now that the class body has run."""
        if not issubclass(owner, Cog):
            return
        self.owner = owner
        self._specs = self._read_options()


def wants_guild_interaction(func: Callable[..., object]) -> bool:
    """Whether ``func``'s ``interaction`` parameter is annotated with a guild interaction type, an :class:`InGuild`.

    Resolves the annotation to its type, so an alias of a guild interaction still counts. A type that can't be resolved
    at runtime doesn't count, so a guild handler imports its interaction type outside ``TYPE_CHECKING``.
    """
    annotation = annotationlib.get_annotations(func, format=annotationlib.Format.FORWARDREF).get("interaction")
    try:
        kind = Command._resolve(annotation, func)  # noqa: SLF001 - the shared annotation resolver
    except NameError:
        return False
    return isinstance(kind, type) and issubclass(kind, InGuild)


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

    def __init__(self, definition: CommandDefinition, subcommands: Iterable[Command]) -> None:
        """Group ``subcommands`` under the command ``definition`` describes."""
        super().__init__(definition)
        name = definition.name
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

        Returns ``False`` (after logging, and replying with :func:`~wd_bot.guard.error_embed`) if no known
        subcommand was chosen.
        """
        if (chosen := self._chosen(interaction.options)) is None:
            await interaction.respond(embeds=[error_embed(interaction.id)], ephemeral=True)
            return False
        subcommand, options = chosen
        return await subcommand.invoke(cog, interaction, options)

    async def complete(self, cog: Cog, interaction: AutocompleteInteraction) -> bool:
        """Route ``interaction`` to the chosen subcommand's autocomplete, like :meth:`invoke`."""
        if (chosen := self._chosen(interaction.options)) is None:
            return False
        subcommand, options = chosen
        return await subcommand.complete(cog, interaction, options)
