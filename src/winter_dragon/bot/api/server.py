"""FastAPI server for WinterDragon user data and OAuth endpoints."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from winter_dragon.bot.api import router


# Store the running app instance
_app_instance: FastAPI | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
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

    return app


async def run_api_server(host: str = "0.0.0.0", port: int = 8001) -> None:
    """Run the FastAPI server."""
    import uvicorn

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
    global _app_instance
    _app_instance = create_app()
    return _app_instance


if __name__ == "__main__":
    asyncio.run(run_api_server())
