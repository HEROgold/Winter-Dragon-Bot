from constants import DISCORD_AUTHORIZE, OAUTH_SCOPE, WEBSITE_URL
from fastapi import APIRouter, Request


router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/callback")
def oath_callback(request: Request):
    # TODO: Respond with the user's home page.
    return {"message": f"{request.__dict__=}"}

def get_oath_url(application_id: int) -> str:
    redirect_uri = router.url_path_for("callback")
    return (
        DISCORD_AUTHORIZE
        + f"?client_id={application_id}"
        + f"&scope={"+".join(OAUTH_SCOPE)}"
        + f"&redirect_uri={WEBSITE_URL}/{redirect_uri}"
    )
