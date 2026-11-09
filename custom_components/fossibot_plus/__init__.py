"""The FOSSiBOT Power Station integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .api import (
    FossibotApiClient,
    FossibotAuthError,
    FossibotConnectionError,
    FossibotLocalTcpServer,
)
from .const import (
    CONF_EMAIL,
    CONF_ALLOWED_PREFIX,
    CONF_HOST,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SERIAL,
    CONF_STATION_IP,
    DEVICE_STATUS_POLL_INTERVAL,
    DOMAIN,
    MODE_LAN,
    MODE_LOCAL,
)
from .coordinator import FossibotCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch", "select", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Reuse HA's shared session instead of opening a new one - the source
    # spec's draft code created its own aiohttp.ClientSession, which would
    # leak connections every time the entry reloads.
    session = async_get_clientsession(hass)
    local = None
    if entry.data.get(CONF_MODE) in (MODE_LOCAL, MODE_LAN):
        local = FossibotLocalTcpServer(
            entry.data.get(CONF_HOST, "0.0.0.0"),
            int(entry.data.get(CONF_PORT, 8058)),
            entry.data[CONF_SERIAL],
            lambda _data: None,
            lambda _online: None,
            entry.data.get(CONF_ALLOWED_PREFIX) or None,
            allowed_ip=entry.data.get(CONF_STATION_IP) or None,
        )
        api = FossibotApiClient(session, local=local)
        devices = await api.async_get_devices()
    else:
        api = FossibotApiClient(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
        await api.async_login()
        devices = await api.async_get_devices()

    # Per-device model map: options override initial data (options flow)
    device_models: dict[str, str] = (
        entry.options.get("device_models")
        or entry.data.get("device_models", {})
    )

    coordinators: dict[str, FossibotCoordinator] = {}
    try:
        for device in devices:
            sn_code = device["snCode"]
            device_name = f"{device.get('deviceName', 'Fossibot')}-{sn_code}"
            coordinator = FossibotCoordinator(hass, api, sn_code, device_name, local=local)
            if local:
                local.set_callbacks(coordinator._on_data, coordinator.set_online)
            coordinator.set_online(bool(device.get("state", True)))
            await coordinator.async_start()
            coordinators[sn_code] = coordinator

        async def _async_refresh_online_status(_now=None) -> None:
            if local:
                return
            # Online/offline is a REST-only field, not part of the WS telemetry
            # frames, so it has to be polled separately on a timer.
            # async_get_devices() handles its own token refresh (re-login on 401)
            # so no extra async_login() call needed here.
            try:
                fresh_devices = await api.async_get_devices()
            except (FossibotAuthError, FossibotConnectionError) as err:
                _LOGGER.debug("Could not refresh FOSSiBOT online status: %s", err)
                return
            seen: set[str] = set()
            for device in fresh_devices:
                sn_code = device.get("snCode")
                coordinator = coordinators.get(sn_code)
                if coordinator is None:
                    continue
                seen.add(sn_code)
                coordinator.set_online(bool(device.get("state", False)))
            # A device that has disappeared from the list entirely is treated
            # as offline too, rather than left showing its last-known state.
            for sn_code, coordinator in coordinators.items():
                if sn_code not in seen:
                    coordinator.set_online(False)

        remove_status_listener = async_track_time_interval(
            hass,
            _async_refresh_online_status,
            timedelta(seconds=DEVICE_STATUS_POLL_INTERVAL),
        )
    except Exception:
        # If anything after async_start() fails, ensure WS tasks are not
        # left running in the background (they would keep reconnecting and
        # fighting with the next async_setup_entry attempt).
        for coordinator in coordinators.values():
            await coordinator.async_stop()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinators": coordinators,
        "remove_status_listener": remove_status_listener,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        data["remove_status_listener"]()
        for coordinator in data["coordinators"].values():
            await coordinator.async_stop()
    return unloaded
