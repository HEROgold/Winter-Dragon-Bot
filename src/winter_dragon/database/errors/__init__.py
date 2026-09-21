class NotFoundError(ValueError):
    """Custom exception for records not found in the database."""


class AlreadyExistsError(ValueError):
    """Custom exception for already existing records in the database."""
