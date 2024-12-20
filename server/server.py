import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.protocol import TCPConnection
from room import Room
import threading
import random
import time

class TCPServer(TCPConnection):
    def __init__(self, host, port):
        super().__init__(host, port)
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        self.clients = {}
        self.rooms = {}
        self.next_udp_port = 12347
        self.max_udp_port = 12447  # Limiter à 100 salles maximum

    def start(self):
        print(f"TCP Server started on {self.host}:{self.port}")
        threading.Thread(target=self.accept_clients).start()

    def accept_clients(self):
        while True:
            client_socket, client_address = self.socket.accept()
            client_id = str(random.randint(1000, 9999))
            self.clients[client_id] = client_socket
            self.send_id(client_socket, client_id)
            time.sleep(0.1)
            client_socket.send("STATE:1".encode())
            threading.Thread(target=self.handle_client, args=(client_socket, client_id)).start()

    def handle_client(self, client_socket, client_id):
        current_room = None
        while True:
            try:
                message = client_socket.recv(1024).decode()
                if not message:
                    print(f"[TCP] Client {client_id} disconnected")
                    break
                
                print(f"[TCP] Received from {client_id}: {message}")
                if message.startswith("JOIN:"):
                    room_type = message.split(":")[1]
                    current_room = self.handle_join_request(client_socket, client_id, room_type)
                elif message.startswith("QUIT"):
                    break
            except Exception as e:
                print(f"[TCP] Error handling client {client_id}: {e}")
                break
        
        self.cleanup_client(client_id, current_room)

    def handle_join_request(self, client_socket, client_id, room_type):
        try:
            room = self.get_or_create_room(room_type)
            if room.add_client(client_id):
                udp_info = f"UDP:{room.udp_host}:{room.udp_port}"
                client_socket.send(udp_info.encode())
                print(f"[TCP] Sent UDP info to client {client_id}: {udp_info}")
                return room
            else:
                client_socket.send("ERROR:Room is full".encode())
                return None
        except Exception as e:
            print(f"[TCP] Error creating/joining room: {e}")
            client_socket.send(f"ERROR:{str(e)}".encode())
            return None

    def cleanup_client(self, client_id, current_room):
        try:
            if current_room:
                if current_room.remove_client(client_id):
                    self.close_room(current_room.room_id)
                else:
                    current_room.broadcast_udp(f"SYSTEM:Client {client_id} disconnected")
            
            if client_id in self.clients:
                self.clients[client_id].close()
                self.clients.pop(client_id)
            
            print(f"[TCP] Client {client_id} cleanup completed")
        except Exception as e:
            print(f"[TCP] Error during cleanup: {e}")

    def close_room(self, room_id):
        if room_id in self.rooms:
            self.rooms[room_id].shutdown()
            del self.rooms[room_id]

    def get_or_create_room(self, room_id):
        if room_id not in self.rooms:
            # Chercher un port UDP disponible
            while self.next_udp_port < self.max_udp_port:
                try:
                    self.rooms[room_id] = Room(room_id, '0.0.0.0', self.next_udp_port)
                    self.next_udp_port += 1
                    return self.rooms[room_id]
                except OSError as e:
                    print(f"[TCP] Port UDP {self.next_udp_port} déjà utilisé, essai du suivant...")
                    self.next_udp_port += 1
            raise Exception("Plus de ports UDP disponibles")
        return self.rooms[room_id]

def main():
    tcp_server = TCPServer('0.0.0.0', 12345)
    tcp_server.start()


if __name__ == "__main__":
    main()
