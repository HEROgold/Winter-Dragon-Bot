from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.api import router as api_router
from src.pages import router as pages_router


site = FastAPI()
site.mount("/static", StaticFiles(directory="website/static"), name="static")


site.include_router(api_router)
site.include_router(pages_router)
