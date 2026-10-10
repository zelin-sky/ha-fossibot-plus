"""Sensor entities for the FOSSiBOT power station."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory, PERCENTAGE,
    UnitOfElectricPotential, UnitOfEnergy, UnitOfFrequency,
    UnitOfPower, UnitOfTemperature, UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    TAG_AC_FREQUENCY, TAG_AC_GRID_POWER, TAG_AC_OUTPUT_POWER, TAG_AC_OUTPUT_VOLTAGE,
    TAG_BATTERY_SOC, TAG_BMS_VERSION, TAG_CHARGE_POWER, TAG_CHARGING_ACTIVE,
    TAG_DC_INPUT_POWER, TAG_DC_OUTPUT_POWER, TAG_FIRMWARE, TAG_PCS_VERSION,
    TAG_REMAINING_MINUTES, TAG_SOLAR_ENERGY, TAG_TEMPERATURE,
    TAG_TOTAL_INPUT_POWER, TAG_TOTAL_OUTPUT_POWER, TAG_USB_OUTPUT_POWER,
)
from .coordinator import FossibotCoordinator


def _low16(v: int) -> int:
    return v & 0xFFFF


def _version(v: int) -> str:
    b = v.to_bytes(4, "little")
    return ".".join(str(x) for x in reversed(b))


@dataclass(frozen=True, kw_only=True)
class FossibotSensorDescription(SensorEntityDescription):
    tag: str = ""
    scale: float = 1
    raw_transform: Callable[[int], int] | None = None
    formatter: Callable[[int], str] | None = None


SENSOR_TYPES: tuple[FossibotSensorDescription, ...] = (
    # ✅ Confirmed — matched against app screen
    FossibotSensorDescription(
        key="battery_soc", tag=TAG_BATTERY_SOC, name="Battery",
        translation_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="temperature", tag=TAG_TEMPERATURE, name="Temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        raw_transform=_low16,   # some models pack metadata in high 16 bits
    ),
    FossibotSensorDescription(
        key="remaining_minutes", tag=TAG_REMAINING_MINUTES, name="Time remaining",
        translation_key="remaining_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="charging", tag=TAG_CHARGING_ACTIVE, name="Charging",
        translation_key="charging",
    ),
    # Output power breakdown (confirmed: 2300 = 1400 + 2500 + 2400)
    FossibotSensorDescription(
        key="ac_output_power", tag=TAG_AC_OUTPUT_POWER, name="AC output power",
        translation_key="ac_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="dc_output_power", tag=TAG_DC_OUTPUT_POWER, name="DC output power",
        translation_key="dc_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="usb_output_power", tag=TAG_USB_OUTPUT_POWER, name="USB output power",
        translation_key="usb_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="total_output_power", tag=TAG_TOTAL_OUTPUT_POWER, name="Total output power",
        translation_key="total_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="ac_output_voltage", tag=TAG_AC_OUTPUT_VOLTAGE, name="AC output voltage",
        translation_key="ac_output_voltage", scale=0.1,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="ac_frequency", tag=TAG_AC_FREQUENCY, name="AC frequency",
        translation_key="ac_frequency", scale=0.1,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Input / charging
    FossibotSensorDescription(
        key="ac_grid_power", tag=TAG_AC_GRID_POWER, name="AC grid power",
        translation_key="ac_grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="dc_input_power", tag=TAG_DC_INPUT_POWER, name="DC input power",
        translation_key="dc_input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="total_input_power", tag=TAG_TOTAL_INPUT_POWER, name="Total input power",
        translation_key="total_input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="charge_power", tag=TAG_CHARGE_POWER, name="Charge power",
        translation_key="charge_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="solar_energy", tag=TAG_SOLAR_ENERGY, name="DC input energy",
        translation_key="solar_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Diagnostic
    FossibotSensorDescription(
        key="firmware", tag=TAG_FIRMWARE, name="Firmware",
        translation_key="firmware", formatter=_version,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FossibotSensorDescription(
        key="bms_version", tag=TAG_BMS_VERSION, name="BMS version",
        translation_key="bms_version", formatter=_version,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FossibotSensorDescription(
        key="pcs_version", tag=TAG_PCS_VERSION, name="PCS version",
        translation_key="pcs_version", formatter=_version,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        FossibotSensor(coordinator, desc)
        for coordinator in data["coordinators"].values()
        for desc in SENSOR_TYPES
    ]
    async_add_entities(entities)


class FossibotSensor(CoordinatorEntity[FossibotCoordinator], SensorEntity):
    entity_description: FossibotSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator: FossibotCoordinator, description: FossibotSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.sn_code}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def native_value(self):
        raw = (self.coordinator.data or {}).get(self.entity_description.tag)
        if raw is None:
            return None
        if self.entity_description.formatter:
            return self.entity_description.formatter(raw)
        if self.entity_description.raw_transform:
            raw = self.entity_description.raw_transform(raw)
        return round(raw * self.entity_description.scale, 2)
