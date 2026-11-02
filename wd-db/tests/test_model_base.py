"""wd-db has one model base, the lifecycle model; the retired bases are gone."""

import importlib

import pytest

import wd_db


@pytest.mark.parametrize("module", ["wd_db.extension.model", "wd_db.extension.api_table", "wd_db.extras"])
def test_retired_model_bases_are_gone(module: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_package_does_not_export_a_model_base() -> None:
    assert not hasattr(wd_db, "SQLModel")


def test_an_anonymised_column_cannot_be_part_of_a_natural_key() -> None:
    from typing import ClassVar

    from sqlmodel import Field

    from wd_db.extension.lifecycle import LifecycleModel

    with pytest.raises(TypeError, match="GuardKeyedAnonymised anonymises member_id, so it can't be part of a unique key"):

        class GuardKeyedAnonymised(LifecycleModel, table=True):
            natural_key: ClassVar[tuple[str, ...]] = ("member_id", "guild_id")
            anonymised: ClassVar[tuple[str, ...]] = ("member_id",)

            member_id: int = Field(default=0)
            guild_id: int = Field(default=0)


def test_an_anonymised_column_cannot_be_part_of_an_alive_unique_key() -> None:
    from typing import ClassVar

    from sqlmodel import Field

    from wd_db.extension.lifecycle import LifecycleModel

    with pytest.raises(TypeError, match="GuardAliveAnonymised anonymises member_id, so it can't be part of a unique key"):

        class GuardAliveAnonymised(LifecycleModel, table=True):
            alive_unique: ClassVar[tuple[str, ...]] = ("member_id",)
            anonymised: ClassVar[tuple[str, ...]] = ("member_id",)

            member_id: int = Field(default=0)
