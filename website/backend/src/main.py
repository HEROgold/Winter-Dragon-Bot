import uvicorn
from pages.base import COMPONENTS_DIR, STATIC_DIR, TEMPLATES_DIR


def main() -> None:
    from app import site
    all_addresses = "0.0.0.0"  # noqa: S104
    uvicorn.run(site, host=all_addresses)


def create_directories() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    COMPONENTS_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    create_directories()
    main()
