"""Backend API for Winter Dragon Bot."""

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse

from winter_dragon.database.extension.model import models
from winter_dragon.database.extras.api import API_AVAILABLE
from winter_dragon.database.extras.api.api_model import APIModel


if not API_AVAILABLE:
    msg = "FastAPI dependencies not available. Install with: pip install winter-dragon[api]"
    raise ImportError(msg)

app = FastAPI(
    title="Winter Dragon API",
    description="Backend API for Winter Dragon Bot",
    version="0.3.0",
)

@app.get("/")
async def root() -> RedirectResponse:
    """Root endpoint."""
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

for model in models:
    router = APIRouter(
        prefix=f"/{model.__name__.casefold()}",
        responses={404: {"description": "Not found"}},
    )
    api_model = APIModel(model, router)
    app.include_router(api_model.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
