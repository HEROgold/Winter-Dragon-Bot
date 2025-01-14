from api import router as api_router
from fastapi import FastAPI


site = FastAPI()


site.include_router(api_router)
