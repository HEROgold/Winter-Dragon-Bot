"""Migration manager for Winter Dragon database migrations."""

import importlib
import pkgutil
from logging import Logger
from pathlib import Path


version_file = Path(__file__).parent / "VERSION.txt"


PREV_VERSION = version_file.read_text().strip() if version_file.exists() else "0.0.0"
CURRENT_VERSION = "0.1.1"

def _run_versioned_migrations(logger: Logger, prev_version: str, current_version: str) -> None:
    """Run migrations based on version differences dynamically."""
    # Get the package containing migration modules
    package_path = Path(__file__).parent
    package_name = "winter_dragon.database.migrations"

    # Find all migration modules (files starting with _)
    for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
        if module_name.startswith("_"):
            try:
                # Convert module name to version format (e.g., _0_1_1 -> 0.1.1)
                version = module_name.strip("_").replace("_", ".")

                # Only import modules for versions newer than prev_version
                if prev_version < version <= current_version:
                    # Import runs migration code!!
                    logger.info(f"Running migration: {module_name} ({version})")
                    importlib.import_module(f"{package_name}.{module_name}")
                    logger.info(f"Migration {module_name} completed successfully.")
            except (ImportError, ValueError):
                logger.exception(f"Error importing migration {module_name}")

def migrate(logger: Logger) -> None:
    """Run migrations if the current version is newer than the previous version."""
    logger.info(f"Database: {CURRENT_VERSION=}, {PREV_VERSION=}")
    if PREV_VERSION < CURRENT_VERSION:

        # Run migrations
        _run_versioned_migrations(logger, PREV_VERSION, CURRENT_VERSION)

        # Update the VERSION file
        version_file.touch(exist_ok=True)
        version_file.write_text(CURRENT_VERSION)
