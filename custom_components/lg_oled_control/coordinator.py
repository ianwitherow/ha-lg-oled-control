"""Coordinator for LG OLED Control integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from bscpylgtv import WebOsClient
from websockets.exceptions import WebSocketException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_TIMEOUT, DOMAIN, MAX_RETRIES, RETRY_DELAY

_LOGGER = logging.getLogger(__name__)


class LGTVCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for LG TV data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        client_key: str,
        name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{name}",
            update_interval=None,  # We'll update on-demand
        )
        self._host = host
        self._client_key = client_key
        self._name = name
        self._client: WebOsClient | None = None

    @property
    def host(self) -> str:
        """Return the TV host."""
        return self._host

    @property
    def tv_name(self) -> str:
        """Return the TV name."""
        return self._name

    async def _async_connect(self) -> WebOsClient:
        """Connect to the TV with retry logic."""
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                client = await WebOsClient.create(
                    self._host,
                    client_key=self._client_key,
                    ping_interval=None,
                    states=[],
                )
                await asyncio.wait_for(client.connect(), timeout=DEFAULT_TIMEOUT)
                return client
            except (
                TimeoutError,
                asyncio.TimeoutError,
                asyncio.CancelledError,
                ConnectionError,
                OSError,
                WebSocketException,
            ) as err:
                last_error = err
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY * attempt
                    _LOGGER.debug(
                        "Connection attempt %d failed: %s. Retrying in %ds...",
                        attempt,
                        type(err).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)

        raise ConnectionError(
            f"Failed to connect to TV after {MAX_RETRIES} attempts"
        ) from last_error

    async def async_execute(self, func_name: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a command on the TV."""
        client = await self._async_connect()
        try:
            func = getattr(client, func_name)
            return await func(*args, **kwargs)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    async def async_get_picture_settings(self) -> dict[str, int]:
        """Get current picture settings."""
        try:
            settings = await self.async_execute(
                "get_picture_settings", ["backlight", "contrast"]
            )
            return {
                "backlight": settings.get("backlight", 50),
                "contrast": settings.get("contrast", 50),
            }
        except Exception as err:
            _LOGGER.warning("Failed to get picture settings: %s", err)
            return {"backlight": 50, "contrast": 50}

    async def async_set_picture_settings(self, settings: dict[str, int]) -> None:
        """Set picture settings."""
        await self.async_execute("set_settings", "picture", settings)

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
        """Turn off the TV."""
        await self.async_execute("power_off")

    async def async_is_on(self) -> bool:
        """Quick check if TV is reachable (no retries)."""
        try:
            client = await WebOsClient.create(
                self._host,
                client_key=self._client_key,
                ping_interval=None,
                states=[],
            )
            await asyncio.wait_for(client.connect(), timeout=2)
            await client.disconnect()
            return True
        except Exception:
            return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from TV."""
        try:
            return await self.async_get_picture_settings()
        except Exception as err:
            raise UpdateFailed(f"Failed to update TV data: {err}") from err
