import inspect

from _types.bot import WinterDragon
from flask import Blueprint, render_template


bp = Blueprint("documentation", __name__)


@bp.route("/docs")
async def docs() -> str:
    # Get all commands from your bot
    commands = WinterDragon.get_all_commands()
    # Get type hints for each command
    command_docs = {command: inspect.getfullargspec(command).annotations for command in commands}
    return render_template("docs.html", command_docs=command_docs)
