'''
Fatigue Score Calculation
'''

def estimate_fatigue(calories, weight_lb, age, fitness_level):
    # max hr caculation
    # explanation - a 20-year-old (200 max HR) with 1.0 fitness has a capacity 
    # roughly proportional to their weight * 12.
    # This gives a capacity range of ~800 to ~2500 calories, which is realistic for a day hike/run.
    max_hr = 220 - age

    capacity = fitness_level * max_hr * (weight_lb / 20) * 15  # Simplified capacity estimate

    if capacity <= 100:
        capacity = 100  # Prevent division by very small number
    
    # Fatigue score between 0 & 1
    fatigue_score = calories / capacity
    fatigue_score = min(fatigue_score, 1)  # Clamp at 1 for sanity
    return fatigue_score
