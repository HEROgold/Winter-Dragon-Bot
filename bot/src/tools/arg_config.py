from argparse import ArgumentParser
from configparser import ConfigParser
from pathlib import Path


class ConfigError(Exception):
    pass


class _ArgsNameSpace:
    config: str


class ArgConfig:
    def __init__(self, args: ArgumentParser, config: ConfigParser, file: Path | None) -> None:
        """Read a config file and add the config settings to the argument parser. in the form of --<key> <value> arguments.

        Attempts a help message for each config setting, showing the section, key and value.
        """
        args.add_argument("-c", "--config", type=str, help="Config file path")
        self.config = config
        self.args = self._parse(args)

        if self.args.config and file:
            msg = "Cannot specify --config argument and a `file` path function argument at the same time."
            raise ConfigError(msg)

        if file:
            self.config.read(file)
            self._add_config_arguments(args)
            self.args = self._parse(args)
        elif self.args.config:
            self.config.read(self.args.config)
            self._add_config_arguments(args)
            self.args = self._parse(args)

    def _parse(self, args: ArgumentParser) -> _ArgsNameSpace:
        return args.parse_args(namespace=_ArgsNameSpace())

    def _add_config_arguments(self, args: ArgumentParser) -> None:
        for section in self.config.sections():
            for key, value in self.config.items(section):
                args.add_argument(f"--{key}", type=type(value), help=f"{section} {key} {value}")
