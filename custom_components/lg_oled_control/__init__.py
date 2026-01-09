"""LG OLED Control integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import CONF_CLIENT_KEY, DOMAIN, PLATFORMS
from .coordinator import LGTVCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LG OLED Control from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = LGTVCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        client_key=entry.data[CONF_CLIENT_KEY],
        name=entry.data.get(CONF_NAME, "LG TV"),
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
