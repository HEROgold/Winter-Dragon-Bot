"""Unit tests: what the bot traces in Sentry, how often, and the REST spans inside a transaction."""

from typing import TYPE_CHECKING, Any, cast

import pytest
import sentry_sdk
from httpxyz import AsyncClient, MockTransport, Request, Response
from wd_config.sentry import SentrySettings
from wd_discord import Client, Token
from wd_discord.route import Route
from wd_discord.sentry import Sentry, TraceOp, httpx_integrations, traces_sampler, transaction


if TYPE_CHECKING:
    from collections.abc import Generator

    from sentry_sdk._types import Event


@pytest.fixture
def rates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SentrySettings, "traces_sample_rate", 0.5)
    monkeypatch.setattr(SentrySettings, "listener_traces_sample_rate", 0.01)


@pytest.fixture
def traced() -> Generator[list[Event]]:
    """Collect the transactions Sentry would send, every one sampled."""
    transactions: list[Event] = []

    def keep(event: Event, _hint: object) -> None:
        transactions.append(event)

    scope = sentry_sdk.get_global_scope()
    previous = scope.client
    scope.set_client(
        sentry_sdk.Client(
            dsn="https://key@sentry.example/1",
            traces_sample_rate=1.0,
            before_send_transaction=keep,
            disabled_integrations=list(httpx_integrations()),
        ),
    )
    yield transactions
    scope.set_client(previous)


@pytest.mark.usefixtures("rates")
@pytest.mark.parametrize(
    ("op", "rate"),
    [(TraceOp.INTERACTION, 0.5), (TraceOp.PERIODIC, 0.5), (TraceOp.LISTENER, 0.01), ("http.server", 0.5)],
)
def test_listeners_are_sampled_at_their_own_rate(op: str, rate: float) -> None:
    assert traces_sampler({"transaction_context": {"op": op}}) == rate


@pytest.mark.usefixtures("rates")
@pytest.mark.parametrize("parent", [True, False])
def test_a_continued_trace_follows_its_parent(*, parent: bool) -> None:
    assert traces_sampler({"parent_sampled": parent, "transaction_context": {"op": TraceOp.LISTENER}}) == float(parent)


def test_a_route_shape_names_its_parameters_instead_of_their_values() -> None:
    channel_id, token = 5, "secret"

    assert Route(t"/channels/{channel_id}/messages").shape == "/channels/{channel_id}/messages"
    assert Route(t"/interactions/{channel_id}/{token}/callback").shape == "/interactions/{channel_id}/{token}/callback"


async def test_a_rest_call_is_a_span_of_the_transaction(traced: list[Event]) -> None:
    async def answer(request: Request) -> Response:
        return Response(404 if "missing" in request.url.path else 200, json={"code": 10003, "message": "Unknown"})

    client = Client(Token("token"))
    client._client = AsyncClient(base_url=client.base_url, transport=MockTransport(answer))  # noqa: SLF001 - swap the transport
    channel_id, other = 5, "missing"

    with transaction(TraceOp.INTERACTION, "/ping"):
        await client.get(t"/channels/{channel_id}")
        await client.get(t"/channels/{other}")

    (sent,) = traced
    assert (sent["transaction"], sent["contexts"]["trace"]["op"]) == ("/ping", "discord.interaction")
    spans = [(span["op"], span["description"], span.get("status")) for span in cast("list[dict[str, Any]]", sent["spans"])]
    assert spans == [
        ("http.client", "GET /channels/{channel_id}", "ok"),
        ("http.client", "GET /channels/{other}", "not_found"),
    ]


def test_tags_set_in_one_transaction_stay_out_of_the_next(traced: list[Event]) -> None:
    with transaction(TraceOp.LISTENER, "first") as first:
        first.set_tag("discord.event", "MESSAGE_CREATE")
        sentry_sdk.set_tag("leaky", "yes")
    with transaction(TraceOp.LISTENER, "second"):
        pass

    assert "leaky" not in traced[1].get("tags", {})


def test_sentry_leaves_the_httpx_integrations_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """They would trace each REST call under its full URL, interaction tokens included."""
    seen: dict[str, Any] = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **options: seen.update(options))
    monkeypatch.setattr(sentry_sdk, "set_user", lambda _: None)

    Sentry()

    assert {type(integration).__name__ for integration in seen["disabled_integrations"]} == {
        "HttpxIntegration",
        "Httpx2Integration",
    }
    assert seen["traces_sampler"] is traces_sampler


@pytest.mark.parametrize("rate", [0.0, 1.0])
def test_profiling_follows_sentry_ini_during_transactions_only(monkeypatch: pytest.MonkeyPatch, rate: float) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(SentrySettings, "profile_session_sample_rate", rate)
    monkeypatch.setattr(sentry_sdk, "init", lambda **options: seen.update(options))
    monkeypatch.setattr(sentry_sdk, "set_user", lambda _: None)

    Sentry()

    assert (seen["profile_session_sample_rate"], seen["profile_lifecycle"]) == (rate, "trace")
