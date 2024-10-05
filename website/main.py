import uvicorn
from app import app


def main() -> None:
    all_addresses = "0.0.0.0"  # noqa: S104
    uvicorn.run(app, host=all_addresses)


if __name__ == "__main__":
    main()
