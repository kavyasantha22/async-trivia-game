import socket
import asyncio
from helper import send_message, receive_message


server_addr = "127.0.0.1"
server_port = 7777

async def connect():    
    reader, writer = await asyncio.open_connection(server_addr, int(server_port))
    print(reader, writer)
    msg = {
        "message_type": "HI",
        "username": "test1"
    }
    print(msg)
    await send_message(writer, msg)

asyncio.run(connect())





