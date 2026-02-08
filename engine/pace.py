'''
Pace Calculation
'''

def estimate_time(distance_mi, elevation_gain_ft, flat_speed_mph, vertical_speed_fph, difficulty, fitness_level, activity_type):
    # Base time
    flat_time = distance_mi / flat_speed_mph                # [hours]
    climb_time = elevation_gain_ft / vertical_speed_fph     # [hours]

    # We apply a small time reduction (bonus) to reward the effort.
    activity_modifier = 1.0
    if activity_type == "running":
        activity_modifier = 0.9  # Runners are 10% faster overall due to momentum

    # difficulty multiplier
    difficulty_factor = {"easy": 1.0, "moderate": 1.15, "hard": 1.3}

    # fitness level
    fitness_modifier = 1.2 - (0.3 * fitness_level) # 0.9 to 1.2 multiplier based on fitness level

    total_time = (flat_time + climb_time) * difficulty_factor.get(difficulty, 1.0) * fitness_modifier * activity_modifier

    

    return total_time
