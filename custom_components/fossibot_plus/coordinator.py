"""Push-based coordinator: state arrives over the WebSocket, not polling."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import FossibotApiClient, FossibotWebSocket
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class FossibotCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """Holds the latest decoded TLV telemetry dict for one device."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: FossibotApiClient,
        sn_code: str,
        device_name: str,
    ) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_{sn_code}")
        self.sn_code = sn_code
        self.device_name = device_name
        # From user_device/list's "state" field (polled separately - see
        # __init__.py - since it's REST-only, not part of WS telemetry).
        # Starts True optimistically until the first poll confirms it.
        self.online: bool = True
        self._api = api
        self._ws = FossibotWebSocket(api.session, api, sn_code, self._on_data)

    def set_online(self, online: bool) -> None:
        if online == self.online:
            return
        self.online = online
        # No new telemetry data to push, but entities need to re-evaluate
        # `available` (see sensor.py/binary_sensor.py/switch.py) now that
        # the device's online state has changed.
        self.async_update_listeners()

    def _on_data(self, metrics: dict[str, int]) -> None:
        # Frames don't always carry every tag; merge so a partial frame
        # doesn't blank out values received in earlier ones.
        self.async_set_updated_data({**(self.data or {}), **metrics})

    async def async_start(self) -> None:
        await self._ws.async_start()

    async def async_stop(self) -> None:
        await self._ws.async_stop()
