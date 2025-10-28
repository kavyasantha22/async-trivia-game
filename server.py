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
from dataclasses import dataclass, field
from answer import generate_answer
import sys
import json
from pathlib import Path
# import logging
# import traceback
import time

# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s %(levelname)s %(name)s: %(message)s",
# )



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
                 question_formats: dict, question_seconds: int, 
                 question_interval_seconds: float, ready_info: str, 
                 question_word: str, correct_answer: str,
                 incorrect_answer: str, points_noun_singular: str,
                 points_noun_plural: str, final_standings_heading: str,
                 one_winner: str, multiple_winners: str):
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

        # self._reader, self._writer = await self.connect(port)
        self._asyncio_server : asyncio.Server | None = None
        self._orchestrator_task : asyncio.Task | None = None
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
        # config_snapshot = {
        #     "host": self._host,
        #     "port": self._port,
        #     "players": self._num_players,
        #     "question_types": self._question_types,
        #     "question_formats": self._question_formats,
        #     "question_seconds": self._question_seconds,
        #     "question_interval_seconds": self._question_interval,
        #     "ready_info": self._ready_info,
        #     "question_word": self._question_word,
        #     "correct_answer_message": self._correct_answer_message,
        #     "incorrect_answer_message": self._incorrect_answer_message,
        #     "points_noun_singular": self._points_noun_singular,
        #     "points_noun_plural": self._points_noun_plural,
        #     "final_standings_heading": self._final_standings_heading,
        #     "one_winner_message": self._one_winner_message,
        #     "multiple_winner_message": self._multiple_winner_message,
        # }
        # self._log("Configuration:\n" + json.dumps(config_snapshot, indent=2))

        try:
            self._asyncio_server = await asyncio.start_server(self._handle_client, host=self._host, port=self._port)
        except Exception as e:
            sys.stderr.write(f"server.py: Binding to port {self._port} was unsuccessful\n")
            sys.exit(1)

        # addrs = ", ".join(str(s.getsockname()) for s in self._asyncio_server.sockets or [])
        # print(addrs)
        socknames = ", ".join(str(s.getsockname()) for s in (self._asyncio_server.sockets or []))
        self._log(f"Listening on {socknames}")

        self._orchestrator_task = asyncio.create_task(self._orchestrator())
        self._orchestrator_task.add_done_callback(
            lambda t: t.exception()
        )

        try:
            async with self._asyncio_server:
                await self._asyncio_server.serve_forever()
        except Exception as e:
            print(e)
        finally:
            return


    # double check
    async def _orchestrator(self): 
        question_round_start: float | None = None

        while True:
            cur_time = asyncio.get_running_loop().time()
            # print(question_round_start, cur_time)

            if self._state is GameState.WAITING_FOR_PLAYERS:
                if len(self._sessions) >= self._num_players and question_round_start is not None and cur_time >= question_round_start:
                    self._round_no = 1
                    self._question_round = self._generate_question_round()
                    question_round_start = None
                    self._transition_state(GameState.QUESTION, "Starting first question round")
                    question_msg = self._construct_question_message()
                    await self._broadcast(question_msg)

                # ready messagen not sent
                elif len(self._sessions) >= self._num_players and question_round_start is None:
                    self._log("Everyone has joined!")
                    ready_msg = self._construct_ready_message()
                    self._log("Everyone has joined!")
                    question_round_start = cur_time + self._question_interval
                    # print("it goes to the right branch")
                    await self._broadcast(ready_msg)

            elif self._state is GameState.QUESTION:
                if cur_time is None:
                    print("Error time fetching from asyncio running loop")
                    continue

                if self._question_round.is_finished(self._active_sessions, cur_time):
                    if self._round_no >= len(self._question_types):
                        self._transition_state(GameState.FINISHED, "All question types completed")
                    else:
                        self._transition_state(GameState.BETWEEN_ROUNDS, "Round finished; sending leaderboard and waiting before next question")
                        question_round_start = cur_time + self._question_interval 
                        leaderboard_msg = self._construct_leaderboard_message()
                        await self._broadcast(leaderboard_msg)

            elif self._state is GameState.BETWEEN_ROUNDS:
                # Where to handle finished? shud we wait for the last interval before finishing or shud we go straight to finished after all qtypes are done?
                if question_round_start is not None and cur_time >= question_round_start:
                    question_round_start = None
                    self._round_no += 1

                    self._question_round = self._generate_question_round()
                    self._transition_state(GameState.QUESTION, f"Starting round {self._round_no}")
                    question_msg = self._construct_question_message()
                    await self._broadcast(question_msg)

            elif self._state is GameState.FINISHED:
                finished_msg = self._construct_finished_message()
                await self._broadcast(finished_msg)
                await self._shutdown_everything()
                return

            else:
                pass

            await asyncio.sleep(0.05)


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

        if self._asyncio_server is not None:
            self._asyncio_server.close()
            try:
                await self._asyncio_server.wait_closed()
            except Exception:
                pass

        if self._orchestrator_task is not None and not self._orchestrator_task.done():
            self._orchestrator_task.cancel()
            try:
                await self._orchestrator_task
            except asyncio.CancelledError:
                pass
            finally:
                self._orchestrator_task = None
        return 

            

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
                self._log(f"is disconnected? {reader.at_eof()}")
                self._log(f"{self._find_session_by_writer(writer).username} is none!")                            
                break
            try:
                await self._process_message(data, writer)
            except Exception as e:
                self._log(f"Process message error from {peer}: {e}")
                break
        # try:
        #     while True:
        #         if reader is None or writer is None:
        #             # print("reader or writer is None!")
        #             break
        #         try:
        #             data = await receive_message(reader)  
        #             print(data) 
        #         except Exception as e:
        #             self._log(f"Receive error from {peer}: {e}")
        #             break                                   
        #         if data is None:
        #             print("Data is none!")                            
        #             break
        #         try:
        #             await self._process_message(data, writer)
        #         except Exception as e:
        #             self._log(f"Process message error from {peer}: {e}")
        #             break

        #         # If the session has been removed (e.g., BYE processed), stop reading
        #         if self._find_session_by_writer(writer) is None:
        #             break

        # finally:
        #     # print("Dropping because there is an exception or data is empty")
        #     # Avoid double-dropping if session already removed
        #     if self._find_session_by_writer(writer) is not None:
        #         await self._drop_session(writer)
            # print(f"[-] disconnected {peer}")
    

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
            # print(f"{username} joined.")

            if len(self._sessions.keys()) >= self._num_players:
                print("Max players reached.")
                return
            
            if username in self._sessions.keys():
                print("username taken.")
                return

            new_session = ClientSession(username, writer)
            self._sessions[username] = new_session
            self._active_sessions.add(new_session)
            self._log(f"Session added: {username}. Active sessions: {len(self._active_sessions)}/{self._num_players}")
            # ready_msg = self._construct_ready_message()
            # await send_message(writer, ready_msg) 

        elif mtype == "BYE":
            print("Dropping because of BYE message")
            await self._drop_session(writer)

        elif mtype == "ANSWER":
            # Detailed answer logging
            answer = received.get("answer","")
            if answer == "":
                return
            correct_answer = self._get_correct_answer()

            if self._state is GameState.QUESTION and self._question_round is not None:
                sess = self._find_session_by_writer(writer)
                if sess is not None:
                    self._question_round.answers_by_session[sess] = answer
                    if correct_answer is not None and correct_answer == answer:
                        sess.point += 1


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

        # print("Nearly finished generating question round...")
        try:
            self._log(
                f"Round generated: round={self._round_no} type={qtype} users={len(self._active_sessions)} time_limit={self._question_seconds} correct='{correct_answer}'"
            )
        except Exception:
            pass

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
        return {
            "message_type" : "READY",
            "info" : self._ready_info.format(
                question_interval_seconds=str(self._question_interval),
                players=self._num_players
            )
        }


    def _construct_result_message(self, answer, correct_answer) -> dict[str, Any]:
        msg: dict[str, Any] = {
            "message_type": "RESULT"
        }
        if correct_answer is not None and correct_answer == answer:
            msg["correct"] = True
            msg["feedback"] = self._correct_answer_message.replace("{answer}", answer)
        else:
            msg["correct"] = False
            msg["feedback"] = self._incorrect_answer_message.format(
                correct_answer=correct_answer,
                answer=answer
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
            print("question round is None when sending question")
            return {}
        
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


def load_config(path: Path) -> Server:
    with Path.open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return Server(**cfg)


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
    # asyncio.get_running_loop().set_debug(True)

    await server.start()
    

if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.run(main(),debug=True)
    
        
