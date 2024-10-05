from constants import DISCORD_AUTHORIZE, OAUTH_SCOPE, WEBSITE_URL
from fastapi import APIRouter


router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.route("/callback", methods=["GET"])
def oath_callback() -> None:
    # TODO: Respond with the user's home page.
    return

def get_oath_url(application_id: int) -> str:
    redirect_uri = router.url_path_for("callback")
    return (
        DISCORD_AUTHORIZE
        + f"?client_id={application_id}"
        + f"&scope={"+".join(OAUTH_SCOPE)}"
        + f"&redirect_uri={WEBSITE_URL}/{redirect_uri}"
    )
