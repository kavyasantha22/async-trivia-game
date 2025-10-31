import unittest

from server import (
    ClientSession,
    GameState,
    QuestionRound,
    Server,
    ServerMessageConfig,
)


def _make_server(question_types=None) -> Server:
    if question_types is None:
        question_types = [
            "Mathematics",
            "Roman Numerals",
        ]
    question_formats = {
        "Mathematics": "Solve {}",
        "Roman Numerals": "Convert {}",
    }
    config = ServerMessageConfig(
        port=12000,
        players=2,
        question_types=question_types,
        question_formats=question_formats,
        question_seconds=30,
        question_interval_seconds=5,
        ready_info="Game starting for {players} players in {question_interval_seconds} seconds.",
        question_word="Question",
        correct_answer="Correct! {answer} == {correct_answer}",
        incorrect_answer="Incorrect. {answer} != {correct_answer}",
        points_noun_singular="point",
        points_noun_plural="points",
        final_standings_heading="Final Standings",
        one_winner="Winner: {}",
        multiple_winners="Winners: {}",
    )

    original_log = Server._log
    try:
        Server._log = lambda self, *_, **__: None
        server = Server(
            port=config.port,
            players=config.players,
            question_types=question_types,
            question_formats=question_formats,
            question_seconds=config.question_seconds,
            question_interval_seconds=config.question_interval_seconds,
            ready_info=config.ready_info,
            question_word=config.question_word,
            correct_answer=config.correct_answer,
            incorrect_answer=config.incorrect_answer,
            points_noun_singular=config.points_noun_singular,
            points_noun_plural=config.points_noun_plural,
            final_standings_heading=config.final_standings_heading,
            one_winner=config.one_winner,
            multiple_winners=config.multiple_winners,
            config_message=config,
        )
    finally:
        Server._log = original_log
    server._log = lambda *_, **__: None
    return server


class TestServerFunctions(unittest.TestCase):

    def setUp(self) -> None:
        self.server = _make_server()

    def test_construct_ready_message_formats_placeholders(self):
        message = self.server._construct_ready_message()

        self.assertEqual(message["message_type"], "READY")
        self.assertEqual(message["info"], "Game starting for 2 players in 5 seconds.")

    def test_construct_question_message_includes_round_details(self):
        self.server._question_round = QuestionRound(
            round_no=1,
            qtype="Mathematics",
            short_question="1 + 1",
            trivia_question="Question 1",
            correct_answer="2",
            started_at=0.0,
            finished_at=5.0,
            num_of_users=2,
            answers_by_session={},
        )

        message = self.server._construct_question_message()

        self.assertEqual(message["message_type"], "QUESTION")
        self.assertEqual(message["question_type"], "Mathematics")
        self.assertEqual(message["short_question"], "1 + 1")
        self.assertEqual(message["trivia_question"], "Question 1")
        self.assertEqual(message["time_limit"], self.server._question_seconds)

    def test_construct_result_message_correct_answer(self):
        message = self.server._construct_result_message("42", "42")

        self.assertTrue(message["correct"])
        self.assertEqual(
            message["feedback"],
            "Correct! 42 == 42",
        )

    def test_construct_result_message_incorrect_answer(self):
        message = self.server._construct_result_message("24", "42")

        self.assertFalse(message["correct"])
        self.assertEqual(
            message["feedback"],
            "Incorrect. 24 != 42",
        )

    def test_construct_leaderboard_message_sorts_and_ranks(self):
        alice = ClientSession("alice", None)
        alice.point = 2
        bob = ClientSession("bob", None)
        bob.point = 1
        zoe = ClientSession("zoe", None)
        zoe.point = 1

        self.server._sessions = {
            object(): alice,
            object(): bob,
            object(): zoe,
        }

        message = self.server._construct_leaderboard_message()

        self.assertEqual(message["message_type"], "LEADERBOARD")
        lines = message["state"].splitlines()
        self.assertEqual(lines, [
            "1. alice: 2 points",
            "2. bob: 1 point",
            "2. zoe: 1 point",
        ])

    def test_construct_finished_message_multiple_winners(self):
        alice = ClientSession("alice", None)
        alice.point = 3
        bob = ClientSession("bob", None)
        bob.point = 3
        carl = ClientSession("carl", None)
        carl.point = 1

        self.server._sessions = {
            object(): alice,
            object(): bob,
            object(): carl,
        }

        message = self.server._construct_finished_message()

        self.assertEqual(message["message_type"], "FINISHED")
        standings = message["final_standings"].splitlines()
        self.assertEqual(standings[0], "Final Standings")
        self.assertIn("1. alice: 3 points", standings[1])
        self.assertIn("1. bob: 3 points", standings[2])
        self.assertIn("Winners: alice, bob", message["final_standings"])

    def test_construct_finished_message_single_winner(self):
        alice = ClientSession("alice", None)
        alice.point = 4
        bob = ClientSession("bob", None)
        bob.point = 2

        self.server._sessions = {
            object(): alice,
            object(): bob,
        }

        message = self.server._construct_finished_message()

        self.assertIn("Winner: alice", message["final_standings"])

    def test_transition_state_updates_state(self):
        self.assertEqual(self.server._state, GameState.WAITING_FOR_PLAYERS)
        self.server._transition_state(GameState.QUESTION, "testing")
        self.assertEqual(self.server._state, GameState.QUESTION)

