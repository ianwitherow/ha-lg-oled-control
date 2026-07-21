"""Light entities for LG OLED Control integration."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from .const import DOMAIN
from .coordinator import LGTVCoordinator
from .entity import LGTVEntity

BRIGHTNESS_SCALE = (1, 100)  # TV picture settings range


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


class LGTVLightEntity(LGTVEntity, LightEntity):
    """Light entity for LG TV brightness controls."""

    entity_description: LGTVLightEntityDescription
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(
        self,
        coordinator: LGTVCoordinator,
        entry: ConfigEntry,
        description: LGTVLightEntityDescription,
    ) -> None:
        """Initialize the light entity."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description
        self._last_on_value: int | None = None

    @property
    def _value(self) -> int:
        """Return the TV-side value (0-100) this entity tracks."""
        data = self.coordinator.data or {}
        if self.entity_description.is_combined:
            return data.get("backlight", 0)
        return data.get(self.entity_description.setting_key, 0)

    @property
    def is_on(self) -> bool:
        """Return True if light is on."""
        return self._value > 0

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        value = self._value
        return value_to_brightness(BRIGHTNESS_SCALE, value) if value > 0 else None

    def _settings_for(self, value: int) -> dict[str, int]:
        """Build the settings payload for this entity."""
        if self.entity_description.is_combined:
            return {"backlight": value, "contrast": value}
        return {self.entity_description.setting_key: value}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light / set brightness."""
        if ATTR_BRIGHTNESS in kwargs:
            value = math.ceil(
                brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS])
            )
        else:
            # Restore the value from before turn_off; full brightness if unknown.
            value = self._last_on_value or 100
        await self.coordinator.async_set_picture_settings(self._settings_for(value))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light (set to 0)."""
        if self._value > 0:
            self._last_on_value = self._value
        await self.coordinator.async_set_picture_settings(self._settings_for(0))
