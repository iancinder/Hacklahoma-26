'''
Energy / Calorie Calculation
'''

def estimate_calories(weight_lb, distance_mi, elevation_gain_ft, flat_speed_mph, activity_type, difficulty_factor):
    # Base metabolic equivalent of task (MET)
    #       1 MET = energy cost of resting ≈ 1 kcal / kg / hour
    if activity_type == "hiking":
        if difficulty_factor == "easy":         # Flat hiking MET ≈ 3 - 5
            base_met = 4.0
        elif difficulty_factor == "moderate":   # Moderate incline hiking ≈ 5-7
            base_met = 6.0
        elif difficulty_factor == "hard":       # Steep hiking MET ≈ 8 - 11
            base_met = 9.5
    elif activity_type == "running":
        if difficulty_factor == "easy":         # Flat running MET ≈ 7 - 8
            base_met = 7.5
        elif difficulty_factor == "moderate":   # Moderate incline running ≈ 8 - 9
            base_met = 8.5
        elif difficulty_factor == "hard":       # Steep trail running MET ≈ 9 - 11
            base_met = 10.0
    else:
        base_met = 3.0                          # Walking

    # Define grade scale
    grade_met_scaling = 2.0

    # Rough grade factor
    grade_factor = elevation_gain_ft / distance_mi / 100        # ~ Evaluation per mile [percentage]
    met = base_met + grade_met_scaling * grade_factor
    met = min(max(met, base_met), 14)                           # Clamp at 14 for sanity

    # We normalize against a standard pace (3.0 mph).
    # We square the factor so intensity rises faster than duration falls.
    if flat_speed_mph > 3.0:
        speed_factor = (flat_speed_mph / 3.0) ** 1.35
        met = met * speed_factor

    # Clamp MET to realistic human limits (20 is about the max for elite athletes)
    met = min(met, 18)

    # Duration estimate in hours using pace
    #       For simplicity, assume average speed = flat speed
    #       Equation: duration = distance / speed

    if flat_speed_mph <= 0:
        flat_speed_mph = 3.0  # Default to 3 mph if invalid input

    duration_hr = distance_mi / flat_speed_mph          # duration is distance / speed

    # Convert weight to kg
    weight_kg = weight_lb * 0.453592        # 1 lb = 0.453592 kg

    calories = met * weight_kg * duration_hr

    return calories
