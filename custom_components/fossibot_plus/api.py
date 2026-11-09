"""REST + WebSocket client for the FOSSiBOT cloud (app.fossibot.hk).

The account login/device-list calls are plain REST. Live telemetry comes
over a WebSocket that the server closes after ~15s of silence, so a
{"type": "hear", "msg": "<email>"} heartbeat frame must be sent every
5 seconds. Each device (snCode) needs its own WS connection.
"""
from __future__ import annotations

import asyncio
import json
import logging
import struct
from typing import Callable

import aiohttp

from .const import (
    CONTROL_ENDPOINT,
    CTRL_COMMAND_PREFIX,
    DEVICE_LIST_ENDPOINT,
    FRAME_SILENCE_TIMEOUT,
    HEARTBEAT_INTERVAL,
    LOGIN_DUPLICATE_SUBMIT_MARKER,
    LOGIN_ENDPOINT,
    LOGIN_MAX_RETRIES,
    LOGIN_RETRY_DELAY,
    LOCAL_ACK_FRAME,
    LOCAL_FRAME_TIMEOUT,
    LOCAL_HELLO_REPLY,
    RECONNECT_DELAY,
    WS_URL,
)

_LOGGER = logging.getLogger(__name__)

_COMMON_HEADERS = {
    "lang": "uk",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; SM-A536E Build/BP2A.250605.031.A3; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/153.0.8010.36 "
        "Mobile Safari/537.36 uni-app (Immersed/33.142857) Html5Plus/1.0"
    ),
}

HEADER_LEN = 6  # bytes
TAIL_LEN = 2    # bytes - CRC16, parsed but NOT validated: the source spec
                # never documented the checksum algorithm.
BLOCK_LEN = 6   # bytes per [tag(2)][value(4, little-endian)] block
HELLO_FRAME_TYPE = 0x0051
HELLO_FIRMWARE_LEN = 4  # bytes after the ASCII serial in a hello frame


class FossibotAuthError(Exception):
    """Email/password rejected by the API."""


class FossibotConnectionError(Exception):
    """Network or unexpected-API-response failure."""


def parse_payload(hex_str: str) -> dict[str, int]:
    """Decode one TLV telemetry frame into {tag_hex: raw_uint32}.

    Layout: 6-byte header, then repeating 6-byte
    [2-byte tag][4-byte little-endian value] blocks, then a 2-byte tail.
    Each tag is a plain uint32 counter/flag/reading - see const.py for what
    each one is currently believed to mean and how confident that is.
    """
    raw = bytes.fromhex(hex_str)
    body = raw[HEADER_LEN:-TAIL_LEN]
    usable = len(body) - (len(body) % BLOCK_LEN)
    metrics: dict[str, int] = {}
    for offset in range(0, usable, BLOCK_LEN):
        block = body[offset : offset + BLOCK_LEN]
        tag = block[0:2].hex()
        value = struct.unpack("<I", block[2:6])[0]
        metrics[tag] = value
    return metrics


def parse_local_frame(raw: bytes) -> tuple[int, dict[str, int]] | None:
    """Parse one complete local binary frame and validate its CRC."""
    if len(raw) < HEADER_LEN + TAIL_LEN:
        return None
    length, frame_type, payload_length = struct.unpack_from("<HHH", raw)
    if length != len(raw) or payload_length != length - HEADER_LEN:
        return None
    if frame_type != 0x000B:
        return None
    if _crc16_modbus(raw[HEADER_LEN:-TAIL_LEN]) != int.from_bytes(raw[-2:], "big"):
        return None
    return frame_type, parse_payload(raw.hex())


def parse_local_hello(raw: bytes) -> str | None:
    """Return the serial from a station hello frame, which carries no CRC."""
    if len(raw) <= HEADER_LEN + HELLO_FIRMWARE_LEN:
        return None
    length, frame_type, payload_length = struct.unpack_from("<HHH", raw)
    if frame_type != HELLO_FRAME_TYPE or length != len(raw) or payload_length != length - HEADER_LEN:
        return None
    try:
        return raw[HEADER_LEN:-HELLO_FIRMWARE_LEN].decode("ascii")
    except UnicodeDecodeError:
        return None


def build_local_command(tag_hex: str, value: int) -> bytes:
    """Build the binary command frame used by the station's local TCP mode."""
    record = bytes.fromhex(tag_hex) + value.to_bytes(4, "little")
    crc = _crc16_modbus(record)
    return b"\x0e\x00\x0c\x00\x08\x00" + record + crc.to_bytes(2, "big")


