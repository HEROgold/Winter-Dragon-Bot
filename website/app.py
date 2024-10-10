from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from website.api import router as api_router
from website.templates import templates


site = FastAPI()
site.mount("/static", StaticFiles(directory="website/static"), name="static")


site.include_router(api_router)
@site.get("/")
def index(request: Request):
    head = None
    header = None
    nav = None
    content = None
    footer = None
    script = None
    return templates.TemplateResponse(request, "index.html", {"request": request, "head": head, "header": header, "nav": nav, "content": content, "footer": footer, "script": script})
