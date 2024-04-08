from flask import Blueprint, render_template

from tools.database_tables import GuildCommands, Session, UserRoles, engine


bp = Blueprint("pages", __name__)


@bp.route("/dashboard")
async def dashboard() -> str:
    # Fetch data from your bot and database to display on the dashboard
    with Session(engine) as session:
        guilds = session.query(GuildCommands).all()
        users = session.query(UserRoles).all()
    return render_template("dashboard.j2", guilds=guilds, users=users)
