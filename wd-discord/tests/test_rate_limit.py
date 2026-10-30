"""Unit tests: the rate-limiter classes."""

lazy import pytest
lazy from httpxyz import AsyncClient, MockTransport, Response
lazy from wd_discord import Client
lazy from wd_discord import rate_limit as rate_limit_module
lazy from wd_discord.rate_limit import (
    BucketRateLimiter,
    GlobalRateLimiter,
    SharedRateLimiter,
)


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


def _client_answering(token: str, headers: dict[str, str]) -> Client:
    """A client for ``token`` whose every request gets a 200 carrying ``headers``."""
    client = Client(token)
    transport = MockTransport(lambda _request: Response(200, json={}, headers=headers))
    client._client = AsyncClient(base_url=client.base_url, transport=transport)  # noqa: SLF001 - swap the transport
    return client


EXHAUSTED = {"X-RateLimit-Bucket": "abc", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset-After": "3"}


async def test_a_client_waits_on_its_own_exhausted_bucket(fake_clock: list[float]) -> None:
    client = _client_answering("token-a", EXHAUSTED)
    await client.post(t"/channels/{1}/messages")
    await client.post(t"/channels/{1}/messages")
    assert fake_clock[0] == pytest.approx(3.0)


async def test_clients_with_different_tokens_do_not_share_buckets(fake_clock: list[float]) -> None:
    first = _client_answering("token-a", EXHAUSTED)
    second = _client_answering("token-b", EXHAUSTED)
    await first.post(t"/channels/{1}/messages")
    await second.post(t"/channels/{1}/messages")
    assert fake_clock[0] == 0.0
