from shared.protocol import UDPConnection
from shared.game import Game  # Ajouter cet import
import threading
import time

class UDPServer(UDPConnection):
    def __init__(self, host, port):
        super().__init__(host, port)
        self.socket.bind((self.host, self.port))
        self.client_addresses = {}
        self.running = True
        self.message_handlers = {}  # Dictionnaire des callbacks
        self.roles = {}

    def register_handler(self, message_type, handler):
        self.message_handlers[message_type] = handler

    def start(self):
        print(f"UDP Server started on {self.host}:{self.port}")
        threading.Thread(target=self.receive_messages).start()

    def stop(self):
        self.running = False

    def receive_messages(self):
        while self.running:
            try:
                message, client_address = self.socket.recvfrom(1024)
                if not message:
                    continue

                decoded_message = message.decode()
                print(f"[UDP] Received from {client_address}: {decoded_message}")

                if decoded_message.startswith("CONNECT:"):
                    client_id = decoded_message.split(":")[1]
                    self.client_addresses[client_id] = client_address
                    role = "def" if len(self.client_addresses) == 1 else "att"
                    self.roles[client_id] = role
                    self.socket.sendto(f"ROLE:{role}".encode(), client_address)
                else:
                    # Trouver le client_id à partir de l'adresse
                    client_id = next((cid for cid, addr in self.client_addresses.items()
                                    if addr == client_address), None)
                    if client_id:
                        # Chercher et exécuter le bon handler
                        for msg_type, handler in self.message_handlers.items():
                            if decoded_message.startswith(msg_type):
                                handler(decoded_message, client_id)
                                break
            except Exception as e:
                if self.running:
                    print(f"[UDP] Error: {e}")
                continue

    def broadcast_to_client(self, message, client_id):
        if client_id in self.client_addresses:
            print(f"[UDP] Sending to {client_id}: {message}")
            self.socket.sendto(message.encode(), self.client_addresses[client_id])

    def broadcast_to_all_clients(self, message):
        for client_id in self.client_addresses:
            self.broadcast_to_client(message, client_id)

class Room:
    def __init__(self, room_id, udp_host, udp_port):
        self.room_id = room_id
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.clients = []
        try:
            self.udp_server = UDPServer(udp_host, udp_port)
            # Enregistrer les handlers
            self.udp_server.register_handler("ADD_PLANT:", self.handle_game_action)
            self.udp_server.register_handler("ADD_ZOMBIE:", self.handle_game_action)
            self.udp_server.start()
        except OSError as e:
            print(f"[ROOM] Could not start UDP server on port {udp_port}: {e}")
            raise e
        self.is_private = not room_id.startswith("public")
        self.game_thread = None
        self.game_running = False
        self.tick_rate = 20  # Réduit à 20 FPS pour la synchro réseau
        self.game = Game(is_solo=False)  # Ajouter l'instance de jeu

    def add_client(self, client_id):
        if len(self.clients) < 2:
            self.clients.append(client_id)
            if len(self.clients) == 2:
                self.start_game()
            return True
        return False

    def start_game(self):
        self.game_running = True
        self.game_thread = threading.Thread(target=self.game_loop)
        self.game_thread.daemon = True
        self.game_thread.start()
        print(f"[ROOM] Game started in room {self.room_id}")

    def game_loop(self):
        time.sleep(1)  # Petit délai pour s'assurer que les clients sont connectés
        self.broadcast_udp("STATE:2")

        last_time = time.time()
        
        while self.game_running and len(self.clients) == 2:
            current_time = time.time()
            delta_time = current_time - last_time
            
            if delta_time >= 1.0/self.tick_rate:  # Mise à jour fixe
                # Update game state
                self.game.update(delta_time)  # Delta time fixe

                # Envoyer l'état du jeu aux clients
                game_state = self.game.get_game_state()
                # self.broadcast_udp(f"GAME_STATE:{game_state}")

                last_time = current_time
            else:
                time.sleep(0.001)  # Petit délai pour éviter de surcharger le CPU

        print(f"[ROOM] Game loop ended in room {self.room_id}")
        self.game_running = False

    def handle_game_action(self, action, client_id):
        if action.startswith("ADD_PLANT:"):
            _, plant_type, row, col = action.split(":")
            success = self.game.add_plant(plant_type, int(row), int(col))
            if success:
                # Broadcast l'action à tous les clients
                self.broadcast_udp(action)
        elif action.startswith("ADD_ZOMBIE:"):
            # Vérifier si le client est l'attaquant
            if self.udp_server.roles.get(client_id) != "att":
                print(f"[ROOM] Client {client_id} is not authorized to add zombies")
                return
            
            _, zombie_type, row = action.split(":")
            success = self.game.add_zombie(zombie_type, int(row))
            print(f"[ROOM] Player {client_id} added zombie at {row} with success: {success}")
            if success:
                # Broadcast l'action à tous les clients
                self.broadcast_udp(action)

    def get_game_state(self):
        return {
            'players': self.clients,
            # Ajouter d'autres états de jeu ici
        }

    def broadcast_game_state(self, game_state):
        self.broadcast_udp(f"GAME_STATE:{game_state}")

    def shutdown(self):
        self.game_running = False
        if self.game_thread:
            self.game_thread.join(timeout=1.0)
        self.udp_server.stop()
        print(f"[ROOM] Room {self.room_id} closed")

    def remove_client(self, client_id):
        if client_id in self.clients:
            self.clients.remove(client_id)
            if len(self.clients) < 2:
                self.game_running = False
            return len(self.clients) == 0
        return False

    def broadcast_udp(self, message, sender_id=None):
        for client_id in self.clients:
            if client_id != sender_id:
                self.udp_server.broadcast_to_client(message, client_id)
