from shared.constants import GRID_WIDTH, ZOMBIE_TYPES, PLANT_TYPES
from typing import Any

class Plant:
    def __init__(self, plant_type: str, row: int, col: int):
        self.type = plant_type
        self.row = row
        self.col = col
        self.health = PLANT_TYPES[plant_type]['health']
        self.cost = PLANT_TYPES[plant_type]['cost']
        self.sun_timer = 0
        self.shoot_timer = 0

    def has_zombie_in_front(self, zombies: list) -> bool:
        for zombie in zombies:
            if zombie.row == self.row and zombie.col > self.col:
                return True
        return False

    def update(self, delta_time: float, zombies: list = None) -> Any:
        if self.type == 'sunflower':
            self.sun_timer += delta_time
            if self.sun_timer >= 5.0:
                self.sun_timer = 0
                return 25

        elif self.type == 'peashooter':
            self.shoot_timer += delta_time
            if self.shoot_timer >= 1.0 and zombies and self.has_zombie_in_front(zombies):
                self.shoot_timer = 0
                return Projectile(self.row, self.col + 1)
        return None

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'row': self.row,
            'col': self.col,
            'health': self.health
        }

    def take_damage(self, damage: int) -> None:
        self.health -= damage
        
    def is_dead(self) -> bool:
        return self.health <= 0

class Zombie:
    def __init__(self, zombie_type: str, row: int):
        self.type = zombie_type
        self.row = row
        self.col = float(GRID_WIDTH)  # Position en float pour un mouvement fluide
        self.health = ZOMBIE_TYPES[zombie_type]['health']
        self.speed = ZOMBIE_TYPES[zombie_type]['speed']
        self.attack_damage = ZOMBIE_TYPES[zombie_type]['damage']
        self.attack_speed = ZOMBIE_TYPES[zombie_type]['attack_speed']
        self.attack_timer = 0
        self.eating = False  # Ajout d'un état pour suivre si le zombie mange
        
    def update(self, delta_time: float, plant_in_front: Plant = None) -> None:
        if plant_in_front:
            # Ajuste la position du zombie pour qu'il soit à droite de la plante
            if not self.eating:
                self.col = plant_in_front.col + 1
                self.eating = True
            
            # Attaque la plante
            self.attack_timer += delta_time
            if self.attack_timer >= self.attack_speed:
                plant_in_front.take_damage(self.attack_damage)
                self.attack_timer = 0
        else:
            # Si plus de plante, on continue d'avancer
            self.eating = False
            self.col -= (self.speed / 5) * delta_time
        
    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'row': self.row,
            'col': int(self.col),  # Convertit en int pour l'affichage
            'health': self.health
        }

class Projectile:
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
        self.speed = 5.0
        self.damage = 20

    def update(self, delta_time: float) -> None:
        self.col += self.speed * delta_time

    def to_dict(self) -> dict:
        return {
            'row': self.row,
            'col': self.col
        }
