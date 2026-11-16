"""Unknown Discord fields are logged once per model and field set."""

import pytest
from wd_discord.models import DiscordModel


class Sample(DiscordModel):
    """A model with one declared field, so anything else is unknown."""

    id: str


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
