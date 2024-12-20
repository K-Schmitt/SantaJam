import pygame
import threading
import socket
import signal
import time
from shared.protocol import TCPConnection, UDPConnection
from shared.constants import GRID_WIDTH, GRID_HEIGHT, PLANT_TYPES, ZOMBIE_TYPES

class Button:
    def __init__(self, x, y, width, height, text, color=(100, 100, 100)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.font = pygame.font.Font(None, 36)
        
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class Menu:
    def __init__(self, game):
        self.game = game
        self.current_menu = "main"
        self.input_text = ""
        self.create_buttons()
        
    def create_buttons(self):
        # Main menu
        self.play_button = Button(300, 250, 200, 50, "Jouer")
        
        # Mode selection menu
        self.solo_button = Button(300, 200, 200, 50, "Solo")
        self.online_button = Button(300, 300, 200, 50, "Online")
        
        # Room selection menu
        self.public_button = Button(300, 200, 200, 50, "Public")
        self.private_button = Button(300, 300, 200, 50, "Privé")
        self.back_button = Button(300, 400, 200, 50, "Retour")
        
        # Private room menu
        self.join_button = Button(300, 350, 200, 50, "Rejoindre")
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            if self.current_menu == "main":
                if self.play_button.is_clicked(mouse_pos):
                    self.current_menu = "mode_selection"
                    
            elif self.current_menu == "mode_selection":
                if self.solo_button.is_clicked(mouse_pos):
                    self.game.start_solo_mode()
                elif self.online_button.is_clicked(mouse_pos):
                    self.game.start_online_mode()
                    self.current_menu = "room_selection"
                    
            elif self.current_menu == "room_selection":
                if self.public_button.is_clicked(mouse_pos):
                    self.game.join_public_room()
                elif self.private_button.is_clicked(mouse_pos):
                    self.current_menu = "private_room"
                elif self.back_button.is_clicked(mouse_pos):
                    self.current_menu = "main"
                    
            elif self.current_menu == "private_room":
                if self.join_button.is_clicked(mouse_pos):
                    self.game.join_private_room(self.input_text)
                elif self.back_button.is_clicked(mouse_pos):
                    self.current_menu = "room_selection"
                    
        elif event.type == pygame.KEYDOWN and self.current_menu == "private_room":
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_RETURN:
                self.game.join_private_room(self.input_text)
            elif len(self.input_text) < 10:
                self.input_text += event.unicode
                
    def draw(self, screen):
        screen.fill((0, 0, 0))
        
        if self.current_menu == "main":
            self.play_button.draw(screen)
            
        elif self.current_menu == "mode_selection":
            self.solo_button.draw(screen)
            self.online_button.draw(screen)
            self.back_button.draw(screen)
            
        elif self.current_menu == "room_selection":
            self.public_button.draw(screen)
            self.private_button.draw(screen)
            self.back_button.draw(screen)
            
        elif self.current_menu == "private_room":
            font = pygame.font.Font(None, 36)
            text_surface = font.render(f"Code: {self.input_text}", True, (255, 255, 255))
            screen.blit(text_surface, (300, 250))
            self.join_button.draw(screen)
            self.back_button.draw(screen)
            
        pygame.display.flip()

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("PVZ Game")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 1
        self.menu = Menu(self)
        self.in_game = False
        self.tcp_client = None
        self.is_solo = False
        self.game_state = None
        self.game_instance = None  # Instance de Game du serveur
        self.last_zombie_spawn = 0  # Pour suivre le temps depuis le dernier zombie
        self.selected_plant = 'sunflower'
        self.plant_buttons = []
        self.sun_points = 0  # Ajout de l'attribut manquant
        self.online_game_started = False # Ajouter ce flag
        self.last_update = time.time()
        self.server_tick_rate = 20  # Même valeur que le serveur
        self.is_attacker = False
        self.selected_zombie = 'basic'
        self.zombie_buttons = []
        
        # Charger les images (à adapter selon vos assets)
        self.images = {
            'background': pygame.Surface((800, 600)),
            'grid_cell': pygame.Surface((70, 70)),
            'sunflower': pygame.Surface((60, 60)),
            'peashooter': pygame.Surface((60, 60)),
            'wallnut': pygame.Surface((60, 60)),
            'basic_zombie': pygame.Surface((60, 60)),
        }
        # Définir des couleurs temporaires pour les surfaces
        self.images['background'].fill((50, 120, 50))  # Vert foncé
        self.images['grid_cell'].fill((70, 140, 70))   # Vert clair
        self.images['sunflower'].fill((255, 255, 0))   # Jaune
        self.images['peashooter'].fill((0, 255, 0))    # Vert
        self.images['wallnut'].fill((139, 69, 19))     # Marron
        self.images['basic_zombie'].fill((150, 150, 150))  # Gris
        self.selected_plant = 'sunflower'
        self.plant_buttons = []
        
        # Ajouter une image pour les projectiles
        self.images['pea'] = pygame.Surface((20, 20))
        self.images['pea'].fill((0, 255, 0))  # Vert pour les pois
        self.images['energy_icon'] = pygame.Surface((30, 30))
        self.images['energy_icon'].fill((255, 0, 0))  # Rouge pour l'énergie
        
        # Définir les images pour les zombies disponibles
        count = 1
        for zombie_type in ZOMBIE_TYPES:
            self.images[f'{zombie_type}'] = pygame.Surface((60, 60))
            self.images[f'{zombie_type}'].fill((75 * count, 75 * count, 75 * count))
            count += 1

    def create_plant_buttons(self):
        self.plant_buttons = []
        x, y = 20, 60
        # Utiliser les points de soleil du game_state au lieu de self.sun_points
        current_sun = self.game_state.get('sun_points', 0) if self.game_state else 0
        
        for plant_type in self.game_state.get('available_plants', []):
            cost = PLANT_TYPES[plant_type]['cost']
            btn = Button(x, y, 100, 40, f"{plant_type}\n{cost}", 
                        (100, 100, 100) if current_sun >= cost else (50, 50, 50))
            self.plant_buttons.append((plant_type, btn))
            y += 50

    def create_zombie_buttons(self):
        self.zombie_buttons = []
        x, y = 20, 60
        current_energy = self.game_state.get('energy', 0) if self.game_state else 0
        
        for zombie_type, stats in ZOMBIE_TYPES.items():
            cost = stats.get('cost', 50)  # Par défaut 50 d'énergie
            btn = Button(x, y, 100, 40, f"{zombie_type}\n{cost}", 
                        (100, 100, 100) if current_energy >= cost else (50, 50, 50))
            self.zombie_buttons.append((zombie_type, btn))
            y += 50

    def draw_game(self):
        # Dessiner le fond
        self.screen.blit(self.images['background'], (0, 0))
        
        # Dessiner la grille
        grid_start_x = 150
        grid_start_y = 100
        cell_size = 70
        
        # Dessiner les cellules de la grille
        for row in range(GRID_HEIGHT):
            for col in range(GRID_WIDTH):
                x = grid_start_x + (col * cell_size)
                y = grid_start_y + (row * cell_size)
                self.screen.blit(self.images['grid_cell'], (x, y))
                pygame.draw.rect(self.screen, (0, 0, 0), (x, y, cell_size, cell_size), 1)
        
        # Si nous avons un état de jeu, dessiner les entités
        if self.game_state:
            # Dessiner les plantes
            for plant in self.game_state.get('plants', []):
                x = grid_start_x + (plant['col'] * cell_size) + 5
                y = grid_start_y + (plant['row'] * cell_size) + 5
                plant_image = self.images.get(plant['type'], self.images['sunflower'])
                self.screen.blit(plant_image, (x, y))
            
            # Dessiner les zombies
            for zombie in self.game_state.get('zombies', []):
                x = grid_start_x + (zombie['col'] * cell_size) + 5
                y = grid_start_y + (zombie['row'] * cell_size) + 5
                zombie_image = self.images[f'{zombie["type"]}']
                self.screen.blit(zombie_image, (x, y))

        # Dessiner les projectiles
        for proj in self.game_state.get('projectiles', []):
            x = grid_start_x + (proj['col'] * cell_size) + 25
            y = grid_start_y + (proj['row'] * cell_size) + 25
            self.screen.blit(self.images['pea'], (x, y))

        if self.is_attacker:
            # Interface attaquant
            if self.game_state:
                # Afficher l'énergie au lieu du soleil
                font = pygame.font.Font(None, 36)
                energy_text = font.render(f"Energy: {self.game_state.get('energy', 0)}", True, (255, 0, 0))
                self.screen.blit(energy_text, (20, 20))
            
            # Dessiner les boutons de zombies
            self.create_zombie_buttons()
            for zombie_type, btn in self.zombie_buttons:
                btn.draw(self.screen)
                if zombie_type == self.selected_zombie:
                    pygame.draw.rect(self.screen, (255, 0, 0), btn.rect, 3)
        else:
            if self.game_state:
            # Afficher les points de soleil
                font = pygame.font.Font(None, 36)
                sun_text = font.render(f"Soleil: {self.game_state.get('sun_points', 0)}", True, (255, 255, 0))
                self.screen.blit(sun_text, (20, 20))

            # Dessiner les boutons de plantes
            self.create_plant_buttons()
            for plant_type, btn in self.plant_buttons:
                btn.draw(self.screen)
                if plant_type == self.selected_plant:
                    pygame.draw.rect(self.screen, (255, 255, 0), btn.rect, 3)

    def render(self):
        if self.in_game:
            self.screen.fill((0, 0, 0))
            self.draw_game()
            pygame.display.flip()
        else:
            self.menu.draw(self.screen)

    def set_tcp_client(self, client):
        self.tcp_client = client

    def join_public_room(self):
        if self.tcp_client:
            self.tcp_client.join_room("public")
            self.in_game = True

    def join_private_room(self, code):
        if self.tcp_client and code:
            self.tcp_client.join_room(f"private_{code}")
            self.in_game = True

    def start_solo_mode(self):
        from shared.game import Game as ServerGame
        self.is_solo = True
        self.in_game = True
        self.state = 1
        self.game_instance = ServerGame(is_solo=True)
        self.game_state = self.game_instance.get_game_state()

    def start_online_mode(self):
        self.is_solo = False
        try:
            self.tcp_client = TCPClient('127.0.0.1', 12353, self)
            self.tcp_client.connect()
        except Exception as e:
            print(f"[CLIENT] Connection error: {e}")
            self.menu.current_menu = "main"

    def update(self):
        current_time = time.time()
        delta_time = current_time - self.last_update
        
        if self.is_solo and self.game_instance:
            self.game_instance.update(1/60, current_time)  # Mode solo reste à 60 FPS
            self.game_state = self.game_instance.get_game_state()
        elif self.online_game_started and self.game_instance:
            if delta_time >= 1.0/self.server_tick_rate:
                self.game_instance.update(delta_time)
                self.game_state = self.game_instance.get_game_state()
                self.last_update = current_time
            else:
                time.sleep(0.001)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False

            if not self.in_game:
                self.menu.handle_event(event)
                continue

            if self.in_game and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                if self.is_attacker:
                    # Gestion des clics pour l'attaquant
                    button_clicked = False
                    for zombie_type, btn in self.zombie_buttons:
                        if btn.is_clicked(mouse_pos):
                            self.selected_zombie = zombie_type
                            button_clicked = True
                            break
                    
                    if not button_clicked:
                        grid_start_x = 150
                        grid_start_y = 100
                        cell_size = 70
                        
                        col = (mouse_pos[0] - grid_start_x) // cell_size
                        row = (mouse_pos[1] - grid_start_y) // cell_size
                        
                        if (0 <= row < GRID_HEIGHT and col == GRID_WIDTH - 1):  # Spawn uniquement sur la dernière colonne
                            if self.online_game_started and self.tcp_client.udp_client:
                                message = f"ADD_ZOMBIE:{self.selected_zombie}:{row}"
                                self.tcp_client.udp_client.send_message(message)
                else:
                    # Gestion défenseur
                    button_clicked = False
                    for plant_type, btn in self.plant_buttons:
                        if btn.is_clicked(mouse_pos):
                            self.selected_plant = plant_type
                            button_clicked = True
                            break

                    if not button_clicked:
                        grid_start_x = 150
                        grid_start_y = 100
                        cell_size = 70
                        
                        col = (mouse_pos[0] - grid_start_x) // cell_size
                        row = (mouse_pos[1] - grid_start_y) // cell_size
                        
                        if (0 <= row < GRID_HEIGHT and 0 <= col < GRID_WIDTH):
                            if self.is_solo:
                                plant_placed = self.game_instance.add_plant(self.selected_plant, row, col)
                                if plant_placed:
                                    self.game_state = self.game_instance.get_game_state()
                            elif self.online_game_started and self.tcp_client.udp_client:
                                message = f"ADD_PLANT:{self.selected_plant}:{row}:{col}"
                                self.tcp_client.udp_client.send_message(message)

        return True

    def cleanup(self):
        pygame.quit()

class TCPClient(TCPConnection):
    def __init__(self, host, port, game):
        super().__init__(host, port)
        self.client_id = None
        self.udp_client = None
        self.running = True
        self.receive_thread = None
        self.game = game

    def connect(self):
        self.socket.connect((self.host, self.port))
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def shutdown(self):
        print("\n[CLIENT] Starting shutdown...")
        self.running = False
        
        if self.socket:
            try:
                self.send_message("QUIT")
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except:
                pass

        if self.udp_client:
            self.udp_client.shutdown()

    def receive_messages(self):
        while self.running:
            try:
                message = self.socket.recv(1024).decode()
                if not message:
                    print("[TCP] Server disconnected")
                    break
                print(f"[TCP] Received: {message}")

                if message.startswith("STATE:"):
                    state = int(message.split(":")[1])
                    self.game.state = state
                    if state == 1:
                        # Init le jeu en mode online quand on reçoit STATE:1
                        from shared.game import Game as ServerGame
                        self.game.game_instance = ServerGame(is_solo=False)
                        self.game.game_state = self.game.game_instance.get_game_state()
                    print(f"[TCP] State: {state}")
                if message.startswith("ID:"):
                    self.client_id = message.split(":")[1]
                    # else:
                    #     self.join_room("public")
                elif message.startswith("UDP:"):
                    _, host, port = message.split(":")
                    print(f"[TCP] Connecting to UDP {host}:{port}")
                    self.udp_client = UDPClient(host, int(port), self.game)
                    self.udp_client.send_message(f"CONNECT:{self.client_id}")
            except Exception as e:
                if self.running:
                    print(f"[TCP] Connection lost: {e}")
                break

    def join_room(self, room_type):
        self.send_message(f"JOIN:{room_type}")

class UDPClient(UDPConnection):
    def __init__(self, host, port, game):
        super().__init__(host, port)
        self.running = True
        self.receive_thread = None
        self.game = game  # Référence au jeu
        self.start_receiving()

    def start_receiving(self):
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def receive_messages(self):
        while self.running:
            try:
                message, _ = self.socket.recvfrom(1024)
                decoded_message = message.decode()
                print(f"[UDP] Received: {decoded_message}")

                if decoded_message == "STATE:2":
                    self.game.online_game_started = True
                    self.game.last_update = time.time()  # Initialiser le timer
                    print("[UDP] Game starting!")
                elif decoded_message.startswith("ROLE:"):
                    role = decoded_message.split(":")[1]
                    self.game.is_attacker = (role == "att")
                    print(f"[UDP] Role assigned: {'Attacker' if self.game.is_attacker else 'Defender'}")
                elif decoded_message.startswith("GAME_STATE:"):
                    self.handle_game_state(decoded_message)
                elif decoded_message.startswith("ADD_PLANT:"):
                    print(f"[UDP] Plant added: {decoded_message}")
                    _, plant_type, row, col = decoded_message.split(":")
                    # Appliquer l'action à l'instance locale du jeu
                    self.game.game_instance.add_plant(plant_type, int(row), int(col))
                    # Mettre à jour l'état du jeu
                    self.game.game_state = self.game.game_instance.get_game_state()
                elif decoded_message.startswith("ADD_ZOMBIE:"):
                    print(f"[UDP] Zombie added: {decoded_message}")
                    _, zombie_type, row = decoded_message.split(":")
                    # Appliquer l'action à l'instance locale du jeu
                    self.game.game_instance.add_zombie(zombie_type, int(row))
                    # Mettre à jour l'état du jeu
                    self.game.game_state = self.game.game_instance.get_game_state()
                elif decoded_message.startswith("SYSTEM:"):
                    print(f"[SYSTEM] {decoded_message.split(':', 1)[1]}")
            except Exception as e:
                if self.running:
                    print(f"[UDP] Receive error: {e}")
                break

    def handle_game_state(self, message):
        try:
            game_state_str = message.split("GAME_STATE:", 1)[1]
            import ast
            game_state = ast.literal_eval(game_state_str)
            self.game.game_state = game_state  # Met à jour l'état du jeu
        except Exception as e:
            print(f"[UDP] Error parsing game state: {e}")

    def send_message(self, message):
        if not self.running:
            return
        try:
            print(f"[UDP] Sending: {message}")
            self.socket.sendto(message.encode(), (self.host, self.port))
        except Exception as e:
            if self.running:
                print(f"[UDP] Send error: {e}")

    def shutdown(self):
        self.running = False
        try:
            self.socket.close()
        except:
            pass
        if self.receive_thread:
            self.receive_thread.join(timeout=0.5)

def signal_handler(signum, frame):
    print("\n[CLIENT] Caught signal, shutting down...")
    if 'client' in globals():
        client.shutdown()

def main():
    global client
    signal.signal(signal.SIGINT, signal_handler)

    try:
        game = Game()
        while game.running:
            if not game.handle_events():
                break
            game.update()
            game.render()
            game.clock.tick(60)

    except Exception as e:
        print(f"[CLIENT] Error: {e}")
    finally:
        if hasattr(game, 'tcp_client') and game.tcp_client:
            game.tcp_client.shutdown()
        game.cleanup()
        print("[CLIENT] Disconnected")

if __name__ == "__main__":
    main()
