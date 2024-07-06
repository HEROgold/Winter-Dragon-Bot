from flask import Blueprint, render_template, request
from flask_login import login_required


bp = Blueprint("control", __name__)


@login_required
@bp.route("/settings", methods=["GET", "POST"])
async def settings() -> str:
    if request.method == "POST":
        return f"{request.args=}"
    return render_template("settings.j2")
    # Fetch current settings from your bot and database to display in the form
    # with Session(engine) as session:
    #     guilds = session.query(GuildCommands).all()
    #     users = session.query(UserRoles).all()
    # return render_template("settings.j2", guilds=guilds, users=users)
