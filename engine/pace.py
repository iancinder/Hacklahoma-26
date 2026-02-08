'''
Pace Calculation
'''

# Global calibration: < 1.0 makes predicted times faster.
# This directly affects the synthetic labels in `generate_data.py`,
# and therefore what the ML time model learns.
TIME_CALIBRATION_FACTOR = 0.6

def estimate_time(distance_mi, elevation_gain_ft, flat_speed_mph, vertical_speed_fph, difficulty, fitness_level, activity_type):
    # Base time
    flat_time = distance_mi / flat_speed_mph                # [hours]
    climb_time = elevation_gain_ft / vertical_speed_fph     # [hours]

    # We apply a small time reduction (bonus) to reward the effort.
    activity_modifier = 1.0
    if activity_type == "running":
        activity_modifier = 0.725  # Runners are 10% faster overall due to momentum

    # difficulty multiplier
    # Tuned to be less punitive (previous values skewed slow)
    difficulty_factor = {"easy": 1.0, "moderate": 1.10, "hard": 1.20}

    # fitness level
    # Tuned so mid-fitness doesn't get an automatic slowdown:
    # fitness_level=0.5 -> 1.0x, fitness_level=1.0 -> 0.9x, fitness_level=0.0 -> 1.1x
    fitness_modifier = 1.1 - (0.2 * fitness_level)

    total_time = (flat_time + climb_time) * difficulty_factor.get(difficulty, 1.0) * fitness_modifier * activity_modifier
    total_time *= TIME_CALIBRATION_FACTOR

    

    return total_time
