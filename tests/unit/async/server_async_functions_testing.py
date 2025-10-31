import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from server import (
    ClientSession,
    GameState,
    QuestionRound,
    Server,
    ServerMessageConfig,
)


def _make_config(players: int = 2) -> ServerMessageConfig:
    return ServerMessageConfig(
        port=0,
        players=players,
        question_types=["Mathematics"],
        question_formats={"Mathematics": "Solve {}"},
        question_seconds=10,
        question_interval_seconds=0,
        ready_info="Ready",
        question_word="Question",
        correct_answer="Correct",
        incorrect_answer="Incorrect",
        points_noun_singular="point",
        points_noun_plural="points",
        final_standings_heading="Standings",
        one_winner="Winner: {}",
        multiple_winners="Winners: {}",
    )


def _make_server(players: int = 2) -> Server:
    cfg = _make_config(players)
    original_log = Server._log
    try:
        Server._log = lambda self, *_, **__: None
        server = Server(
            port=cfg.port,
            players=cfg.players,
            question_types=cfg.question_types,
            question_formats=cfg.question_formats,
            question_seconds=cfg.question_seconds,
            question_interval_seconds=cfg.question_interval_seconds,
            ready_info=cfg.ready_info,
            question_word=cfg.question_word,
            correct_answer=cfg.correct_answer,
            incorrect_answer=cfg.incorrect_answer,
            points_noun_singular=cfg.points_noun_singular,
            points_noun_plural=cfg.points_noun_plural,
            final_standings_heading=cfg.final_standings_heading,
            one_winner=cfg.one_winner,
            multiple_winners=cfg.multiple_winners,
            config_message=cfg,
        )
    finally:
        Server._log = original_log
    server._log = lambda *_, **__: None
    return server


class TestServerAsyncFunctions(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.server = _make_server(players=2)

    def tearDown(self) -> None:
        self.server = None

    async def test_orchestrator_broadcasts_finished_message(self):
        self.server._state = GameState.FINISHED
        finished_message = {"message_type": "FINISHED"}
        self.server._construct_finished_message = MagicMock(return_value=finished_message)

        with patch.object(self.server, "_broadcast", new=AsyncMock()) as broadcast_mock, \
             patch.object(self.server, "_shutdown_everything", new=AsyncMock()) as shutdown_mock:
            await self.server._orchestrator()

        broadcast_mock.assert_awaited_once_with(finished_message)
        shutdown_mock.assert_awaited_once()

    async def test_handle_client_registers_and_receives(self):
        reader = AsyncMock()
        writer = MagicMock()
        writer.get_extra_info.return_value = ("127.0.0.1", 1234)

        messages = [{"message_type": "PING"}, None]

        with patch("server.receive_message", new=AsyncMock(side_effect=messages)), \
             patch.object(self.server, "_process_message", new=AsyncMock()) as process_mock:
            await self.server._handle_client(reader, writer)

        process_mock.assert_awaited_once_with({"message_type": "PING"}, writer)

    async def test_broadcast_sends_to_all_sessions(self):
        writer_one = _DummyWriter()
        writer_two = _DummyWriter()
        await self.server._process_message({"message_type": "HI", "username": "alice"}, writer_one)
        await self.server._process_message({"message_type": "HI", "username": "bob"}, writer_two)
        self.assertEqual(len(self.server._active_sessions), 2)

        sent = []

        async def fake_send_message(writer, message):
            sent.append((writer, message))

        with patch("server.send_message", new=fake_send_message):
            await self.server._broadcast({"message_type": "PING"})

        self.assertEqual(len(sent), len(self.server._active_sessions))

    async def test_shutdown_everything_closes_sessions(self):
        writer = _DummyWriter()
        await self.server._process_message({"message_type": "HI", "username": "alice"}, writer)

        await self.server._shutdown_everything()

        self.assertTrue(writer.close_called)
        self.assertTrue(writer.wait_closed_called)
        session = next(iter(self.server._sessions.values()), None)
        self.assertIsNotNone(session)
        self.assertFalse(session.is_active)

    async def test_process_message_hi_registers_session(self):
        writer = _DummyWriter()
        await self.server._process_message({"message_type": "HI", "username": "alice"}, writer)

        self.assertIn(writer, self.server._sessions)
        session = self.server._sessions[writer]
        self.assertEqual(session.username, "alice")

    async def test_process_message_answer_records_and_scores(self):
        writer = _DummyWriter()
        await self.server._process_message({"message_type": "HI", "username": "alice"}, writer)
        session = self.server._sessions[writer]
        self.server._active_sessions.clear()
        self.server._active_sessions.add(session)
        self.server._state = GameState.QUESTION

        question_round = QuestionRound(
            round_no=1,
            qtype="Mathematics",
            short_question="1 + 1",
            trivia_question="Question",
            correct_answer="2",
            started_at=0.0,
            finished_at=1.0,
            num_of_users=1,
            answers_by_session={session: None},
        )
        question_round.is_finished = MagicMock(return_value=True)
        self.server._question_round = question_round
        self.server._answer_cond = asyncio.Condition()

        with patch("server.send_message", new=AsyncMock()) as send_mock:
            await self.server._process_message({"message_type": "ANSWER", "answer": "2"}, writer)

        self.assertEqual(session.point, 1)
        self.assertEqual(question_round.answers_by_session[session], "2")
        self.assertTrue(question_round.is_finished.called)
        send_mock.assert_awaited_once()


class _DummyWriter:
    def __init__(self):
        self.close_called = False
        self.wait_closed_called = False

    def close(self):
        self.close_called = True

    async def wait_closed(self):
        self.wait_closed_called = True

    def get_extra_info(self, name):
        return ("127.0.0.1", 0)

    def is_closing(self):
        return self.close_called

    def __hash__(self):
        return id(self)

