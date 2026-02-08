'''
Fatigue Score Calculation
'''

def estimate_fatigue(calories, weight_lb, age, fitness_level):
    # Recovery capacity heuristic
    recovery_capacity = fitness_level * (220 - age) * weight_lb

    # Fatigue score between 0 & 1
    fatigue_score = calories * 4184 / recovery_capacity     # 1 kilocalorie = 4184 Joules (calorie refers to kilocalorie)
    fatigue_score = min(fatigue_score, 1.0)

    return fatigue_score
