from flask import Flask, redirect
from werkzeug import Response

from blueprints import ctrl, docs, page
from tools.config_reader import DISCORD_AUTHORIZE, STATIC_PATH, TEMPLATE_PATH, WEBSITE_URL, config
from tools.flask_tools import register_blueprints


app = Flask(__name__, template_folder=TEMPLATE_PATH, static_folder=STATIC_PATH)
register_blueprints(app, [ctrl, docs, page])

@app.route("/")
def index() -> Response:
    return redirect(
        DISCORD_AUTHORIZE
        + f"?client_id={config['Main']['client_id']}"
        + f"&redirect_uri={WEBSITE_URL}"
        + "&response_type=code"
        + "&scope=identify"
    )


@app.route("/post_all", methods=["GET", "POST"])
def post_all(code: str) -> str:
    return f"{code=}"
