import socket


ip_addr = "0.0.0.0"
port = 7777

csocket = socket.socket()
csocket.bind((ip_addr, port))
csocket.listen(1)

print(f"Listening on {ip_addr}:{port}")

client1, _ = csocket.accept()
print("peer: " + str(client1.getpeername()))
print("local: " + str(client1.getsockname()))

data = client1.recv(1024)
if data:
    print(f"Received: {data.decode()}")
    client1.sendall(b"your message is received.")

client1.close()



    




