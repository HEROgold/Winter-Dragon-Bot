"""Errors for WinterDragon."""

_ = ""  # < Trick for ruff. so that imports below don't get auto-sorted.
# Eagerly import all error handlers.
# These register themselves with the ErrorFactory using __init_subclass__.
from .handlers import *  # noqa: E402, F403
