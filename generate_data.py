import pandas as pd
import numpy as np
import random
import os

try:
    from engine.pace import estimate_time
    from engine.energy import estimate_calories
    from engine.fatigue import estimate_fatigue
except ImportError:
    print("Error: Could not import engine modules. Ensure they are in the 'engine' folder.")
    exit()

# Configuration
NUM_SAMPLES = 100000

def generate_dataset():
    print(f"Generating {NUM_SAMPLES} fake hikers")

    # Generate Input Arrays
    
    # Distance & Elevation (Correlated)
    # Gamma distribution creates a right-skew (lots of short hikes, few long ones)
    dist_arr = np.random.gamma(6, 2.5, NUM_SAMPLES).clip(0.5, 40)
    
    # Generate a random steepness factor (ft/mile) to correlate elevation with distance
    steepness_arr = np.random.gamma(2, 250, NUM_SAMPLES)
    elev_arr = (dist_arr * steepness_arr).clip(10, dist_arr * 1200)

    # Independent Variables
    weight_arr = np.random.normal(170, 40, NUM_SAMPLES).clip(90, 400)
    age_arr = np.random.randint(18, 70, NUM_SAMPLES)
    fitness_arr = np.random.uniform(0.01, 1.0, NUM_SAMPLES)
    
    # Speed assumptions (Normal distribution)
    flat_speed_arr = np.random.normal(3.5, 0.5, NUM_SAMPLES).clip(1.25, 6.0)
    vert_speed_arr = np.random.normal(1000, 300, NUM_SAMPLES).clip(200, 2200)

    # Categorical: Weighted difficulty (66% Easy, 24% Moderate, 10% Hard)
    difficulties = ['easy', 'moderate', 'hard']
    diff_weights = [0.66, 0.24, 0.10] 
    diff_arr = random.choices(difficulties, weights=diff_weights, k=NUM_SAMPLES)

    activities = ['hiking', 'running']
    act_arr = [random.choice(activities) for _ in range(NUM_SAMPLES)]

    # --- 2. Build DataFrame ---
    df = pd.DataFrame({
        'weight_lb': weight_arr,
        'age': age_arr,
        'fitness_level': fitness_arr,
        'distance_mi': dist_arr,        
        'elevation_gain_ft': elev_arr,
        'flat_speed_mph': flat_speed_arr,
        'vertical_speed_fph': vert_speed_arr,
        'difficulty': diff_arr,
        'activity_type': act_arr
    })

    # --- 3. Calculate Ground Truth (Labels) ---
    print("Running physics engine to generate truth labels...")

    def calculate_row(row):
        t = estimate_time(
            row['distance_mi'], row['elevation_gain_ft'], 
            row['flat_speed_mph'], row['vertical_speed_fph'], 
            row['difficulty'], row['fitness_level'], row['activity_type']
        )
        c = estimate_calories(
            row['weight_lb'], row['distance_mi'], row['elevation_gain_ft'], 
            row['flat_speed_mph'], row['activity_type'], row['difficulty']
        )
        f = estimate_fatigue(
            c, row['weight_lb'], row['age'], row['fitness_level']
        )
        return pd.Series([t, c, f])

    # Apply physics engine to every row
    df[['time_hr', 'calories', 'fatigue_score']] = df.apply(calculate_row, axis=1)

    # --- 4. Cleanup & Save ---
    df['time_hr'] = df['time_hr'].round(2)
    df['calories'] = df['calories'].round(0)
    df['fatigue_score'] = df['fatigue_score'].clip(0, 1).round(3)
    df['elevation_gain_ft'] = df['elevation_gain_ft'].round(0)
    df['distance_mi'] = df['distance_mi'].round(2)

    # Always save next to this script (repo root), regardless of current working directory.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(base_dir, 'hiking_dataset_100k.csv')
    df.to_csv(filename, index=False)
    print(f"Done. Saved {NUM_SAMPLES} rows to '{filename}'")

if __name__ == "__main__":
    generate_dataset()