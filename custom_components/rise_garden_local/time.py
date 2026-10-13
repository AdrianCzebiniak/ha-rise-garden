"""Time platform (local): when the grow lights come on, in local time."""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RiseLocalError
from .const import DOMAIN
from .entity import RiseLocalEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    unit_id = await store["client"].unit_id() or entry.unique_id or "rise"
    async_add_entities([RiseLocalLightsOn(store["coordinator"], unit_id)])


class RiseLocalLightsOn(RiseLocalEntity, TimeEntity):
    """Start of the light schedule (sunrise ramp included)."""

    _attr_name = "Lights on"
    _attr_icon = "mdi:weather-sunset-up"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_lights_on"

    @property
    def native_value(self) -> time | None:
        model = self.coordinator.light_model()
        return None if model is None else time.fromisoformat(model["on"])

    async def async_set_value(self, value: time) -> None:
        try:
            await self.coordinator.async_set_light_model(on=value.strftime("%H:%M:%S"))
        except (RiseLocalError, ValueError) as err:
            raise HomeAssistantError(f"Failed to set light schedule: {err}") from err
