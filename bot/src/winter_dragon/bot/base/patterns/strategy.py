"""Observer pattern implementation."""

from typing import Protocol


class Strategy[T](Protocol):
    """Strategy class that defines a strategy interface for the strategy pattern."""

    def __init__(self) -> None:
        """Initialize the strategy."""

    def execute(self, *args: T, **kwargs: T) -> None:
        """Execute the strategy."""


class Context[T](Protocol):
    """Context class that uses a strategy to perform an operation."""

    def __init__(self, strategy: Strategy[T]) -> None:
        """Initialize the context with a specific strategy."""
        self._strategy = strategy

    def set_strategy(self, strategy: Strategy[T]) -> None:
        """Set a new strategy."""
        self._strategy = strategy

    def execute_strategy(self, *args: T, **kwargs: T) -> None:
        """Execute the current strategy."""
        self._strategy.execute(*args, **kwargs)
