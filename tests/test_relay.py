"""Tests for the always-on relay between the station and Home Assistant."""
import asyncio
import importlib
import importlib.util
import pathlib
import struct
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("fossibot_relay", ROOT / "tools" / "fossibot_relay.py")
relay_module = importlib.util.module_from_spec(spec)
sys.modules["fossibot_relay"] = relay_module
spec.loader.exec_module(relay_module)
relay_module.log = lambda *parts: None

package = types.ModuleType("fossibot_plus")
package.__path__ = [str(ROOT / "custom_components" / "fossibot_plus")]
sys.modules.setdefault("fossibot_plus", package)
try:
    import aiohttp  # noqa: F401
except ImportError:
    sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
api = importlib.import_module("fossibot_plus.api")

SERIAL = "F180V012345TEST1"
HELLO = b"\x1a\x00\x51\x00\x14\x00" + SERIAL.encode() + bytes.fromhex("07020110")
HELLO_REPLY = bytes.fromhex("0c0052000600000000000000")
ACK = bytes.fromhex("0a001f00040004001f00")
LED_ON = bytes.fromhex("0e000c000800260001000000e106")


def telemetry(soc=87):
    records = struct.pack("<HI", 1, soc)
    length = 6 + len(records) + 2
    crc = api._crc16_modbus(records)
    return struct.pack("<HHH", length, 0x000B, length - 6) + records + crc.to_bytes(2, "big")


class FakeHa:
    """Stands in for HA's listener and records what arrives from the relay."""

    def __init__(self):
        self.server = None
        self.port = None
        self.received = bytearray()
        self.writers = []
        self.connected = asyncio.Event()

    async def start(self, port=0):
        self.connected = asyncio.Event()
        self.server = await asyncio.start_server(self._accept, "127.0.0.1", port)
        self.port = self.server.sockets[0].getsockname()[1]

    async def _accept(self, reader, writer):
        self.writers.append(writer)
        self.connected.set()
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                return
            self.received.extend(chunk)

    async def wait_for(self, data):
        for _ in range(150):
            if data in self.received:
                return True
            await asyncio.sleep(0.02)
        return False

    async def stop(self):
        self.server.close()
        for writer in self.writers:
            writer.close()
        self.writers.clear()


