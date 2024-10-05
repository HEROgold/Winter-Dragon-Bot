from api import router as api_router
from fastapi import FastAPI
from router import router as global_router


app = FastAPI()

app.include_router(global_router)
app.include_router(api_router)

@app.get("/")
def root():
    return {"message": "Hello World"}
