"""LG OLED Control integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from .const import CONF_CLIENT_KEY, DOMAIN, PLATFORMS
from .coordinator import LGTVCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LG OLED Control from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # The coordinator registers its own shutdown on entry unload via
    # config_entry; entries aren't unloaded on HA stop, hence the listener.
    coordinator = LGTVCoordinator(
        hass,
        entry,
        host=entry.data[CONF_HOST],
        client_key=entry.data[CONF_CLIENT_KEY],
        name=entry.data.get(CONF_NAME, "LG TV"),
    )

    # Never raises: an unreachable TV loads as "off", not a setup failure.
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    async def _async_on_hass_stop(event: Event) -> None:
        await coordinator.async_shutdown()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_on_hass_stop)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
