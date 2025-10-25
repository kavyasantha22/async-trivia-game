import json
import asyncio

def encode_message(message):
    return json.dumps(message).encode("utf-8")


def decode_message(json_bytes):
    return json.loads(json_bytes.decode("utf-8"))


async def send_message(writer: asyncio.StreamWriter, message: dict):
    load = encode_message(message) + b"\n"
    # print(load)
    writer.write(load)
    await writer.drain()


async def receive_message(reader: asyncio.StreamReader) -> dict | None:
    line = await reader.readline()      
    decoded = decode_message(line)  
    return decoded
