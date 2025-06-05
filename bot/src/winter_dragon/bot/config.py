"""Module for a config descriptor.

The Config descriptor is used to read and write config values from a ConfigParser object.
It is used to create a descriptor for config values, preserving type information.
It also provides a way to set default values and to set config values using decorators.
"""

from __future__ import annotations

import configparser
from collections.abc import Callable, Generator
from functools import wraps
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict, Unpack

from winter_dragon.bot.constants import BOT_CONFIG
from winter_dragon.bot.errors import FirstTimeLaunchError


if TYPE_CHECKING:
    from pathlib import Path


class ConfigParser(configparser.ConfigParser):
    """Custom config parser that handles the config file."""

    def __init__(self) -> None:
        """Initialize the config parser."""
        super().__init__()
        try:
            with BOT_CONFIG.open():
                pass
        except FileNotFoundError as e:
            BOT_CONFIG.touch(exist_ok=True)
            self._write_defaults()
            msg = f"First time launch detected, please edit settings with value !! in {BOT_CONFIG}"
            raise FirstTimeLaunchError(msg) from e
        self.read(BOT_CONFIG)

    def _write_defaults(self) -> None:
        self["Tokens"] = {
            "discord_token": "!!",
        }
        with BOT_CONFIG.open("w") as fp:
            self.write(fp)

    def is_valid(self) -> bool:
        """Check if the config is valid."""
        for section in self.sections():
            for setting in self.options(section):
                if self[section][setting] == "!!":
                    return False
        return True

    def get_invalid(self) -> Generator[str]:
        """Get all invalid config values."""
        for section in self.sections():
            for setting in self.options(section):
                if self[section][setting] == "!!":
                    yield f"{section}:{setting}"


_UNSET: Any = object()


class InvalidDefaultError(ValueError):
    """Raised when the default value is not set or invalid."""


class InvalidConverterError(ValueError):
    """Raised when the converter is not set or invalid."""


class ConfigSettings(TypedDict):
    """typed Kwargs for the Config descriptor."""

    optional: NotRequired[bool]


