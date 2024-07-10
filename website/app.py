from flask import Flask, request
from flask_login import LoginManager

from bot.config import STATIC_PATH, TEMPLATE_PATH, config
from database.tables.users import User
from website.tools.blueprints import register_blueprints

from .blueprints import ctrl, docs, page, tokens


app = Flask(__name__, template_folder=TEMPLATE_PATH, static_folder=STATIC_PATH)
app.config["SECRET_KEY"] = config["Tokens"]["client_secret"]
register_blueprints(app, ctrl, docs, page, tokens)
lm = LoginManager(app)


@app.route("/post_all", methods=["GET", "POST"])
def post_all() -> str:
    """
    Debug route that prints all request data.
    """
    return f"{request.args=}"


@lm.user_loader
def load_user(user_id: str) -> User:
    return User.fetch_user(int(user_id))
