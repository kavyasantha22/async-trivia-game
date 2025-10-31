import asyncio
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


class _DummyResponse:
    def __init__(self, payload=None):
        if payload is None:
            payload = {"message": {"content": ""}}
        self._payload = payload

    def json(self):
        return self._payload


if "requests" not in sys.modules:
    sys.modules["requests"] = SimpleNamespace(post=lambda *args, **kwargs: _DummyResponse())

from client import Client


class _DummyWriter:
    def __init__(self) -> None:
        self._closed = False

    def close(self) -> None:
        self._closed = True

    async def wait_closed(self) -> None:
        return None

    def is_closing(self) -> bool:
        return self._closed


class TestClientFunction(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.input_queue = asyncio.Queue()
        self.queue_patch = patch("client.INPUT_QUEUE", new=self.input_queue)
        self.queue_patch.start()

        self.sent_messages = asyncio.Queue()

        async def fake_send_message(writer, message):
            await self.sent_messages.put(message)

        self.send_patch = patch("client.send_message", new=fake_send_message)
        self.send_patch.start()

        self.dummy_writer = _DummyWriter()
        self.dummy_reader = AsyncMock()
        self.open_connection_patch = patch(
            "asyncio.open_connection",
            new=AsyncMock(return_value=(self.dummy_reader, self.dummy_writer)),
        )
        self.open_connection_patch.start()

        self.client = Client(username="test1", mode="you")

    async def asyncTearDown(self):
        if self.send_patch:
            self.send_patch.stop()
        if self.queue_patch:
            self.queue_patch.stop()
        if self.open_connection_patch:
            self.open_connection_patch.stop()

        if self.client._answer_task:
            self.client._answer_task.cancel()
        if self.client._recv_loop_task:
            self.client._recv_loop_task.cancel()


    async def test_client_connects_to_server(self):
        await self.input_queue.put("CONNECT example.com:1234")
        await self.client.connect()
        self.assertTrue(self.client.connected)
        self.assertIs(self.client.writer, self.dummy_writer)
        await self.client._disconnect()


    async def test_client_disconnects_from_server(self):
        await self.input_queue.put("CONNECT example.com:1234")
        await self.client.connect()
        self.assertTrue(self.client.connected)
        await self.client._disconnect()
        self.assertFalse(self.client.connected)

    async def test_answer_question_user_mode_uses_input_queue(self):
        question = {
            "question_type": "Mathematics",
            "short_question": "1 + 2",
            "trivia_question": "Compute 1 + 2",
            "time_limit": 1,
        }

        user_answer = "42"
        await self.input_queue.put(user_answer)

        self.client.writer = object()

        await self.client._answer_question(question, 1)

        sent = await asyncio.wait_for(self.sent_messages.get(), timeout=1)
        self.assertEqual(sent, {"message_type": "ANSWER", "answer": user_answer})

    async def test_answer_question_auto_mode_generates_answer(self):
        auto_client = Client(username="bot", mode="auto")
        auto_client.writer = object()
        question = {
            "question_type": "Mathematics",
            "short_question": "5 - 3 + 1",
            "trivia_question": "Compute 5 - 3 + 1",
            "time_limit": 1,
        }

        await auto_client._answer_question(question, 1)

        sent = await asyncio.wait_for(self.sent_messages.get(), timeout=1)
        self.assertEqual(sent, {"message_type": "ANSWER", "answer": "3"})

    async def test_answer_question_ai_mode_uses_ollama(self): 
        ollama_config = {
            "ollama_host": "localhost",
            "ollama_port": 11434,
            "ollama_model": "llama2",
        }
        ai_client = Client(username="ai", mode="ai", ollama_config=ollama_config)
        ai_client.writer = object()
        question = {
            "question_type": "Roman Numerals",
            "short_question": "X",
            "trivia_question": "Convert X to decimal",
            "time_limit": 1,
        }


        with patch.object(Client, "_ask_ollama", new=AsyncMock(return_value="10")) as ask_mock:
            await ai_client._answer_question(question, 1)
            ask_mock.assert_awaited()

        sent = await asyncio.wait_for(self.sent_messages.get(), timeout=1)
        self.assertEqual(sent, {"message_type": "ANSWER", "answer": "10"})

    async def test_answer_question_times_out_without_input(self):
        question = {
            "question_type": "Mathematics",
            "short_question": "7 + 8",
            "trivia_question": "Compute 7 + 8",
            "time_limit": 0.1,
        }

        self.client.writer = object()

        result = await self.client._answer_question(question, 0.1)

        self.assertIsNone(result)
        self.assertTrue(self.sent_messages.empty())