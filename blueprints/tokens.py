import os

from flask import Blueprint, jsonify, redirect, request, session, url_for
from requests_oauthlib import OAuth2Session
from werkzeug import Response

from tools.config_reader import OAUTH_SCOPE, V10, config


OAUTH2_CLIENT_ID = config["Main"]["application_id"]
OAUTH2_CLIENT_SECRET = config["Tokens"]["client_secret"]
OAUTH2_REDIRECT_URI = "http://localhost:5000/callback"

AUTHORIZATION_BASE_URL = f"{V10}/oauth2/authorize"
TOKEN_URL = f"{V10}/oauth2/token"

bp = Blueprint("login", __name__)

if "http://" in OAUTH2_REDIRECT_URI:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"


def token_updater(token: str) -> None:
    session["oauth2_token"] = token


def make_session(
    token: str | None = None,
    state: str | None = None,
    scope: str | list[str] | None = None
) -> OAuth2Session:
    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            "client_id": OAUTH2_CLIENT_ID,
            "client_secret": OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater
    )


@bp.route("/")
def index() -> Response:
    if token := session.get("oauth2_token", None):
        auth = make_session(token=token)
        return redirect(url_for(".me"))

    scope = request.args.get(
        "scope",
        OAUTH_SCOPE
    )
    auth = make_session(scope=scope)
    authorization_url, state = auth.authorization_url(AUTHORIZATION_BASE_URL)
    session["oauth2_state"] = state
    return redirect(authorization_url)


@bp.route("/callback")
def callback() -> str | Response:
    if request.values.get("error"):
        return request.values["error"]
    oauth = make_session(state=session.get("oauth2_state"))
    token = oauth.fetch_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url
    )
    session["oauth2_token"] = token
    return redirect(url_for(".me"))


@bp.route("/me")
def me() -> Response:
    oauth = make_session(token=session.get("oauth2_token"))
    user = oauth.get(f"{V10}/users/@me").json()
    guilds = oauth.get(f"{V10}/users/@me/guilds").json()
    connections = oauth.get(f"{V10}/users/@me/connections").json()
    return jsonify(user=user, guilds=guilds, connections=connections)
