"""Module that holds all exceptions that occur with tournament strategies."""

class InvalidTeamCountError(Exception):
    """Exception raised when there are not enough teams to start a tournament."""

class CannotAdvanceError(Exception):
    """Exception raised when a tournament cannot advance to the next round."""
