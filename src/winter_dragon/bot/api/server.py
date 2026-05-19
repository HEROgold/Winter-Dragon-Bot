"""FastAPI server for WinterDragon user data and OAuth endpoints."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from winter_dragon.bot.api import router


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Manage app lifecycle."""
    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI app."""
    app = FastAPI(
        title="WinterDragon API",
        description="User data and OAuth endpoints for WinterDragon frontend",
        version="1.0.0",
    )

    # Add CORS middleware for frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/api/login")

    return app


async def run_api_server(host: str = "0.0.0.0", port: int = 8001) -> None:  # noqa: S104
    """Run the FastAPI server."""
    app = create_app()
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def start_api_server() -> FastAPI:
    """Start the API server and return app instance for integration."""
    return create_app()


if __name__ == "__main__":
    asyncio.run(run_api_server())
