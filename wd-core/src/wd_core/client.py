"""Domain specific web-client for WD."""
from __future__ import annotations

lazy from httpxyz import AsyncClient as _AsyncClient


class AsyncClient(_AsyncClient):
    """Async client for WD."""
