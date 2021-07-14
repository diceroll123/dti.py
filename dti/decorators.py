import functools
import inspect
from typing import Any, Callable


def _require_state(func: Callable[..., Any]):
    # for internal use only.
    # this decorator goes on just about all internal coroutines dealing with the state
    # we use this as an excuse to update the cache in long-running processes
    # if the state has no cache, it will after this runs.
    if not inspect.iscoroutinefunction(func):
        raise TypeError("The require_state decorator only goes on Awaitables")

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with self._state._lock:
            await self._state._update()
            return await func(self, *args, **kwargs)

    return wrapper
