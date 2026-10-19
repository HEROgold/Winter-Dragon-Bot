"""Finding the extension modules a bot loads its cogs from."""

from __future__ import annotations

lazy import pkgutil
lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from collections.abc import Generator
    lazy from types import ModuleType


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
