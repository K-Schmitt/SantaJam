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
        self.projectiles: List[Projectile] = []
        self.selected_plant = 'candycane'
        self.is_solo = is_solo
        self.last_zombie_spawn = 0
        self.zombie_spawn_interval = 7
        self.energy = 50
        self.energy_timer = 0
        self.game_over = False
        self.winner = None
        self.pending_zombies = []
        self.game_duration = 0
        if is_solo:
            self.zombie_wave_interval = 30
            self.last_wave_time = 0
            self.difficulty_level = 1
            self.zombie_types = ['basic', 'cone', 'bucket']

    def update(self, delta_time: float, current_time: int = None) -> None:
        if self.game_over:
            return

        self.game_duration += delta_time

        if self.is_solo and current_time is not None:
            self.handle_zombie_spawn(current_time)

        if not self.is_solo:
            self.energy_timer += delta_time
            if self.energy_timer >= 5.0:
                self.energy += 25
                self.energy_timer = 0
                self.energy = min(self.energy, 999)

        if current_time is not None:
            for pending in self.pending_zombies[:]:
                if current_time >= pending[3]:
                    self.add_zombie(pending[0], pending[1], pending[2])
                    self.pending_zombies.remove(pending)

        for plant in self.plants:
            result = plant.update(delta_time, self.zombies)
            if isinstance(result, int):
                self.sun_points += result
            elif result is not None:
                self.projectiles.append(result)

        for proj in self.projectiles[:]:
            if proj not in self.projectiles:
                continue
            proj.update(delta_time)
            for zombie in self.zombies[:]:
                if zombie not in self.zombies:
                    continue
                if (proj.row == zombie.row and 
                    abs(proj.col - zombie.col) < 0.5):
                    zombie.health -= proj.damage
                    if proj in self.projectiles:
                        self.projectiles.remove(proj)
                    self.last_hit = True
                    if zombie.health <= 0 and zombie in self.zombies:
                        self.zombies.remove(zombie)
                    break
            if proj in self.projectiles and proj.col >= GRID_WIDTH:
                self.projectiles.remove(proj)

        for zombie in self.zombies[:]:
            plant_in_front = None
            for plant in self.plants:
                if (plant.row == zombie.row and
                    plant.col <= zombie.col and
                    plant.col >= int(zombie.col) - 0.1 and
                    (plant_in_front is None or plant.col > plant_in_front.col)):
                    plant_in_front = plant

            zombie.update(delta_time, plant_in_front)

            if zombie.col < -1:
                self.zombies.remove(zombie)
                self.game_over = True
                if not self.is_solo:
                    self.winner = 'att'
                break

        for plant in self.plants[:]:
            if plant.is_dead():
                self.grid[plant.row][plant.col] = None
                self.plants.remove(plant)
                self.energy += 50

        self.sun_points = min(self.sun_points, 999)
        
    def handle_zombie_spawn(self, current_time: int) -> None:
        self.adjust_difficulty()

        if current_time - self.last_wave_time >= self.zombie_wave_interval:
            self.spawn_zombie_wave(current_time)
            self.last_wave_time = current_time
        else:
            if current_time - self.last_zombie_spawn > self.zombie_spawn_interval:
                zombie_type = self.choose_zombie_type()
                row = random.randint(0, GRID_HEIGHT - 1)
                self.add_zombie(zombie_type, row)
                self.last_zombie_spawn = current_time

    def adjust_difficulty(self) -> None:
        self.difficulty_level = 1 + int(self.game_duration // 60)

        self.zombie_spawn_interval = max(2, 7 - 0.5 * self.difficulty_level)

        # if self.difficulty_level >= 3 and 'fast' not in self.zombie_types:
        #     self.zombie_types.append('fast')
        # if self.difficulty_level >= 5 and 'tank' not in self.zombie_types:
        #     self.zombie_types.append('tank')

    def choose_zombie_type(self) -> str:
        weights = {
            'basic': max(1, 10 - self.difficulty_level * 2),
            'cone': max(1, 5 - self.difficulty_level),
            'bucket': max(1, self.difficulty_level - 2),
        }
        available_zombies = [(zombie, weight) for zombie, weight in weights.items() if zombie in self.zombie_types]
        total_weight = sum(weight for _, weight in available_zombies)
        rand_choice = random.uniform(0, total_weight)
        current = 0

        for zombie, weight in available_zombies:
            current += weight
            if rand_choice <= current:
                return zombie
        return 'basic'

    def spawn_zombie_wave(self, current_time: int) -> None:
        wave_size = 2 + (self.difficulty_level - 1) * 2
        for i in range(wave_size):
            zombie_type = self.choose_zombie_type()
            row = random.randint(0, GRID_HEIGHT - 1)
            spawn_time = current_time + 2 + (i * 0.3)
            self.pending_zombies.append((zombie_type, row, i * 0.3, spawn_time))

    def get_game_state(self) -> Dict[str, Any]:
        return {
            'plants': sorted([plant.to_dict() for plant in self.plants], key=lambda p: p['row']),
            'zombies': sorted([zombie.to_dict() for zombie in self.zombies], key=lambda z: (z['row'], z['col'])),
            'projectiles': [proj.to_dict() for proj in self.projectiles],
            'sun_points': self.sun_points,
            'energy': self.energy,
            'grid': self.grid,
            'available_plants': [p for p in PLANT_TYPES.keys() if p != 'shovel'],
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

    def add_zombie(self, zombie_type: str, row: int, initial_offset: float = 0) -> bool:
        if zombie_type not in ZOMBIE_TYPES:
            print(f"[GAME] Invalid zombie type: {zombie_type}")
            return False

        if not self.is_solo:
            cost = ZOMBIE_TYPES[zombie_type].get('cost', 50)
            if cost > self.energy:
                print(f"[GAME] Not enough energy: {cost} required, have {self.energy}")
                return False

        if not (0 <= row < GRID_HEIGHT):
            print(f"[GAME] Invalid row: {row}")
            return False

        new_zombie = Zombie(zombie_type, row, initial_offset)
        self.zombies.append(new_zombie)
        if not self.is_solo:
            self.energy -= cost
        return True

    def remove_plant(self, row: int, col: int) -> bool:
        if row < 0 or row >= GRID_HEIGHT or col < 0 or col >= GRID_WIDTH:
            print(f"[GAME] Invalid position for removal: {row}, {col}")
            return False
        plant = self.grid[row][col]
        if plant is None:
            print(f"[GAME] No plant at position: {row}, {col}")
            return False

        refund = int(plant.cost * 0.5)
        self.sun_points += refund
        self.grid[row][col] = None
        self.plants.remove(plant)
        # print(f"[GAME] Removed plant at {row}, {col}. Refunded {refund} sun points")
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