class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ha = FakeHa()
        await self.ha.start()
        self.relay = None
        self.station_writers = []

    async def start_relay(self, station_ip="127.0.0.1", ha_port=None):
        self.relay = relay_module.Relay(
            "127.0.0.1", 0, station_ip, "127.0.0.1", ha_port or self.ha.port, ha_retry=0.05
        )
        await self.relay.start()
        return self.relay.port

    async def connect_station(self, port):
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        self.station_writers.append(writer)
        return reader, writer

    async def asyncTearDown(self):
        for writer in self.station_writers:
            writer.close()
        if self.relay:
            await self.relay.stop()
        await self.ha.stop()

    async def test_replies_to_hello_while_ha_is_down(self):
        await self.ha.stop()
        reader, writer = await self.connect_station(await self.start_relay())
        writer.write(HELLO)
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(HELLO_REPLY)), 2), HELLO_REPLY)

    async def test_acks_reports_while_ha_is_down(self):
        await self.ha.stop()
        reader, writer = await self.connect_station(await self.start_relay())
        writer.write(telemetry())
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(ACK)), 2), ACK)

    async def test_forwards_reports_to_ha(self):
        _reader, writer = await self.connect_station(await self.start_relay())
        await asyncio.wait_for(self.ha.connected.wait(), 2)
        writer.write(telemetry(soc=61))
        await writer.drain()
        self.assertTrue(await self.ha.wait_for(telemetry(soc=61)))

    async def test_forwards_a_report_split_across_packets(self):
        _reader, writer = await self.connect_station(await self.start_relay())
        await asyncio.wait_for(self.ha.connected.wait(), 2)
        frame = telemetry(soc=62)
        writer.write(frame[:5])
        await writer.drain()
        await asyncio.sleep(0.05)
        writer.write(frame[5:])
        await writer.drain()
        self.assertTrue(await self.ha.wait_for(frame))

    async def test_forwards_commands_from_ha_to_station(self):
        reader, writer = await self.connect_station(await self.start_relay())
        await asyncio.wait_for(self.ha.connected.wait(), 2)
        writer.write(HELLO)
        await writer.drain()
        await asyncio.wait_for(reader.readexactly(len(HELLO_REPLY)), 2)
        self.ha.writers[-1].write(LED_ON)
        await self.ha.writers[-1].drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(LED_ON)), 2), LED_ON)

    async def test_does_not_pass_ha_replies_to_station(self):
        reader, writer = await self.connect_station(await self.start_relay())
        await asyncio.wait_for(self.ha.connected.wait(), 2)
        writer.write(telemetry())
        await writer.drain()
        await asyncio.wait_for(reader.readexactly(len(ACK)), 2)
        self.ha.writers[-1].write(ACK + HELLO_REPLY + LED_ON)
        await self.ha.writers[-1].drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(LED_ON)), 2), LED_ON)

    async def test_ha_restart_does_not_touch_the_station_link(self):
        reader, writer = await self.connect_station(await self.start_relay())
        await asyncio.wait_for(self.ha.connected.wait(), 2)
        port = self.ha.port
        await self.ha.stop()
        await asyncio.sleep(0.1)
        writer.write(telemetry(soc=40))
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(ACK)), 2), ACK)
        self.ha = FakeHa()
        await self.ha.start(port)
        await asyncio.wait_for(self.ha.connected.wait(), 2)
        writer.write(telemetry(soc=41))
        await writer.drain()
        self.assertTrue(await self.ha.wait_for(telemetry(soc=41)))

    async def test_sends_known_hello_when_ha_connects_later(self):
        port = self.ha.port
        await self.ha.stop()
        reader, writer = await self.connect_station(await self.start_relay(ha_port=port))
        writer.write(HELLO)
        await writer.drain()
        await asyncio.wait_for(reader.readexactly(len(HELLO_REPLY)), 2)
        self.ha = FakeHa()
        await self.ha.start(port)
        self.assertTrue(await self.ha.wait_for(HELLO))

    async def test_rejects_peer_other_than_station(self):
        reader, _writer = await self.connect_station(await self.start_relay(station_ip="127.0.0.2"))
        self.assertEqual(await asyncio.wait_for(reader.read(64), 2), b"")

    async def test_new_station_connection_replaces_the_old_one(self):
        port = await self.start_relay()
        old_reader, _old = await self.connect_station(port)
        new_reader, new = await self.connect_station(port)
        new.write(telemetry())
        await new.drain()
        self.assertEqual(await asyncio.wait_for(new_reader.readexactly(len(ACK)), 2), ACK)
        self.assertEqual(await asyncio.wait_for(old_reader.read(64), 2), b"")

    async def test_works_with_the_integration_listener(self):
        await self.ha.stop()
        data = []
        states = []
        listener = api.FossibotLocalTcpServer(
            "127.0.0.1", 0, SERIAL, data.append, states.append, allowed_ip="127.0.0.1"
        )
        await listener.async_start()
        try:
            ha_port = listener._server.sockets[0].getsockname()[1]
            reader, writer = await self.connect_station(await self.start_relay(ha_port=ha_port))
            writer.write(HELLO)
            await writer.drain()
            self.assertEqual(await asyncio.wait_for(reader.readexactly(len(HELLO_REPLY)), 2), HELLO_REPLY)
            writer.write(telemetry(soc=77))
            await writer.drain()
            self.assertEqual(await asyncio.wait_for(reader.readexactly(len(ACK)), 2), ACK)
            for _ in range(100):
                if data:
                    break
                await asyncio.sleep(0.02)
            self.assertEqual(data[-1]["0100"], 77)
            await listener.async_send("2600", 1)
            self.assertEqual(await asyncio.wait_for(reader.readexactly(len(LED_ON)), 2), LED_ON)
        finally:
            await listener.async_stop()


class RelayOnSelectorLoopTests(RelayTests):
    """Phone and HA run Linux, which uses a selector loop."""

    loop_factory = asyncio.SelectorEventLoop


if __name__ == "__main__":
    unittest.main()