# TODO: support other config types like TOML
class Config[VT]:
    """A descriptor for config values, preserving type information."""

    _parser: ConfigParser
    _file: Path
    _write_on_edit: bool = True
    _validate_type: bool = True
    _optional: bool = False

    def __init__(
        self,
        default: VT = _UNSET,
        converter: Callable[..., VT] = _UNSET,
        **kwargs: Unpack[ConfigSettings],
    ) -> None:
        """Initialize the config descriptor with a default value.

        Validate that parser and filepath are present.
        """
        if default is _UNSET:
            msg = "Default value is not set."
            raise InvalidDefaultError(msg)
        self.validate_parser()
        self.validate_file()
        self._default = default
        self._converter = converter
        self._optional = kwargs.get("optional", self._optional)
        # Ensure the parser reads the file at initialization. Avoids rewriting the file when settings are already set.
        # Only slows down startup time if used properly, reading every entire file for every descriptor.
        Config._parser.read(Config._file)
        self._fix_bool_converter()

    def convert(self, value: str) -> VT:
        """Convert the value to the desired type using the given converter method."""
        return self._converter(value)

    @staticmethod
    def set_parser(parser: ConfigParser) -> None:
        """Set the parser for ALL descriptors."""
        Config._parser = parser

    @staticmethod
    def set_file(file: Path) -> None:
        """Set the file for ALL descriptors."""
        Config._file = file

    @property
    def write_on_edit(self) -> bool:
        """Get the write_on_edit property."""
        return Config._write_on_edit

    @write_on_edit.setter
    def write_on_edit(self, value: bool) -> None:
        """Write the config file on edit."""
        Config._write_on_edit = value

    def validate_strict_type(self) -> None:
        """Validate the type of the converter matches the desired type."""
        if not Config._validate_type:
            return
        if self._converter is _UNSET:
            msg = "Converter is not set."
            raise InvalidConverterError(msg)

        config_value = Config._parser.get(self._section, self._setting)
        converted_value = self.convert(config_value)

        if self._optional and (type(converted_value) not in (type(self._default), type(None))):
            # Check if optional value is either None or the same type as the default.
            return
        if type(converted_value) is not type(self._default):
            msg = f"Converter {self._converter.__name__} does not return the same type as the default value ({type(self._default)})."
            raise InvalidConverterError(msg)

    def validate_file(self) -> None:
        """Validate the config file."""
        if Config._file is None:  # type: ignore[reportUnnecessaryComparison]
            msg = "Config file is not set."
            raise ValueError(msg)

    def validate_parser(self) -> None:
        """Validate the config parser."""
        if Config._parser is None:  # type: ignore[reportUnnecessaryComparison]
            msg = "Config parser is not set."
            raise ValueError(msg)

    def __set_name__(self, owner: type, name: str) -> None:
        """Set the name of the attribute to the name of the descriptor."""
        self.name = name
        self._section = owner.__name__
        self._setting = name
        self._ensure_section()
        self._ensure_option()
        # ignore type error, config.get() raises the wanted errors, but checker forces `str` type.
        self._original_value = Config._parser.get(self._section, self._setting) or self._default  # type: ignore[reportArgumentType]
        self.private = f"_{self._section}_{self._setting}_{self.name}"

    def _ensure_section(self) -> None:
        """Ensure the section exists in the config file. Creates one if it doesn't exist."""
        if not self._parser.has_section(self._section):
            self._parser.add_section(self._section)

    def _ensure_option(self) -> None:
        """Ensure the option exists in the config file. Creates one if it doesn't exist."""
        if not self._parser.has_option(self._section, self._setting):
            Config._set(self._section, self._setting, self._default)

    def __get__(self, obj: object, obj_type: object) -> VT:
        """Get the value of the attribute."""
        # obj_type is the class in which the variable is defined
        # so it can be different than type of VT
        # but we don't need obj or it's type to get the value from config in our case.
        self.validate_strict_type()
        return self.convert(Config._parser.get(self._section, self._setting))

    def __set__(self, obj: object, value: VT) -> None:
        """Set the value of the attribute."""
        Config._set(self._section, self._setting, value)
        setattr(obj, self.private, value)

    @staticmethod
    def _sanitize_str(value: str) -> str:
        """Escape the percent sign in the value."""
        return value.replace("%", "%%")

    @staticmethod
    def _set(section: str, setting: str, value: VT) -> None:
        """Set a config value, and write it to the file."""
        if not Config._parser.has_section(section):
            Config._parser.add_section(section)
        sanitized_str = Config._sanitize_str(str(value))
        Config._parser.set(section, setting, sanitized_str)
        if Config._write_on_edit:
            with Config._file.open("w") as f:
                Config._parser.write(f)

    @staticmethod
    def set(section: str, setting: str, value: VT):  # noqa: ANN205
        """Set a config value using this descriptor."""

        def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                Config._set(section, setting, value)
                return func(*args, **kwargs)

            return inner

        return wrapper

    @staticmethod
    def with_setting[OVT](setting: Config[OVT]):  # noqa: ANN205
        """Insert a config value into **kwargs to a given method/function using this decorator."""

        def wrapper[F, **P, T: Callable[P, F]](func: T) -> T:
            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                kwargs[setting.name] = setting.convert(Config._parser.get(setting._section, setting._setting))
                return func(*args, **kwargs)  # type: ignore[reportCallIssue, reportReturnType]

            return inner  # type: ignore[reportReturnType]

        return wrapper

    @staticmethod
    def as_kwarg(section: str, setting: str, name: str | None = None, default: VT = _UNSET):  # noqa: ANN205
        """Insert a config value into **kwargs to a given method/function using this descriptor.

        Use kwarg.get(`name`) to get the value.
        `name` is the name the kwarg gets if passed, if None, it will be the same as `setting`.
        Section parameter is just for finding the config value.
        """
        if name is None:
            name = setting
        if default is _UNSET and not Config._parser.has_option(section, setting):
            msg = f"Config value {section=} {setting=} is not set. and no default value is given."
            raise ValueError(msg)

        def wrapper[F, **P, T: Callable[P, F]](func: T) -> T:
            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                if default is not _UNSET:
                    Config._set_default(section, setting, default)
                kwargs[name] = Config._parser.get(section, setting)
                return func(*args, **kwargs)  # type: ignore[reportCallIssue, reportReturnType]

            return inner  # type: ignore[reportReturnType]

        return wrapper

    @staticmethod
    def _set_default(section: str, setting: str, value: VT) -> None:
        if Config._parser.get(section, setting, fallback=_UNSET) is _UNSET:
            Config._set(section, setting, value)

    @staticmethod
    def default(section: str, setting: str, value: VT):  # noqa: ANN205
        """Set a default config value if none are set yet using this descriptor."""

        def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                Config._set_default(section, setting, value)
                return func(*args, **kwargs)

            return inner

        return wrapper

    def _fix_bool_converter(self) -> None:
        """Fix the bool converter to handle string values."""
        if self._converter is not bool:
            return

        def bool_converter(value: str) -> VT:
            """Convert a string to a boolean."""
            if value.lower() in {"true", "1", "yes"}:
                return True  # type: ignore[reportReturnType]
            if value.lower() in {"false", "0", "no"}:
                return False  # type: ignore[reportReturnType]
            if val := self._parser.getboolean(self._section, self._setting, fallback=None):
                return val  # type: ignore[reportReturnType]
            msg = f"Cannot convert {value} to bool."
            raise ValueError(msg)

        # Attempt to use the direct converter from RawConfigParser using getattr, default to custom converter.
        self._converter = getattr(self._parser, "_convert_to_boolean", bool_converter)


config = ConfigParser()
Config.set_parser(config)
Config.set_file(BOT_CONFIG)
