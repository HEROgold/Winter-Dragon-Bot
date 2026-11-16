"""Unit tests: reference links, the way a dashboard page shows a Discord ID (no network)."""

import pytest
from wd_discord.snowflake import Snowflake

from winter_dragon.web.references import (
    LookupStatus,
    Named,
    ReferenceKind,
    References,
    card_path,
    link,
)
from winter_dragon.web.responses import templates


USER = Snowflake(111)
GUILD = Snowflake(222)
ROLE = Snowflake(333)


def render(reference: object) -> str:
    template = templates.env.from_string('{% from "_references.html" import reference %}{{ reference(link) }}')
    return template.render(link=reference).strip()


def test_found_user_links_to_its_card_by_name() -> None:
    reference = link(ReferenceKind.USER, USER, Named(LookupStatus.FOUND, "Someone"))

    assert reference.href == "/cards/user/111"
    assert reference.label == "Someone"
    assert reference.note is None
    assert render(reference) == '<a href="/cards/user/111">Someone</a>'


def test_role_card_path_includes_its_guild() -> None:
    assert card_path(ReferenceKind.ROLE, ROLE, GUILD) == "/cards/role/222/333"
    with pytest.raises(ValueError, match="guild"):
        card_path(ReferenceKind.ROLE, ROLE)


@pytest.mark.parametrize(
    ("status", "note"),
    [(LookupStatus.UNKNOWN, "Not found on Discord."), (LookupStatus.UNAVAILABLE, "Couldn't load the name right now.")],
)
def test_unnamed_reference_shows_the_plain_id_and_a_note(status: LookupStatus, note: str) -> None:
    reference = link(ReferenceKind.USER, USER, Named(status))

    assert reference.href is None
    assert reference.label == "111"
    assert reference.note == note
    rendered = render(reference)
    assert "<a " not in rendered
    assert "111" in rendered
    assert note.replace("'", "&#39;") in rendered


def test_a_name_is_escaped() -> None:
    reference = link(ReferenceKind.USER, USER, Named(LookupStatus.FOUND, "<b>x</b>"))

    assert "<b>" not in render(reference)


def test_references_without_a_directory_are_plain_ids() -> None:
    references = References()

    # from_thread.run isn't reached without a directory, so no event loop is needed.
    (reference,) = references.users([USER])

    assert reference.status is LookupStatus.UNAVAILABLE
    assert reference.href is None
