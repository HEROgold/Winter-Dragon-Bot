"""Custom exceptions for config errors."""

class ConfigError(Exception):
    """Base class for all configuration-related exceptions."""


class FirstTimeLaunchError(Exception):
    """Raised when it's detected that WinterDragon is launched for the first time."""
