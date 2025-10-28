import asyncio
from helper import send_message, receive_message
from questions import (
    generate_mathematics_question, 
    generate_network_broadcast_question, 
    generate_roman_numerals_question,
    generate_usable_addresses_question,
) 
from enum import Enum, auto
from typing import Any
from dataclasses import dataclass, field, fields, asdict
from answer import generate_answer
import sys
import json
from pathlib import Path
import time

@dataclass
class ServerMessageConfig:
    port: int
    players: int
    question_types: list[str]
    question_formats: dict[str, str]
    question_seconds: int
    question_interval_seconds: float
    ready_info: str
    question_word: str
    correct_answer: str
    incorrect_answer: str
    points_noun_singular: str
    points_noun_plural: str
    final_standings_heading: str
    one_winner: str
    multiple_winners: str
    

class ClientSession:
    def __init__(self, username: str, writer: asyncio.StreamWriter | None):
        self.username = username
        self.point = 0 
        self.writer = writer 
        self.is_active = True


class GameState(Enum):
    WAITING_FOR_PLAYERS = auto()
    QUESTION = auto()
    BETWEEN_ROUNDS = auto()
    FINISHED = auto()


@dataclass
class QuestionRound:
    round_no: int
    qtype: str
    short_question: str
    trivia_question: str
    correct_answer: str               
    started_at: float                 
    finished_at: float     
    num_of_users: int
    is_open: bool = True
    answers_by_session: dict[ClientSession, str | None] = field(default_factory=dict)  

    def has_everyone_answered(self, active_sessions: set[ClientSession]) -> bool:
        for sess in active_sessions:
            if self.answers_by_session.get(sess) is None:
                return False
        return True
    
    def is_finished(self, active_essions: set[ClientSession], now: float):
        if self.has_everyone_answered(active_essions) or now >= self.finished_at:
            self.is_open = False
            return True
        return False
    

