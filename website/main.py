import uvicorn
from app import app
from config import config


def main() -> None:
    all_addresses = "0.0.0.0"  # noqa: S104
    uvicorn.run(app, host=all_addresses, port=config.getint("Main", "port"))


if __name__ == "__main__":
    main()
