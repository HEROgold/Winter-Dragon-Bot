"""Module that contains Configuration helpers."""

from __future__ import annotations

import configparser
from collections.abc import Callable, Generator
from configparser import ConfigParser
from functools import wraps
from typing import TYPE_CHECKING, Any, Self, cast

from winter_dragon.bot.constants import BOT_CONFIG
from winter_dragon.bot.errors import FirstTimeLaunchError


if TYPE_CHECKING:
    from pathlib import Path


class _ConfigParserSingleton(configparser.ConfigParser):
    _instance = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
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
        for section in self.sections():
            for setting in self.options(section):
                if self[section][setting] == "!!":
                    return False
        return True

    def get_invalid(self) -> Generator[str, Any]:
        for section in self.sections():
            for setting in self.options(section):
                if self[section][setting] == "!!":
                    yield f"{section}:{setting}"

_UNSET = object()


class Config[VT: Any]:
    """A descriptor for config values, preserving type information."""

    _parser: ConfigParser
    _file: Path
    _write_on_edit: bool = True

    def __init__(self, default: VT = _UNSET) -> None:
        """Initialize the config descriptor with a default value.

        Validate that parser and filepath are present.
        """
        if default is _UNSET:
            msg = "Default value is not set."
            raise ValueError(msg)
        self.validate_parser()
        self.validate_file()
        self._default = default

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

    def validate_file(self) -> None:
        """Validate the config file."""
        if Config._file is None: # type: ignore[reportUnnecessaryComparison]
            msg = "Config file is not set."
            raise ValueError(msg)

    def validate_parser(self) -> None:
        """Validate the config parser."""
        if Config._parser is None: # type: ignore[reportUnnecessaryComparison]
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
        self._original_value = Config._parser.get(self._section, self._setting) or self._default # type: ignore[reportArgumentType]
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
        # ignore type error, config.get() raises the wanted errors, but checker forces `str` type.
        config_value = Config._parser.get(self._section, self._setting)  # type: ignore[reportArgumentType]
        return cast(VT, config_value)  # noqa: TC006

    def __set__(self, obj: object, value: VT) -> None:
        """Set the value of the attribute."""
        Config._set(self._section, self._setting, value)
        setattr(obj, self.private, value)

    @staticmethod
    def _set(section: str, setting: str, value: VT) -> None:
        """Set a config value, and write it to the file."""
        Config._parser.set(section, setting, str(value))
        if Config._write_on_edit:
            with Config._file.open("w") as f:
                Config._parser.write(f)

    @staticmethod
    def set(section: str, setting: str, value: Any):  # noqa: ANN205, ANN401
        """Set a config value using this descriptor."""

        def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                Config._set(section, setting, value)
                return func(*args, **kwargs)

            return inner

        return wrapper

    @staticmethod
    def as_kwarg(section: str, setting: str, name: str | None = None, default: Any = _UNSET):  # noqa: ANN205, ANN401
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
                return func(*args, **kwargs) # type: ignore[reportCallIssue, reportReturnType]

            return inner # type: ignore[reportReturnType]

        return wrapper

    @staticmethod
    def _set_default(section: str, setting: str, value: VT) -> None:
        if Config._parser.get(section, setting, fallback=_UNSET) is _UNSET:
            Config._set(section, setting, value)

    @staticmethod
    def default(section: str, setting: str, value: Any):  # noqa: ANN205, ANN401
        """Set a default config value if none are set yet using this descriptor."""

        def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                Config._set_default(section, setting, value)
                return func(*args, **kwargs)

            return inner

        return wrapper


config = _ConfigParserSingleton()
Config.set_parser(config)
Config.set_file(BOT_CONFIG)
