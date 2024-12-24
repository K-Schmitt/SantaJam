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

def resource_path(relative_path):
    """Obtenir le chemin absolu pour accéder aux ressources."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class Button:
    def __init__(self, x, y, width, height, text, color=(100, 100, 100)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.font = pygame.font.Font(None, 36)
        self.candy_cane_offset = 0
        self.segment_length = 10
        self.buttonClick = pygame.mixer.Sound(resource_path(os.path.join('client', 'soundEffect', 'buttonclick.ogg')))
        self.buttonClick.set_volume(0.35)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        rect_points = [
            (self.rect.left, self.rect.top),
            (self.rect.right, self.rect.top),
            (self.rect.right, self.rect.bottom),
            (self.rect.left, self.rect.bottom)
        ]

        for i in range(4):
            start_pos = rect_points[i]
            end_pos = rect_points[(i + 1) % 4]
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

                color = (255, 0, 0) if (j + self.candy_cane_offset) % 2 >= 1 else (255, 255, 255)
                pygame.draw.line(screen, color, seg_start, seg_end, 3)

        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

        self.candy_cane_offset = (self.candy_cane_offset + 0.05) % 2

    def is_clicked(self, pos):
        if self.rect.collidepoint(pos):
            self.buttonClick.play()
            return True
        return False

class Card:
    def __init__(self, x, y, entity_type, entity_group, cost):
        self.rect = pygame.Rect(x, y, 85, 100)
        self.entity_type = entity_type
        self.entity_group = entity_group
        self.cost = cost
        self.sprite_rect = pygame.Rect(0, 0, 100, 100)
        self.buttonClick = pygame.mixer.Sound(resource_path(os.path.join('client', 'soundEffect', 'buttonclick.ogg')))
        self.buttonClick.set_volume(0.35)

    def draw(self, screen, cards_image, is_selected, can_afford):
        if self.entity_group == 'plant':
            sprite_y = 0
            if self.entity_type == 'candycane':
                sprite_x = 0
            elif self.entity_type == 'peashooter':
                sprite_x = 100
            elif self.entity_type == 'icewall':
                sprite_x = 200
            else:
                sprite_x = 300
        else:
            sprite_y = 100
            if self.entity_type == 'basic':
                sprite_x = 0
            elif self.entity_type == 'cone':
                sprite_x = 100
            elif self.entity_type == 'bucket':
                sprite_x = 200
            else:
                sprite_x = 300

        self.sprite_rect = pygame.Rect(sprite_x, sprite_y, 100, 100)
        scaled_surface = pygame.Surface((80, 100), pygame.SRCALPHA)
        temp_surface = pygame.Surface((100, 100), pygame.SRCALPHA)
        temp_surface.blit(cards_image, (0, 0), self.sprite_rect)
        scaled_surface = pygame.transform.scale(temp_surface, (85, 100))
        screen.blit(scaled_surface, self.rect)

        if is_selected:
            color = (255, 255, 0) if self.entity_group == 'plant' else (255, 0, 0)
            pygame.draw.rect(screen, color, self.rect, 3)

        if not can_afford:
            overlay = pygame.Surface((100, 100))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(128)
            screen.blit(overlay, self.rect)

        font = pygame.font.Font(None, 36)
        cost_text = font.render(str(self.cost), True, (255, 255, 255))
        cost_rect = cost_text.get_rect(center=(self.rect.centerx, self.rect.bottom - 20))
        screen.blit(cost_text, cost_rect)

    def is_clicked(self, pos):
        if self.rect.collidepoint(pos):
            if hasattr(self, 'buttonClick'):
                self.buttonClick.play()
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
        self.volume_slider_rect2 = pygame.Rect(300, 250, 200, 20)
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
            self.quit_button,
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
        self.play_button = Button(300, 200, 200, 50, "Jouer")
        self.options_button = Button(300, 300, 200, 50, "Options")
        self.quit_button = Button(300, 400, 200, 50, "Quitter")

        self.solo_button = Button(300, 200, 200, 50, "Solo")
        self.online_button = Button(300, 300, 200, 50, "Online")

        self.public_button = Button(300, 200, 200, 50, "Public")
        self.private_button = Button(300, 300, 200, 50, "Privé")
        self.back_button = Button(300, 400, 200, 50, "Retour")

        self.join_button = Button(300, 350, 200, 50, "Rejoindre")

        self.resume_button = Button(300, 200, 200, 50, "Reprendre")
        self.pause_options_button = Button(300, 300, 200, 50, "Options")
        self.quit_to_menu_button = Button(300, 400, 200, 50, "Quitter")

        self.sound_toggle_button = Button(300, 200, 200, 50, "Son: Activé")
        self.back_to_main_button = Button(300, 400, 200, 50, "Retour")
        self.sfx_volume_slider_rect = pygame.Rect(300, 350, 200, 20)

        self.update_buttons_volume()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            if self.current_menu == "main":
                if self.play_button.is_clicked(mouse_pos):
                    self.current_menu = "mode_selection"
                elif self.options_button.is_clicked(mouse_pos):
                    self.current_menu = "options"
                elif self.quit_button.is_clicked(mouse_pos):
                    self.game.running = False
                    return False

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
            if event.button == 1:
                if self.current_menu == "options" and self.volume_slider_rect.collidepoint(event.pos):
                    rel_x = (event.pos[0] - self.volume_slider_rect.x) / self.volume_slider_rect.width
                    self.game.set_volume(rel_x)
                elif self.game.paused and self.volume_slider_rect2.collidepoint(event.pos):
                    rel_x = (event.pos[0] - self.volume_slider_rect2.x) / self.volume_slider_rect2.width
                    self.game.set_volume(rel_x)
                elif self.current_menu == "options" and self.sfx_volume_slider_rect.collidepoint(event.pos):
                    rel_x = (event.pos[0] - self.sfx_volume_slider_rect.x) / self.sfx_volume_slider_rect.width
                    self.game.set_sfx_volume(rel_x)

        elif event.type == pygame.MOUSEMOTION:
            if event.buttons[0]:
                if self.current_menu == "options" and self.volume_slider_rect.collidepoint(event.pos):
                    rel_x = (event.pos[0] - self.volume_slider_rect.x) / self.volume_slider_rect.width
                    self.game.set_volume(rel_x)
                elif self.game.paused and self.volume_slider_rect2.collidepoint(event.pos):
                    rel_x = (event.pos[0] - self.volume_slider_rect2.x) / self.volume_slider_rect2.width
                    self.game.set_volume(rel_x)
                elif (self.current_menu == "options" or self.game.paused) and self.sfx_volume_slider_rect.collidepoint(event.pos):
                    rel_x = (event.pos[0] - self.sfx_volume_slider_rect.x) / self.sfx_volume_slider_rect.width
                    self.game.set_sfx_volume(rel_x)

    def draw(self, screen):
        screen.fill((42, 21, 174))

        for snowflake in self.snowflakes:
            snowflake.update()
            snowflake.draw(screen)

        if self.current_menu == "main":
            self.play_button.draw(screen)
            self.options_button.draw(screen)
            self.quit_button.draw(screen)

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

            pygame.draw.rect(screen, (100, 100, 100), self.volume_slider_rect)
            volume_pos = self.volume_slider_rect.x + (self.volume_slider_rect.width * self.game.music_volume)
            pygame.draw.circle(screen, (255, 255, 255), (int(volume_pos), self.volume_slider_rect.centery), 10)

            pygame.draw.rect(screen, (100, 100, 100), self.sfx_volume_slider_rect)
            sfx_pos = self.sfx_volume_slider_rect.x + (self.sfx_volume_slider_rect.width * self.game.sfx_volume)
            pygame.draw.circle(screen, (255, 255, 255), (int(sfx_pos), self.sfx_volume_slider_rect.centery), 10)

            font = pygame.font.Font(None, 36)
            volume_text = font.render(f"Volume: {int(self.game.music_volume * 100)}%", True, (255, 255, 255))
            screen.blit(volume_text, (300, 300))

            volume_text = font.render(f"Effets: {int(self.game.sfx_volume * 100)}%", True, (255, 255, 255))
            screen.blit(volume_text, (300, 375))

        pygame.display.flip()

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Christmas Defense")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 1
        self.sound_enabled = True
        self.music_volume = 0.3
        self.sfx_volume = 0.35
        self.menu = Menu(self)
        self.in_game = False
        self.tcp_client = None
        self.is_solo = False
        self.game_state = None
        self.game_instance = None
        self.last_zombie_spawn = 0
        self.selected_plant = 'candycane'
        self.plant_buttons = []
        self.sun_points = 0
        self.online_game_started = False
        self.last_update = time.time()
        self.server_tick_rate = 20
        self.is_attacker = False
        self.selected_zombie = 'basic'
        self.zombie_buttons = []
        self.prev_game_state = None
        self.prev_update_time = time.time()
        self.paused = False
        self.pause_start_time = 0
        self.total_pause_time = 0
        self.game_start_time = 0

        self.images = {
            'background': pygame.Surface((800, 600)),
            'grid_cell': pygame.Surface((80, 80)),
        }

        self.images['background'] = pygame.image.load(resource_path(os.path.join('client', 'assets', 'background.png')))
        self.images['grid_cell'].fill((80, 140, 80))
        self.images['sprinter'] = pygame.transform.scale(pygame.image.load(resource_path(os.path.join('client', 'assets', 'sprinter.png'))), (80, 140))
        self.selected_plant = 'candycane'
        self.plant_buttons = []

        candycane_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'candycane.png')))
        self.images['candycane'] = pygame.Surface((80, 80), pygame.SRCALPHA)
        self.images['candycane_ready'] = pygame.Surface((80, 80), pygame.SRCALPHA)
        self.images['candycane'].blit(candycane_sprite, (0, 0), (0, 0, 80, 80))
        self.images['candycane'] = pygame.transform.scale(self.images['candycane'], (100, 100))
        self.images['candycane_ready'].blit(candycane_sprite, (0, 0), (80, 0, 160, 80))
        self.images['candycane_ready'] = pygame.transform.scale(self.images['candycane_ready'], (100, 100))

        icewall_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'icewall.png')))
        self.images['icewall'] = {}
        self.images['icewall_hit'] = {}
        self.icewall_states = {}

        for health_state in range(3):
            self.images['icewall'][health_state] = pygame.Surface((80, 120), pygame.SRCALPHA)
            self.images['icewall'][health_state].blit(icewall_sprite, (0, 0), (0, health_state * 120, 80, 120))
            self.images['icewall'][health_state] = pygame.transform.scale(self.images['icewall'][health_state], (120, 120))

            self.images['icewall_hit'][health_state] = pygame.Surface((80, 120), pygame.SRCALPHA)
            self.images['icewall_hit'][health_state].blit(icewall_sprite, (0, 0), (80, health_state * 120, 160, 120))
            self.images['icewall_hit'][health_state] = pygame.transform.scale(self.images['icewall_hit'][health_state], (120, 120))

        self.images['pea'] = pygame.transform.scale(pygame.image.load(resource_path(os.path.join('client', 'assets', 'snowball.png'))), (30, 30))
        self.images['energy_icon'] = pygame.Surface((30, 30))
        self.images['energy_icon'].fill((255, 0, 0))

        self.images['shovel'] = pygame.Surface((60, 60))
        self.images['shovel'].fill((139, 69, 19))

        self.menu_music = pygame.mixer.Sound(resource_path(os.path.join('client', 'music', 'Crazy_Dave.mp3')))
        self.game_music = pygame.mixer.Sound(resource_path(os.path.join('client', 'music', 'Loonboon.mp3')))
        self.lose_music = pygame.mixer.Sound(resource_path(os.path.join('client', 'music', 'losemusic.ogg')))
        self.current_music = None

        self.menu_music.set_volume(self.music_volume if self.sound_enabled else 0)
        self.game_music.set_volume(self.music_volume if self.sound_enabled else 0)
        self.lose_music.set_volume(self.music_volume if self.sound_enabled else 0)

        self.splat = pygame.mixer.Sound(resource_path(os.path.join('client', 'soundEffect', 'splat.ogg')))
        self.point = pygame.mixer.Sound(resource_path(os.path.join('client', 'soundEffect', 'points.ogg')))

        self.splat.set_volume(self.sfx_volume if self.sound_enabled else 0)
        self.point.set_volume(self.sfx_volume if self.sound_enabled else 0)

        self.grid_start_x = 41
        self.grid_start_y = 179
        self.cell_size = 80

        self.waiting_font = pygame.font.Font(None, 74)
        self.waiting_text = self.waiting_font.render("En attente d'un autre joueur...", True, (255, 255, 255))
        self.waiting_rect = self.waiting_text.get_rect(center=(400, 300))

        self.zombie_animations = {}
        self.animation_speed = 0.2

        self.ICEWALL_HIT_DURATION = 0.3
        self.ICEWALL_HIT_COOLDOWN = 1.0

        peashooter_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'shooter.png')))
        self.images['peashooter'] = []
        for i in range(5):
            frame = pygame.Surface((80, 80), pygame.SRCALPHA)
            frame.blit(peashooter_sprite, (0, 0), (i * 80, 0, 80, 80))
            frame = pygame.transform.scale(frame, (120, 120))
            self.images['peashooter'].append(frame)

        self.peashooter_states = {}

        self.cards_image = pygame.image.load(resource_path(os.path.join('client', 'assets', 'cartes.png')))
        self.plant_cards = []
        self.zombie_cards = []

        self.basic_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'basic.png')))
        self.cone_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'cone.png')))
        self.bucket_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'krampus.png')))

        self.basic_attack_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'basic_att.png')))
        self.cone_attack_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'cone_att.png')))
        self.bucket_attack_sprite = pygame.image.load(resource_path(os.path.join('client', 'assets', 'krampus_att.png')))

        self.zombie_attack_states = {}

        self.images['basic'] = []
        self.images['cone'] = []
        self.images['bucket'] = []

        for i in range(4):
            frame = pygame.Surface((80, 80), pygame.SRCALPHA)
            frame.blit(self.basic_sprite, (0, 0), (i * 80, 0, 80, 80))
            frame = pygame.transform.scale(frame, (120, 140))
            self.images['basic'].append(frame)

        for i in range(3):
            frame = pygame.Surface((80, 80), pygame.SRCALPHA)
            frame.blit(self.cone_sprite, (0, 0), (i * 80, 0, 80, 80))
            frame = pygame.transform.scale(frame, (130, 140))
            self.images['cone'].append(frame)

            frame = pygame.Surface((80, 140), pygame.SRCALPHA)
            frame.blit(self.bucket_sprite, (0, 0), (i * 80, 0, 80, 140))
            frame = pygame.transform.scale(frame, (130, 130))
            self.images['bucket'].append(frame)

        self.pause_button = Button(700, 20, 80, 40, "||")

        self.replay_button = Button(200, 400, 200, 50, "Rejouer")
        self.end_quit_button = Button(450, 400, 200, 50, "Quitter")

        self.interface_cards = pygame.image.load(resource_path(os.path.join('client', 'assets', 'card.png')))
        self.interface_cards = pygame.transform.scale(self.interface_cards, (160, 140))

    def play_music(self, music):
        if self.current_music != music:
            if self.current_music:
                self.current_music.stop()
            music.play(-1)
            self.current_music = music
            self.current_music.set_volume(self.music_volume if self.sound_enabled else 0)

    def play_sound_effect(self, sound):
        if self.sound_enabled:
            sound.set_volume(self.sfx_volume)
            sound.play()

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        if self.current_music:
            self.current_music.set_volume(self.music_volume if self.sound_enabled else 0)
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
            sound.set_volume(self.sfx_volume if self.sound_enabled else 0)

        if hasattr(self, 'menu'):
            self.menu.update_buttons_volume()

        if hasattr(self, 'plant_cards'):
            for _, card in self.plant_cards:
                if hasattr(card, 'buttonClick'):
                    card.buttonClick.set_volume(self.sfx_volume if self.sound_enabled else 0)

        if hasattr(self, 'zombie_cards'):
            for _, card in self.zombie_cards:
                if hasattr(card, 'buttonClick'):
                    card.buttonClick.set_volume(self.sfx_volume if self.sound_enabled else 0)

    def create_plant_buttons(self):
        self.plant_cards = []
        x, y = 50, 35
        current_sun = self.game_state.get('sun_points', 0) if self.game_state else 0

        for plant_type in self.game_state.get('available_plants', []):
            cost = PLANT_TYPES[plant_type]['cost']
            card = Card(x, y, plant_type, 'plant', cost)
            card.buttonClick.set_volume(self.sfx_volume if self.sound_enabled else 0)
            self.plant_cards.append((plant_type, card))
            x += 85

        shovel_card = Card(x, y, 'shovel', 'plant', 0)
        shovel_card.buttonClick.set_volume(self.sfx_volume if self.sound_enabled else 0)
        self.plant_cards.append(('shovel', shovel_card))

    def create_zombie_buttons(self):
        self.zombie_cards = []
        x, y = 50, 35
        current_energy = self.game_state.get('energy', 0) if self.game_state else 0

        for zombie_type, stats in ZOMBIE_TYPES.items():
            cost = stats.get('cost', 50)
            card = Card(x, y, zombie_type, 'zombie', cost)
            card.buttonClick.set_volume(self.sfx_volume if self.sound_enabled else 0)
            self.zombie_cards.append((zombie_type, card))
            x += 85

        dead_card = Card(x, y, 'dead', 'zombie', 0)
        dead_card.buttonClick.set_volume(self.sfx_volume if self.sound_enabled else 0)
        self.zombie_cards.append(('dead', dead_card))

    def draw_game(self):
        self.screen.blit(self.images['background'], (0, 0))

        font = pygame.font.Font(None, 36)

        plant_energy_card = pygame.Surface((160, 47), pygame.SRCALPHA)
        plant_energy_card.blit(self.interface_cards, (0, 0), (0, 0, 160, 47))
        plant_energy_card = pygame.transform.scale(plant_energy_card, (170, 47))
        self.screen.blit(plant_energy_card, (410, 35))

        if not self.is_attacker:
            sun_points = self.game_state.get('sun_points', 0) if self.game_state else 0
            sun_text = font.render(f"{sun_points}", True, (255, 255, 255))
            self.screen.blit(sun_text, (510, 47))

        time_card = pygame.Surface((160, 47), pygame.SRCALPHA)
        time_card.blit(self.interface_cards, (0, 0), (0, 47, 160, 94))
        time_card = pygame.transform.scale(time_card, (170, 47))
        self.screen.blit(time_card, (410, 85))

        if self.game_state and self.game_state.get('game_over', False):
            elapsed_time = max(0, int(self.game_state.get('end_time', time.time() - self.game_start_time)))
        else:
            current_time = time.time()
            pause_duration = self.total_pause_time
            if self.paused:
                pause_duration += (current_time - self.pause_start_time)
            elapsed_time = max(0, int(current_time - self.game_start_time - pause_duration))

        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        time_text = font.render(f"{minutes:02d}:{seconds:02d}", True, (255, 255, 255))
        self.screen.blit(time_text, (495, 97))

        if self.is_attacker:
            zombie_energy_card = pygame.Surface((160, 47), pygame.SRCALPHA)
            zombie_energy_card.blit(self.interface_cards, (0, 0), (0, 94, 160, 140))
            zombie_energy_card = pygame.transform.scale(zombie_energy_card, (170, 47))
            self.screen.blit(zombie_energy_card, (410, 35))

            zombie_energy = self.game_state.get('energy', 0) if self.game_state else 0
            energy_text = font.render(f"{zombie_energy}", True, (255, 255, 255))
            self.screen.blit(energy_text, (510, 47))

        self.draw_buttons()

        if self.game_state:
            self.draw_plants()
            self.draw_projectiles()
            self.draw_zombies()

        self.draw_end_game_message()

        if self.is_solo:
            self.pause_button.draw(self.screen)

    def draw_plants(self):
        """Dessine les plantes sur la grille."""
        for plant in self.game_state.get('plants', []):
            x = self.grid_start_x + (plant['col'] * self.cell_size) - 15
            y = self.grid_start_y + (plant['row'] * self.cell_size) - 15


            if plant['type'] == 'candycane':
                plant_image = self.images['candycane_ready'] if plant.get('ready_to_harvest', False) else self.images['candycane']
                if plant.get('ready_to_harvest', False):
                    self.draw_glow(x, y)
            elif plant['type'] == 'icewall':
                plant_image = self.get_icewall_image(plant)
                y -= 20
                x -= 5
            elif plant['type'] == 'peashooter':
                plant_image = self.get_peashooter_image(plant)
            else:
                continue
            self.screen.blit(plant_image, (x, y))

    def draw_zombies(self):
        """Dessine les zombies avec interpolation."""
        current_time = time.time()
        alpha = min(1.0, (current_time - self.prev_update_time) * self.server_tick_rate)

        if self.prev_game_state:
            prev_zombies = {(z.get('id', f"{z['row']}_{z['col']}"), z['row']): z for z in self.prev_game_state.get('zombies', [])}
            current_zombies = {(z.get('id', f"{z['row']}_{z['col']}"), z['row']): z for z in self.game_state.get('zombies', [])}

            for (z_id, row), zombie in current_zombies.items():
                prev_zombie = prev_zombies.get((z_id, row))
                if prev_zombie:
                    x, y = self.interpolate_zombie_position(prev_zombie, zombie, alpha)
                    if prev_zombie['type'] == 'cone':
                        y -= 20
                    elif prev_zombie['type'] == 'bucket':
                        y -= 20
                else:
                    x = self.grid_start_x + (zombie['col'] * self.cell_size) + 5
                    y = self.grid_start_y + ((zombie['row'] - 1) * self.cell_size)

                zombie_image = self.get_zombie_image(zombie, z_id)
                self.screen.blit(zombie_image, (x, y))
        else:
            for zombie in self.game_state.get('zombies', []):
                x = self.grid_start_x + (zombie['col'] * self.cell_size) + 5
                y = self.grid_start_y + ((zombie['row'] - 1) * self.cell_size)
                zombie_image = self.get_zombie_image(zombie)
                self.screen.blit(zombie_image, (x, y))

    def draw_projectiles(self):
        """Dessine les projectiles."""
        for proj in self.game_state.get('projectiles', []):
            x = self.grid_start_x + (proj['col'] * self.cell_size) + 55
            y = self.grid_start_y + (proj['row'] * self.cell_size) + 25
            self.screen.blit(self.images['pea'], (x, y))

    def draw_buttons(self):
        """Dessine les cartes pour l'attaquant ou le défenseur."""
        if self.is_attacker:
            self.create_zombie_buttons()
            current_energy = self.game_state.get('energy', 0) if self.game_state else 0
            for zombie_type, card in self.zombie_cards:
                cost = 0 if zombie_type == 'dead' else ZOMBIE_TYPES[zombie_type]['cost']
                card.draw(self.screen, self.cards_image,
                        zombie_type == self.selected_zombie,
                        current_energy >= cost)
        else:
            self.create_plant_buttons()
            current_sun = self.game_state.get('sun_points', 0) if self.game_state else 0
            for plant_type, card in self.plant_cards:
                cost = 0 if plant_type == 'shovel' else PLANT_TYPES[plant_type]['cost']
                card.draw(self.screen, self.cards_image,
                        plant_type == self.selected_plant,
                        current_sun >= cost)

    def draw_end_game_message(self):
        """Dessine le message de fin de jeu si nécessaire."""
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
                overlay = pygame.Surface((800, 600))
                overlay.fill((0, 0, 0))
                overlay.set_alpha(128)
                self.screen.blit(overlay, (0, 0))

                text_rect = text.get_rect(center=(400, 300))
                self.screen.blit(text, text_rect)

                self.replay_button.draw(self.screen)
                self.end_quit_button.draw(self.screen)

    def draw_glow(self, x, y):
        """Dessine un effet de lueur autour d'une plante prête à être récoltée."""
        glow_surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (255, 215, 0, 128), (self.cell_size // 2, self.cell_size // 2), self.cell_size // 2)
        self.screen.blit(glow_surface, (x + 15, y + 15))


    def get_icewall_image(self, plant):
        """Renvoie l'image appropriée pour une IceWall, avec animation and état de santé."""
        current_time = time.time()
        plant_key = (plant['row'], plant['col'])

        if plant_key not in self.icewall_states:
            self.icewall_states[plant_key] = {
                'hit_time': 0,
                'last_hit': 0,
                'is_being_eaten': False
            }

        state = self.icewall_states[plant_key]

        health_ratio = plant.get('health', 100) / PLANT_TYPES['icewall']['health']
        if health_ratio > 0.66:
            health_state = 0
        elif health_ratio > 0.33:
            health_state = 1
        else:
            health_state = 2

        is_being_eaten = any(
            zombie['row'] == plant['row'] and abs(zombie['col'] - plant['col']) <= 1
            for zombie in self.game_state.get('zombies', [])
        )

        if not self.paused and not self.game_state.get('game_over', False):
            if is_being_eaten and (current_time - state['last_hit'] > self.ICEWALL_HIT_COOLDOWN):
                state['hit_time'] = current_time
                state['last_hit'] = current_time
                return self.images['icewall_hit'][health_state]
            elif current_time - state['hit_time'] < self.ICEWALL_HIT_DURATION:
                return self.images['icewall_hit'][health_state]

        return self.images['icewall'][health_state]


    def get_peashooter_image(self, plant):
        """Renvoie l'image animée d'un Peashooter selon son état."""
        plant_key = (plant['row'], plant['col'])
        current_time = time.time()

        if not isinstance(self.images['peashooter'], list):
            return self.images['peashooter']

        if plant_key not in self.peashooter_states:
            self.peashooter_states[plant_key] = {
                'shooting': False,
                'frame': 0,
                'last_update': current_time
            }

        state = self.peashooter_states[plant_key]
        is_shooting = plant.get('shooting', False)

        if not self.paused and not self.game_state.get('game_over', False):
            if is_shooting and not state['shooting']:
                state['shooting'] = True
                state['frame'] = 0
                state['last_update'] = current_time
            elif state['shooting']:
                if current_time - state['last_update'] > 0.1:
                    state['frame'] = (state['frame'] + 1) % len(self.images['peashooter'])
                    state['last_update'] = current_time
                    if state['frame'] == 0:
                        state['shooting'] = False

        if not state['shooting']:
            return self.images['peashooter'][0]

        return self.images['peashooter'][state['frame']]


    def get_zombie_image(self, zombie, z_id=None):
        """Renvoie l'image appropriée pour un zombie, avec gestion de l'animation and de la santé."""
        if z_id and z_id not in self.zombie_animations:
            self.zombie_animations[z_id] = {'frame': 0, 'timer': time.time()}
            self.zombie_attack_states[z_id] = {'attacking': False, 'frame': 0, 'last_update': time.time()}

        anim = self.zombie_animations.get(z_id, {'frame': 0, 'timer': time.time()})
        attack_state = self.zombie_attack_states.get(z_id, {'attacking': False, 'frame': 0, 'last_update': time.time()})

        is_attacking = False
        if not self.paused and not self.game_state.get('game_over', False):
            if zombie['is_eating']:
                is_attacking = True

        attack_state['attacking'] = is_attacking

        current_time = time.time()
        if not self.paused and not self.game_state.get('game_over', False):
            if is_attacking:
                if current_time - attack_state['last_update'] > self.animation_speed:
                    attack_state['frame'] = (attack_state['frame'] + 1) % 3
                    attack_state['last_update'] = current_time
            else:
                if current_time - anim['timer'] > self.animation_speed:
                    anim['frame'] = (anim['frame'] + 1) % len(self.images[zombie['type']])
                    anim['timer'] = current_time


        health_ratio = zombie.get('health', 100) / ZOMBIE_TYPES[zombie['type']]['health']
        if health_ratio > 0.66:
            sprite_y = 0
        elif health_ratio > 0.33:
            sprite_y = 80
        else:
            sprite_y = 160

        frame = pygame.Surface((80, 80), pygame.SRCALPHA)

        if is_attacking:
            if zombie['type'] == 'basic':
                frame.blit(self.basic_attack_sprite, (0, 0), (attack_state['frame'] * 80, sprite_y, 80, 80))
                frame = pygame.transform.scale(frame, (130, 130))
            elif zombie['type'] == 'cone':
                frame.blit(self.cone_attack_sprite, (0, 0), (attack_state['frame'] * 80, sprite_y, 80, 80))
                frame = pygame.transform.scale(frame, (130, 140))
            elif zombie['type'] == 'bucket':
                frame.blit(self.bucket_attack_sprite, (0, 0), (attack_state['frame'] * 80, sprite_y, 80, 140))
                frame = pygame.transform.scale(frame, (130, 130))
        else:
            if zombie['type'] == 'basic':
                frame.blit(self.basic_sprite, (0, 0), (anim['frame'] * 80, sprite_y, 80, 80))
                frame = pygame.transform.scale(frame, (130, 130))
            elif zombie['type'] == 'cone':
                frame.blit(self.cone_sprite, (0, 0), (anim['frame'] * 80, sprite_y, 80, 80))
                frame = pygame.transform.scale(frame, (130, 140))
            elif zombie['type'] == 'bucket':
                frame.blit(self.bucket_sprite, (0, 0), (anim['frame'] * 80, sprite_y, 80, 140))
                frame = pygame.transform.scale(frame, (130, 140))

        return frame


    def interpolate_zombie_position(self, prev_zombie, curr_zombie, alpha):
        """Interpole la position d'un zombie entre son état précédent and actuel."""
        prev_col = prev_zombie['col']
        curr_col = curr_zombie['col']
        interp_col = prev_col + (curr_col - prev_col) * alpha

        x = self.grid_start_x + (interp_col * self.cell_size) + 5
        y = self.grid_start_y + ((curr_zombie['row']) * self.cell_size) - 50
        return x, y


    def draw_pause_menu(self):
        overlay = pygame.Surface((800, 600))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(150)
        self.screen.blit(overlay, (0, 0))

        if not hasattr(self, 'pause_state'):
            self.pause_state = "main"

        if self.pause_state == "main":
            self.menu.resume_button.draw(self.screen)
            self.menu.pause_options_button.draw(self.screen)
            self.menu.quit_to_menu_button.draw(self.screen)
        else:
            font = pygame.font.Font(None, 36)
            music_text = font.render(f"Volume Musique: {int(self.music_volume * 100)}%", True, (255, 255, 255))
            sfx_text = font.render(f"Volume Effets: {int(self.sfx_volume * 100)}%", True, (255, 255, 255))

            pygame.draw.rect(self.screen, (100, 100, 100), self.menu.volume_slider_rect2)
            pygame.draw.rect(self.screen, (100, 100, 100), self.menu.sfx_volume_slider_rect)

            music_pos = self.menu.volume_slider_rect2.x + (self.menu.volume_slider_rect2.width * self.music_volume)
            sfx_pos = self.menu.sfx_volume_slider_rect.x + (self.menu.sfx_volume_slider_rect.width * self.sfx_volume)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(music_pos), self.menu.volume_slider_rect2.centery), 10)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(sfx_pos), self.menu.sfx_volume_slider_rect.centery), 10)

            self.screen.blit(music_text, (300, 225))
            self.screen.blit(sfx_text, (300, 325))
            self.menu.back_to_main_button.draw(self.screen)

    def render(self):
        if self.in_game:
            self.screen.fill((0, 0, 0))
            if not self.is_solo and not self.online_game_started:
                self.screen.blit(self.waiting_text, self.waiting_rect)
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
        self.zombie_animations = {}
        self.pause_start_time = 0
        self.total_pause_time = 0

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
        self.game_start_time = time.time()
        self.last_update = self.game_start_time

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
            return

        if self.game_state and self.game_state.get('game_over', False):
            if self.current_music != self.lose_music:
                self.play_music(self.lose_music)
            if 'end_time' not in self.game_state:
                self.game_state['end_time'] = int(time.time() - self.game_start_time - self.total_pause_time)
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

            if self.paused and self.is_solo and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if self.pause_state == "main":
                    if self.menu.resume_button.rect.collidepoint(mouse_pos):
                        self.play_sound_effect(self.menu.resume_button.buttonClick)
                        self.paused = False
                    elif self.menu.pause_options_button.rect.collidepoint(mouse_pos):
                        self.play_sound_effect(self.menu.pause_options_button.buttonClick)
                        self.pause_state = "options"
                    elif self.menu.quit_to_menu_button.rect.collidepoint(mouse_pos):
                        self.play_sound_effect(self.menu.quit_to_menu_button.buttonClick)
                        self.in_game = False
                        self.menu.current_menu = "main"
                        self.reset_game_state()
                        self.play_music(self.menu_music)
                        self.paused = False
                        return True
                elif self.pause_state == "options":
                    if self.menu.back_to_main_button.rect.collidepoint(mouse_pos):
                        self.play_sound_effect(self.menu.back_to_main_button.buttonClick)
                        self.pause_state = "main"
                    elif self.menu.volume_slider_rect2.collidepoint(mouse_pos):
                        rel_x = (mouse_pos[0] - self.menu.volume_slider_rect2.x) / self.menu.volume_slider_rect2.width
                        self.set_volume(rel_x)
                    elif self.menu.sfx_volume_slider_rect.collidepoint(mouse_pos):
                        rel_x = (mouse_pos[0] - self.menu.sfx_volume_slider_rect.x) / self.menu.sfx_volume_slider_rect.width
                        self.set_sfx_volume(rel_x)
                return True

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and self.game_state and self.game_state.get('game_over', False):
                    self.in_game = False
                    self.menu.current_menu = "main"
                    self.reset_game_state()
                    self.play_music(self.menu_music)
                    return True

                if self.is_solo and self.in_game:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state and self.game_state.get('game_over', False):
                            self.in_game = False
                            self.menu.current_menu = "main"
                            self.reset_game_state()
                            self.play_music(self.menu_music)
                            return True
                        else:
                            self.paused = not self.paused
                            if self.paused:
                                self.pause_start_time = time.time()
                            else:
                                self.total_pause_time += time.time() - self.pause_start_time
                    elif event.key == pygame.K_q and self.paused:
                        self.in_game = False
                        self.menu.current_menu = "main"
                        self.reset_game_state()
                        self.play_music(self.menu_music)
                        self.paused = False
                        return True


            if not self.in_game or self.paused:
                self.menu.handle_event(event)
                continue

            if self.in_game and event.type == pygame.MOUSEBUTTONDOWN:
                if self.game_state and self.game_state.get('game_over', False):
                    mouse_pos = pygame.mouse.get_pos()
                    if self.replay_button.rect.collidepoint(mouse_pos):
                        if self.is_solo:
                            self.start_solo_mode()
                        else:
                            if self.tcp_client:
                                self.tcp_client.shutdown()
                            self.tcp_client = None
                            self.game_instance = None
                            self.game_state = None
                            self.online_game_started = False
                            self.start_online_mode()
                        return True
                    elif self.end_quit_button.rect.collidepoint(mouse_pos):
                        if not self.is_solo and self.tcp_client:
                            self.tcp_client.shutdown()
                            self.tcp_client = None
                        self.in_game = False
                        self.menu.current_menu = "main"
                        self.reset_game_state()
                        self.play_music(self.menu_music)
                        return True
                    return True

                mouse_pos = pygame.mouse.get_pos()

                if self.is_solo and self.pause_button.rect.collidepoint(mouse_pos):
                    self.play_sound_effect(self.pause_button.buttonClick)
                    self.paused = not self.paused
                    return True

                if self.is_attacker:
                    button_clicked = False
                    for zombie_type, card in self.zombie_cards:
                        if card.is_clicked(mouse_pos):
                            self.selected_zombie = zombie_type
                            button_clicked = True
                            break

                    if not button_clicked:
                        col = (mouse_pos[0] - self.grid_start_x) // self.cell_size
                        row = (mouse_pos[1] - self.grid_start_y) // self.cell_size

                        if (0 <= row < GRID_HEIGHT and col == GRID_WIDTH - 1):
                            if (0 <= row < GRID_HEIGHT and col == GRID_WIDTH - 1):
                                if self.online_game_started and self.tcp_client.udp_client:
                                    message = f"ADD_ZOMBIE:{self.selected_zombie}:{row}"
                                    self.tcp_client.udp_client.send_message(message)
                else:
                    button_clicked = False

                    col = (mouse_pos[0] - self.grid_start_x) // self.cell_size
                    row = (mouse_pos[1] - self.grid_start_y) // self.cell_size

                    if (0 <= row < GRID_HEIGHT and 0 <= col < GRID_WIDTH):
                        for plant in self.game_state.get('plants', []):
                            if (plant['row'] == row and plant['col'] == col and
                                plant['type'] == 'candycane' and
                                plant.get('ready_to_harvest', False)):

                                if self.is_solo:
                                    sun_points = self.game_instance.plants[
                                        next(i for i, p in enumerate(self.game_instance.plants)
                                            if p.row == row and p.col == col)
                                    ].harvest()
                                    if sun_points > 0:
                                        self.play_sound_effect(self.point)
                                    self.game_instance.sun_points += sun_points
                                    self.game_state = self.game_instance.get_game_state()
                                elif self.online_game_started and self.tcp_client.udp_client:
                                    message = f"HARVEST_SUNFLOWER:{row}:{col}"
                                    self.tcp_client.udp_client.send_message(message)
                                return True
                    for plant_type, card in self.plant_cards:
                        if card.is_clicked(mouse_pos):
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
                            elif self.selected_zombie == 'dead':
                                if self.is_solo:
                                    if self.game_instance.remove_zombie(row):
                                        self.game_state = self.game_instance.get_game_state()
                                elif self.online_game_started and self.tcp_client.udp_client:
                                    message = f"REMOVE_ZOMBIE:{row}"
                                    self.tcp_client.udp_client.send_message(message)
                            else:
                                if self.is_solo:
                                    plant_placed = self.game_instance.add_plant(self.selected_plant, row, col)
                                    if plant_placed and self.selected_plant == 'icewall':
                                        self.icewall_states[(row, col)] = {
                                            'hit_time': 0,
                                            'last_hit': 0,
                                            'is_being_eaten': False
                                        }
                                    if plant_placed:
                                        self.game_state = self.game_instance.get_game_state()
                                elif self.online_game_started and self.tcp_client.udp_client:
                                    message = f"ADD_PLANT:{self.selected_plant}:{row}:{col}"
                                    self.tcp_client.udp_client.send_message(message)

            if self.paused and self.is_solo:
                mouse_pos = pygame.mouse.get_pos()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if hasattr(self, 'pause_state') and self.pause_state == "main":
                        if self.menu.resume_button.is_clicked(mouse_pos):
                            self.paused = False
                        elif self.menu.pause_options_button.is_clicked(mouse_pos):
                            self.pause_state = "options"
                        elif self.menu.quit_to_menu_button.is_clicked(mouse_pos):
                            self.in_game = False
                            self.menu.current_menu = "main"
                            self.reset_game_state()
                            self.play_music(self.menu_music)
                            self.paused = False
                            return True
                    elif hasattr(self, 'pause_state') and self.pause_state == "options":
                        if self.menu.back_to_main_button.is_clicked(mouse_pos):
                            self.pause_state = "main"
                        elif self.menu.volume_slider_rect2.collidepoint(mouse_pos):
                            rel_x = (mouse_pos[0] - self.menu.volume_slider_rect2.x) / self.menu.volume_slider_rect2.width
                            self.set_volume(rel_x)
                        elif self.menu.sfx_volume_slider_rect.collidepoint(mouse_pos):
                            rel_x = (mouse_pos[0] - self.menu.sfx_volume_slider_rect.x) / self.menu.sfx_volume_slider_rect.width
                            self.set_sfx_volume(rel_x)

            if self.game_state and self.game_state.get('game_over', False) and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                if self.replay_button.rect.collidepoint(mouse_pos):
                    if self.is_solo:
                        self.start_solo_mode()
                    else:
                        if self.tcp_client:
                            self.tcp_client.shutdown()
                        self.tcp_client = None
                        self.game_instance = None
                        self.game_state = None
                        self.online_game_started = False
                        self.start_online_mode()
                    return True
                elif self.end_quit_button.rect.collidepoint(mouse_pos):
                    if not self.is_solo and self.tcp_client:
                        self.tcp_client.shutdown()
                        self.tcp_client = None
                    self.in_game = False
                    self.menu.current_menu = "main"
                    self.reset_game_state()
                    self.play_music(self.menu_music)
                    return True

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
            self.game.reset_game_state()

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
                # print(f"[TCP] Received: {message}")

                if message.startswith("STATE:"):
                    state = int(message.split(":")[1])
                    self.game.state = state
                    if state == 1:
                        from shared.game import Game as ServerGame
                        self.game.game_instance = ServerGame(is_solo=False)
                        self.game.game_state = self.game.game_instance.get_game_state()
                    print(f"[TCP] State: {state}")
                if message.startswith("ID:"):
                    self.client_id = message.split(":")[1]
                elif message.startswith("UDP:"):
                    _, host, port = message.split(":")
                    # Remplace l'adresse 0.0.0.0 par 127.0.0.1 pour le client
                    if host == '0.0.0.0':
                        host = '127.0.0.1'
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
        self.game = game
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
                # print(f"[UDP] Received: {decoded_message}")

                if decoded_message == "STATE:2":
                    self.game.online_game_started = True
                    self.game.last_update = time.time()
                    print("[UDP] Game starting!")
                elif decoded_message.startswith("ROLE:"):
                    role = decoded_message.split(":")[1]
                    self.game.is_attacker = (role == "att")
                    # print(f"[UDP] Role assigned: {'Attacker' if self.game.is_attacker else 'Defender'}")
                elif decoded_message.startswith("GAME_STATE:"):
                    self.handle_game_state(decoded_message)
                elif decoded_message.startswith("ADD_PLANT:"):
                    # print(f"[UDP] Plant added: {decoded_message}")
                    _, plant_type, row, col = decoded_message.split(":")
                    self.game.game_instance.add_plant(plant_type, int(row), int(col))
                    self.game.game_state = self.game.game_instance.get_game_state()
                elif decoded_message.startswith("ADD_ZOMBIE:"):
                    # print(f"[UDP] Zombie added: {decoded_message}")
                    _, zombie_type, row = decoded_message.split(":")
                    self.game.game_instance.add_zombie(zombie_type, int(row))
                    self.game.game_state = self.game.game_instance.get_game_state()
                elif decoded_message.startswith("REMOVE_PLANT:"):
                    # print(f"[UDP] Plant removed: {decoded_message}")
                    _, row, col = decoded_message.split(":")
                    self.game.game_instance.remove_plant(int(row), int(col))
                    self.game.game_state = self.game.game_instance.get_game_state()
                elif decoded_message.startswith("REMOVE_PLANT:"):
                    # print(f"[UDP] Plant removed: {decoded_message}")
                    _, row, col = decoded_message.split(":")
                    self.game.game_instance.remove_plant(int(row), int(col))
                    self.game.game_state = self.game.game_instance.get_game_state()
                elif decoded_message.startswith("HARVEST_SUNFLOWER:"):
                    # print(f"[UDP] Sunflower harvested: {decoded_message}")
                    _, row, col = decoded_message.split(":")
                    sun_points = self.game.game_instance.plants[
                        next(i for i, p in enumerate(self.game.game_instance.plants)
                            if p.row == int(row) and p.col == int(col))
                    ].harvest()
                    if sun_points > 0:
                        self.game.play_sound_effect(self.game.point)
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
            self.game.game_state = game_state
        except Exception as e:
            print(f"[UDP] Error parsing game state: {e}")

    def send_message(self, message):
        if not self.running:
            return
        try:
            # print(f"[UDP] Sending: {message}")
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
        game.play_music(game.menu_music)
        while game.running:
            if not game.handle_events():
                break
            game.update()
            game.render()
            game.clock.tick(60)

    except Exception as e:
        print(f"[CLIENT] Error: {e}")
        import traceback
        traceback.print_exc()  # Ajout du traceback complet pour le débogage
    finally:
        if 'game' in locals() and hasattr(game, 'tcp_client') and game.tcp_client:
            game.tcp_client.shutdown()
        if 'game' in locals():
            game.cleanup()
        print("[CLIENT] Disconnected")

if __name__ == "__main__":
    main()
