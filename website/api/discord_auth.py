from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from website.constants import APPLICATION_ID, DISCORD_AUTHORIZE, OAUTH_SCOPE, WEBSITE_URL


router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/")
def oath(request: Request) -> RedirectResponse:  # noqa: ARG001
    url = get_oath_url()
    return RedirectResponse(url=url)


@router.get("/callback")
def oath_callback(request: Request) -> dict[str, str]:
    # TODO: Respond with the user's home page.
    return {"message": f"{request.__dict__}"}


def get_oath_url(application_id: int = APPLICATION_ID) -> str:
    redirect_uri = router.url_path_for("oauth_callback")
    return (
        DISCORD_AUTHORIZE
        + f"?client_id={application_id}"
        + f"&scope={"+".join(OAUTH_SCOPE)}"
        + f"&redirect_uri={WEBSITE_URL}/{redirect_uri}"
    )
