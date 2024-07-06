
from flask import Blueprint, redirect, render_template, request
from flask_login import login_required
from werkzeug import Response

from database.tables import Session, engine
from database.tables.associations import GuildCommands
from database.tables.roles import UserRoles


bp = Blueprint("pages", __name__)


@login_required
@bp.route("/dashboard")
async def dashboard() -> str:
    # Fetch data from your bot and database to display on the dashboard
    with Session(engine) as session:
        guilds = session.query(GuildCommands).all()
        users = session.query(UserRoles).all()
    return render_template("dashboard.j2", guilds=guilds, users=users)

@bp.route("/redirect")
async def redirect_site() -> Response:
    return redirect(request.args.get("redirect_url", request.referrer))
