"""Light entities for LG OLED Control integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LGTVCoordinator

_LOGGER = logging.getLogger(__name__)


def brightness_to_value(brightness: int) -> int:
    """Convert HA brightness (0-255) to TV value (0-100)."""
    return round(brightness * 100 / 255)


def value_to_brightness(value: int) -> int:
    """Convert TV value (0-100) to HA brightness (0-255)."""
    return round(value * 255 / 100)


@dataclass(frozen=True)
class LGTVLightEntityDescription(LightEntityDescription):
    """Describes LG TV light entity."""

    setting_key: str = ""
    is_combined: bool = False


LIGHT_DESCRIPTIONS: tuple[LGTVLightEntityDescription, ...] = (
    LGTVLightEntityDescription(
        key="backlight",
        name="Backlight",
        icon="mdi:brightness-6",
        setting_key="backlight",
    ),
    LGTVLightEntityDescription(
        key="contrast",
        name="Contrast",
        icon="mdi:contrast-box",
        setting_key="contrast",
    ),
    LGTVLightEntityDescription(
        key="brightness_contrast",
        name="Brightness & Contrast",
        icon="mdi:tune",
        setting_key="",
        is_combined=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light entities from a config entry."""
    coordinator: LGTVCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        LGTVLightEntity(coordinator, entry, description)
        for description in LIGHT_DESCRIPTIONS
    ]

    async_add_entities(entities)


class LGTVLightEntity(LightEntity):
    """Light entity for LG TV brightness controls."""

    entity_description: LGTVLightEntityDescription
    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(
        self,
        coordinator: LGTVCoordinator,
        entry: ConfigEntry,
        description: LGTVLightEntityDescription,
    ) -> None:
        """Initialize the light entity."""
        self.coordinator = coordinator
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.data[CONF_HOST]}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_HOST])},
            name=entry.data.get(CONF_NAME, "LG TV"),
            manufacturer="LG",
            model="OLED TV",
        )
        self._brightness: int = 128  # Default to ~50%
        self._is_on: bool = True

    @property
    def is_on(self) -> bool:
        """Return True if light is on."""
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light / set brightness."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            value = brightness_to_value(brightness)

            try:
                if self.entity_description.is_combined:
                    await self.coordinator.async_set_picture_settings(
                        {"backlight": value, "contrast": value}
                    )
                else:
                    await self.coordinator.async_set_picture_settings(
                        {self.entity_description.setting_key: value}
                    )
                self._brightness = brightness
                self._is_on = True
                self.async_write_ha_state()
            except Exception as err:
                _LOGGER.error(
                    "Failed to set %s to %s: %s",
                    self.entity_description.key,
                    value,
                    err,
                )
        else:
            # Just turn on - set to 100%
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light (set to 0)."""
        try:
            if self.entity_description.is_combined:
                await self.coordinator.async_set_picture_settings(
                    {"backlight": 0, "contrast": 0}
                )
            else:
                await self.coordinator.async_set_picture_settings(
                    {self.entity_description.setting_key: 0}
                )
            self._brightness = 0
            self._is_on = False
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Failed to turn off %s: %s",
                self.entity_description.key,
                err,
            )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()
        # Try to get initial value
        try:
            settings = await self.coordinator.async_get_picture_settings()
            if self.entity_description.is_combined:
                value = settings.get("backlight", 50)
            else:
                value = settings.get(self.entity_description.setting_key, 50)
            self._brightness = value_to_brightness(value)
            self._is_on = value > 0
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.debug("Could not get initial value: %s", err)
