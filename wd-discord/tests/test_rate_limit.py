"""Unit tests: rate-limit models, scope resolution, and the limiter classes."""

from __future__ import annotations

lazy from datetime import UTC, datetime, timedelta

lazy import pytest
lazy from wd_discord import rate_limit as rate_limit_module
lazy from wd_discord.rate_limit import (
    BucketRateLimiter,
    Buckets,
    GlobalRateLimiter,
    HeaderFormat,
    ScopeError,
    SharedRateLimiter,
)


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


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Fake ``time.monotonic()``/``asyncio.sleep()`` sharing one advancing clock.

    A "sleep" advances the shared clock by its delay instead of actually waiting, so tests that
    exercise real waiting logic run instantly and can assert on exactly how long it waited.
    """
    clock = [0.0]

    def fake_monotonic() -> float:
        return clock[0]

    async def fake_sleep(delay: float) -> None:
        clock[0] += delay

    monkeypatch.setattr(rate_limit_module.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(rate_limit_module.asyncio, "sleep", fake_sleep)
    return clock


async def test_global_limiter_allows_up_to_limit_without_waiting(fake_clock: list[float]) -> None:
    limiter = GlobalRateLimiter(limit=2)
    await limiter.acquire("k")
    await limiter.acquire("k")
    assert fake_clock[0] == 0.0


async def test_global_limiter_waits_for_window_when_exhausted(fake_clock: list[float]) -> None:
    limiter = GlobalRateLimiter(limit=1)
    await limiter.acquire("k")
    await limiter.acquire("k")
    assert fake_clock[0] == pytest.approx(1.0)


async def test_global_limiter_on_429_sleeps_retry_after(fake_clock: list[float]) -> None:
    await GlobalRateLimiter().on_429("k", 2.5)
    assert fake_clock[0] == pytest.approx(2.5)


async def test_bucket_limiter_unseen_route_proceeds_immediately(fake_clock: list[float]) -> None:
    await BucketRateLimiter().acquire("GET /never-seen")
    assert fake_clock[0] == 0.0


async def test_bucket_limiter_waits_for_reset_when_exhausted(fake_clock: list[float]) -> None:
    limiter = BucketRateLimiter()
    limiter.update(
        "GET /x",
        {"X-RateLimit-Bucket": "abc", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset-After": "3"},
    )
    await limiter.acquire("GET /x")
    assert fake_clock[0] == pytest.approx(3.0)


async def test_bucket_limiter_does_not_wait_while_remaining(fake_clock: list[float]) -> None:
    limiter = BucketRateLimiter()
    limiter.update(
        "GET /x",
        {"X-RateLimit-Bucket": "abc", "X-RateLimit-Remaining": "1", "X-RateLimit-Reset-After": "3"},
    )
    await limiter.acquire("GET /x")
    assert fake_clock[0] == 0.0


async def test_bucket_limiter_shares_state_across_keys_via_bucket_id(fake_clock: list[float]) -> None:
    limiter = BucketRateLimiter()
    headers = {"X-RateLimit-Bucket": "shared-bucket", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset-After": "2"}
    limiter.update("GET /a", headers)
    limiter.update("GET /b", headers)  # different route key, same Discord bucket

    await limiter.acquire("GET /b")

    assert fake_clock[0] == pytest.approx(2.0)


async def test_bucket_limiter_on_429_sleeps_retry_after(fake_clock: list[float]) -> None:
    await BucketRateLimiter().on_429("GET /x", 1.5)
    assert fake_clock[0] == pytest.approx(1.5)


async def test_shared_limiter_acquire_and_update_are_noops(fake_clock: list[float]) -> None:
    limiter = SharedRateLimiter()
    await limiter.acquire("k")
    limiter.update("k", {})
    assert fake_clock[0] == 0.0


async def test_shared_limiter_on_429_sleeps_retry_after(fake_clock: list[float]) -> None:
    await SharedRateLimiter().on_429("k", 0.75)
    assert fake_clock[0] == pytest.approx(0.75)
