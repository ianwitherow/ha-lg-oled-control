"""Shared base entity for LG OLED Control integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LGTVCoordinator


class LGTVEntity(CoordinatorEntity[LGTVCoordinator]):
    """Base entity: device info, unique id, and TV-on availability."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LGTVCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data[CONF_HOST]}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_HOST])},
            name=entry.data.get(CONF_NAME, "LG TV"),
            manufacturer="LG",
            model="OLED TV",
        )

    @property
    def tv_is_on(self) -> bool:
        """Return True if the TV is on."""
        data = self.coordinator.data
        return bool(data and data.get("is_on"))

    @property
    def available(self) -> bool:
        """Only usable while the TV is on."""
        return super().available and self.tv_is_on