class _FrameAssembler:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> list[bytes]:
        self._buffer.extend(chunk)
        frames: list[bytes] = []
        while len(self._buffer) >= HEADER_LEN:
            length = int.from_bytes(self._buffer[:2], "little")
            if length < HEADER_LEN + TAIL_LEN or length > 4096:
                del self._buffer[0]
                continue
            if len(self._buffer) < length:
                break
            frames.append(bytes(self._buffer[:length]))
            del self._buffer[:length]
        return frames


class FossibotLocalTcpServer:
    """TCP server the station connects to, on its own AP or in place of the cloud."""

    def __init__(
        self,
        host: str,
        port: int,
        sn_code: str,
        on_data: Callable[[dict[str, int]], None],
        on_state: Callable[[bool], None],
        allowed_prefix: str | None = None,
        allowed_ip: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.sn_code = sn_code
        self._on_data = on_data
        self._on_state = on_state
        self._allowed_prefix = allowed_prefix
        self._allowed_ip = allowed_ip
        self._warned: set[str] = set()
        self._server: asyncio.AbstractServer | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._reader_task: asyncio.Task | None = None
        self._watchdog_task: asyncio.Task | None = None
        self._assembler = _FrameAssembler()
        self._send_lock = asyncio.Lock()

    def set_callbacks(
        self,
        on_data: Callable[[dict[str, int]], None],
        on_state: Callable[[bool], None],
    ) -> None:
        self._on_data = on_data
        self._on_state = on_state

    async def async_start(self) -> None:
        self._server = await asyncio.start_server(
            self._accept, self.host, self.port
        )

    async def async_stop(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
        if self._watchdog_task:
            self._watchdog_task.cancel()
        if self._writer:
            await self._close_writer(self._writer)
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._writer = None
        self._on_state(False)

    async def async_send(self, tag_hex: str, value: int) -> None:
        if not self._writer or self._writer.is_closing():
            raise FossibotConnectionError("local station is not connected")
        async with self._send_lock:
            self._writer.write(build_local_command(tag_hex, value))
            await self._writer.drain()

    async def _accept(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        address = peer[0] if peer else ""
        if self._allowed_ip and address != self._allowed_ip:
            self._warn_once(f"Rejected connection from {address}: expected the station at {self._allowed_ip}")
            await self._close_writer(writer)
            return
        if self._allowed_prefix and not address.startswith(self._allowed_prefix):
            await self._close_writer(writer)
            return
        if self._writer:
            await self._close_writer(self._writer)
        self._writer = writer
        self._assembler = _FrameAssembler()
        self._on_state(False)
        self._reader_task = asyncio.create_task(self._read_loop(reader, writer))

    async def _read_loop(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                for raw in self._assembler.feed(chunk):
                    hello = parse_local_hello(raw)
                    if hello is not None:
                        if hello.casefold() != self.sn_code.casefold():
                            self._warn_once("Closed station connection: its serial does not match the configured one")
                            return
                        writer.write(LOCAL_HELLO_REPLY)
                        await writer.drain()
                        continue
                    parsed = parse_local_frame(raw)
                    if parsed is None:
                        continue
                    _, metrics = parsed
                    writer.write(LOCAL_ACK_FRAME)
                    await writer.drain()
                    self._on_data(metrics)
                    self._on_state(True)
                    if self._watchdog_task:
                        self._watchdog_task.cancel()
                    self._watchdog_task = asyncio.create_task(self._watchdog())
        except (asyncio.CancelledError, ConnectionError):
            pass
        finally:
            if self._writer is writer:
                self._writer = None
                self._on_state(False)
            await self._close_writer(writer)

    @staticmethod
    async def _close_writer(writer: asyncio.StreamWriter) -> None:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass  # The station reset the connection; it is closed either way.

    def _warn_once(self, message: str) -> None:
        if message not in self._warned:
            self._warned.add(message)
            _LOGGER.warning(message)

    async def _watchdog(self) -> None:
        await asyncio.sleep(LOCAL_FRAME_TIMEOUT)
        self._on_state(False)


def _crc16_modbus(data: bytes) -> int:
    """CRC16/MODBUS: poly 0xA001 (reflected 0x8005), init 0xFFFF."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_control_command(tag_hex: str, value: int) -> str:
    """Build the FOSSiBOT control command hex string for a given tag/value.

    Reverse-engineered from six captured (tag, value) -> cmd pairs (AC/DC/
    USB, each on and off), all of which this formula reproduces byte-for-
    byte. See const.py's CTRL_COMMAND_PREFIX for the format breakdown.
    """
    payload = bytes.fromhex(tag_hex) + value.to_bytes(4, "little")
    crc = _crc16_modbus(payload)
    return CTRL_COMMAND_PREFIX + payload.hex() + crc.to_bytes(2, "big").hex()


class FossibotApiClient:
    """Login + device discovery over the REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str = "",
        password: str = "",
        local: FossibotLocalTcpServer | None = None,
    ) -> None:
        self.session = session
        self.email = email
        self.password = password
        self.token: str | None = None
        self.local = local

    async def async_login(self) -> str:
        if self.local:
            raise FossibotConnectionError("cloud login is unavailable in local mode")
        headers = {**_COMMON_HEADERS, "Content-Type": "application/json"}
        payload = {"username": self.email, "password": self.password}

        for attempt in range(LOGIN_MAX_RETRIES + 1):
            try:
                async with self.session.post(
                    LOGIN_ENDPOINT, json=payload, headers=headers
                ) as resp:
                    text = await resp.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.debug("FOSSiBOT login request failed: %s", err)
                raise FossibotConnectionError(
                    f"request to {LOGIN_ENDPOINT} failed: {err}"
                ) from err

            _LOGGER.debug("FOSSiBOT login response: status=%s body=%s", resp.status, text)
            try:
                data = json.loads(text)
            except ValueError as err:
                raise FossibotConnectionError(
                    f"non-JSON response (HTTP {resp.status}): {text[:200]!r}"
                ) from err

            if data.get("code") == 200 and data.get("token"):
                self.token = data["token"]
                return self.token

            msg = data.get("msg", f"login failed (HTTP {resp.status})")
            if LOGIN_DUPLICATE_SUBMIT_MARKER in msg and attempt < LOGIN_MAX_RETRIES:
                # The backend's anti-duplicate-submission guard rejected an
                # identical login sent too soon after a previous one (e.g.
                # the config flow's own validation login). The credentials
                # are fine - just wait it out and retry.
                _LOGGER.debug(
                    "FOSSiBOT login hit anti-duplicate guard (attempt %s/%s), "
                    "retrying in %ss: %s",
                    attempt + 1,
                    LOGIN_MAX_RETRIES,
                    LOGIN_RETRY_DELAY,
                    msg,
                )
                await asyncio.sleep(LOGIN_RETRY_DELAY)
                continue

            raise FossibotAuthError(msg)

        raise FossibotAuthError("login failed after retries")

    async def async_get_devices(self, *, _retried: bool = False) -> list[dict]:
        if self.local:
            return [{"snCode": self.local.sn_code, "deviceName": "Fossibot", "state": True}]
        if not self.token:
            await self.async_login()
        headers = {**_COMMON_HEADERS, "Authorization": f"Bearer {self.token}"}
        try:
            async with self.session.get(
                DEVICE_LIST_ENDPOINT,
                params={"pageNum": 1, "pageSize": 50},
                headers=headers,
            ) as resp:
                if resp.status == 401 and not _retried:
                    # Token expired - the source spec never covers refresh,
                    # so just re-login once and retry.
                    await self.async_login()
                    return await self.async_get_devices(_retried=True)
                text = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("FOSSiBOT device-list request failed: %s", err)
            raise FossibotConnectionError(
                f"request to {DEVICE_LIST_ENDPOINT} failed: {err}"
            ) from err

        _LOGGER.debug("FOSSiBOT device-list response: status=%s body=%s", resp.status, text)
        try:
            data = json.loads(text)
        except ValueError as err:
            raise FossibotConnectionError(str(err)) from err

        if data.get("code") != 200:
            raise FossibotConnectionError(data.get("msg", "device list failed"))
        return data.get("rows", [])

    async def async_send_control(
        self, sn_code: str, tag_hex: str, value: int, *, _retried: bool = False
    ) -> None:
        """Send a control command that writes `value` to `tag_hex` on `sn_code`.

        Captured via Charles for AC (tag 2700), DC (2800), and USB (2900),
        each on (1) and off (0) - see build_control_command() for the byte
        format this reproduces exactly. Untested for any other tag/value.
        """
        if self.local:
            await self.local.async_send(tag_hex, value)
            return
        if not self.token:
            await self.async_login()
        cmd = build_control_command(tag_hex, value)
        headers = {**_COMMON_HEADERS, "Authorization": f"Bearer {self.token}"}
        try:
            async with self.session.get(
                CONTROL_ENDPOINT,
                params={"snCode": sn_code, "cmd": cmd},
                headers=headers,
            ) as resp:
                if resp.status == 401 and not _retried:
                    await self.async_login()
                    return await self.async_send_control(
                        sn_code, tag_hex, value, _retried=True
                    )
                text = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("FOSSiBOT control request failed: %s", err)
            raise FossibotConnectionError(
                f"control command to {sn_code} failed: {err}"
            ) from err

        _LOGGER.debug(
            "FOSSiBOT control %s tag=%s value=%s cmd=%s -> status=%s body=%s",
            sn_code,
            tag_hex,
            value,
            cmd,
            resp.status,
            text,
        )
        try:
            data = json.loads(text)
        except ValueError:
            # Best-effort: an unparsable response shouldn't crash the switch,
            # since the command may well have succeeded anyway (the six
            # captured examples were all read as plain 200/JSON, but this
            # endpoint's error shape was never actually captured).
            return
        if data.get("code") != 200:
            raise FossibotConnectionError(
                data.get("msg", f"control command failed (HTTP {resp.status})")
            )


class FossibotWebSocket:
    """One persistent WSS telemetry channel for a single device (snCode).

    The original spec only described the happy path (connect, heartbeat
    every 5s). It said nothing about what to do if the socket drops, so
    this adds a reconnect loop with a fixed backoff.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api: FossibotApiClient,
        sn_code: str,
        on_data: Callable[[dict[str, int]], None],
    ) -> None:
        self._session = session
        self._api = api
        self._sn_code = sn_code
        self._on_data = on_data
        self._heartbeat_task: asyncio.Task | None = None
        self._listen_task: asyncio.Task | None = None
        self._stopped = False

    async def async_start(self) -> None:
        self._stopped = False
        self._listen_task = asyncio.create_task(self._run())

    async def async_stop(self) -> None:
        self._stopped = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._listen_task:
            self._listen_task.cancel()

    async def _run(self) -> None:
        while not self._stopped:
            try:
                await self._connect_and_listen()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("FOSSiBOT WS %s dropped: %s", self._sn_code, err)
            if self._stopped:
                break
            await asyncio.sleep(RECONNECT_DELAY)

    async def _connect_and_listen(self) -> None:
        headers = {
            **_COMMON_HEADERS,
            "Authorization": f"Bearer {self._api.token}",
            "snCode": self._sn_code,
            "Origin": "http://localhost",
            "User-Agent": "okhttp/3.12.11",
        }
        async with self._session.ws_connect(WS_URL, headers=headers, heartbeat=None) as ws:
            self._heartbeat_task = asyncio.create_task(self._send_heartbeat(ws))
            try:
                while True:
                    # `async for msg in ws` blocks forever if the connection
                    # dies silently at the network level (no close frame, no
                    # exception - observed in the field). Bound each read so
                    # a dead-but-not-closed socket still triggers reconnect.
                    try:
                        msg = await asyncio.wait_for(
                            ws.receive(), timeout=FRAME_SILENCE_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        _LOGGER.warning(
                            "FOSSiBOT WS %s: no data for %ss, reconnecting",
                            self._sn_code,
                            FRAME_SILENCE_TIMEOUT,
                        )
                        return
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self._handle_frame(msg.data)
                    elif msg.type in (
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                        aiohttp.WSMsgType.CLOSE,
                    ):
                        return
            finally:
                self._heartbeat_task.cancel()

    async def _send_heartbeat(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        payload = {"type": "hear", "msg": self._api.email}
        try:
            while not ws.closed:
                await ws.send_json(payload)
                await asyncio.sleep(HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            pass
        except aiohttp.ClientError as err:
            _LOGGER.debug("Heartbeat send failed for %s: %s", self._sn_code, err)

    def _handle_frame(self, raw: str) -> None:
        try:
            envelope = json.loads(raw)
            hex_data = envelope["data"]
            metrics = parse_payload(hex_data)
        except (ValueError, KeyError, IndexError) as err:
            _LOGGER.debug("Ignoring unparsable frame from %s: %s", self._sn_code, err)
            return
        _LOGGER.debug(
            "FOSSiBOT %s frame: raw=%s decoded=%s", self._sn_code, hex_data, metrics
        )
        self._on_data(metrics)
