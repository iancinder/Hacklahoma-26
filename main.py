'''
Hacklahoma 2026

Developed By:   Kegan Reynolds (2/7/2026)

Purpose:        This script serves as a deterministic prediction engine for a website that will acquire user inputs
                such as weight, height, and age, as well as inputs from AllTrails for a particular hike such as
                distance, elevation, and difficulty. The engine will then use these inputs to predict tailred metrics
                such as:
                - Estimated time to complete
                - Estimated calorie burn
                - Recommended pace
                - Recommended rest points
                - Estimated heart rate
                - Estimated fatigue points
'''

# Declare engine package files
from engine.pace import estimate_time
from engine.energy import estimate_calories
from engine.fatigue import estimate_fatigue


# Define user inputs
user = {
    "age": 22,                          # [years]
    "weight_lb": 172,                   # [pounds]
    "flat_speed_mph": 3.8,              # Typical hiking pace [miles per hour]
    "vertical_speed_fph": 1500,         # Typical climbing rate [feet per hour]
    "fitness_level": 0.7                # 0-1 scale
}

# Define trail inputs
trail = {
    "distance_mi": 3.8,                  # [miles]
    "elevation_gain_ft": 78,          # [feet]
    "difficulty": "easy"            # Categories: easy, moderate, hard
}

# Define application inputs
app = {
    "activity_type": "hiking"           # Categories: hiking, running, walking
}


# Call calculation functions
time_hr = estimate_time(trail["distance_mi"], trail["elevation_gain_ft"],
                        user["flat_speed_mph"], user["vertical_speed_fph"],
                        trail["difficulty"])

calories = estimate_calories(user["weight_lb"], trail["distance_mi"], trail["elevation_gain_ft"],
                         app["activity_type"], trail["difficulty"])

fatigue = estimate_fatigue(calories, user["weight_lb"], user["age"], user["fitness_level"])


# Print calculation outputs for verification
print(f"Estimated time: {time_hr:.2f} hours")
print(f"Estimated calories: {calories:.0f} kcal")
print(f"Estimated fatigue: {fatigue:.2f}")
