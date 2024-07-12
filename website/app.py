from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from database.tables.users import FastApiUser
from website.settings import Settings
from website.types.user_manager import get_user_manager


if TYPE_CHECKING:
    from starlette.templating import _TemplateResponse  # type: ignore[reportPrivateUsage]


app = FastAPI()
settings = Settings()
templates = Jinja2Templates(directory="website/templates")
static = StaticFiles(directory="website/static")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
fastapi_users = FastAPIUsers[FastApiUser, int](
    get_user_manager=get_user_manager(), # TODO: Investigate why this errors.
    auth_backends=[auth_backend],
)

app.mount("/static", static)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"]
)


@app.get("/items/{id_}", response_class=HTMLResponse)
async def read_item(request: Request, id_: str) -> "_TemplateResponse":
    return templates.TemplateResponse(
        request=request, name="item.html", context={"id": id_}
    )
