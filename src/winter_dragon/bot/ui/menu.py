"""Action menus for interactive settings and options."""


from herogold.log import LoggerMixin

from .view import View


class Menu(View, LoggerMixin):
    """Interactive menu for performing actions with options and toggles."""
