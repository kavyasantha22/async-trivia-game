import sys
from pathlib import Path
import json
from helper import send_message, receive_message
from answer import generate_answer
import asyncio
from typing import Any, Optional
import requests
import re

INPUT_QUEUE: asyncio.Queue[str] = asyncio.Queue()

class Client:

    def __init__(self, username, mode, ollama_config=None) -> None:
        self.username = username
        self.mode = mode
        self._ollama_config : dict[str, Any] | None = None
        if self.mode == 'ai':
            if ollama_config is None:
                sys.stderr.write("client.py: Missing values for Ollama configuration")
                sys.exit(1)
            else:
                self._ollama_config = ollama_config            
        self.reader, self.writer = None, None
        self.connected = False
        self._shutdown_event = asyncio.Event()

        self._answer_task = None
        self._recv_loop_task = None


    def _construct_hi_message(self) -> dict[str, str]:
        return {
            "message_type": "HI",
            "username": self.username
        }
    

    def _construct_bye_message(self) -> dict[str, str]:
        return {
            "message_type": "BYE"
        }


    async def connect(self) -> None:
        while True:
            if self.is_shutting_down():
                return 
            
            inp = await INPUT_QUEUE.get()

            if re.match(r"^CONNECT\s+\S+:\d+$", inp):
                hostname, port = inp.split()[1].split(":")
                try:
                    self.reader, self.writer = await asyncio.open_connection(hostname, int(port))
                except ConnectionRefusedError:
                    print(f"Connection failed")
                    continue 
                except (OSError):
                    continue
                msg = self._construct_hi_message()
                await send_message(self.writer, msg)
                self.connected = True
                return


    async def _disconnect(self) -> bool:
        if self.writer is None:
            return True
        try:
            await send_message(self.writer, self._construct_bye_message())
        except Exception:
            pass  # connection may already be gone
        self.connected = False
        
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass
        # self.reader = None
        # self.writer = None

        return True
        
    
    async def run_loop(self) -> None:
        while not self.is_shutting_down():
            await self.connect()
            await self.play()


    async def play(self) -> None:
        if self.reader is None or self.writer is None or self.is_shutting_down():
            return


        ready_msg = await receive_message(self.reader)
        
        if not ready_msg:
            await self._disconnect()
            return

        
        if ready_msg['message_type'] == "READY":
            print(ready_msg['info'])

        self._recv_loop_task = asyncio.create_task(self._recv_message_loop())
        try:
            await self._recv_loop_task
        except asyncio.CancelledError:
            pass

    
    async def _recv_message_loop(self):
        while self.connected and not self.is_shutting_down():
            if not self.reader:
                await self._disconnect()
                break
            msg = await receive_message(self.reader)

            if not msg:
                await self._disconnect()
                return

            t = msg.get("message_type")
            if t == "READY":
                print(msg["info"])
            elif t == "QUESTION":
                print(msg["trivia_question"])
                self._answer_task = asyncio.create_task(self._answer_question(msg, msg["time_limit"])) 
            elif t == "RESULT":
                print(msg["feedback"])
            elif t == "LEADERBOARD":
                print(msg["state"])
            elif t == "FINISHED":
                print(msg["final_standings"])
                await self._disconnect()
                self.connected = False  
                break
            
 
    async def _answer_question(self, question, qtimeout: float | int) -> None:
        if self.is_shutting_down() or not self.writer: 
            return
        
        answer = {
            "message_type": "ANSWER"
        }
        try:
            if self.mode == 'you':
                ans = await asyncio.wait_for(INPUT_QUEUE.get(), timeout=qtimeout)
                if ans:
                    answer["answer"] = ans
                await send_message(self.writer, answer)
                

            elif self.mode == 'auto':
                qtype = question['question_type'] 
                squest = question['short_question']
                ans = await asyncio.wait_for(
                    asyncio.to_thread(generate_answer, qtype, squest),
                    timeout=qtimeout,
                )
                if ans:
                    answer["answer"] = ans
                await send_message(self.writer, answer)
                

            elif self.mode == 'ai':
                ans = await self._ask_ollama(question=question, timeout=qtimeout)
                if ans:
                    answer["answer"] = ans
                await send_message(self.writer, answer)
                

        except asyncio.TimeoutError:
            return None
              

    async def _ask_ollama(self, question: dict[str, Any], timeout: float) -> str | None:
        def _call():
            return requests.post(url, json=payload)
        
        if self._ollama_config is None:
            return None
        base = self._ollama_config['ollama_host']  
        port = self._ollama_config['ollama_port']
        model = self._ollama_config['ollama_model']

        if not base.startswith(('http://', 'https://')):
            base = f'http://{base}'
            
        url = f'{base}:{port}/api/chat'
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": question["trivia_question"]
                }
            ],
            "stream": False
        }
        try:
            # Outer timeout guards total time; inner tuple guards per I/O op
            resp = await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout)
            return resp.json()["message"]["content"]
        except asyncio.TimeoutError:
            return None


    async def request_shutdown(self) -> None:
        if self._shutdown_event.is_set():
            return
        
        self._shutdown_event.set()
        await self._disconnect()
                
        # print("disconnected.")
        await cancel_task(self._answer_task)
        await cancel_task(self._recv_loop_task)
        
        # print("tasks canceled.")
        self._answer_task = None 
        self._recv_loop_task = None


    def is_shutting_down(self):
        return self._shutdown_event.is_set()
    

    async def input_reader(self):
        while True:
            line = (await asyncio.to_thread(input))
            if line == "EXIT":
                await self.request_shutdown()
                return 
            elif line == "DISCONNECT":
                await self._disconnect()
            else:
                await INPUT_QUEUE.put(line)


async def cancel_task(task: Optional[asyncio.Task]) -> None:
    if not task:
        return

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        pass
        # print(e)


def parse_config_path() -> Path:        
    if len(sys.argv) != 3 or sys.argv[1] != "--config":
        sys.stderr.write("client.py: Configuration not provided\n")
        sys.exit(1)

    config_path = Path(sys.argv[2])
    if not config_path.exists():
        sys.stderr.write(f"client.py: File {config_path} does not exist")
        sys.exit(1)
    return config_path


async def main():
    config_path = parse_config_path()
    file = config_path.open("r", encoding='utf-8')
    config = json.load(file)
    file.close()

    username = config.get('username')
    mode = config.get('client_mode')
    ollama_config = config.get('ollama_config')
        
    client = Client(username, mode, ollama_config)

    input_reader_task = asyncio.create_task(client.input_reader())
    client_loop_task = asyncio.create_task(client.run_loop())

    await asyncio.wait(
        [input_reader_task, client_loop_task],
        return_when=asyncio.FIRST_COMPLETED
    )


if __name__ == "__main__":
    asyncio.run(main())

        
        