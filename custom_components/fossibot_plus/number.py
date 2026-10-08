"""Number entity: AC charging power limit.

Tag 2a00, scale 1:1 (raw value = watts). Limits auto-detected from the
device serial number prefix — no user configuration needed.
"""
from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfElectricCurrent, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FossibotApiClient
from .const import (
    CHARGE_POWER_LIMITS,
    DC_CHARGE_CURRENT_LIMITS,
    DOMAIN,
    TAG_CHARGE_POWER,
    TAG_DC_CHARGE_CURRENT,
    TAG_CHARGE_LIMIT,
    TAG_DISCHARGE_LIMIT,
    TAG_SCREEN_BRIGHTNESS,
    detect_model,
)
from .coordinator import FossibotCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api: FossibotApiClient = data["api"]
    entities = []
    for coordinator in data["coordinators"].values():
        entities.append(FossibotChargePowerNumber(coordinator, api))
        entities.append(FossibotDcChargeCurrentNumber(coordinator, api))
        for spec in SIMPLE_NUMBERS:
            entities.append(FossibotSimpleNumber(coordinator, api, *spec))
    async_add_entities(entities)


class FossibotChargePowerNumber(CoordinatorEntity[FossibotCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        coordinator: FossibotCoordinator,
        api: FossibotApiClient,
    ) -> None:
        super().__init__(coordinator)
        self._api = api

        # Detect limits from serial number — each device in the account gets
        # its own correct range, so mixed-model accounts work automatically.
        model = detect_model(coordinator.sn_code)
        limits = CHARGE_POWER_LIMITS[model]
        _LOGGER.debug(
            "FOSSiBOT %s detected as model=%s, charge limits %s–%s W",
            coordinator.sn_code, model, limits["min"], limits["max"],
        )

        self._attr_native_min_value = float(limits["min"])
        self._attr_native_max_value = float(limits["max"])
        self._attr_native_step = float(limits["step"])

        self.entity_description = NumberEntityDescription(
            key="charge_power_limit",
            translation_key="charge_power_limit",
            name="Charge power limit",
        )
        self._attr_unique_id = f"{coordinator.sn_code}_charge_power_limit"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(TAG_CHARGE_POWER)
        return float(raw) if raw is not None else None

    async def async_set_native_value(self, value: float) -> None:
        # Snap to the nearest 100 W step
        watts = int(round(value / 100) * 100)
        watts = max(int(self._attr_native_min_value),
                    min(int(self._attr_native_max_value), watts))
        await self._api.async_send_control(
            self.coordinator.sn_code, TAG_CHARGE_POWER, watts
        )
        if self.coordinator.data is not None:
            new_data = dict(self.coordinator.data)
            new_data[TAG_CHARGE_POWER] = watts
            self.coordinator.async_set_updated_data(new_data)


class FossibotDcChargeCurrentNumber(CoordinatorEntity[FossibotCoordinator], NumberEntity):
    """DC charge current (tag 3500, amps). F3000 allows up to 25 A."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = 1.0
    _attr_native_step = 1.0
    _attr_icon = "mdi:current-dc"

    def __init__(
        self,
        coordinator: FossibotCoordinator,
        api: FossibotApiClient,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        model = detect_model(coordinator.sn_code)
        self._attr_native_max_value = float(DC_CHARGE_CURRENT_LIMITS[model])
        self.entity_description = NumberEntityDescription(
            key="dc_charge_current",
            translation_key="dc_charge_current",
            name="DC charge current",
        )
        self._attr_unique_id = f"{coordinator.sn_code}_dc_charge_current"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(TAG_DC_CHARGE_CURRENT)
        return float(raw & 0xFF) if raw is not None else None

    async def async_set_native_value(self, value: float) -> None:
        amps = max(1, min(int(self._attr_native_max_value), int(round(value))))
        await self._api.async_send_control(
            self.coordinator.sn_code, TAG_DC_CHARGE_CURRENT, amps
        )
        if self.coordinator.data is not None:
            new_data = dict(self.coordinator.data)
            new_data[TAG_DC_CHARGE_CURRENT] = amps
            self.coordinator.async_set_updated_data(new_data)


# (key, tag, name, min, max, step, icon, entity_category)
SIMPLE_NUMBERS: tuple[tuple, ...] = (
    ("charge_limit", TAG_CHARGE_LIMIT, "Charge limit", 60, 100, 1,
     "mdi:battery-arrow-up-outline", None),
    ("discharge_limit", TAG_DISCHARGE_LIMIT, "Discharge limit", 0, 20, 1,
     "mdi:battery-arrow-down-outline", None),
    ("screen_brightness", TAG_SCREEN_BRIGHTNESS, "Screen brightness", 0, 100, 1,
     "mdi:brightness-6", EntityCategory.CONFIG),
)


class FossibotSimpleNumber(CoordinatorEntity[FossibotCoordinator], NumberEntity):
    """Plain u8 percentage setting written 1:1 to its tag."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, api, key, tag, name, vmin, vmax, step, icon, category) -> None:
        super().__init__(coordinator)
        self._api = api
        self._tag = tag
        self._attr_native_min_value = float(vmin)
        self._attr_native_max_value = float(vmax)
        self._attr_native_step = float(step)
        self._attr_icon = icon
        self._attr_entity_category = category
        self.entity_description = NumberEntityDescription(
            key=key, translation_key=key, name=name
        )
        self._attr_unique_id = f"{coordinator.sn_code}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._tag)
        return float(raw & 0xFF) if raw is not None else None

    async def async_set_native_value(self, value: float) -> None:
        v = int(round(value))
        v = max(int(self._attr_native_min_value), min(int(self._attr_native_max_value), v))
        await self._api.async_send_control(self.coordinator.sn_code, self._tag, v)
        if self.coordinator.data is not None:
            new_data = dict(self.coordinator.data)
            new_data[self._tag] = v
            self.coordinator.async_set_updated_data(new_data)
