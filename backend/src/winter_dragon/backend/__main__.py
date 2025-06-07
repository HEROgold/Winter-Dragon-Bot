"""The main entry point for the Winter Dragon backend."""
import uvicorn

from .app import app


def main() -> None:
    """Run the FastAPI application with uvicorn."""
    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
