"""Tests for the station-facing TCP server, run with: python -m unittest discover -s tests

The integration's __init__.py needs Home Assistant, so api.py is loaded through a bare
package. aiohttp is only used by the cloud client, which these tests do not exercise.
"""
import asyncio
import importlib
import logging
import pathlib
import socket
import struct
import sys
import types
import unittest

COMPONENT = pathlib.Path(__file__).parents[1] / "custom_components" / "fossibot_plus"
package = types.ModuleType("fossibot_plus")
package.__path__ = [str(COMPONENT)]
sys.modules.setdefault("fossibot_plus", package)
try:
    import aiohttp  # noqa: F401
except ImportError:
    sys.modules["aiohttp"] = types.ModuleType("aiohttp")
api = importlib.import_module("fossibot_plus.api")
logging.getLogger("fossibot_plus.api").setLevel(logging.ERROR)

SERIAL = "F180V012345TEST1"
FIRMWARE = bytes.fromhex("07020110")
HELLO = b"\x1a\x00\x51\x00\x14\x00" + SERIAL.encode() + FIRMWARE
HELLO_REPLY = bytes.fromhex("0c0052000600000000000000")
ACK = bytes.fromhex("0a001f00040004001f00")
LED_ON = bytes.fromhex("0e000c000800260001000000e106")


def telemetry(soc=87):
    records = struct.pack("<HI", 1, soc) + struct.pack("<HI", 38, 0)
    length = 6 + len(records) + 2
    crc = api._crc16_modbus(records)
    return struct.pack("<HHH", length, 0x000B, length - 6) + records + crc.to_bytes(2, "big")


class ParseHelloTests(unittest.TestCase):
    def test_returns_serial_from_hello_frame(self):
        self.assertEqual(api.parse_local_hello(HELLO), SERIAL)

    def test_ignores_other_frame_types(self):
        self.assertIsNone(api.parse_local_hello(telemetry()))

    def test_ignores_truncated_hello(self):
        self.assertIsNone(api.parse_local_hello(HELLO[:12]))


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.data = []
        self.states = []
        self.loop_errors = []
        asyncio.get_running_loop().set_exception_handler(
            lambda _loop, context: self.loop_errors.append(context)
        )
        self.writers = []
        self.server = None

    async def start(self, allowed_ip="127.0.0.1", serial=SERIAL):
        self.server = api.FossibotLocalTcpServer(
            "127.0.0.1",
            0,
            serial,
            self.data.append,
            self.states.append,
            allowed_ip=allowed_ip,
        )
        await self.server.async_start()
        return self.server._server.sockets[0].getsockname()[1]

    async def connect(self, port):
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        self.writers.append(writer)
        return reader, writer

    async def asyncTearDown(self):
        for writer in self.writers:
            writer.close()
        if self.server:
            await self.server.async_stop()

    async def test_replies_to_hello_with_matching_serial(self):
        reader, writer = await self.connect(await self.start())
        writer.write(HELLO)
        await writer.drain()
        reply = await asyncio.wait_for(reader.readexactly(len(HELLO_REPLY)), 2)
        self.assertEqual(reply, HELLO_REPLY)

    async def test_closes_connection_on_other_serial(self):
        reader, writer = await self.connect(await self.start(serial="F180V0OTHERSTAT1"))
        writer.write(HELLO)
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.read(64), 2), b"")

    async def test_serial_comparison_ignores_case(self):
        reader, writer = await self.connect(await self.start(serial=SERIAL.lower()))
        writer.write(HELLO)
        await writer.drain()
        reply = await asyncio.wait_for(reader.readexactly(len(HELLO_REPLY)), 2)
        self.assertEqual(reply, HELLO_REPLY)

    async def test_rejects_peer_other_than_allowed_ip(self):
        reader, _writer = await self.connect(await self.start(allowed_ip="127.0.0.2"))
        self.assertEqual(await asyncio.wait_for(reader.read(64), 2), b"")

    async def test_allowed_ip_is_an_exact_match(self):
        reader, _writer = await self.connect(await self.start(allowed_ip="127.0.0"))
        self.assertEqual(await asyncio.wait_for(reader.read(64), 2), b"")

    async def test_telemetry_after_hello_is_delivered_and_acked(self):
        reader, writer = await self.connect(await self.start())
        writer.write(HELLO)
        await writer.drain()
        await asyncio.wait_for(reader.readexactly(len(HELLO_REPLY)), 2)
        writer.write(telemetry(soc=87))
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(ACK)), 2), ACK)
        self.assertEqual(self.data[-1]["0100"], 87)
        self.assertEqual(self.states[-1], True)

    async def test_telemetry_without_hello_is_accepted_on_reconnect(self):
        reader, writer = await self.connect(await self.start())
        writer.write(telemetry(soc=55))
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(ACK)), 2), ACK)
        self.assertEqual(self.data[-1]["0100"], 55)

    async def test_command_reaches_the_station_after_hello(self):
        reader, writer = await self.connect(await self.start())
        writer.write(HELLO)
        await writer.drain()
        await asyncio.wait_for(reader.readexactly(len(HELLO_REPLY)), 2)
        await self.server.async_send("2600", 1)
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(LED_ON)), 2), LED_ON)

    async def test_connection_reset_by_station_marks_it_offline_cleanly(self):
        port = await self.start()
        reader, writer = await self.connect(port)
        writer.write(telemetry())
        await writer.drain()
        await asyncio.wait_for(reader.readexactly(len(ACK)), 2)
        sock = writer.get_extra_info("socket")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        writer.transport.abort()
        for _ in range(50):
            if self.states and self.states[-1] is False:
                break
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.05)
        self.assertEqual(self.states[-1], False)
        self.assertEqual(self.server._reader_task.done(), True)
        self.assertIsNone(self.server._reader_task.exception())
        self.assertEqual(self.loop_errors, [])


class ServerOnSelectorLoopTests(ServerTests):
    """HA on Linux uses a selector loop, whose wait_closed() re-raises a reset."""

    loop_factory = asyncio.SelectorEventLoop


if __name__ == "__main__":
    unittest.main()
