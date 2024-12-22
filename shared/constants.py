GRID_WIDTH = 9
GRID_HEIGHT = 5

PLANT_TYPES = {
    'candycane': {'cost': 50, 'health': 100},
    'peashooter': {'cost': 50, 'health': 100},
    'wallnut': {'cost': 50, 'health': 300},
    'shovel': {'cost': 0, 'refund': 0.5},  # Rembourse 50% du coût de la plante
}

# Ajouter les coûts d'énergie pour les zombies
ZOMBIE_TYPES = {
    'basic': {
        'health': 100,
        'speed': 1,
        'damage': 10,
        'attack_speed': 1.0,
        'cost': 50
    },
    'cone': {
        'health': 200,
        'speed': 1,
        'damage': 10,
        'attack_speed': 1.0,
        'cost': 75
    },
    'bucket': {
        'health': 500,
        'speed': 1,
        'damage': 10,
        'attack_speed': 1.0,
        'cost': 100
    },
    'sprinter': {
        'health': 100,
        'speed': 3,
        'damage': 10,
        'attack_speed': 1.0,
        'cost': 75
    },
}
