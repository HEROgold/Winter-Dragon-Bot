from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.tables.users import User
from website.settings import Settings


if TYPE_CHECKING:
    from starlette.templating import _TemplateResponse  # type: ignore[reportPrivateUsage]


app = FastAPI()
settings = Settings()
templates = Jinja2Templates(directory="website/templates")
static = StaticFiles(directory="website/static")

app.mount("/static", static)


def load_user(user_id: str) -> User:
    return User.fetch_user(int(user_id))


@app.get("/items/{id}", response_class=HTMLResponse)
async def read_item(request: Request, id_: str) -> "_TemplateResponse":
    return templates.TemplateResponse(
        request=request, name="item.html", context={"id": id_}
    )
