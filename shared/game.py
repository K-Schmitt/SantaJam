from typing import List, Dict, Any
from .entities import Plant, Zombie, Projectile  # Ajout de Projectile
from .constants import GRID_WIDTH, GRID_HEIGHT, PLANT_TYPES, ZOMBIE_TYPES
import random

class Game:
    def __init__(self, is_solo: bool = False):
        self.plants: List[Plant] = []
        self.zombies: List[Zombie] = []
        self.sun_points = 50
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.projectiles: List[Projectile] = []  # Ajout de la liste des projectiles
        self.selected_plant = 'candycane'  # Plante sélectionnée par défaut
        self.is_solo = is_solo
        self.last_zombie_spawn = 0
        self.zombie_spawn_interval = 7  # 7 secondes
        self.energy = 50  # Énergie initiale pour les zombies
        self.energy_timer = 0  # Timer pour la génération d'énergie
        self.game_over = False
        self.winner = None  # 'att' ou 'def' en multi, None en solo
        if is_solo:
            self.zombie_types = ['basic', 'cone', 'bucket']
            self.count_zombies = 0

    def update(self, delta_time: float, current_time: int = None) -> None:
        if self.game_over:
            return

        # Gestion du spawn de zombies en solo
        if self.is_solo and current_time is not None:
            if self.count_zombies >= 15:
                self.count_zombies = 0
            if current_time - self.last_zombie_spawn > self.zombie_spawn_interval - self.count_zombies * 0.3:
                self.add_zombie(self.zombie_types[int(self.count_zombies * 0.2)], random.randint(0, GRID_HEIGHT - 1))
                self.last_zombie_spawn = current_time
                self.count_zombies += 1

        # Gestion de l'énergie pour les zombies (en mode non-solo)
        if not self.is_solo:
            self.energy_timer += delta_time
            if self.energy_timer >= 5.0:  # Toutes les 5 secondes
                self.energy += 25
                self.energy_timer = 0
                self.energy = min(self.energy, 999)  # Limite maximum

        # Update all plants and collect sun points
        for plant in self.plants:
            result = plant.update(delta_time, self.zombies)  # Passage des zombies à la méthode update
            if isinstance(result, int):  # Si c'est du soleil
                self.sun_points += result
            elif result is not None:  # Si c'est un projectile
                self.projectiles.append(result)

        # Update projectiles
        for proj in self.projectiles[:]:
            proj.update(delta_time)
            # Vérifier les collisions avec les zombies
            for zombie in self.zombies[:]:
                if (proj.row == zombie.row and 
                    abs(proj.col - zombie.col) < 0.5):
                    zombie.health -= proj.damage
                    self.projectiles.remove(proj)
                    self.last_hit = True
                    if zombie.health <= 0:
                        self.zombies.remove(zombie)
                    break
            if proj.col >= GRID_WIDTH:
                self.projectiles.remove(proj)

        # Update all zombies and handle plant interactions
        for zombie in self.zombies[:]:
            # Trouve la plante la plus proche devant le zombie
            plant_in_front = None
            for plant in self.plants:
                if (plant.row == zombie.row and
                    plant.col <= zombie.col and  # Changé de > à <= pour détecter les plantes à gauche
                    plant.col >= int(zombie.col) - 0.2 and  # Ajout d'une zone de collision
                    (plant_in_front is None or plant.col > plant_in_front.col)):
                    plant_in_front = plant

            # Update zombie avec la plante devant (si elle existe)
            zombie.update(delta_time, plant_in_front)

            # Vérifie si un zombie est sorti de l'écran
            if zombie.col < -1:
                self.zombies.remove(zombie)
                self.game_over = True
                if not self.is_solo:
                    self.winner = 'att'
                break

        # Retire les plantes mortes
        for plant in self.plants[:]:
            if plant.is_dead():
                self.grid[plant.row][plant.col] = None
                self.plants.remove(plant)
                self.energy += 50

        # Limite maximum de points de soleil
        self.sun_points = min(self.sun_points, 999)

    def get_game_state(self) -> Dict[str, Any]:
        return {
            'plants': [plant.to_dict() for plant in self.plants],
            'zombies': [zombie.to_dict() for zombie in self.zombies],
            'projectiles': [proj.to_dict() for proj in self.projectiles],
            'sun_points': self.sun_points,
            'energy': self.energy,
            'grid': self.grid,
            'available_plants': [p for p in PLANT_TYPES.keys() if p != 'shovel'],  # Filtrer la pelle
            'game_over': self.game_over,
            'winner': self.winner,
            'last_hit': self.last_hit if hasattr(self, 'last_hit') else False
        }

    def add_plant(self, plant_type: str, row: int, col: int) -> bool:
        if row < 0 or row >= GRID_HEIGHT or col < 0 or col >= GRID_WIDTH:
            print(f"[GAME] Invalid plant position: {row}, {col}")
            return False
        if self.grid[row][col] is not None:
            print(f"[GAME] Plant already exists at {row}, {col}")
            return False

        new_plant = Plant(plant_type, row, col)
        if new_plant.cost > self.sun_points:
            print(f"[GAME] Not enough sun points to add plant: {new_plant.cost} and sun_points: {self.sun_points}")
            return False

        self.plants.append(new_plant)
        self.grid[row][col] = new_plant
        self.sun_points -= new_plant.cost
        return True

    def add_zombie(self, zombie_type: str, row: int) -> bool:
        if zombie_type not in ZOMBIE_TYPES:
            print(f"[GAME] Invalid zombie type: {zombie_type}")
            return False
        
        # Vérifier si assez d'énergie
        if not self.is_solo:
            cost = ZOMBIE_TYPES[zombie_type].get('cost', 50)
            if cost > self.energy:
                print(f"[GAME] Not enough energy: {cost} required, have {self.energy}")
                return False

        if not (0 <= row < GRID_HEIGHT):
            print(f"[GAME] Invalid row: {row}")
            return False

        new_zombie = Zombie(zombie_type, row)
        self.zombies.append(new_zombie)
        if not self.is_solo:
            self.energy -= cost
        print(f"[GAME] Added zombie {zombie_type} at row {row}, remaining energy: {self.energy}")
        return True

    def remove_plant(self, row: int, col: int) -> bool:
        if row < 0 or row >= GRID_HEIGHT or col < 0 or col >= GRID_WIDTH:
            print(f"[GAME] Invalid position for removal: {row}, {col}")
            return False
            
        plant = self.grid[row][col]
        if plant is None:
            print(f"[GAME] No plant at position: {row}, {col}")
            return False
            
        refund = int(plant.cost * 0.5)  # Remboursement fixe de 50%
        self.sun_points += refund
        self.grid[row][col] = None
        self.plants.remove(plant)
        print(f"[GAME] Removed plant at {row}, {col}. Refunded {refund} sun points")
        return True

    def harvest_candycane(self, row: int, col: int) -> bool:
        """Récolter un tournesol à la position donnée"""
        for plant in self.plants:
            if plant.row == row and plant.col == col and plant.type == 'candycane':
                points = plant.harvest()
                if points > 0:
                    self.sun_points += points
                    return True
        return False
