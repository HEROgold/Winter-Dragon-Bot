"""Observer pattern implementation."""

from typing import Protocol


class Observer[T](Protocol):
    """Observer interface for the observer pattern."""

    def update(self, *args: T, **kwargs: T) -> None:
        """Update method to be called when the observed object changes."""

class Notifier[T]:
    """Notifier class that maintains a list of observers and notifies them of changes."""

    def __init__(self) -> None:
        """Initialize the notifier with an empty list of observers."""
        self._observers: list[Observer[T]] = []

    def add(self, observer: Observer[T]) -> None:
        """Attach an observer to the notifier."""
        self._observers.append(observer)

    def remove(self, observer: Observer[T]) -> None:
        """Detach an observer from the notifier."""
        self._observers.remove(observer)

    def notify(self, *args: T, **kwargs: T) -> None:
        """Notify all attached observers of a change."""
        for observer in self._observers:
            observer.update(*args, **kwargs)
