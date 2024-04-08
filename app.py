from flask import Flask, redirect, request
from flask_login import LoginManager
from werkzeug import Response

from blueprints import ctrl, docs, page, tokens
from tools.config_reader import DISCORD_AUTHORIZE, STATIC_PATH, TEMPLATE_PATH, WEBSITE_URL, config
from tools.database_tables import AuthToken, Session, engine
from tools.flask_tools import register_blueprints


API_ENDPOINT = "https://discord.com/api/v10"

app = Flask(__name__, template_folder=TEMPLATE_PATH, static_folder=STATIC_PATH)
register_blueprints(app, [ctrl, docs, page, tokens])
lm = LoginManager(app)

@app.route("/")
def index() -> Response:
    return redirect(
        DISCORD_AUTHORIZE
        + f"?client_id={config['Main']['application_id']}"
        + f"&redirect_uri={WEBSITE_URL}"
        + "&response_type=code"
        + "&scope=identify+guilds+guilds.members.read"
        # +relationships.read
    )


@app.route("/post_all", methods=["GET", "POST"])
def post_all() -> str:
    """
    Debug route that prints all request data.
    """
    return f"{request.args=}"


@lm.user_loader
def load_user(user_id: str) -> AuthToken:
    with Session(engine) as session:
        if at := session.query(AuthToken).where(AuthToken.user_id == int(user_id)).first():
            return at
    # Should not happen
    return None # type: ignore
