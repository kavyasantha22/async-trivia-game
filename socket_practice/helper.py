import json
import struct
import asyncio

_HEADER = struct.Struct("!I")

def encode_message(message):
    return json.dumps(message).encode('utf-8')


def decode_message(json_bytes):
    return json.loads(json_bytes.decode('utf-8'))


def _prepare_header(message):
    return _HEADER.pack(len(message))


async def send_message(writer: asyncio.StreamWriter, message: dict):
    payload = encode_message(message)
    header = _prepare_header(payload)
    writer.write(header + payload)
    await writer.drain()


async def receive_message(reader: asyncio.StreamReader) -> dict:
    header_bytes = await reader.readexactly(_HEADER.size)
    (payload_size,) = _HEADER.unpack(header_bytes)
    payload = await reader.readexactly(payload_size)
    return decode_message(payload)
    


