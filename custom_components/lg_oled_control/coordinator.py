"""Coordinator for LG OLED Control integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from functools import partial
import logging
from typing import Any

import websockets
from bscpylgtv import PyLGTVPairException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import LGTVWebOsClient
from .const import (
    CLIENT_STATES,
    COMMAND_TIMEOUT,
    CONNECT_RETRY_ATTEMPTS,
    CONNECT_TIMEOUT,
    DEFAULT_BACKLIGHT,
    DEFAULT_CONTRAST,
    DISCONNECT_TIMEOUT,
    DOMAIN,
    PING_INTERVAL,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class LGTVCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Maintains a connection to the TV and its state.

    State (power, backlight, contrast) is pushed by the TV via the client's
    state callback; the periodic update acts as the reconnect loop and a
    fallback poll. Every connection gets a fresh client object so no state
    (tasks, futures, sockets) can leak from a bad connection into the next
    one. Data shape: {"is_on": bool, "backlight": int, "contrast": int} —
    picture values are last-known and survive the TV being off.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        host: str,
        client_key: str,
        name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{name}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
            always_update=False,
        )
        self._host = host
        self._client_key = client_key
        self._name = name
        self._client: LGTVWebOsClient | None = None
        self._connect_task: asyncio.Task | None = None
        self._last_picture: dict[str, int] = {
            "backlight": DEFAULT_BACKLIGHT,
            "contrast": DEFAULT_CONTRAST,
        }
        self._closed = False
        self._pair_warned = False

    @property
    def host(self) -> str:
        """Return the TV host."""
        return self._host

    @property
    def tv_name(self) -> str:
        """Return the TV name."""
        return self._name

    def _client_connected(self) -> bool:
        """Return True if the client has a live, open websocket.

        Deliberately does not trust the client's is_connected() alone: a
        wedged client task holding a closed socket must read as disconnected,
        or the coordinator would never reconnect and the TV would show as on
        forever while every command fails.
        """
        client = self._client
        if client is None or not client.is_connected():
            return False
        connection = client.connection
        if connection is None:
            return False
        state = getattr(connection, "state", None)
        return state is None or getattr(state, "name", "OPEN") == "OPEN"

    def _build_data(self) -> dict[str, Any]:
        """Build the coordinator data dict (single source of truth)."""
        client = self._client
        is_on = bool(self._client_connected() and client.is_on)
        return {"is_on": is_on, **self._last_picture}

    @callback
    def _push_data(self) -> None:
        """Publish current data to listeners if it changed."""
        data = self._build_data()
        if data != self.data:
            self.async_set_updated_data(data)

    def _handle_client_state_change(self) -> None:
        """Handle a state push from the TV (runs in the event loop)."""
        client = self._client
        if client is None:
            return
        picture = client.picture_settings or {}
        for key in self._last_picture:
            value = picture.get(key)
            if isinstance(value, int):
                self._last_picture[key] = value
        self._push_data()

    async def _async_dispose_client(self) -> None:
        """Tear down the current client, tolerating a wedged one."""
        client, self._client = self._client, None
        if client is None:
            return
        try:
            await asyncio.wait_for(client.disconnect(), timeout=DISCONNECT_TIMEOUT)
        except Exception:
            # Abandon it; its tasks were cancelled and anything left gets
            # collected. A fresh client replaces it either way.
            _LOGGER.debug("Client for %s did not disconnect cleanly", self._host)

    async def _async_connect(self) -> None:
        """One connect attempt. Only ever runs inside self._connect_task."""
        await self._async_dispose_client()
        # The constructor builds an SSL context (blocking disk I/O), so
        # run it in the executor.
        client = await self.hass.async_add_executor_job(
            partial(
                LGTVWebOsClient,
                self._host,
                client_key=self._client_key,
                states=CLIENT_STATES,
                ping_interval=PING_INTERVAL,
                connect_retry_attempts=CONNECT_RETRY_ATTEMPTS,
                on_state_change=self._handle_client_state_change,
            )
        )
        await client.async_init()
        self._client = client
        try:
            await asyncio.wait_for(client.connect(), timeout=CONNECT_TIMEOUT)
        except BaseException:
            # Don't leak a half-open connection: a timed-out connect leaves
            # the library's connect_task running in the background.
            await self._async_dispose_client()
            raise

        client.connect_task.add_done_callback(
            partial(self._handle_connect_task_done, client)
        )
        self._pair_warned = False
        self._push_data()
        _LOGGER.debug("Connected to TV at %s", self._host)

    async def _async_ensure_connected(self) -> None:
        """Connect to the TV if not already connected.

        Concurrent callers (poll + commands) share a single connect attempt.
        """
        if self._closed:
            raise HomeAssistantError("Integration is shutting down")
        if self._client_connected():
            return
        if self._connect_task is None or self._connect_task.done():
            self._connect_task = self.hass.async_create_task(
                self._async_connect(), name=f"{DOMAIN}_{self._name}_connect"
            )
        # shield: one caller being cancelled must not abort the shared attempt
        await asyncio.shield(self._connect_task)

    def _handle_connect_task_done(
        self, client: LGTVWebOsClient, _task: asyncio.Task
    ) -> None:
        """Handle the connection ending (runs in the event loop)."""
        if self._closed or client is not self._client:
            return
        _LOGGER.debug("Connection to TV at %s ended", self._host)
        # Reconnect right away rather than pushing "off" immediately: a
        # transient drop recovers without the power sensor flapping, while a
        # TV that really turned off fails the reconnect and settles as off.
        self.hass.async_create_task(self.async_request_refresh())

    async def _async_update_data(self) -> dict[str, Any]:
        """Reconnect if needed and return current state.

        Never raises: an unreachable TV is a normal state (off), not an
        update failure — entities must not become unavailable.
        """
        try:
            await self._async_ensure_connected()
        except PyLGTVPairException:
            if not self._pair_warned:
                self._pair_warned = True
                _LOGGER.warning(
                    "TV at %s rejected the pairing key; remove and re-add "
                    "the integration to pair again",
                    self._host,
                )
        except Exception as err:
            _LOGGER.debug(
                "TV at %s unreachable: %s", self._host, type(err).__name__
            )
        return self._build_data()

    async def async_execute(
        self, func_name: str, *args: Any, expect_disconnect: bool = False, **kwargs: Any
    ) -> Any:
        """Execute a command on the TV.

        Retries once through a reconnect if the connection was dropped;
        never retries otherwise (commands like volume_up aren't idempotent).
        With expect_disconnect, the TV closing the connection mid-command is
        treated as success (power_off).
        """
        for attempt in range(2):
            try:
                await self._async_ensure_connected()
            except HomeAssistantError:
                raise
            except PyLGTVPairException as err:
                raise HomeAssistantError(
                    f"TV at {self._host} rejected the pairing key; remove and "
                    "re-add the integration to pair again"
                ) from err
            except Exception as err:
                raise HomeAssistantError(
                    f"TV at {self._host} is unreachable"
                ) from err

            client = self._client
            try:
                func = getattr(client, func_name)
                return await asyncio.wait_for(func(*args, **kwargs), COMMAND_TIMEOUT)
            except asyncio.CancelledError:
                task = asyncio.current_task()
                if task is not None and task.cancelling():
                    # Genuine external cancellation (HA cancelling the call),
                    # not the library cancelling futures on teardown.
                    raise
                err = ConnectionError("Connection dropped mid-command")
            except Exception as caught:
                err = caught

            # A closed-connection error counts as dropped even if the client
            # still claims to be connected — that combination means the
            # client is wedged and must be replaced, not trusted.
            dropped = not self._client_connected() or isinstance(
                err, (ConnectionError, websockets.exceptions.ConnectionClosed)
            )
            if dropped and expect_disconnect:
                return None
            if not dropped or attempt == 1:
                raise HomeAssistantError(
                    f"Command {func_name} failed: {type(err).__name__}"
                ) from err
            # Connection dropped mid-command: replace the client and retry
            # once (ensure_connected builds a fresh one after disposal).
            await self._async_dispose_client()

        raise HomeAssistantError(f"Command {func_name} failed")  # unreachable

    async def async_set_picture_settings(self, settings: dict[str, int]) -> None:
        """Set picture settings, updating state optimistically.

        The picture_settings subscription confirms/corrects shortly after.
        """
        await self.async_execute("set_settings", "picture", settings)
        for key, value in settings.items():
            if key in self._last_picture:
                self._last_picture[key] = value
        self._push_data()

    async def async_volume_up(self) -> None:
        """Increase volume."""
        await self.async_execute("volume_up")

    async def async_volume_down(self) -> None:
        """Decrease volume."""
        await self.async_execute("volume_down")

    async def async_channel_up(self) -> None:
        """Next channel."""
        await self.async_execute("channel_up")

    async def async_channel_down(self) -> None:
        """Previous channel."""
        await self.async_execute("channel_down")

    async def async_power_off(self) -> None:
        """Turn off the TV.

        The TV dropping the connection in response is success, not an error.
        """
        await self.async_execute("power_off", expect_disconnect=True)
        self.async_set_updated_data({**self._build_data(), "is_on": False})

    async def async_shutdown(self) -> None:
        """Disconnect and stop the coordinator."""
        self._closed = True
        if self._connect_task is not None and not self._connect_task.done():
            self._connect_task.cancel()
            try:
                await self._connect_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        await self._async_dispose_client()
        await super().async_shutdown()
