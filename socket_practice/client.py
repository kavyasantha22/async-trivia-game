import socket


server_addr = "127.0.0.1"
server_port = 7777

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((server_addr, server_port))

s.sendall(b"hello server")
data = s.recv(1024) 
print("Received:", data.decode())

s.close()





