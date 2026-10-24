"""https://docs.discord.com/developers/resources/user#user-object.

NOT FINISHED.
"""
lazy from .collectibles import Collectibles
lazy from .profile import Avatar, NamePlate
lazy from .user import User


__all__ = [
    "Avatar",
    "Collectibles",
    "NamePlate",
    "User",
]





