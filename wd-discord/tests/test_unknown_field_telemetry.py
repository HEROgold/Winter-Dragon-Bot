"""Unknown Discord fields reach Sentry as one issue per model and field set, whatever the values."""

from typing import TYPE_CHECKING

import pytest
import sentry_sdk
from wd_config.sentry import SentrySettings
from wd_discord.models import DiscordModel


if TYPE_CHECKING:
    from collections.abc import Generator

    from sentry_sdk._types import Event


class Sample(DiscordModel):
    """A model with one declared field, so anything else is unknown."""

    id: str


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> Generator[list[Event]]:
    """Collect the events Sentry would send, with telemetry turned on."""
    monkeypatch.setattr(SentrySettings, "Telemetry", True)
    events: list[Event] = []

    def keep(event: Event, _hint: object) -> None:
        events.append(event)

    scope = sentry_sdk.get_global_scope()
    previous = scope.client
    scope.set_client(sentry_sdk.Client(dsn="https://key@sentry.example/1", before_send=keep))
    yield events
    scope.set_client(previous)


def test_values_do_not_split_the_issue(sent: list[Event]) -> None:
    """Two payloads with the same unknown keys but different values share message and fingerprint."""
    Sample.model_validate({"id": "1", "version": 1, "status": None})
    Sample.model_validate({"id": "2", "status": "x", "version": 2})

    assert len(sent) == 2
    assert sent[0]["fingerprint"] == sent[1]["fingerprint"] == ["wd-discord-unknown-fields", "Sample", "status", "version"]
    assert sent[0]["message"] == sent[1]["message"] == "wd-discord: unknown fields on Sample: status, version"
    assert sent[1]["contexts"]["unknown_fields"] == {"status": "'x'", "version": "2"}


def test_each_set_of_unknown_fields_is_logged_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A payload repeated hundreds of times (a GUILD_CREATE's members) logs its unknown fields once."""
    from wd_discord import models  # noqa: PLC0415 - patching the module the reporter lives in

    logged: list[object] = []

    class Logger:
        def warning(self, message: object) -> None:
            logged.append(message)

    monkeypatch.setattr(models, "_logged", set())
    monkeypatch.setattr(models, "logger", Logger())
    Sample.model_validate({"id": "1", "version": 1})
    Sample.model_validate({"id": "2", "version": 2})
    Sample.model_validate({"id": "3", "status": "x"})

    assert len(logged) == 2