class Server:
    def __init__(self, port: int, players: int, question_types: list[str],
                 question_formats: dict, question_seconds: int | float, 
                 question_interval_seconds: int | float, ready_info: str, 
                 question_word: str, correct_answer: str,
                 incorrect_answer: str, points_noun_singular: str,
                 points_noun_plural: str, final_standings_heading: str,
                 one_winner: str, multiple_winners: str, config_message: ServerMessageConfig):
        self._host = "0.0.0.0"
        self._port = port
        self._num_players = players
        self._question_types = question_types
        self._question_formats = question_formats
        self._question_seconds = question_seconds
        self._question_interval = question_interval_seconds
        self._ready_info = ready_info
        self._question_word = question_word
        self._correct_answer_message = correct_answer
        self._incorrect_answer_message = incorrect_answer
        self._points_noun_singular = points_noun_singular
        self._points_noun_plural = points_noun_plural
        self._final_standings_heading = final_standings_heading
        self._one_winner_message = one_winner
        self._multiple_winner_message = multiple_winners
        
        self.config_message: ServerMessageConfig = config_message
        self._join_cond: asyncio.Condition = asyncio.Condition()
        self._answer_cond: asyncio.Condition | None = None
        self._round_no = 0
        self._question_round: QuestionRound | None = None
        self._sessions : dict[str, ClientSession] = dict()
        self._active_sessions : set[ClientSession] = set()

        self._TRIVIA_QUESTION_FORMAT = "{question_word} {question_number} ({question_type}):\n{question}"

        self._state : GameState = GameState.WAITING_FOR_PLAYERS
        self._log(f"Initialised server on {self._host}:{self._port}; awaiting {self._num_players} players; state={self._state.name}")


    def _log(self, message: str) -> None:
        ts = time.strftime("%H:%M:%S")
        print(f"[SRV {ts}] {message}")


    def _summarize_message(self, message: dict[str, Any]) -> str:
        try:
            mtype = message.get("message_type")
            if mtype == "QUESTION":
                return f"QUESTION round={self._round_no} type={message.get('question_type')} timeout={message.get('time_limit')}"
            if mtype == "READY":
                return f"READY interval={self._question_interval}"
            if mtype == "LEADERBOARD":
                state = message.get("state", "")
                return f"LEADERBOARD lines={len(state.splitlines())}"
            if mtype == "FINISHED":
                return "FINISHED final_standings"
            if mtype == "RESULT":
                return f"RESULT correct={message.get('correct')}"
            return f"{mtype} keys={list(message.keys())}"
        except Exception:
            return "<unprintable message>"

    def _transition_state(self, new_state: GameState, reason: str) -> None:
        old_state = self._state
        if old_state is new_state:
            self._log(f"State unchanged: {old_state.name} ({reason})")
            return
        self._state = new_state
        print()
        self._log(f"State {old_state.name} -> {new_state.name} ({reason})")


    async def start(self) -> None:
        try:
            server = await asyncio.start_server(self._handle_client, host=self._host, port=self._port)
        except Exception as e:
            sys.stderr.write(f"server.py: Binding to port {self._port} was unsuccessful\n")
            sys.exit(1)

        socknames = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
        self._log(f"Listening on {socknames}")

        async with server:
            await self._orchestrator()


    async def _orchestrator(self): 
        while True:
            if self._state is GameState.WAITING_FOR_PLAYERS:
                async with self._join_cond:
                    await self._join_cond.wait_for(lambda: len(self._sessions) >= self._num_players)

                self._log("Everyone has joined!")
                ready_msg = self._construct_ready_message()
                self._log("Sending ready message...")
                # question_round_start = cur_time + self._question_interval
                await self._broadcast(ready_msg)
                print("Finished sending ready message!")
                await asyncio.sleep(self._question_interval)
                self._transition_state(GameState.QUESTION, "Starting first question round")

            elif self._state is GameState.QUESTION:
                self._answer_cond = asyncio.Condition()
                self._round_no += 1
                self._question_round = self._generate_question_round()
                question_msg = self._construct_question_message()
                await self._broadcast(question_msg)

                try:
                    # Deadline-based cancel that doesn't require making a separate task
                    async with asyncio.timeout(self._question_round.finished_at - asyncio.get_running_loop().time()):
                        async with self._answer_cond:
                            await self._answer_cond.wait_for(
                                lambda: self._question_round.has_everyone_answered(self._active_sessions)
                            )

                except asyncio.TimeoutError:  
                    pass
                
                if self._round_no >= len(self._question_types):
                    self._transition_state(GameState.FINISHED, "All question types completed")
                    continue

                leaderboard_msg = self._construct_leaderboard_message()
                await self._broadcast(leaderboard_msg)

                self._transition_state(GameState.BETWEEN_ROUNDS, "Round finished; sending leaderboard and waiting before next question")
                self._answer_cond = None
                await asyncio.sleep(self._question_interval)

                self._transition_state(GameState.QUESTION, f"Starting round {self._round_no}")

            elif self._state is GameState.FINISHED:
                finished_msg = self._construct_finished_message()
                await self._broadcast(finished_msg)
                await self._shutdown_everything()
                return
            
            else:
                pass


    async def _shutdown_everything(self):
        self._log("Shutting down server and closing client sessions")
        for sess in self._sessions.values():
            if sess.writer is None:
                print(f"{sess.username} has no writer")
                continue
            try:
                await self._drop_session(sess.writer)
            except Exception:
                pass
            

    def _get_correct_answer(self) -> str | None:
        if self._question_round is None:
            return None 
        return self._question_round.correct_answer


    async def _broadcast(self, message: dict[str, Any]) -> None:
        # print("broadcasting...")
        tasks = []

        recipients: list[str] = []
        for sess in list(self._active_sessions):
            if sess.writer is None:
                print(f"{sess.username} has no writer")
                continue
            recipients.append(sess.username)
            tasks.append(asyncio.create_task(send_message(sess.writer, message)))

        self._log(f"Broadcast -> {recipients} | {self._summarize_message(message)}")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Surface any exceptions for visibility
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                self._log(f"Broadcast send error to {recipients[idx]}: {res}")

        # print("Finished broadcasting.")


    async def _handle_client(self, reader, writer) -> None:
        peer = writer.get_extra_info("peername")
        self._log(f"[+] connected {peer}")
        while True:
            if reader is None or writer is None:
                # print("reader or writer is None!")
                break
            try:
                data = await receive_message(reader)  
                # print(data) 
            except Exception as e:
                self._log(f"Receive error from {peer}: {e}")
                break                                   
            if data is None:
                print("Data is none!")                            
                break

            try:
                await self._process_message(data, writer)
            except Exception as e:
                self._log(f"Process message error from {peer}: {e}")
                break
    

    async def _drop_session(self, writer : asyncio.StreamWriter) -> None:
        discarded_ses = self._find_session_by_writer(writer)

        if discarded_ses is None:
            print(f"Session with writer {writer} is not found.")
            return
        
        self._active_sessions.discard(discarded_ses)
        print(f"dropping {discarded_ses.username}...")
        self._log(f"Active sessions: {len(self._active_sessions)}/{self._num_players}")
        discarded_ses.is_active = False
        discarded_ses.writer = None
        try: 
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        return
    
    
    async def _process_message(self, received: dict, writer) -> None:
        try:
            mtype = received["message_type"]
        except Exception:
            print("There is no message_type")
            print(received)
            return

        sess = self._find_session_by_writer(writer)
        uname = sess.username if sess is not None else "<unknown>"
        self._log(f"Recv <- {uname} | {mtype} {received}")

        if mtype == "HI":
            username = received["username"]

            async with self._join_cond:
                if len(self._sessions.keys()) >= self._num_players:
                    print("Max players reached.")
                    return
                new_session = ClientSession(username, writer)
                self._sessions[username] = new_session
                self._active_sessions.add(new_session)
                if len(self._sessions) >= self._num_players:
                    self._join_cond.notify_all()

            self._log(f"Session added: {username}. Active sessions: {len(self._active_sessions)}/{self._num_players}")

        elif mtype == "BYE":
            await self._drop_session(writer)
            if self._answer_cond:
                async with self._answer_cond:
                    if self._question_round and self._question_round.is_finished(self._active_sessions, asyncio.get_running_loop().time()):
                        self._answer_cond.notify_all()

        elif mtype == "ANSWER":
            # Detailed answer logging
            answer = received.get("answer","")
            if answer == "":
                return
            correct_answer = self._get_correct_answer()

            if self._state is GameState.QUESTION and self._question_round is not None:
                sess = self._find_session_by_writer(writer)
                if sess is not None and self._answer_cond:
                    self._question_round.answers_by_session[sess] = answer
                    if correct_answer is not None and correct_answer == answer:
                        sess.point += 1

                    async with self._answer_cond:
                        if self._question_round.is_finished(self._active_sessions, asyncio.get_running_loop().time()):
                            self._answer_cond.notify_all()


            result_msg = self._construct_result_message(answer, correct_answer)
            to_uname = sess.username if sess is not None else "<unknown>"
            self._log(f"Send -> {to_uname} | {self._summarize_message(result_msg)} answer='{answer}' correct_answer='{correct_answer}'")
            await send_message(writer, result_msg)

    
    def _find_session_by_writer(self, writer : asyncio.StreamWriter) -> ClientSession | None:
        for ses in self._active_sessions:
            if ses.writer == writer:
                return ses
        return None
    

    def _generate_question_round(self) -> QuestionRound:
        loop = asyncio.get_running_loop()
        qtype = self._question_types[self._round_no - 1]
        short_question = self._generate_short_question(qtype)
        trivia_question = self._TRIVIA_QUESTION_FORMAT.format(
            question_word=self._question_word,
            question_number=self._round_no,
            question_type=qtype,
            question=self._question_formats[qtype].replace("{}", short_question)
        )
        started_at = loop.time()
        finished_at = started_at + self._question_seconds
        correct_answer = generate_answer(qtype, short_question)


        self._log(
            f"Round generated: round={self._round_no} type={qtype} users={len(self._active_sessions)} time_limit={self._question_seconds} correct='{correct_answer}'"
        )

        return QuestionRound(
            round_no=self._round_no,
            qtype=qtype,
            short_question=short_question,
            trivia_question=trivia_question,
            started_at=started_at,
            finished_at=finished_at,
            num_of_users=len(self._active_sessions),
            correct_answer=correct_answer,
            answers_by_session={sess: None for sess in self._active_sessions},
        )


    def _construct_ready_message(self) -> dict[str, Any]:
        self._log("Constructing ready message!")
        msg = {
            "message_type" : "READY"
        }
        self._log("Ready message is halfway done!")
        # msg["info"] = ""
        print(self._ready_info)
        print(asdict(self.config_message))
        # msg["info"] = self._ready_info.format(
        #     asdict(self.config_message)
        # )
        self._log("Ready message is being returned now!")
        return msg


    def _construct_result_message(self, answer, correct_answer) -> dict[str, Any]:
        msg: dict[str, Any] = {
            "message_type": "RESULT"
        }
        if correct_answer is not None and correct_answer == answer:
            msg["correct"] = True
            msg["feedback"] = self._correct_answer_message.format(
                asdict(self.config_message)
            )
        else:
            msg["correct"] = False
            msg["feedback"] = self._incorrect_answer_message.format(
                asdict(self.config_message)
            )

        return msg
    
    
    def _construct_leaderboard_message(self) -> dict[str, Any]:
        msg = {
            "message_type" : "LEADERBOARD"
        }

        ranking = sorted(self._sessions.values(),
                        key=lambda session: (-1*session.point, session.username))
        
        str_ranking = ""
        prev_point = -1
        rank = 0
        for i in range(len(ranking)):
            sess = ranking[i]

            if sess.point != prev_point:
                rank = i + 1
                prev_point = sess.point

            str_ranking += f"{rank}. {sess.username}: {sess.point}"
            if sess.point == 1:
                str_ranking += f" {self._points_noun_singular}\n"
            else:
                str_ranking += f" {self._points_noun_plural}\n"
        
        # No space on the last line
        msg["state"] = str_ranking[:-1]
        return msg
    
    
    def _construct_finished_message(self) -> dict[str, Any]:
        msg = {
            "message_type" : "FINISHED"
        }

        ranking = sorted(self._sessions.values(),
                key=lambda session: (-1*session.point, session.username))
        
        str_ranking = f"{self._final_standings_heading}\n"

        str_ranking += self._construct_leaderboard_message()["state"] + '\n'

        if len(ranking) > 1 and ranking[0].point == ranking[1].point:
            winner_point = ranking[0].point 
            temp = ""
            for sess in ranking:
                if winner_point == sess.point:
                    temp += sess.username + ", "
            temp = temp[:-2]
            str_ranking += self._multiple_winner_message.replace("{}", temp)
        else:
            str_ranking += self._one_winner_message.replace("{}", ranking[0].username)

        msg["final_standings"] = str_ranking 
        return msg
    

    def _construct_question_message(self) -> dict[str, Any]:
        if self._question_round is None:
            self._log("Question round is none!")
        
        return {
            "message_type" : "QUESTION",
            "question_type" : self._question_round.qtype,
            "short_question" :  self._question_round.short_question,
            "trivia_question" :  self._question_round.trivia_question,
            "time_limit" : self._question_seconds
        }


    def _generate_short_question(self, question_type) -> str:
        if question_type == "Usable IP Addresses of a Subnet":
            return generate_usable_addresses_question()
        elif question_type == "Network and Broadcast Address of a Subnet":
            return generate_network_broadcast_question()
        elif question_type == "Roman Numerals":
            return generate_roman_numerals_question()
        elif question_type == "Mathematics":
            return generate_mathematics_question()
        else:
            print("Unrecognised question type.")
            print(question_type)
            return ""

def from_dict(data: dict[str, Any]) -> ServerMessageConfig:
    allowed = {f.name for f in fields(ServerMessageConfig)}
    clean = {k: v for k, v in data.items() if k in allowed}
    # print(clean)
    return ServerMessageConfig(**clean)


def load_config(path: Path) -> Server:
    with Path.open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return Server(**cfg, config_message=from_dict(cfg))


def parse_config_path() -> Path:
    def _missing_config() -> None:
        sys.stderr.write("server.py: Configuration not provided\n")
        sys.exit(1)

    if len(sys.argv) != 3 or sys.argv[1] != "--config":
        _missing_config()

    config_path = Path(sys.argv[2])
    if not config_path.exists():
        sys.stderr.write(f"server.py: File {config_path} does not exist\n")
        sys.exit(1)
    return config_path


async def main():
    config_path = parse_config_path()
    server = load_config(config_path)

    await server.start()
    

if __name__ == "__main__":
    asyncio.run(main())
    
        