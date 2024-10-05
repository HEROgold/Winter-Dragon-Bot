import uvicorn
from api import router as api_router
from app import app
from router import router as global_router


def main() -> None:
    all_addresses = "0.0.0.0"  # noqa: S104
    global_router.include_router(api_router)
    uvicorn.run(app, host=all_addresses)


if __name__ == "__main__":
    main()
