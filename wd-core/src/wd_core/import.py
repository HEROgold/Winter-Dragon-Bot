"""Module helping with importing modules for the Winter Dragon project.

This module provides helpers for importing and validation of wd-* packages
for public extension and internal use.
"""
from __future__ import annotations

from importlib import metadata


class PackageVersion(str):
    """A string representing a package version."""


def get_package_version(package_name: str) -> PackageVersion:
    """Get the version of a package."""
    return PackageVersion(metadata.version(package_name))
