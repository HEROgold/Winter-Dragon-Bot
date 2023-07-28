from asyncio import iscoroutinefunction
from functools import lru_cache, wraps
from time import monotonic
from typing import Any


def memoize(func):
    """
    (c) 2021 Nathan Henrie, MIT License
    https://n8henrie.com/2021/11/decorator-to-memoize-sync-or-async-functions-in-python/
    """
    cache = {}

    async def memoized_async_func(*args, **kwargs) -> Any:
        key = (args, frozenset(sorted(kwargs.items())))
        if key in cache:
            return cache[key]
        result = await func(*args, **kwargs)
        cache[key] = result
        return result

    def memoized_sync_func(*args, **kwargs) -> Any:
        key = (args, frozenset(sorted(kwargs.items())))
        if key in cache:
            return cache[key]
        result = func(*args, **kwargs)
        cache[key] = result
        return result

    return memoized_async_func if iscoroutinefunction(func) else memoized_sync_func


def lru_cache_with_ttl(maxsize=128, typed=False, ttl=60):
    """
    Least-recently used cache with time-to-live (ttl) limit.
    https://stackoverflow.com/a/71634221
    """

    class Result:
        __slots__ = ('value', 'death')

        def __init__(self, value, death):
            self.value = value
            self.death = death

    def decorator(func):
        @lru_cache(maxsize=maxsize, typed=typed)
        def cached_func(*args, **kwargs):
            value = func(*args, **kwargs)
            death = monotonic() + ttl
            return Result(value, death)

        @wraps(func)
        def wrapper(*args, **kwargs):
            result = cached_func(*args, **kwargs)
            if result.death < monotonic():
                result.value = func(*args, **kwargs)
                result.death = monotonic() + ttl
            return result.value

        wrapper.cache_clear = cached_func.cache_clear
        return wrapper

    return decorator
