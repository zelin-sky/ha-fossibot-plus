"""Always-on relay between a FOSSiBOT station and Home Assistant.

The station leaves Wi-Fi about 75 s after losing its server, so a Home Assistant restart must
not look like a server outage. This relay holds the station's connection itself: it answers the
hello and ACKs every report whether or not Home Assistant is running. Reports are copied to Home
Assistant's listener while it is up, and only write commands travel back to the station.

Usage: fossibot_relay.py BIND PORT STATION_IP HA_HOST HA_PORT
"""
from __future__ import annotations

import asyncio
import sys
import time

HEADER_LEN = 6
MAX_FRAME_LEN = 4096
MAX_HA_BUFFER = 1024 * 1024
TYPE_REPORT = 0x000B
TYPE_WRITE = 0x000C
TYPE_HELLO = 0x0051
HELLO_REPLY = bytes.fromhex("0c0052000600000000000000")
REPORT_ACK = bytes.fromhex("0a001f00040004001f00")


def log(*parts) -> None:
    print(time.strftime("%F %T"), *parts, flush=True)


class FrameBuffer:
    """Split a TCP stream into frames, whose first two bytes are the little-endian length."""

    def __init__(self) -> None:
        self._data = bytearray()

    def feed(self, chunk: bytes) -> list[bytes]:
        self._data.extend(chunk)
        frames = []
        while len(self._data) >= HEADER_LEN:
            length = int.from_bytes(self._data[:2], "little")
            if length < HEADER_LEN or length > MAX_FRAME_LEN:
                del self._data[0]
                continue
            if len(self._data) < length:
                break
            frames.append(bytes(self._data[:length]))
            del self._data[:length]
        return frames


def frame_type(frame: bytes) -> int:
    return int.from_bytes(frame[2:4], "little")


async def close_writer(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass


class Relay:
    def __init__(
        self,
        bind: str,
        port: int,
        station_ip: str,
        ha_host: str,
        ha_port: int,
        ha_retry: float = 3.0,
    ) -> None:
        self._bind = bind
        self._requested_port = port
        self._station_ip = station_ip
        self._ha_host = ha_host
        self._ha_port = ha_port
        self._ha_retry = ha_retry
        self._server: asyncio.AbstractServer | None = None
        self._ha_task: asyncio.Task | None = None
        self._station: asyncio.StreamWriter | None = None
        self._ha: asyncio.StreamWriter | None = None
        self._hello: bytes | None = None
        self._ha_was_up = False
        self.port = port

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._on_station, self._bind, self._requested_port)
        self.port = self._server.sockets[0].getsockname()[1]
        self._ha_task = asyncio.create_task(self._ha_loop())
        log("listening on", self._bind, self.port, "for station", self._station_ip)

    async def stop(self) -> None:
        if self._ha_task:
            self._ha_task.cancel()
            try:
                await self._ha_task
            except asyncio.CancelledError:
                pass
        for writer in (self._station, self._ha):
            if writer:
                await close_writer(writer)
        self._station = self._ha = None
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def _copy_to_ha(self, frame: bytes) -> None:
        ha = self._ha
        if ha is None or ha.is_closing():
            return
        if ha.transport.get_write_buffer_size() > MAX_HA_BUFFER:
            log("Home Assistant is not reading; dropping its connection")
            ha.close()
            return
        ha.write(frame)

    async def _on_station(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        address = peer[0] if peer else ""
        if address != self._station_ip:
            log("rejected connection from", address)
            await close_writer(writer)
            return
        if self._station:
            await close_writer(self._station)
        self._station = writer
        log("station connected from", address)
        frames = FrameBuffer()
        reason = "closed"
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                for frame in frames.feed(chunk):
                    kind = frame_type(frame)
                    if kind == TYPE_HELLO:
                        self._hello = frame
                        writer.write(HELLO_REPLY)
                    elif kind == TYPE_REPORT:
                        writer.write(REPORT_ACK)
                    else:
                        continue
                    self._copy_to_ha(frame)
                await writer.drain()
        except OSError as err:
            reason = str(err)
        finally:
            if self._station is writer:
                self._station = None
                log("station disconnected:", reason)
            await close_writer(writer)

    async def _ha_loop(self) -> None:
        while True:
            try:
                reader, writer = await asyncio.open_connection(self._ha_host, self._ha_port)
            except OSError:
                if self._ha_was_up:
                    log("Home Assistant is unavailable; still holding the station's connection")
                    self._ha_was_up = False
                await asyncio.sleep(self._ha_retry)
                continue
            self._ha = writer
            self._ha_was_up = True
            log("connected to Home Assistant")
            if self._hello:
                writer.write(self._hello)
            try:
                await self._read_ha(reader)
            except OSError:
                pass
            finally:
                self._ha = None
                await close_writer(writer)
            await asyncio.sleep(self._ha_retry)

    async def _read_ha(self, reader: asyncio.StreamReader) -> None:
        frames = FrameBuffer()
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                return
            for frame in frames.feed(chunk):
                if frame_type(frame) != TYPE_WRITE:
                    continue
                station = self._station
                if station is None or station.is_closing():
                    log("dropped a command: the station is not connected")
                    continue
                station.write(frame)


async def main() -> None:
    bind, port, station_ip, ha_host, ha_port = sys.argv[1:6]
    relay = Relay(bind, int(port), station_ip, ha_host, int(ha_port))
    await relay.start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
