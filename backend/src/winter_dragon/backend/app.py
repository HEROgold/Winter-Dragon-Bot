"""Winter Dragon Bot API main module.

This module initializes the FastAPI application and includes all API routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .api.v1 import router as v1_router


app = FastAPI(
    title="Winter Dragon Bot API",
    description="API for Winter Dragon Discord bot management and configuration",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with the actual frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(v1_router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root endpoint to API documentation."""
    return RedirectResponse(url="/docs")
