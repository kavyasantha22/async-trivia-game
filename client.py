import sys
from pathlib import Path
import json
from helper import send_message, receive_message
from answer import generate_answer
import asyncio
from typing import Any
import requests
from timeouts import time_limit


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
        self.reader, self.writer = await asyncio.open_connection(hostname, int(port))
        # peer = self.writer.get_extra_info("peername")
        # print(f"Connected to {peer}")
        msg = self._construct_hi_message()
        await send_message(self.writer, msg)
        self.connected = True


    async def _disconnect(self) -> bool:
        if self.writer is None:
            # print("Already disconnected.")
            return True
        try:
            await send_message(self.writer, self._construct_bye_message())
        except Exception:
            pass  # connection may already be gone
        try:
            self.writer.close()
            await self.writer.wait_closed()
        finally:
            self.connected = False
            self.reader, self.writer = None, None
            return True
        

    async def play(self) -> None:
        if self.reader is None or self.writer is None:
            print("You are not connected yet. Cannot play.")
            return
        
        ready_msg = await receive_message(self.reader)
        if ready_msg['message_type'] == "READY":
            print(ready_msg['info'])
        else:
            print("Other type of message is received???")

        while self.connected:
            # print(2)
            recv_msg = await receive_message(self.reader)
            if recv_msg['message_type'] == "QUESTION":
                print(recv_msg["trivia_question"])

                qtimeout = recv_msg["time_limit"]
                answer = await self.construct_answer_message(recv_msg, qtimeout)
                if answer is not None:
                    await send_message(self.writer, answer)

            elif recv_msg['message_type'] == "RESULT":
                print(recv_msg['feedback'])

            elif recv_msg['message_type'] == "LEADERBOARD":
                print(recv_msg["state"])

            elif recv_msg['message_type'] == "FINISHED":
                print(recv_msg["final_standings"])
                # await self._disconnect()
                self.connected = False

            elif recv_msg['message_type'] == "READY":
                print(recv_msg["info"])

            else:
                print("Not recognised message type")
                
        return

            
 
    async def construct_answer_message(self, question, qtimeout: float | int) -> dict | None:
        answer = {
            "message_type": "ANSWER"
        }
        try:
            if self.mode == 'you':
                ans = await asyncio.wait_for(self.handle_input("Your answer: "), timeout=qtimeout)
                answer["answer"] = ans

            elif self.mode == 'auto':
                qtype = question['question_type'] # Not sure whether this is the right format
                squest = question['short_question']
                ans = await asyncio.wait_for(
                    asyncio.to_thread(generate_answer, qtype, squest),
                    timeout=qtimeout,
                )
                answer["answer"] = ans

            elif self.mode == 'ai':
                ans = await self._ask_ollama(question, qtimeout)
                if ans is not None:
                    answer["answer"] = ans
                else:
                    answer["answer"] = ""

            return answer
        except asyncio.TimeoutError:
            return None
    

    async def handle_input(self, message=None) -> str:
        inp = await get_input(message=message, client=self)
        if inp == "DISCONNECT":
            await self._disconnect()
            return ""
        else:
            return inp
        

    async def _ask_ollama(self, question: dict[str, Any], timeout: float) -> str | None:
        if self._ollama_config is None:
            return None
        host = self._ollama_config['ollama_host']
        port = self._ollama_config['ollama_port']
        model = self._ollama_config['ollama_model']

        url = f"{host}:{port}/api/chat"
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
            with time_limit(timeout):
                ollama_request = requests.post(url, data=json.dumps(payload), timeout=timeout)
                data = ollama_request.json()
                return data["message"]["content"]
            
        except (TimeoutError, requests.Timeout):
            return None
        

    async def prompt_connect(self) -> None:
        while True:
            inp = (await get_input("Please connect to the desired server.\nformat: 'CONNECT <HOSTNAME>:<PORT>'")).split(" ")
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


async def get_input(timeout = None, message : str | None = None, client : Client | None = None) -> str:
    if message is not None:
        print(message)

    inp = await asyncio.to_thread(input)
    if inp == "EXIT":
        if client is not None:
            await client._disconnect()
        sys.exit(0)
    return inp


async def main():
    config_path = parse_config_path()
    file = config_path.open("r", encoding='utf-8')
    config = json.load(file)
    file.close()

    username = config.get('username')
    mode = config.get('client_mode')
    ollama_config = config.get('ollama_config')
        
    client = Client(username, mode, ollama_config)

    while True:
        await client.prompt_connect()
        await client.play()



if __name__ == "__main__":
    asyncio.run(main())

        
        
