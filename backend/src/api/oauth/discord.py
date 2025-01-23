import discordoauth2
from constants import APPLICATION_ID, OAUTH_SCOPE, WEBSITE_URI
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/oauth", tags=["oauth"])
client = discordoauth2.Client(
    APPLICATION_ID,
    "client_secret",
    WEBSITE_URI,
)


@router.get("/")
def oath(_: Request) -> RedirectResponse:
    return RedirectResponse(url=client.generate_uri(OAUTH_SCOPE))


@router.get("/callback")
def oath_callback(request: Request) -> RedirectResponse:
    code = request.get("code", "")
    access = client.exchange_code(code)
    print(access.fetch_identify())
    # TODO @HEROgold: give the user_id to the home page
    # 000
    return RedirectResponse(url="/home")
