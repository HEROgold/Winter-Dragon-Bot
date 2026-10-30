"""The shared truncate helper cuts text to a Discord limit the same way for every caller."""

lazy from wd_discord.limits import truncate


def test_text_within_the_limit_is_returned_unchanged() -> None:
    assert truncate("dragon", 6) == "dragon"


def test_text_over_the_limit_ends_in_an_ellipsis_and_fits() -> None:
    assert truncate("winter dragon", 8) == "winter …"
