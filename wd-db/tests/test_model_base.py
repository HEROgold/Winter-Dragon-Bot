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
