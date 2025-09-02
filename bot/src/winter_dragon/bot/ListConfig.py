from confkit import BaseDataType


class ListConfig(BaseDataType[list[str]]):
    """A config value that is a list of values."""

    separator = r","

    def convert(self, value: str) -> list[str]:
        """Convert a string to a list."""
        return [item.casefold() for item in value.split(ListConfig.separator)]

    def __str__(self) -> str:
        """Return a string representation of the list."""
        return ListConfig.separator.join(self.value)