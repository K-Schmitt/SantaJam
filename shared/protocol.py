import socket
import threading

class TCPConnection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def send_message(self, message):
        self.socket.send(message.encode())

    def receive_message(self):
        return self.socket.recv(1024).decode()

    def send_id(self, client_socket, client_id):
        client_socket.send(f"ID:{client_id}".encode())

    def receive_id(self):
        message = self.socket.recv(1024).decode()
        if message.startswith("ID:"):
            return message.split(":")[1]

class UDPConnection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_message(self, message):
        self.socket.sendto(message.encode(), (self.host, self.port))

    def receive_message(self):
        message, _ = self.socket.recvfrom(1024)
        return message.decode()
