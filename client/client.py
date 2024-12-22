import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
import threading
import socket
import signal
import time
from shared.protocol import TCPConnection, UDPConnection
from shared.constants import GRID_WIDTH, GRID_HEIGHT, PLANT_TYPES, ZOMBIE_TYPES
import random

class Button:
    def __init__(self, x, y, width, height, text, color=(100, 100, 100)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.font = pygame.font.Font(None, 36)
        self.candy_cane_offset = 0  # Pour l'animation de la bordure
        self.segment_length = 10    # Longueur de chaque segment de la bordure
        self.buttonClick = pygame.mixer.Sound('client/soundEffect/buttonclick.ogg')
        self.buttonClick.set_volume(0.35)  # Volume par défaut

    def draw(self, screen):
        # Dessiner le fond du bouton
        pygame.draw.rect(screen, self.color, self.rect)
        
        # Dessiner la bordure style sucre d'orge
        rect_points = [
            (self.rect.left, self.rect.top),     # Haut gauche
            (self.rect.right, self.rect.top),    # Haut droite
            (self.rect.right, self.rect.bottom), # Bas droite
            (self.rect.left, self.rect.bottom)   # Bas gauche
        ]
        
        for i in range(4):  # Pour chaque côté du rectangle
            start_pos = rect_points[i]
            end_pos = rect_points[(i + 1) % 4]
            
            # Calculer la longueur du côté
            length = ((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)**0.5
            num_segments = int(length / self.segment_length)
            
            for j in range(num_segments):
                start_ratio = j / num_segments
                end_ratio = (j + 1) / num_segments
                
                seg_start = (
                    start_pos[0] + (end_pos[0] - start_pos[0]) * start_ratio,
                    start_pos[1] + (end_pos[1] - start_pos[1]) * start_ratio
                )
                seg_end = (
                    start_pos[0] + (end_pos[0] - start_pos[0]) * end_ratio,
                    start_pos[1] + (end_pos[1] - start_pos[1]) * end_ratio
                )
                
                # Alterner entre rouge et blanc
                color = (255, 0, 0) if (j + self.candy_cane_offset) % 2 >= 1 else (255, 255, 255)
                pygame.draw.line(screen, color, seg_start, seg_end, 3)

        # Dessiner le texte
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
        # Mettre à jour l'offset pour l'animation (optionnel)
        self.candy_cane_offset = (self.candy_cane_offset + 0.05) % 2

    def is_clicked(self, pos):
        if self.rect.collidepoint(pos):
            self.buttonClick.play()  # Jouer le son quand le bouton est cliqué
            return True
        return False

class Snowflake:
    def __init__(self, screen_width, screen_height):
        self.x = random.randint(0, screen_width)
        self.y = random.randint(-screen_height, 0)
        self.size = random.randint(2, 5)
        self.speed = random.uniform(1, 3)
        self.screen_width = screen_width
        self.screen_height = screen_height

    def update(self):
        self.y += self.speed
        if self.y > self.screen_height:
            self.y = random.randint(-self.screen_height, 0)
            self.x = random.randint(0, self.screen_width)

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), self.size)

