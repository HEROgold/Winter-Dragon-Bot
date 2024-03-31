from flask import Blueprint, render_template, request
from tools.database_tables import GuildCommands, Session, UserRoles, engine


bp = Blueprint("control", __name__)


@bp.route("/settings", methods=["GET", "POST"])
async def settings() -> str:
    if request.method == "POST":
        # Update settings in your bot and database based on form data
        pass
    # Fetch current settings from your bot and database to display in the form
    with Session(engine) as session:
        guilds = session.query(GuildCommands).all()
        users = session.query(UserRoles).all()
    return render_template("settings.html", guilds=guilds, users=users)
