"""Binary sensor for LG OLED Control integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LGTVCoordinator
from .entity import LGTVEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor from a config entry."""
    coordinator: LGTVCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([LGTVPowerSensor(coordinator, entry)])


class LGTVPowerSensor(LGTVEntity, BinarySensorEntity):
    """Binary sensor for TV power state."""

    _attr_name = "Power"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(
        self,
        coordinator: LGTVCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, "power")

    @property
    def is_on(self) -> bool:
        """Return True if TV is on."""
        return self.tv_is_on

    @property
    def available(self) -> bool:
        """An unreachable TV reads as off, never unavailable."""
        return True
