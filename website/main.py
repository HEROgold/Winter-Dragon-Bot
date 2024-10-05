import uvicorn
from api import router as api_router
from app import app
from router import router as global_router


def main() -> None:
    uvicorn.run(app)
    global_router.include_router(api_router)


if __name__ == "__main__":
    main()
