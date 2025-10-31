import asyncio
import json
import unittest

from helper import receive_message, send_message


class _DummyWriter:
    def __init__(self):
        self.buffer: asyncio.Queue[bytes] = asyncio.Queue()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer.put_nowait(data)

    async def drain(self) -> None:
        await asyncio.sleep(0)

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.closed = True


class _DummyReader:
    def __init__(self) -> None:
        self.buffer: asyncio.Queue[bytes] = asyncio.Queue()

    def feed_line(self, data: bytes) -> None:
        self.buffer.put_nowait(data)

    async def readline(self) -> bytes:
        return await self.buffer.get()


class TestHelperMessaging(unittest.IsolatedAsyncioTestCase):

    async def test_send_message_delivers_payload_to_server(self):
        writer = _DummyWriter()
        payload = {"message_type": "HI", "username": "test1"}

        await send_message(writer, payload)
        raw = await asyncio.wait_for(writer.buffer.get(), timeout=1)
        received = json.loads(raw.decode("utf-8").strip())

        self.assertEqual(received, payload)

    async def test_receive_message_returns_payload_from_server(self):
        reader = _DummyReader()
        payload = {"message_type": "READY", "info": "Welcome"}
        reader.feed_line((json.dumps(payload) + "\n").encode("utf-8"))

        received = await asyncio.wait_for(receive_message(reader), timeout=1)

        self.assertEqual(received, payload)

    async def test_receive_message_returns_none_when_connection_closes(self):
        reader = _DummyReader()
        reader.feed_line(b"")

        result = await asyncio.wait_for(receive_message(reader), timeout=1)

        self.assertIsNone(result)

    async def test_multiple_messages_preserve_order(self):
        writer = _DummyWriter()
        payloads = [
            {"message_type": "ONE"},
            {"message_type": "TWO", "value": 2},
            {"message_type": "THREE", "nested": {"a": 1}},
        ]

        for payload in payloads:
            await send_message(writer, payload)

        received = []
        for _ in payloads:
            raw = await asyncio.wait_for(writer.buffer.get(), timeout=1)
            received.append(json.loads(raw.decode("utf-8").strip()))

        self.assertEqual(received, payloads)
