"""Sensor entities decoding FOSSiBOT TLV telemetry tags."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    TAG_AC_FREQUENCY,
    TAG_AC_GRID_POWER,
    TAG_AC_OUTPUT_POWER,
    TAG_AC_OUTPUT_VOLTAGE,
    TAG_BATTERY_SOC,
    TAG_CHARGE_POWER,
    TAG_CHARGING_ACTIVE,
    TAG_REMAINING_MINUTES,
    TAG_TEMPERATURE,
    TAG_TOTAL_INPUT_POWER,
    TAG_TOTAL_OUTPUT_POWER,
    TAG_USB_OUTPUT_POWER,
    TAG_BATTERY_TEMP_MIN,
    TAG_BMS_MOS_TEMP,
    TAG_PACK_VOLTAGE,
    TAG_BATTERY_CURRENT,
    TAG_BMS_FAULT,
    TAG_DC_INPUT_POWER,
    TAG_INVERTER_TEMP,
    TAG_MOS_TEMP,
    TAG_PCS_FAULT,
    TAG_PV_VOLTAGE,
    TAG_PV_CURRENT,
    TAG_PV_FAULT,
    TAG_DC_OUTPUT_POWER,
    TAG_FIRMWARE,
    TAG_BMS_VERSION,
    TAG_PCS_VERSION,
    TAG_SOLAR_ENERGY,
)
from .coordinator import FossibotCoordinator


@dataclass(frozen=True, kw_only=True)
class FossibotSensorDescription(SensorEntityDescription):
    tag: str = ""
    scale: float = 1
    # Optional post-processing (e.g. take only low 16 bits)
    raw_transform: Callable[[int], int] | None = None
    # Optional formatter producing the final (e.g. string) state
    formatter: Callable[[int], str] | None = None


def _i16(v: int) -> int:
    """Signed 16-bit from the low word."""
    v &= 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def _i32_app(v: int) -> int:
    """Signed value as the official app decodes it: if the high word is
    0x0000/0xFFFF treat it as sign-extended i16, otherwise as i32."""
    hi = (v >> 16) & 0xFFFF
    if hi in (0x0000, 0xFFFF):
        return _i16(v)
    return v - 0x100000000 if v >= 0x80000000 else v


def _version(v: int) -> str:
    b = v.to_bytes(4, "little")
    return "-".join(f"{x:02x}" for x in reversed(b))


def _low16(v: int) -> int:
    """Return only the lower 16 bits — handles models that pack metadata in high word."""
    return v & 0xFFFF


SENSOR_TYPES: tuple[FossibotSensorDescription, ...] = (
    # ✅ Confirmed ─────────────────────────────────────────────────────────────
    FossibotSensorDescription(
        key="battery_soc",
        tag=TAG_BATTERY_SOC,
        name="Battery",
        translation_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="temperature",
        tag=TAG_TEMPERATURE,
        name="Temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        # Some models pack extra data in the high 16 bits of this tag (e.g.
        # one device reported raw=196638 = 0x0003001E; low16=30°C is correct).
        # Taking only the low 16 bits is safe for all observed models.
        raw_transform=_low16,
    ),
    FossibotSensorDescription(
        key="remaining_minutes",
        tag=TAG_REMAINING_MINUTES,
        name="Time remaining",
        translation_key="remaining_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="charging",
        tag=TAG_CHARGING_ACTIVE,
        name="Charging",
        translation_key="charging",
    ),
    # ✅ Output power breakdown (confirmed: 2300 = 1400 + 2500 in every frame)
    FossibotSensorDescription(
        key="ac_output_power",
        tag=TAG_AC_OUTPUT_POWER,
        name="AC output power",
        translation_key="ac_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="usb_output_power",
        tag=TAG_USB_OUTPUT_POWER,
        name="USB output power",
        translation_key="usb_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="total_output_power",
        tag=TAG_TOTAL_OUTPUT_POWER,
        name="Total output power",
        translation_key="total_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="ac_output_voltage",
        tag=TAG_AC_OUTPUT_VOLTAGE,
        name="AC output voltage",
        translation_key="ac_output_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
    ),
    FossibotSensorDescription(
        key="ac_frequency",
        tag=TAG_AC_FREQUENCY,
        name="AC frequency",
        translation_key="ac_frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
    ),
    # ✅ Input / charging power
    FossibotSensorDescription(
        key="ac_grid_power",
        tag=TAG_AC_GRID_POWER,
        name="AC grid power",
        translation_key="ac_grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="total_input_power",
        tag=TAG_TOTAL_INPUT_POWER,
        name="Total input power",
        translation_key="total_input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="charge_power",
        tag=TAG_CHARGE_POWER,
        name="Charge power",
        translation_key="charge_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # ➕ Extra registers (fossibot-control register map) ─────────────────────
    # Battery voltage/current, temperatures other than 0200, DC input
    # voltage/current and fault codes are not sent by F3000 (see const.py)
    # and stay "unknown" there; kept to check other models.
    FossibotSensorDescription(
        key="pack_voltage", tag=TAG_PACK_VOLTAGE, name="Battery voltage",
        translation_key="pack_voltage", scale=0.1,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="battery_current", tag=TAG_BATTERY_CURRENT, name="Battery current",
        translation_key="battery_current", scale=0.001, raw_transform=_i32_app,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="battery_temp_min", tag=TAG_BATTERY_TEMP_MIN, name="Battery temperature min",
        translation_key="battery_temp_min", raw_transform=_i16,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FossibotSensorDescription(
        key="bms_mos_temp", tag=TAG_BMS_MOS_TEMP, name="BMS MOS temperature",
        translation_key="bms_mos_temp", raw_transform=_i16,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FossibotSensorDescription(
        key="dc_input_power", tag=TAG_DC_INPUT_POWER, name="DC input power",
        translation_key="dc_input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="pv_voltage", tag=TAG_PV_VOLTAGE, name="DC input voltage",
        translation_key="pv_voltage", scale=0.1,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="pv_current", tag=TAG_PV_CURRENT, name="DC input current",
        translation_key="pv_current", scale=0.001, raw_transform=_i32_app,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="solar_energy", tag=TAG_SOLAR_ENERGY, name="DC input energy",
        translation_key="solar_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    FossibotSensorDescription(
        key="dc_output_power", tag=TAG_DC_OUTPUT_POWER, name="DC output power",
        translation_key="dc_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="inverter_temp", tag=TAG_INVERTER_TEMP, name="Inverter temperature",
        translation_key="inverter_temp", raw_transform=_i16,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="mos_temp", tag=TAG_MOS_TEMP, name="MOS temperature",
        translation_key="mos_temp", raw_transform=_i16,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FossibotSensorDescription(
        key="bms_fault", tag=TAG_BMS_FAULT, name="BMS fault code",
        translation_key="bms_fault", entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FossibotSensorDescription(
        key="pcs_fault", tag=TAG_PCS_FAULT, name="PCS fault code",
        translation_key="pcs_fault", entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FossibotSensorDescription(
        key="pv_fault", tag=TAG_PV_FAULT, name="DC input fault code",
        translation_key="pv_fault", entity_category=EntityCategory.DIAGNOSTIC,
    ),
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
        FossibotSensor(coordinator, description)
        for coordinator in data["coordinators"].values()
        for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


class FossibotSensor(CoordinatorEntity[FossibotCoordinator], SensorEntity):
    entity_description: FossibotSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: FossibotCoordinator, description: FossibotSensorDescription
    ) -> None:
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
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self.entity_description.tag)
        if raw is None:
            return None
        if self.entity_description.formatter is not None:
            return self.entity_description.formatter(raw)
        if self.entity_description.raw_transform is not None:
            raw = self.entity_description.raw_transform(raw)
        return round(raw * self.entity_description.scale, 2)
