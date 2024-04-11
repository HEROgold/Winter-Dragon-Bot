from datetime import datetime, timedelta

import requests
from flask import Blueprint, request
from flask_login import current_user, login_required, login_user, logout_user

from _types.dicts import AccessToken
from tools.config_reader import OAUTH2, V10, WEBSITE_URL, config
from tools.database_tables import AuthToken, Session, engine


bp = Blueprint("tokens", __name__)

CLIENT_ID = config["Main"]["application_id"]
CLIENT_SECRET = config["Tokens"]["client_secret"]

@bp.route("/get_token", methods=["GET"])
async def get_token() -> AccessToken:
    """
    If user logged in, get or refresh token based on expire date.
    If user not logged in, get new token and log in user
    """
    with Session(engine) as session:
        code = current_user.access_token if current_user.is_authenticated else request.args.get("code", "")
        if token := session.query(AuthToken).where(AuthToken.access_token == code).first():
            if token.expires_at <= datetime.now():  # noqa: DTZ005
                return await refresh_token(token.refresh_token)
            return token.as_json()
    return await exchange_code()


@bp.route("/exchange", methods=["GET"])
async def exchange_code() -> AccessToken:
    code = request.args.get("code", "")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": WEBSITE_URL
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = requests.post(  # noqa: ASYNC100
        f"{V10}/oauth2/token",
        data=data,
        headers=headers,
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=5
    )
    r.raise_for_status()

    j = r.json()

    remaining_time = timedelta(j["expires_in"])
    with Session(engine) as session:
        # TODO: get user id from /users/@me api
        response = requests.post(  # noqa: ASYNC100
            f"{V10}/users/@me",
            headers={"Authorization": f"Bearer {j['access_token']}"},
            timeout=5
        ).json()

        print(response, "!"*100)
        u = AuthToken(
            # user_id=auth["user"]["id"], # fetch user id
            access_token=j["access_token"],
            refresh_token=j["refresh_token"],
            expires_at=datetime.now() + remaining_time,  # noqa: DTZ005
            token_type=j["token_type"],
            scope=j["scope"],
            created_at=datetime.now()  # noqa: DTZ005
        )
        session.add(u)
        session.commit()
        login_user(u)
    return j


@bp.route("/refresh", methods=["POST"])
@login_required
async def refresh_token(refresh_token: str) -> AccessToken:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = requests.post(  # noqa: ASYNC100
        f"{V10}/oauth2/token",
        data=data,
        headers=headers,
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=5
    )
    r.raise_for_status()

    with Session(engine) as session:
        session.query(AuthToken).where(AuthToken.refresh_token == refresh_token).update({
            "access_token": r.json()["access_token"],
            "expires_at": datetime.now() + timedelta(r.json()["expires_in"]),  # noqa: DTZ005
            "refresh_token": r.json()["refresh_token"],
        })
        session.commit()
    return r.json()


bp.route("/revoke", methods=["POST"])
@login_required
async def revoke_access_token(access_token: str) -> None:
    data = {
        "token": access_token,
        "token_type_hint": "access_token"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    requests.post(  # noqa: ASYNC100
        f"{V10}/oauth2/token/revoke",
        data=data,
        headers=headers,
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=5
    )

    with Session(engine) as session:
        logout_user()
        session.query(AuthToken).where(AuthToken.access_token == access_token).delete()
        session.commit()


# TODO Fix 400 error
@bp.route("/callback")
def callback() -> str:
    code = get_token()
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{WEBSITE_URL}",
        "scope": "identify email"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(f"{OAUTH2}/token", data=data, headers=headers, timeout=5)
    response.raise_for_status()
    token = response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(f"{V10}/users/@me", headers=headers, timeout=5)
    response.raise_for_status()
    user = response.json()
    return f"{user=}"
