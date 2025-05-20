"""The main entry point for the Winter Dragon backend."""
import uvicorn


def main() -> None:
    """Run the FastAPI application with uvicorn."""
    uvicorn.run(
        "winter_dragon.backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
