import json
import asyncio

def encode_message(message):
    return json.dumps(message).encode("utf-8")


def decode_message(json_bytes):
    return json.loads(json_bytes.decode("utf-8"))


async def send_message(writer: asyncio.StreamWriter, message: dict):
    load = encode_message(message) + b"\n"
    writer.write(load)
    await writer.drain()


async def receive_message(reader: asyncio.StreamReader) -> dict:
    line = await reader.readline()      
    if not line:
        raise ConnectionError("Disconnected")
    decoded = decode_message(line)  
    return decoded
