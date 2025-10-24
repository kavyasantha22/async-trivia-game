import socket
import asyncio
from helper import send_message, receive_message


async def handle_client(reader, writer):
    peer = writer.get_extra_info("peername")
    print(f"[+] connection from {peer}")
    msg = await receive_message(reader)
    print(msg['message_type'])
    print(msg['username'])
    

async def start():
    server = await asyncio.start_server(handle_client, "0.0.0.0", port=7777)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets or [])
    print(addrs)
    async with server:
        await server.serve_forever()

asyncio.run(start())





    




