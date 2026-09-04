"""Unit tests: rate-limit models and scope resolution."""
from __future__ import annotations

lazy from datetime import UTC, datetime, timedelta

lazy import pytest
lazy from wd_discord.rate_limit import Buckets, HeaderFormat, ScopeError


def _header(*, global_: bool | None = None, scope: str | None = None) -> HeaderFormat:
    return HeaderFormat(
        limit=5,
        remaining=0,
        reset=datetime(2016, 8, 2, tzinfo=UTC),
        reset_after=timedelta(seconds=1),
        bucket=Buckets.per_endpoint,
        _global=global_,
        _scope=scope,
    )


def test_bucket_values() -> None:
    assert Buckets.global_ == "global_"
    assert Buckets.per_endpoint == "per_endpoint"
    assert Buckets.per_user == "per_user"
    assert Buckets.shared == "shared"


def test_scope_global() -> None:
    assert _header(global_=True).scope == "global"


def test_scope_named() -> None:
    assert _header(scope="user").scope == "user"


def test_scope_requires_exactly_one() -> None:
    with pytest.raises(ScopeError):
        _ = _header(global_=True, scope="user").scope
    with pytest.raises(ScopeError):
        _ = _header().scope
