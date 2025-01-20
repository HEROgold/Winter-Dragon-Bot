import uvicorn


def main() -> None:
    from app import site
    all_addresses = "0.0.0.0"  # noqa: S104
    uvicorn.run(site, host=all_addresses)


if __name__ == "__main__":
    main()
