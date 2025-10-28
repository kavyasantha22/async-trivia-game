import sys
from pathlib import Path
import json
from helper import send_message, receive_message
from answer import generate_answer
import asyncio
from typing import Any, Optional
import requests


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
        self.has_answered: bool | None = None
        self._shutdown_event = asyncio.Event()

        self._answer_task = None
        self._recv_loop_task = None
        self._input_task = None


    def _construct_hi_message(self) -> dict:
        return {
            "message_type": "HI",
            "username": self.username
        }
    

    def _construct_bye_message(self) -> dict:
        return {
            "message_type": "BYE"
        }


    async def _connect(self, hostname: str, port: str) -> None:
        print("Trying to connect...")
        self.reader, self.writer = await asyncio.open_connection(hostname, int(port))
        # peer = self.writer.get_extra_info("peername")
        # print(f"Connected to {peer}")
        msg = self._construct_hi_message()
        await send_message(self.writer, msg)
        self.connected = True


    async def _disconnect(self) -> bool:
        print("Trying to disconnect...")
        if self.writer is None:
            return True
        try:
            await send_message(self.writer, self._construct_bye_message())
        except Exception:
            pass  # connection may already be gone

        self.connected = False
        self.reader, self.writer = None, None
        return True
        

    async def play(self) -> None:
        if self.reader is None or self.writer is None:
            print("You are not connected yet. Cannot play.")
            return
        print(f"{self.username} is waiting for ready message...")
        ready_msg = await receive_message(self.reader)

        if ready_msg is None:
            print(f"{self.username} ready message is not received. Trying to disconenct...")
            await self._disconnect()
            return
        
        if ready_msg['message_type'] == "READY":
            print(ready_msg['info'])
        else:
            print("Other type of message is received???")

        self._recv_loop_task = asyncio.create_task(self._recv_message_loop())
        try:
            await self._recv_loop_task
        except asyncio.CancelledError:
            pass

    
    async def _recv_message_loop(self):
        while self.connected and not self.is_shutting_down():
            msg = await receive_message(self.reader)
            if not msg:
                break
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
                self.connected = False  
                break
            else:
                print("Not recognised message type")
            
 
    async def _answer_question(self, question, qtimeout: float | int) -> None:
        if self.is_shutting_down() or not self.writer: 
            return
        
        if not self.writer:
            return 
        
        answer = {
            "message_type": "ANSWER"
        }
        try:
            if self.mode == 'you':
                ans = await asyncio.wait_for(_STDIN_Q.get(), timeout=qtimeout)
                if ans:
                    answer["answer"] = ans

            elif self.mode == 'auto':
                qtype = question['question_type'] 
                squest = question['short_question']
                ans = await asyncio.wait_for(
                    asyncio.to_thread(generate_answer, qtype, squest),
                    timeout=qtimeout,
                )

                answer["answer"] = ans

            elif self.mode == 'ai':
                ans = await self._ask_ollama(question=question, timeout=qtimeout)
                if ans is not None:
                    answer["answer"] = ans
                else:
                    answer["answer"] = ""


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


    async def prompt_connect(self) -> None:
        while True:
            if self.is_shutting_down():     
                return
            
            inp = await _STDIN_Q.get()

            if inp is None:
                if self.is_shutting_down(): 
                    return
                continue

            inp = inp.split()
            if inp[0] != "CONNECT":
                print("Unrecognised command.")
                continue
            try:
                hostname, port = inp[1].split(":")
                await self._connect(hostname, port)
                break
            except Exception as e:
                print(f"Connection failed")
                continue


    async def request_shutdown(self) -> None:
        if self._shutdown_event.is_set():
            return
        self._shutdown_event.set()
        await self._disconnect()
        # close writer ASAP to unblock reader
        await self._cancel_answer_task()
        if self._recv_loop_task and not self._recv_loop_task.done():
            self._recv_loop_task.cancel()


    async def _cancel_answer_task(self):
        t = self._answer_task
        if not t: 
            return
        
        if not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

        self._answer_task = None


    def is_shutting_down(self):
        return self._shutdown_event.is_set()


_STDIN_Q: asyncio.Queue[str] = asyncio.Queue()


async def install_stdin_reader(client: Client) -> None:
    while True:
        line = (await asyncio.to_thread(sys.stdin.readline)).strip()
        if line == "EXIT":
            await client.request_shutdown()
            break
        elif line == "DISCONNECT":
            await client._disconnect()
        else:
            await _STDIN_Q.put(line)
    

def parse_config_path() -> Path:
    def _missing_config() -> None:
        sys.stderr.write("client.py: Configuration not provided\n")
        sys.exit(1)

    if len(sys.argv) != 3 or sys.argv[1] != "--config":
        _missing_config()

    config_path = Path(sys.argv[2])
    if not config_path.exists():
        sys.stderr.write(f"client.py: File {config_path} does not exist")
        sys.exit(1)
    return config_path


async def bfunc(client: Client):
    while not client.is_shutting_down():
        await client.prompt_connect()
        await client.play()


async def main():
    config_path = parse_config_path()
    file = config_path.open("r", encoding='utf-8')
    config = json.load(file)
    file.close()

    username = config.get('username')
    mode = config.get('client_mode')
    ollama_config = config.get('ollama_config')
        
    client = Client(username, mode, ollama_config)

    a = asyncio.create_task(install_stdin_reader(client))

    b = asyncio.create_task(bfunc(client))

    await asyncio.wait([a,b],return_when=asyncio.FIRST_COMPLETED)
    
    sys.exit(0)



if __name__ == "__main__":
    asyncio.run(main())

        
        