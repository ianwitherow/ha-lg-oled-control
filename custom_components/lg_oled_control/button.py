"""Button entities for LG OLED Control integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LGTVCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LGTVButtonEntityDescription(ButtonEntityDescription):
    """Describes LG TV button entity."""

    press_fn: Callable[[LGTVCoordinator], Awaitable[None]] | None = None


BUTTON_DESCRIPTIONS: tuple[LGTVButtonEntityDescription, ...] = (
    LGTVButtonEntityDescription(
        key="volume_up",
        name="Volume Up",
        icon="mdi:volume-plus",
        press_fn=lambda coord: coord.async_volume_up(),
    ),
    LGTVButtonEntityDescription(
        key="volume_down",
        name="Volume Down",
        icon="mdi:volume-minus",
        press_fn=lambda coord: coord.async_volume_down(),
    ),
    LGTVButtonEntityDescription(
        key="channel_up",
        name="Channel Up",
        icon="mdi:chevron-up-box",
        press_fn=lambda coord: coord.async_channel_up(),
    ),
    LGTVButtonEntityDescription(
        key="channel_down",
        name="Channel Down",
        icon="mdi:chevron-down-box",
        press_fn=lambda coord: coord.async_channel_down(),
    ),
    LGTVButtonEntityDescription(
        key="power_off",
        name="Power Off",
        icon="mdi:power",
        press_fn=lambda coord: coord.async_power_off(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry."""
    coordinator: LGTVCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        LGTVButtonEntity(coordinator, entry, description)
        for description in BUTTON_DESCRIPTIONS
    ]

    async_add_entities(entities)


class LGTVButtonEntity(ButtonEntity):
    """Button entity for LG TV actions."""

    entity_description: LGTVButtonEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LGTVCoordinator,
        entry: ConfigEntry,
        description: LGTVButtonEntityDescription,
    ) -> None:
        """Initialize the button entity."""
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

    async def async_press(self) -> None:
        """Handle button press."""
        if self.entity_description.press_fn is not None:
            try:
                await self.entity_description.press_fn(self.coordinator)
            except Exception as err:
                _LOGGER.error(
                    "Failed to execute %s: %s",
                    self.entity_description.key,
                    err,
                )
