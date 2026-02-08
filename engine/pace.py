'''
Pace Calculation
'''

def estimate_time(distance_mi, elevation_gain_ft, flat_speed_mph, vertical_speed_fph, difficulty):
    # Base time
    flat_time = distance_mi / flat_speed_mph                # [hours]
    climb_time = elevation_gain_ft / vertical_speed_fph     # [hours]

    # difficulty multiplier
    difficulty_factor = {"easy": 1.0, "moderate": 1.15, "hard": 1.3}

    total_time = (flat_time + climb_time) * difficulty_factor.get(difficulty, 1.0)

    return total_time
