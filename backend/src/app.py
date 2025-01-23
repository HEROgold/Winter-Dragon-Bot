from api import router as api_router
from fastapi import FastAPI
from fastapi.responses import FileResponse


site = FastAPI()


site.include_router(api_router)

@site.get("/favicon.ico")
def favicon() -> FileResponse:
    return FileResponse("static/favicon.ico")
