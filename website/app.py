from fastapi import FastAPI

from website.api import router as api_router


site = FastAPI()

site.include_router(api_router)
