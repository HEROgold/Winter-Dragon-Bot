from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from website.api import router as api_router


site = FastAPI()

site.mount("/static", StaticFiles(directory="website/static"), name="static")


site.include_router(api_router)
