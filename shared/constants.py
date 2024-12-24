GRID_WIDTH = 9
GRID_HEIGHT = 5

PLANT_TYPES = {
    'candycane': {'cost': 50, 'health': 100},
    'peashooter': {'cost': 75, 'health': 100},
    'icewall': {'cost': 75, 'health': 400},
    'shovel': {'cost': 0, 'refund': 0.5},
}

ZOMBIE_TYPES = {
    'basic': {
        'health': 150,
        'speed': 1,
        'damage': 10,
        'attack_speed': 1.0,
        'cost': 50
    },
    'cone': {
        'health': 250,
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
    # 'sprinter': {
    #     'health': 100,
    #     'speed': 3,
    #     'damage': 10,
    #     'attack_speed': 1.0,
    #     'cost': 75
    # },
}
