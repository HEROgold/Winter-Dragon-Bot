"""Module that contains Configuration helpers."""

import configparser
from collections.abc import Callable, Generator
from typing import Any, Self, cast

from winter_dragon.bot.constants import BOT_CONFIG
from winter_dragon.bot.errors import FirstTimeLaunchError


MISSING: Any = object()

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
        fp = BOT_CONFIG.open("w")
        self.write(fp)
        fp.close()

    def set_default(self, section: str, setting: str, value: Any) -> None:  # noqa: ANN401
        """Set a default value for a config setting.

        If the section or setting does not exist, it will be created.
        """
        if not self.has_section(section):
            self.add_section(section)
        if not self.has_option(section, setting):
            self.set(section, setting, str(value))

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

    def default(self, section: str, setting: str, value: Any) -> None:  # noqa: ANN401
        """Set a default value for a config setting.

        If the section or setting does not exist, it will be created.
        """
        self.set_default(section, setting, value)


class Config[VT]:
    """A descriptor for config values, preserving type information."""

    def __init__(self, default: VT | None = None) -> None:
        """Initialize the descriptor with a default value."""
        self._default = default

    def __set_name__(self, owner: type, name: str) -> None:
        """Set the name of the attribute."""
        self.name = name
        self._section = owner.__name__
        self._setting = name
        config.set_default(self._section, self._setting, self._default)
        self.private = f"_{self._section}_{self._setting}_{self.name}"

    def __get__(self, obj: object, obj_type: object) -> VT:
        """Get the value of the attribute."""
        # obj_type is the class in which the variable is defined
        # so it can be different than type of VT
        # but we don't need obj or it's type to get the value from config in our case.
        # ignore type error, config.get() raises the wanted errors, but checker forces `str` type.
        return cast(VT, config.get(self._section, self._setting))  # noqa: TC006

    def __set__(self, obj: object, value: VT) -> None:
        """Set the value of the attribute."""
        config.set(self._section, self._setting, str(value))
        setattr(obj, self.private, value)

    @staticmethod
    def set(section: str, setting: str, value: Any):  # noqa: ANN205, ANN401
        """Set a config value using this descriptor."""

        def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                config.set(section, setting, value)
                return func(*args, **kwargs)

            return inner

        return wrapper

    @staticmethod
    def as_kwarg(section: str, setting: str, name: str | None = None, default: Any = MISSING):  # noqa: ANN205, ANN401
        """Insert a config value into **kwargs to a given method/function using this descriptor.

        Use kwarg.get(`name`) to get the value.
        `name` is the name the kwarg gets if passed, if None, it will be the same as `setting`.
        Section parameter is just for finding the config value.
        """
        if name is None:
            name = setting

        def wrapper[F, **P, T: Callable[P, F]](func: T) -> T:
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                if default is not MISSING:
                    config.set_default(section, setting, default)
                kwargs[name] = config.get(section, setting)
                return func(*args, **kwargs) # type: ignore[reportCallIssue, reportReturnType]

            return inner # type: ignore[reportReturnType]

        return wrapper

    @staticmethod
    def default(section: str, setting: str, value: Any):  # noqa: ANN205, ANN401
        """Set a default config value using this descriptor."""

        def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
            def inner(*args: P.args, **kwargs: P.kwargs) -> F:
                config.set_default(section, setting, value)
                return func(*args, **kwargs)

            return inner

        return wrapper


config = _ConfigParserSingleton()
