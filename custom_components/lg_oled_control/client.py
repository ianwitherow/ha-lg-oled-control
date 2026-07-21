"""Hardened WebOsClient subclass for LG OLED Control.

bscpylgtv 0.5.2's connection teardown is broken on Python 3.11+ in ways that
leave a permanently corrupted client after a disconnect:

- ``connect_handler``'s cleanup passes state-update-callback *coroutines* to
  ``asyncio.wait``, which raises ``TypeError`` on Python 3.11+ and skips the
  client's post-disconnect reset (``connection``, ``connect_task``,
  ``handler_tasks``, ``futures``, ...). The client can then report
  ``is_connected() == True`` with a closed socket indefinitely: commands fail
  with ``ConnectionClosedOK`` and the TV reads as permanently on.
- ``set_power_state`` reacts to the TV reporting standby by calling
  ``disconnect()`` from inside a consumer callback task. The teardown cancels
  that same callback task, the ``CancelledError`` is swallowed inside
  ``disconnect()``, and the consumer handler deadlocks forever ("Task was
  destroyed but it is pending!" in HA's log).
- ``ping_handler`` only pings while the TV reports on, so a connection that
  dies silently while the TV is in standby is never detected.

This subclass avoids all three without patching the library:

- State updates are delivered through a plain synchronous callback instead of
  ``register_state_update_callback``, so ``state_update_callbacks`` stays
  empty and the teardown path never sees a coroutine: cleanup completes and
  the client resets itself on every disconnect.
- ``set_power_state`` just records the state. The coordinator owns the
  connection lifecycle; a TV in standby may keep a live connection, which
  makes power-on push instantly.
- ``ping_handler`` always pings, so a dead connection is torn down within
  ping_interval + ping_timeout regardless of reported power state.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import websockets
from bscpylgtv import WebOsClient


class LGTVWebOsClient(WebOsClient):
    """WebOsClient with safe teardown, no auto-disconnect, always-on pings."""

    def __init__(
        self,
        *args: Any,
        on_state_change: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the client."""
        super().__init__(*args, **kwargs)
        self._on_state_change = on_state_change

    def _notify(self) -> None:
        """Notify the owner of a state change (sync, event-loop safe)."""
        if self._on_state_change is not None and self.doStateUpdate:
            self._on_state_change()

    async def set_power_state(self, payload: Any) -> None:
        """Record the TV power state without upstream's auto-disconnect."""
        self._power_state = {"state": payload.get("state", "Unknown")}
        self._notify()

    async def set_current_app_state(self, appId: Any) -> None:
        """Record the current app; skip upstream's channel subscriptions."""
        self._current_appId = appId
        self._notify()

    async def set_picture_settings_state(self, picture_settings: Any) -> None:
        """Record picture settings pushed by the TV."""
        if isinstance(self._picture_settings, dict) and isinstance(
            picture_settings, dict
        ):
            self._picture_settings.update(picture_settings)
        else:
            self._picture_settings = picture_settings
        self._notify()

    async def ping_handler(self, ws: Any) -> None:
        """Keep-alive that pings regardless of reported power state."""
        try:
            while True:
                await asyncio.sleep(self.ping_interval)
                ping_waiter = await ws.ping()
                await asyncio.wait_for(ping_waiter, timeout=self.ping_timeout)
        except (
            asyncio.TimeoutError,
            asyncio.CancelledError,
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
        ):
            pass
