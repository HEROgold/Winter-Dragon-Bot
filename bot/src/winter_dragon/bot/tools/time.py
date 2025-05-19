"""Module for helping with time calculations."""

def get_seconds(seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0) -> int:
    """Convert days, hours, minutes and seconds to seconds."""
    hours += days * 24
    minutes += hours * 60
    seconds += minutes * 60
    return seconds
