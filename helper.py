import json
import socket
import struct

_HEADER = struct.Struct("!I")

def encode_message(message):
    return json.dumps(message).encode('utf-8')


def decode_message(json_bytes):
    return json.loads(json_bytes.decode('utf-8'))


def _prepare_header(message):
    return _HEADER.pack(len(message))


def send_message(sock: socket.socket, message: dict):
    payload = encode_message(message)
    header = _prepare_header(payload)
    sock.sendall(header + payload)


def _receive_exact(sock: socket.socket, size: int):
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("Socket closed while receiving message.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def receive_message(sock: socket.socket):
    header = _receive_exact(sock, _HEADER.size)
    payload_size, = _HEADER.unpack_from(header)
    payload = _receive_exact(sock, payload_size)
    return decode_message(payload)
    

def generate_questions():
    pass


# framing sanity
assert _HEADER.size == 4
assert _HEADER.unpack(_HEADER.pack(1234)) == (1234,)

# encode/decode roundtrip
obj = {"message_type": "ANSWER", "answer": "42"}
assert decode_message(encode_message(obj)) == obj
