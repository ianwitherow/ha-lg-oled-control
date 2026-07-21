"""Button entities for LG OLED Control integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LGTVCoordinator
from .entity import LGTVEntity


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


class LGTVButtonEntity(LGTVEntity, ButtonEntity):
    """Button entity for LG TV actions."""

    entity_description: LGTVButtonEntityDescription

    def __init__(
        self,
        coordinator: LGTVCoordinator,
        entry: ConfigEntry,
        description: LGTVButtonEntityDescription,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Handle button press."""
        if self.entity_description.press_fn is not None:
            await self.entity_description.press_fn(self.coordinator)
