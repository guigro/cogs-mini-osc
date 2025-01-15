import socket
import json

tcp_ip = "localhost"
tcp_port = 9000

message = {
    "address": "/from_tcp",
    "args": [42, "hello"]
}

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((tcp_ip, tcp_port))
client_socket.send(json.dumps(message).encode('utf-8'))

response = client_socket.recv(1024).decode('utf-8')
print("Response:", response)

client_socket.close()