class Menu:
    def __init__(self, game):
        self.game = game
        self.volume_slider_rect = pygame.Rect(300, 275, 200, 20)
        self.sfx_volume_slider_rect = pygame.Rect(300, 350, 200, 20)
        self.current_menu = "main"
        self.input_text = ""
        self.create_buttons()
        self.snowflakes = [Snowflake(800, 600) for _ in range(100)]

    def update_buttons_volume(self):
        """Met à jour le volume de tous les boutons du menu"""
        buttons = [
            self.play_button,
            self.options_button,
            self.solo_button,
            self.online_button,
            self.public_button,
            self.private_button,
            self.back_button,
            self.join_button,
            self.sound_toggle_button,
            self.back_to_main_button
        ]
        for button in buttons:
            if button and hasattr(button, 'buttonClick'):
                button.buttonClick.set_volume(self.game.sfx_volume if self.game.sound_enabled else 0)

    def create_buttons(self):
        # Main menu
        self.play_button = Button(300, 250, 200, 50, "Jouer")
        self.options_button = Button(300, 350, 200, 50, "Options")

        # Mode selection menu
        self.solo_button = Button(300, 200, 200, 50, "Solo")
        self.online_button = Button(300, 300, 200, 50, "Online")

        # Room selection menu
        self.public_button = Button(300, 200, 200, 50, "Public")
        self.private_button = Button(300, 300, 200, 50, "Privé")
        self.back_button = Button(300, 400, 200, 50, "Retour")

        # Private room menu
        self.join_button = Button(300, 350, 200, 50, "Rejoindre")

        # Options menu
        self.sound_toggle_button = Button(300, 200, 200, 50, "Son: Activé")
        self.back_to_main_button = Button(300, 400, 200, 50, "Retour")
        self.volume_slider_rect = pygame.Rect(300, 250, 200, 20)
        self.sfx_volume_slider_rect = pygame.Rect(300, 350, 200, 20)

        # Initialiser le volume pour tous les boutons
        self.update_buttons_volume()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            if self.current_menu == "main":
                if self.play_button.is_clicked(mouse_pos):
                    self.current_menu = "mode_selection"
                elif self.options_button.is_clicked(mouse_pos):
                    self.current_menu = "options"

            elif self.current_menu == "mode_selection":
                if self.solo_button.is_clicked(mouse_pos):
                    self.game.start_solo_mode()
                elif self.online_button.is_clicked(mouse_pos):
                    self.game.start_online_mode()
                    self.current_menu = "room_selection"
                elif self.back_button.is_clicked(mouse_pos):
                    self.current_menu = "main"

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

            elif self.current_menu == "options":
                if self.sound_toggle_button.is_clicked(mouse_pos):
                    self.game.toggle_sound()
                    self.sound_toggle_button.text = "Son: Activé" if self.game.sound_enabled else "Son: Désactivé"
                elif self.back_to_main_button.is_clicked(mouse_pos):
                    self.current_menu = "main"
                elif self.volume_slider_rect.collidepoint(mouse_pos):
                    # Calculer le nouveau volume basé sur la position X du clic
                    rel_x = (mouse_pos[0] - self.volume_slider_rect.x) / self.volume_slider_rect.width
                    self.game.set_volume(rel_x)
                elif self.sfx_volume_slider_rect.collidepoint(mouse_pos):
                    rel_x = (mouse_pos[0] - self.sfx_volume_slider_rect.x) / self.sfx_volume_slider_rect.width
                    self.game.set_sfx_volume(rel_x)

        elif event.type == pygame.KEYDOWN and self.current_menu == "private_room":
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_RETURN:
                self.game.join_private_room(self.input_text)
            elif len(self.input_text) < 10:
                self.input_text += event.unicode

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Clic gauche
                if (self.current_menu == "options" or self.game.paused) and self.volume_slider_rect.collidepoint(event.pos):
                    # Mettre à jour le volume une dernière fois
                    rel_x = (event.pos[0] - self.volume_slider_rect.x) / self.volume_slider_rect.width
                    self.game.set_volume(rel_x)
                elif (self.current_menu == "options" or self.game.paused) and self.sfx_volume_slider_rect.collidepoint(event.pos):
                    rel_x = (event.pos[0] - self.sfx_volume_slider_rect.x) / self.sfx_volume_slider_rect.width
                    self.game.set_sfx_volume(rel_x)

        elif event.type == pygame.MOUSEMOTION:
            if event.buttons[0]:  # Si le bouton gauche est maintenu
                if (self.current_menu == "options" or self.game.paused) and self.volume_slider_rect.collidepoint(event.pos):
                    # Mettre à jour le volume pendant le glissement
                    rel_x = (event.pos[0] - self.volume_slider_rect.x) / self.volume_slider_rect.width
                    self.game.set_volume(rel_x)
                elif (self.current_menu == "options" or self.game.paused) and self.sfx_volume_slider_rect.collidepoint(event.pos):
                    rel_x = (event.pos[0] - self.sfx_volume_slider_rect.x) / self.sfx_volume_slider_rect.width
                    self.game.set_sfx_volume(rel_x)

    def draw(self, screen):
        screen.fill((42, 21, 174))

        # Mise à jour et dessin des flocons de neige
        for snowflake in self.snowflakes:
            snowflake.update()
            snowflake.draw(screen)

        if self.current_menu == "main":
            self.play_button.draw(screen)
            self.options_button.draw(screen)

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

        elif self.current_menu == "options":
            self.sound_toggle_button.draw(screen)
            self.back_to_main_button.draw(screen)

            # Dessiner le slider de volume
            pygame.draw.rect(screen, (100, 100, 100), self.volume_slider_rect)
            volume_pos = self.volume_slider_rect.x + (self.volume_slider_rect.width * self.game.music_volume)
            pygame.draw.circle(screen, (255, 255, 255), (int(volume_pos), self.volume_slider_rect.centery), 10)

            pygame.draw.rect(screen, (100, 100, 100), self.sfx_volume_slider_rect)
            sfx_pos = self.sfx_volume_slider_rect.x + (self.sfx_volume_slider_rect.width * self.game.sfx_volume)
            pygame.draw.circle(screen, (255, 255, 255), (int(sfx_pos), self.sfx_volume_slider_rect.centery), 10)

            # Afficher le pourcentage du volume
            font = pygame.font.Font(None, 36)
            volume_text = font.render(f"Volume: {int(self.game.music_volume * 100)}%", True, (255, 255, 255))
            screen.blit(volume_text, (300, 300))

            volume_text = font.render(f"Effets: {int(self.game.sfx_volume * 100)}%", True, (255, 255, 255))
            screen.blit(volume_text, (300, 375))

        pygame.display.flip()

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()  # Initialiser le mixeur audio
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("PVZ Game")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 1
        self.sound_enabled = True  # Ajout du flag pour le son
        self.music_volume = 0.3  # Volume pour la musique
        self.sfx_volume = 0.35    # Volume pour les effets sonores
        self.menu = Menu(self)
        self.in_game = False
        self.tcp_client = None
        self.is_solo = False
        self.game_state = None
        self.game_instance = None  # Instance de Game du serveur
        self.last_zombie_spawn = 0  # Pour suivre le temps depuis le dernier zombie
        self.selected_plant = 'candycane'
        self.plant_buttons = []
        self.sun_points = 0  # Ajout de l'attribut manquant
        self.online_game_started = False # Ajouter ce flag
        self.last_update = time.time()
        self.server_tick_rate = 20  # Même valeur que le serveur
        self.is_attacker = False
        self.selected_zombie = 'basic'
        self.zombie_buttons = []
        self.prev_game_state = None  # Pour l'interpolation
        self.prev_update_time = time.time()  # Pour l'interpolation
        self.paused = False  # Ajouter l'état de pause

        # Charger les images (à adapter selon vos assets)
        self.images = {
            'background': pygame.Surface((800, 600)),
            'grid_cell': pygame.Surface((80, 80)),
            'candycane': pygame.Surface((60, 60)),
            'peashooter': pygame.Surface((60, 60)),
            'wallnut': pygame.Surface((60, 60)),
            'basic_zombie': pygame.Surface((60, 60)),
        }

        # Définir des couleurs temporaires pour les surfaces
        self.images['background'] = pygame.image.load('client/assets/background.png')
        self.images['grid_cell'].fill((80, 140, 80))   # Vert clair
        self.images['peashooter'] = pygame.transform.scale(pygame.image.load('client/assets/peashooter.gif'), (80, 80))
        self.images['wallnut'] = pygame.transform.scale(pygame.image.load('client/assets/wallnut.png'), (80, 80))
        self.images['basic'] = pygame.transform.scale(pygame.image.load('client/assets/basic.png'), (80, 140))
        self.images['cone'] = pygame.transform.scale(pygame.image.load('client/assets/cone.png'), (80, 140))
        self.images['bucket'] = pygame.transform.scale(pygame.image.load('client/assets/bucket.png'), (80, 140))
        self.images['sprinter'] = pygame.transform.scale(pygame.image.load('client/assets/sprinter.png'), (80, 140))
        self.selected_plant = 'candycane'
        self.plant_buttons = []

        candycane_sprite = pygame.image.load('client/assets/candycane.png')
        # Créer des surfaces avec canal alpha
        self.images['candycane'] = pygame.Surface((80, 80), pygame.SRCALPHA)
        self.images['candycane_ready'] = pygame.Surface((80, 80), pygame.SRCALPHA)
        # Copier la partie gauche pour l'état inactif
        self.images['candycane'].blit(candycane_sprite, (0, 0), (0, 0, 80, 80))
        # Copier la partie droite pour l'état actif
        self.images['candycane_ready'].blit(candycane_sprite, (0, 0), (80, 0, 160, 80))


        # Ajouter une image pour les projectiles
        self.images['pea'] = pygame.Surface((20, 20))
        self.images['pea'].fill((0, 255, 0))  # Vert pour les pois
        self.images['energy_icon'] = pygame.Surface((30, 30))
        self.images['energy_icon'].fill((255, 0, 0))  # Rouge pour l'énergie

        # Définir les images pour les zombies disponibles
        # count = 1
        # for zombie_type in ZOMBIE_TYPES:
        #     self.images[f'{zombie_type}'] = pygame.Surface((60, 60))
        #     self.images[f'{zombie_type}'].fill((60 * count, 60 * count, 60 * count))
        #     count += 1

        self.images['shovel'] = pygame.Surface((60, 60))
        self.images['shovel'].fill((139, 69, 19))  # Marron

        # Charger les musiques
        self.menu_music = pygame.mixer.Sound('client/music/Crazy_Dave.mp3')
        self.game_music = pygame.mixer.Sound('client/music/Loonboon.mp3')
        self.lose_music = pygame.mixer.Sound('client/music/losemusic.ogg')
        self.current_music = None

        # Configuration du volume
        self.menu_music.set_volume(self.music_volume if self.sound_enabled else 0)
        self.game_music.set_volume(self.music_volume if self.sound_enabled else 0)
        self.lose_music.set_volume(self.music_volume if self.sound_enabled else 0)

        # Charger sound effect
        self.splat = pygame.mixer.Sound('client/soundEffect/splat.ogg')
        self.point = pygame.mixer.Sound('client/soundEffect/points.ogg')

        self.splat.set_volume(self.sfx_volume if self.sound_enabled else 0)
        self.point.set_volume(self.sfx_volume if self.sound_enabled else 0)

        self.grid_start_x = 41
        self.grid_start_y = 179
        self.cell_size = 80

        self.waiting_font = pygame.font.Font(None, 74)
        self.waiting_text = self.waiting_font.render("En attente d'un autre joueur...", True, (255, 255, 255))
        self.waiting_rect = self.waiting_text.get_rect(center=(400, 300))

    def play_music(self, music):
        if self.current_music != music:
            if self.current_music:
                self.current_music.stop()
            music.play(-1)  # -1 pour jouer en boucle
            self.current_music = music
            self.current_music.set_volume(self.music_volume if self.sound_enabled else 0)

    def play_sound_effect(self, sound):
        if self.sound_enabled:
            sound.set_volume(self.sfx_volume)
            sound.play()

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        # Mettre à jour le volume de la musique
        if self.current_music:
            self.current_music.set_volume(self.music_volume if self.sound_enabled else 0)
        # Mettre à jour le volume des effets sonores
        for sound in [self.splat, self.point]:
            sound.set_volume(self.sfx_volume if self.sound_enabled else 0)
            self.set_sfx_volume(self.sfx_volume)

    def set_volume(self, volume):
        self.music_volume = max(0.0, min(1.0, volume))
        if self.sound_enabled and self.current_music:
            self.current_music.set_volume(self.music_volume)

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0.0, min(1.0, volume))

        for sound in [self.splat, self.point]:
            sound.set_volume(self.sfx_volume)
        
        # Mettre à jour les boutons du menu
        if hasattr(self, 'menu'):
            self.menu.update_buttons_volume()
        
        # Mettre à jour le volume pour les boutons de plantes et zombies
        for _, btn in self.plant_buttons:
            btn.buttonClick.set_volume(self.sfx_volume if self.sound_enabled else 0)
        for _, btn in self.zombie_buttons:
            btn.buttonClick.set_volume(self.sfx_volume if self.sound_enabled else 0)

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

        # Ajouter le bouton pelle après les autres boutons
        shovel_btn = Button(x, y, 100, 40, "Pelle", (139, 69, 19))
        self.plant_buttons.append(('shovel', shovel_btn))

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

        # Dessiner les cellules de la grille
        # for row in range(GRID_HEIGHT):
        #     for col in range(GRID_WIDTH):
        #         x = self.grid_start_x + (col * self.cell_size)
        #         y = self.grid_start_y + (row * self.cell_size)
        #         # self.screen.blit(self.images['grid_cell'], (x, y))
        #         pygame.draw.rect(self.screen, (70, 140, 70), (x, y, self.cell_size, self.cell_size), 1)

        # Si nous avons un état de jeu, dessiner les entités
        if self.game_state:
            # Dessiner les plantes
            for plant in self.game_state.get('plants', []):
                x = self.grid_start_x + (plant['col'] * self.cell_size) + 5
                y = self.grid_start_y + (plant['row'] * self.cell_size) + 5

                # Utiliser l'image appropriée selon l'état du candycane
                if plant['type'] == 'candycane':
                    if plant.get('ready_to_harvest', False):
                        plant_image = self.images['candycane_ready']
                        glow_surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
                        pygame.draw.circle(glow_surface, (255, 215, 0, 128),
                                        (self.cell_size//2, self.cell_size//2), self.cell_size//2)
                        self.screen.blit(glow_surface, (x, y))
                    else:
                        plant_image = self.images['candycane']
                else:
                    plant_image = self.images.get(plant['type'], self.images['candycane'])

                self.screen.blit(plant_image, (x, y))

            # Dessiner les zombies
            current_time = time.time()
            alpha = min(1.0, (current_time - self.prev_update_time) * self.server_tick_rate)

            # Dessiner les zombies avec interpolation
            if self.prev_game_state:
                # Utiliser row et col comme identifiants de secours si pas d'ID
                prev_zombies = {(z.get('id', f"{z['row']}_{z['col']}"), z['row']): z
                            for z in self.prev_game_state.get('zombies', [])}
                current_zombies = {(z.get('id', f"{z['row']}_{z['col']}"), z['row']): z
                                for z in self.game_state.get('zombies', [])}

                for (z_id, row), zombie in current_zombies.items():
                    prev_zombie = prev_zombies.get((z_id, row))
                    if prev_zombie:
                        # Interpoler la position
                        prev_col = prev_zombie['col']
                        curr_col = zombie['col']
                        interp_col = prev_col + (curr_col - prev_col) * alpha

                        x = self.grid_start_x + (interp_col * self.cell_size) + 5
                        y = self.grid_start_y + ((zombie['row'] - 1) * self.cell_size) + 5
                        zombie_image = self.images[f'{zombie["type"]}']
                        self.screen.blit(zombie_image, (x, y))
                    else:
                        # Nouveau zombie, pas d'interpolation
                        x = self.grid_start_x + (zombie['col'] * self.cell_size) + 5
                        y = self.grid_start_y + (zombie['row'] * self.cell_size) + 5
                        zombie_image = self.images[f'{zombie["type"]}']
                        self.screen.blit(zombie_image, (x, y))
            else:
                # Si pas d'état précédent, dessiner sans interpolation
                for zombie in self.game_state.get('zombies', []):
                    x = self.grid_start_x + (zombie['col'] * self.cell_size) + 5
                    y = self.grid_start_y + (zombie['row'] * self.cell_size) + 5
                    zombie_image = self.images[f'{zombie["type"]}']
                    self.screen.blit(zombie_image, (x, y))

        # Dessiner les projectiles
        for proj in self.game_state.get('projectiles', []):
            x = self.grid_start_x + (proj['col'] * self.cell_size) + 25
            y = self.grid_start_y + (proj['row'] * self.cell_size) + 25
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
                sun_text = font.render(f"CandyCane: {self.game_state.get('sun_points', 0)}", True, (255, 255, 0))
                self.screen.blit(sun_text, (20, 20))

            # Dessiner les boutons de plantes
            self.create_plant_buttons()
            for plant_type, btn in self.plant_buttons:
                btn.draw(self.screen)
                if plant_type == self.selected_plant:
                    pygame.draw.rect(self.screen, (255, 255, 0), btn.rect, 3)

        # Dessiner le message de game over ou de victoire
        if self.game_state and self.game_state.get('game_over', False):
            font = pygame.font.Font(None, 74)
            if self.is_solo:
                text = font.render("GAME OVER", True, (255, 0, 0))
            else:
                if self.is_attacker:
                    text = font.render("VICTORY!", True, (0, 255, 0)) if self.game_state.get('winner') == 'att' else None
                else:
                    text = font.render("GAME OVER", True, (255, 0, 0)) if self.game_state.get('winner') == 'att' else None
            if text:
                text_rect = text.get_rect(center=(400, 300))
                self.screen.blit(text, text_rect)

    def draw_pause_menu(self):
        # Assombrir l'écran de jeu
        overlay = pygame.Surface((800, 600))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(150)
        self.screen.blit(overlay, (0, 0))

        # Dessiner le menu de pause
        font = pygame.font.Font(None, 50)
        pause_text = font.render("PAUSE", True, (0, 0, 0))
        resume_text = font.render("press ECHAP to resume", True, (0, 0, 0))
        quit_text = font.render("Q pour quitter", True, (0, 0, 0))

        pause_rect = pause_text.get_rect(center=(400, 200))
        resume_rect = resume_text.get_rect(center=(400, 300))
        quit_rect = quit_text.get_rect(center=(400, 400))

        self.screen.blit(pause_text, pause_rect)
        self.screen.blit(resume_text, resume_rect)
        self.screen.blit(quit_text, quit_rect)

        # Ajouter l'affichage des contrôles de volume
        font = pygame.font.Font(None, 36)
        music_text = font.render(f"Volume Musique: {int(self.music_volume * 100)}%", True, (255, 255, 255))
        sfx_text = font.render(f"Volume Effets: {int(self.sfx_volume * 100)}%", True, (255, 255, 255))

        # Dessiner les sliders
        pygame.draw.rect(self.screen, (100, 100, 100), self.menu.volume_slider_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), self.menu.sfx_volume_slider_rect)

        # Dessiner les positions actuelles des sliders
        music_pos = self.menu.volume_slider_rect.x + (self.menu.volume_slider_rect.width * self.music_volume)
        sfx_pos = self.menu.sfx_volume_slider_rect.x + (self.menu.sfx_volume_slider_rect.width * self.sfx_volume)
        pygame.draw.circle(self.screen, (255, 255, 255), (int(music_pos), self.menu.volume_slider_rect.centery), 10)
        pygame.draw.circle(self.screen, (255, 255, 255), (int(sfx_pos), self.menu.sfx_volume_slider_rect.centery), 10)

        self.screen.blit(music_text, (300, 225))
        self.screen.blit(sfx_text, (300, 325))

    def render(self):
        if self.in_game:
            self.screen.fill((0, 0, 0))
            if not self.is_solo and not self.online_game_started:
                # Afficher l'écran d'attente
                self.screen.blit(self.waiting_text, self.waiting_rect)
                # Ajouter une animation de points qui défilent
                dots = "." * (int(time.time() * 2) % 4)
                dots_text = self.waiting_font.render(dots, True, (255, 255, 255))
                dots_rect = dots_text.get_rect(midleft=self.waiting_rect.midright)
                self.screen.blit(dots_text, dots_rect)
            else:
                self.draw_game()
                if self.paused and self.is_solo:
                    self.draw_pause_menu()
            pygame.display.flip()
        else:
            self.menu.draw(self.screen)

    def reset_game_state(self):
        """Réinitialise l'état du jeu"""
        self.game_state = None
        self.game_instance = None
        self.is_attacker = False
        self.online_game_started = False
        self.plant_buttons = []
        self.zombie_buttons = []
        self.selected_plant = 'candycane'
        self.selected_zombie = 'basic'
        self.prev_game_state = None
        self.last_update = time.time()
        self.prev_update_time = time.time()

    def set_tcp_client(self, client):
        self.tcp_client = client

    def join_public_room(self):
        if self.tcp_client:
            self.tcp_client.join_room("public")
            self.in_game = True
            self.play_music(self.game_music)

    def join_private_room(self, code):
        if self.tcp_client and code:
            self.tcp_client.join_room(f"private_{code}")
            self.in_game = True
            self.play_music(self.game_music)

    def start_solo_mode(self):
        from shared.game import Game as ServerGame
        self.is_solo = True
        self.in_game = True
        self.state = 1
        self.game_instance = ServerGame(is_solo=True)
        self.game_state = self.game_instance.get_game_state()
        self.play_music(self.game_music)

    def start_online_mode(self):
        self.is_solo = False
        try:
            self.tcp_client = TCPClient('127.0.0.1', 12345, self)
            self.tcp_client.connect()
        except Exception as e:
            print(f"[CLIENT] Connection error: {e}")
            self.menu.current_menu = "main"

    def update(self):
        if self.paused:
            return  # Ne pas mettre à jour le jeu si en pause

        if self.game_state and self.game_state.get('game_over', False):
            # Si c'est la première fois qu'on détecte le game over
            if self.current_music != self.lose_music:
                self.play_music(self.lose_music)
            return

        current_time = time.time()
        delta_time = current_time - self.last_update

        if self.is_solo and self.game_instance:
            self.prev_game_state = self.game_state
            self.prev_update_time = current_time
            self.game_instance.update(1/60, current_time)

            if hasattr(self.game_instance, 'last_hit') and self.game_instance.last_hit:
                self.play_sound_effect(self.splat)
                self.game_instance.last_hit = False
            
            self.game_state = self.game_instance.get_game_state()
            
        elif self.online_game_started and self.game_instance:
            if delta_time >= 1.0/self.server_tick_rate:
                self.prev_game_state = self.game_state
                self.prev_update_time = current_time
                self.game_instance.update(delta_time)
                # Vérifier si un zombie a été touché
                if hasattr(self.game_instance, 'last_hit') and self.game_instance.last_hit:
                    self.play_sound_effect(self.splat)
                    self.game_instance.last_hit = False
                
                self.game_state = self.game_instance.get_game_state()
                self.last_update = current_time
            else:
                time.sleep(0.001)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False

            if event.type == pygame.KEYDOWN:
                # Gérer le retour au menu quand le jeu est terminé
                if event.key == pygame.K_ESCAPE and self.game_state and self.game_state.get('game_over', False):
                    self.in_game = False
                    self.menu.current_menu = "main"
                    self.reset_game_state()  # Réinitialiser l'état du jeu
                    self.play_music(self.menu_music)  # Remettre la musique du menu
                    return True

                # Gérer la pause en mode solo
                if self.is_solo and self.in_game:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state and self.game_state.get('game_over', False):
                            self.in_game = False
                            self.menu.current_menu = "main"
                            self.reset_game_state()
                            self.play_music(self.menu_music)  # Ne pas oublier de remettre la musique du menu
                            return True
                        else:
                            self.paused = not self.paused
                    elif event.key == pygame.K_q and self.paused:
                        self.in_game = False
                        self.menu.current_menu = "main"
                        self.reset_game_state()
                        self.play_music(self.menu_music)
                        self.paused = False
                        return True

            # Si le jeu est terminé, permettre de retourner au menu avec ÉCHAP
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.game_state and self.game_state.get('game_over', False):
                    self.in_game = False
                    self.state = 1
                    self.game_state = None
                    self.menu.current_menu = "main"
                    self.play_music(self.menu_music)
                    return True

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
                        col = (mouse_pos[0] - self.grid_start_x) // self.cell_size
                        row = (mouse_pos[1] - self.grid_start_y) // self.cell_size

                        if (0 <= row < GRID_HEIGHT and col == GRID_WIDTH - 1):  # Spawn uniquement sur la dernière colonne
                            if (0 <= row < GRID_HEIGHT and col == GRID_WIDTH - 1):  # Spawn uniquement sur la dernière colonne
                                if self.online_game_started and self.tcp_client.udp_client:
                                    message = f"ADD_ZOMBIE:{self.selected_zombie}:{row}"
                                    self.tcp_client.udp_client.send_message(message)
                else:
                    # Gestion défenseur
                    button_clicked = False

                    col = (mouse_pos[0] - self.grid_start_x) // self.cell_size
                    row = (mouse_pos[1] - self.grid_start_y) // self.cell_size

                    # Vérifier si on clique sur une plante existante
                    if (0 <= row < GRID_HEIGHT and 0 <= col < GRID_WIDTH):
                        for plant in self.game_state.get('plants', []):
                            if (plant['row'] == row and plant['col'] == col and 
                                plant['type'] == 'candycane' and 
                                plant.get('ready_to_harvest', False)):

                                if self.is_solo:
                                    # Mode solo
                                    sun_points = self.game_instance.plants[
                                        next(i for i, p in enumerate(self.game_instance.plants) 
                                            if p.row == row and p.col == col)
                                    ].harvest()
                                    if sun_points > 0:  # Si la récolte a réussi
                                        self.play_sound_effect(self.point)  # Jouer le son
                                    self.game_instance.sun_points += sun_points
                                    self.game_state = self.game_instance.get_game_state()
                                elif self.online_game_started and self.tcp_client.udp_client:
                                    # Mode online
                                    message = f"HARVEST_SUNFLOWER:{row}:{col}"
                                    self.tcp_client.udp_client.send_message(message)
                                return True
                    for plant_type, btn in self.plant_buttons:
                        if btn.is_clicked(mouse_pos):
                            self.selected_plant = plant_type
                            button_clicked = True
                            break

                    if not button_clicked:
                        col = (mouse_pos[0] - self.grid_start_x) // self.cell_size
                        row = (mouse_pos[1] - self.grid_start_y) // self.cell_size

                        if (0 <= row < GRID_HEIGHT and 0 <= col < GRID_WIDTH):
                            if self.selected_plant == 'shovel':
                                if self.is_solo:
                                    if self.game_instance.remove_plant(row, col):
                                        self.game_state = self.game_instance.get_game_state()
                                elif self.online_game_started and self.tcp_client.udp_client:
                                    message = f"REMOVE_PLANT:{row}:{col}"
                                    self.tcp_client.udp_client.send_message(message)
                            else:
                                # Code existant pour placer une plante
                                if self.is_solo:
                                    plant_placed = self.game_instance.add_plant(self.selected_plant, row, col)
                                    if plant_placed:
                                        self.game_state = self.game_instance.get_game_state()
                                elif self.online_game_started and self.tcp_client.udp_client:
                                    message = f"ADD_PLANT:{self.selected_plant}:{row}:{col}"
                                    self.tcp_client.udp_client.send_message(message)

        return True

    def cleanup(self):
        if self.current_music:
            self.current_music.stop()
        pygame.mixer.quit()
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
        if self.game:
            self.game.reset_game_state()  # Réinitialiser l'état du jeu à la déconnexion

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
                elif decoded_message.startswith("REMOVE_PLANT:"):
                    print(f"[UDP] Plant removed: {decoded_message}")
                    _, row, col = decoded_message.split(":")
                    # Appliquer l'action à l'instance locale du jeu
                    self.game.game_instance.remove_plant(int(row), int(col))
                    # Mettre à jour l'état du jeu
                    self.game.game_state = self.game_instance.get_game_state()
                elif decoded_message.startswith("REMOVE_PLANT:"):
                    print(f"[UDP] Plant removed: {decoded_message}")
                    _, row, col = decoded_message.split(":")
                    self.game.game_instance.remove_plant(int(row), int(col))
                    self.game.game_state = self.game_instance.get_game_state()
                elif decoded_message.startswith("HARVEST_SUNFLOWER:"):
                    print(f"[UDP] Sunflower harvested: {decoded_message}")
                    _, row, col = decoded_message.split(":")
                    sun_points = self.game.game_instance.plants[
                        next(i for i, p in enumerate(self.game.game_instance.plants) 
                            if p.row == int(row) and p.col == int(col))
                    ].harvest()
                    if sun_points > 0:
                        self.game.play_sound_effect(self.game.point)  # Jouer le son
                    self.game.game_instance.sun_points += sun_points
                    self.game.game_state = self.game.game_instance.get_game_state()
                elif decoded_message.startswith("SYSTEM:"):
                    print(f"[SYSTEM] {decoded_message.split(':', 1)[1]}")
            except Exception as e:
                if self.running:
                    print(f"[UDP] Receive error: {e}")

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
        game.play_music(game.menu_music)  # Démarrer la musique du menu
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
