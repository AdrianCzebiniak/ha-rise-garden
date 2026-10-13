"""Sensor platform (local): RSSI, pump current, clock, light/pump schedule summaries."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import RiseLocalEntity
from .schedule import to_local, window


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    unit_id = await store["client"].unit_id() or entry.unique_id or "rise"
    coord = store["coordinator"]
    async_add_entities(
        [
            RiseLocalSensor(
                coord, unit_id, "rssi", "Wi-Fi signal", "rssi",
                lambda v: v,
                device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                unit=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                category=EntityCategory.DIAGNOSTIC,
                icon="mdi:wifi",
            ),
            RiseLocalSensor(
                coord, unit_id, "pump_current", "Pump current", "pump_current",
                lambda v: v,
                device_class=SensorDeviceClass.CURRENT,
                unit=UnitOfElectricCurrent.MILLIAMPERE,
                icon="mdi:current-dc",
            ),
            RiseLocalClock(coord, unit_id),
            RiseLocalLightSchedule(coord, unit_id),
            RiseLocalPumpSchedule(coord, unit_id),
            RiseLocalNetwork(coord, unit_id),
        ]
    )


class RiseLocalSensor(RiseLocalEntity, SensorEntity):
    """Generic numeric sensor reading one coordinator key."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        unit_id: str,
        key: str,
        name: str,
        uid_suffix: str,
        transform: Callable,
        *,
        device_class=None,
        unit=None,
        category=None,
        icon=None,
    ) -> None:
        super().__init__(coordinator, unit_id)
        self._key = key
        self._transform = transform
        self._attr_name = name
        self._attr_unique_id = f"{unit_id}_{uid_suffix}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = category
        self._attr_icon = icon

    @property
    def native_value(self):
        val = self.coordinator.data.get(self._key)
        return None if val is None else self._transform(val)


class RiseLocalClock(RiseLocalEntity, SensorEntity):
    """The controller's own clock (proves the schedule runs on-device)."""

    _attr_name = "Controller time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_clock"

    @property
    def native_value(self):
        raw = self.coordinator.data.get("time")
        if not raw:
            return None
        # "<epoch> <YYYY-MM-DD HH:MM:SS>"
        epoch = raw.split()[0]
        try:
            return datetime.fromtimestamp(int(epoch), tz=dt_util.UTC)
        except (ValueError, OSError):
            return None


class RiseLocalLightSchedule(RiseLocalEntity, SensorEntity):
    """Light schedule summary ('07:00-23:00', local time) with the full steps."""

    _attr_name = "Light schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_light_schedule"

    @property
    def native_value(self) -> str | None:
        steps = self.coordinator.data.get("light_schedule")
        return window(steps, self.coordinator.utc_offset()) if steps else None

    @property
    def extra_state_attributes(self) -> dict:
        steps = self.coordinator.data.get("light_schedule") or []
        return {"steps": to_local(steps, self.coordinator.utc_offset()), "steps_utc": steps}


class RiseLocalPumpSchedule(RiseLocalEntity, SensorEntity):
    """Pump cycle summary ('5 min every 60 min')."""

    _attr_name = "Pump schedule"
    _attr_icon = "mdi:water-sync"

    def __init__(self, coordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_pump_schedule"

    @property
    def native_value(self) -> str | None:
        cycle = self.coordinator.data.get("pump_cycle")
        if not cycle:
            return None
        on, off = cycle
        return f"{on / 60:g} min every {(on + off) / 60:g} min"


class RiseLocalNetwork(RiseLocalEntity, SensorEntity):
    """The Wi-Fi network the controller is joined to (read once at setup)."""

    _attr_name = "Wi-Fi network"
    _attr_icon = "mdi:wifi-settings"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_ssid"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.ssid
