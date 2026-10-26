"""Finding, importing, reloading and rolling back the extension modules a bot loads its cogs from."""

lazy import inspect
lazy import pkgutil
lazy import sys
lazy from importlib.util import find_spec, module_from_spec
lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin
lazy from wd_errors.extension import ExtensionError

lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_bot.module_tables import ModuleTables


if TYPE_CHECKING:
    lazy from collections.abc import Generator
    lazy from importlib.machinery import ModuleSpec
    lazy from types import ModuleType

    lazy from wd_bot.bot import Bot
    lazy from wd_bot.registry import Scope


class ExtensionDiscovery:
    """Lists the modules inside an extensions package, at any depth."""

    def __init__(self, package: ModuleType) -> None:
        """Discover extensions inside ``package``."""
        self.package = package

    def modules(self) -> Generator[str]:
        """Yield every module (not package) under :attr:`package`, named relative to it.

        A module ``<package>.admin.sync`` is yielded as ``"admin.sync"``. Walking imports each
        subpackage, so this raises whatever such an import raises, and ``AttributeError`` if
        :attr:`package` isn't a package.
        """
        prefix = f"{self.package.__name__}."
        for module in pkgutil.walk_packages(self.package.__path__, prefix=prefix):
            if not module.ispkg:
                yield module.name.removeprefix(prefix)


class ExtensionLoader(LoggerMixin):
    """Imports a bot's extension modules and builds their cogs; reloads one in place, rolling back on failure."""

    def __init__(self, bot: Bot, package: ModuleType) -> None:
        """Load extensions from ``package`` into ``bot``."""
        self.bot = bot
        self.package = package
        """The package :meth:`load_all` discovers extension modules in."""
        self.failed: set[str] = set()
        """The extensions (or the package, when discovery broke) that failed to load since the last :meth:`load_all`.

        While it isn't empty, :meth:`Bot.sync_commands <wd_bot.bot.Bot.sync_commands>` won't write to Discord.
        """

    async def load_all(self) -> None:
        """Load every module in :attr:`package`, recording (not raising) each failure in :attr:`failed`."""
        self.logger.debug(t"Starting to load cogs from {self.package.__name__}")
        self.failed.clear()
        for extension in self._discover():
            self.logger.info(t"Loading cog {extension}")
            try:
                await self.load(extension)
            except Exception:
                self.failed.add(extension)
                self.logger.exception(t"Failed to load cog {extension}")
            else:
                self.logger.info(t"Loaded cog {extension}")

    async def load(self, extension: str) -> None:
        """Import the module ``extension`` (named relative to :attr:`package`) and add its cogs to the bot.

        Raises :class:`~wd_errors.extension.ExtensionError` when it isn't found, fails to import or a cog fails to
        build.
        """
        spec = find_spec(f"{self.package.__name__}.{extension}")
        if not spec:
            raise ExtensionError(extension, RuntimeError("Extension not found"))
        await self._load_from_spec(spec, extension)
        self.failed.discard(extension)

    async def add_cogs(self, module: ModuleType) -> None:
        """Build every concrete :class:`~wd_bot.cogs.Cog` subclass in ``module`` and add it to the bot."""
        for obj in module.__dict__.values():
            if inspect.isclass(obj) and issubclass(obj, Cog) and obj not in (Cog, GroupCog):
                cog = obj(bot=self.bot)
                # Register now rather than relying on the task Cog.__init__ scheduled: sync_commands
                # runs right after load_all and must see every command. auto_load is idempotent.
                await cog.auto_load()

    async def reload(self, module_name: str) -> set[Scope]:
        """Re-import the module ``module_name`` and swap its cogs for fresh ones; return the command scopes that changed.

        The new code is imported before anything is removed, so if it fails to import, or its cogs fail to build, the
        old cogs stay added and :class:`~wd_errors.extension.ExtensionError` is raised. The SQLModel tables the module
        defines are set aside while it runs again, so its table classes can be redefined; a failed reload puts them
        back.
        """
        old_module = sys.modules.get(module_name)
        spec = find_spec(module_name)
        if spec is None or spec.loader is None:
            raise ExtensionError(module_name, RuntimeError("Extension not found"))
        module = module_from_spec(spec)
        tables = ModuleTables.detach(module_name, old_module)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            tables.restore()
            raise ExtensionError(module_name, e) from e

        old_cogs = self._cogs_from(module_name)
        scopes: set[Scope] = set()
        for cog in old_cogs:
            scopes |= await self.bot.remove_cog(cog)
        sys.modules[module_name] = module
        try:
            await self.add_cogs(module)
        except Exception as e:
            for cog in self._cogs_from(module_name):
                await self.bot.remove_cog(cog)
            if old_module is not None:
                sys.modules[module_name] = old_module
            tables.restore()
            for cog in old_cogs:
                await self.bot.add_cog(cog)
            raise ExtensionError(module_name, e) from e
        for cog in self._cogs_from(module_name):
            scopes |= self.bot.registry.scopes_of(cog)
        self.logger.info(t"Reloaded extension {module_name}")
        return scopes

    def _discover(self) -> list[str]:
        """Return the modules in :attr:`package`, named relative to it; a discovery failure is recorded in :attr:`failed`."""
        try:
            return list(ExtensionDiscovery(self.package).modules())
        except ImportError:
            self.failed.add(self.package.__name__)
            self.logger.warning(t"{self.package.__name__} package not found, skipping cog discovery")
        except Exception:
            self.failed.add(self.package.__name__)
            self.logger.exception(t"Error discovering {self.package.__name__} modules")
        return []

    async def _load_from_spec(self, spec: ModuleSpec, key: str) -> None:
        """Import a module spec under its full name and add its cogs.

        A module another extension already imported is reused, not executed again: a second copy would
        redefine its classes, which e.g. SQLModel tables don't allow.
        """
        if spec.loader is None:
            raise ExtensionError(key, RuntimeError("Module spec has no loader"))
        module = sys.modules.get(spec.name)
        if module is None:
            module = module_from_spec(spec)
            sys.modules[spec.name] = module
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                del sys.modules[spec.name]
                raise ExtensionError(key, e) from e
        try:
            await self.add_cogs(module)
        except Exception as e:
            raise ExtensionError(key, e) from e

    def _cogs_from(self, module_name: str) -> list[Cog]:
        """Return the bot's cogs whose class is defined in the module ``module_name``."""
        return [cog for cog in self.bot.cogs.values() if type(cog).__module__ == module_name]
