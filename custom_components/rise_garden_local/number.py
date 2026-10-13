"""Number platform (local): pump cycle ('wpc') and light schedule settings."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RiseGardenLocal, RiseLocalError
from .const import DOMAIN
from .entity import RiseLocalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    unit_id = await store["client"].unit_id() or entry.unique_id or "rise"
    async_add_entities(
        [
            RiseLocalPumpCycle(store["coordinator"], store["client"], unit_id, 0, "Pump run time", "mdi:timer-play-outline"),
            RiseLocalPumpCycle(store["coordinator"], store["client"], unit_id, 1, "Pump rest time", "mdi:timer-pause-outline"),
            RiseLocalLightSetting(
                store["coordinator"], unit_id, "hours", "Light hours", "mdi:sun-clock",
                UnitOfTime.HOURS, 0.25, 24, 0.25,
            ),
            RiseLocalLightSetting(
                store["coordinator"], unit_id, "peak", "Peak brightness", "mdi:brightness-7",
                PERCENTAGE, 1, 100, 1,
            ),
            RiseLocalLightSetting(
                store["coordinator"], unit_id, "ramp_min", "Sunrise/sunset ramp", "mdi:weather-sunset",
                UnitOfTime.MINUTES, 0, 240, 1,
            ),
        ]
    )


class RiseLocalPumpCycle(RiseLocalEntity, NumberEntity):
    """One half of the pump cycle: index 0 = seconds on, 1 = seconds off."""

    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_native_min_value = 1
    _attr_native_max_value = 86400
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, client: RiseGardenLocal, unit_id: str, index: int, name: str, icon: str) -> None:
        super().__init__(coordinator, unit_id)
        self._client = client
        self._index = index
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{unit_id}_pump_{'on' if index == 0 else 'off'}_time"

    @property
    def native_value(self) -> int | None:
        cycle = self.coordinator.data.get("pump_cycle")
        return None if cycle is None else cycle[self._index]

    async def async_set_native_value(self, value: float) -> None:
        cycle = self.coordinator.data.get("pump_cycle")
        if cycle is None:
            raise HomeAssistantError("Pump cycle unknown; controller not read yet")
        new = list(cycle)
        new[self._index] = int(value)
        try:
            await self._client.set_pump_cycle(new[0], new[1])
        except (RiseLocalError, ValueError) as err:
            raise HomeAssistantError(f"Failed to set pump cycle: {err}") from err
        self.coordinator.data["pump_cycle"] = new
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class RiseLocalLightSetting(RiseLocalEntity, NumberEntity):
    """One field of the light schedule model; editing it rewrites the schedule."""

    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, unit_id: str, field: str, name: str, icon: str,
                 unit: str, min_value: float, max_value: float, step: float) -> None:
        super().__init__(coordinator, unit_id)
        self._field = field
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_unique_id = f"{unit_id}_light_{field}"

    @property
    def native_value(self) -> float | None:
        model = self.coordinator.light_model()
        return None if model is None else model[self._field]

    async def async_set_native_value(self, value: float) -> None:
        value = value if self._field == "hours" else int(value)
        try:
            await self.coordinator.async_set_light_model(**{self._field: value})
        except (RiseLocalError, ValueError) as err:
            raise HomeAssistantError(f"Failed to set light schedule: {err}") from err
