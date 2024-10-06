import uvicorn

from website.app import site


def main() -> None:
    all_addresses = "0.0.0.0"  # noqa: S104
    uvicorn.run(site, host=all_addresses)


if __name__ == "__main__":
    main()
