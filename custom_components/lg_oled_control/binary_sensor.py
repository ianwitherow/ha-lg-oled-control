"""Binary sensor for LG OLED Control integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LGTVCoordinator

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=3)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor from a config entry."""
    coordinator: LGTVCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([LGTVPowerSensor(coordinator, entry)])


class LGTVPowerSensor(BinarySensorEntity):
    """Binary sensor for TV power state."""

    _attr_has_entity_name = True
    _attr_name = "Power"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(
        self,
        coordinator: LGTVCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.data[CONF_HOST]}_power"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_HOST])},
            name=entry.data.get(CONF_NAME, "LG TV"),
            manufacturer="LG",
            model="OLED TV",
        )
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """Return True if TV is on."""
        return self._is_on

    async def async_update(self) -> None:
        """Check if TV is reachable."""
        self._is_on = await self.coordinator.async_is_on()
