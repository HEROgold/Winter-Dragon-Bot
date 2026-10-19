"""Size errors."""
from __future__ import annotations


class SizeError(ValueError):
    """Raised when a value is the wrong size."""

class InexactSizeError(SizeError):
    """Raised when a string is not the expected length."""

    def __init__(self, expected_size: int, actual_size: int) -> None:
        """Initialize the error."""
        super().__init__(f"Expected size {expected_size}, got {actual_size}.")

class TooShortError(SizeError):
    """Raised when a string is shorter than the minimum length."""

    def __init__(self, min_length: int, actual_length: int) -> None:
        """Initialize the error."""
        super().__init__(f"length must be at least {min_length}, got {actual_length}.")

class TooLongError(SizeError):
    """Raised when a string exceeds the maximum length."""

    def __init__(self, max_length: int, actual_length: int) -> None:
        """Initialize the error."""
        super().__init__(f"length must be at most {max_length}, got {actual_length}.")

class BoundsError(SizeError, ExceptionGroup):
    """Raised when a value is out of bounds."""

    def __init__(self, min_value: int, max_value: int, actual_value: int) -> None:
        """Initialize the error."""
        msg = f"value must be between {min_value} and {max_value}, got {actual_value}."
        errors = [
            TooShortError(min_value, actual_value),
            TooLongError(max_value, actual_value),
        ]
        super().__init__(msg, errors)
