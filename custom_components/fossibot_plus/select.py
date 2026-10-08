"""Select entities (dropdowns) for the FOSSiBOT power station.

Covers LED mode and charge mode — both confirmed from captured
/ctrl/route requests with all CRC values verified.
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FossibotApiClient
from homeassistant.const import EntityCategory

from .const import (
    DOMAIN,
    TAG_AC_STANDBY,
    TAG_CHARGE_MODE,
    TAG_DC_STANDBY,
    TAG_LED_MODE,
    TAG_POWER_OFF_TIMER,
    TAG_SCREEN_TIMEOUT,
    TAG_USB_STANDBY,
)
from .coordinator import FossibotCoordinator

_LOGGER = logging.getLogger(__name__)

# --- LED mode ---------------------------------------------------------------
LED_OPTIONS = ["off", "steady", "sos", "strobe"]
LED_TO_VALUE = {"off": 0, "steady": 1, "sos": 2, "strobe": 3}
VALUE_TO_LED = {v: k for k, v in LED_TO_VALUE.items()}

# --- Charge mode ------------------------------------------------------------
CHARGE_OPTIONS = ["ups", "eco"]
CHARGE_TO_VALUE = {"ups": 0, "eco": 1}
VALUE_TO_CHARGE = {v: k for k, v in CHARGE_TO_VALUE.items()}

STANDBY_OPTIONS = ["never", "30m", "1h", "4h", "8h", "12h", "24h"]
STANDBY_TO_VALUE = {k: i for i, k in enumerate(STANDBY_OPTIONS)}
VALUE_TO_STANDBY = {v: k for k, v in STANDBY_TO_VALUE.items()}
SCREEN_OPTIONS = ["always_on", "30s", "1m", "5m", "10m", "30m"]
POWEROFF_OPTIONS = ["never", "5m", "10m", "1h", "8h"]

STANDBY_TYPES = (
    ("dc_standby", TAG_DC_STANDBY, "DC standby"),
    ("usb_standby", TAG_USB_STANDBY, "USB standby"),
    ("ac_standby", TAG_AC_STANDBY, "AC standby"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api: FossibotApiClient = data["api"]
    entities = []
    for coordinator in data["coordinators"].values():
        entities.append(FossibotLedSelect(coordinator, api))
        entities.append(FossibotChargeModeSelect(coordinator, api))
        for key, tag, name in STANDBY_TYPES:
            entities.append(FossibotStandbySelect(coordinator, api, key, tag, name))
        entities.append(FossibotEnumSelect(
            coordinator, api, "screen_timeout", TAG_SCREEN_TIMEOUT,
            "Screen timeout", SCREEN_OPTIONS, "mdi:monitor-off"))
        entities.append(FossibotEnumSelect(
            coordinator, api, "power_off_timer", TAG_POWER_OFF_TIMER,
            "Power-off timer", POWEROFF_OPTIONS, "mdi:power-sleep"))
    async_add_entities(entities)


class _FossibotSelect(CoordinatorEntity[FossibotCoordinator], SelectEntity):
    """Base class for FOSSiBOT select entities."""
    _attr_has_entity_name = True
    _tag: str
    _option_to_value: dict[str, int]
    _value_to_option: dict[int, str]

    def __init__(self, coordinator: FossibotCoordinator, api: FossibotApiClient) -> None:
        super().__init__(coordinator)
        self._api = api
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._tag)
        return None if raw is None else self._value_to_option.get(raw)

    async def async_select_option(self, option: str) -> None:
        value = self._option_to_value[option]
        await self._api.async_send_control(self.coordinator.sn_code, self._tag, value)
        if self.coordinator.data is not None:
            new_data = dict(self.coordinator.data)
            new_data[self._tag] = value
            self.coordinator.async_set_updated_data(new_data)


class FossibotLedSelect(_FossibotSelect):
    _tag = TAG_LED_MODE
    _option_to_value = LED_TO_VALUE
    _value_to_option = VALUE_TO_LED
    _attr_options = LED_OPTIONS

    def __init__(self, coordinator: FossibotCoordinator, api: FossibotApiClient) -> None:
        super().__init__(coordinator, api)
        self.entity_description = SelectEntityDescription(
            key="led_mode", translation_key="led_mode", name="LED mode"
        )
        self._attr_unique_id = f"{coordinator.sn_code}_led_mode"


class FossibotChargeModeSelect(_FossibotSelect):
    _tag = TAG_CHARGE_MODE
    _option_to_value = CHARGE_TO_VALUE
    _value_to_option = VALUE_TO_CHARGE
    _attr_options = CHARGE_OPTIONS

    def __init__(self, coordinator: FossibotCoordinator, api: FossibotApiClient) -> None:
        super().__init__(coordinator, api)
        self.entity_description = SelectEntityDescription(
            key="charge_mode", translation_key="charge_mode", name="Charge mode"
        )
        self._attr_unique_id = f"{coordinator.sn_code}_charge_mode"


class FossibotStandbySelect(_FossibotSelect):
    _option_to_value = STANDBY_TO_VALUE
    _value_to_option = VALUE_TO_STANDBY
    _attr_options = STANDBY_OPTIONS
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-off-outline"

    def __init__(self, coordinator: FossibotCoordinator, api: FossibotApiClient,
                 key: str, tag: str, name: str) -> None:
        super().__init__(coordinator, api)
        self._tag = tag
        self.entity_description = SelectEntityDescription(
            key=key, translation_key=key, name=name
        )
        self._attr_unique_id = f"{coordinator.sn_code}_{key}"


class FossibotEnumSelect(_FossibotSelect):
    """Generic config select: option index == raw register value."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: FossibotCoordinator, api: FossibotApiClient,
                 key: str, tag: str, name: str, options: list[str], icon: str) -> None:
        super().__init__(coordinator, api)
        self._tag = tag
        self._attr_options = options
        self._option_to_value = {o: i for i, o in enumerate(options)}
        self._value_to_option = {i: o for i, o in enumerate(options)}
        self._attr_icon = icon
        self.entity_description = SelectEntityDescription(
            key=key, translation_key=key, name=name
        )
        self._attr_unique_id = f"{coordinator.sn_code}_{key}"
