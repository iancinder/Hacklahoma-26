import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import os
import numpy as np

def train_models():
    print("Loading dataset...")
    try:
        # Always load dataset from the repo directory (next to this script)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        df = pd.read_csv(os.path.join(base_dir, 'hiking_dataset_100k.csv'))
    except FileNotFoundError:
        print("Error: 'hiking_dataset_100k.csv' not found. Run generate_data.py first.")
        return

    # --- 1. SETUP FEATURES ---
    # We must tell the model which columns are numbers and which are text
    numeric_features = ['weight_lb', 'age', 'fitness_level', 'distance_mi', 
                        'elevation_gain_ft', 'flat_speed_mph', 'vertical_speed_fph']
    
    categorical_features = ['difficulty', 'activity_type']

    # Define X (Inputs)
    X = df[numeric_features + categorical_features]

    # --- 2. BUILD THE PIPELINE ---
    # This "Pipeline" automatically handles the text-to-number conversion
    # So you can pass "hard" or "hiking" directly to the model later.
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ])

    # We use Random Forest: It's accurate and handles non-linear data well
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=50, n_jobs=-1, random_state=42))
    ])

    # --- 3. TRAIN & SAVE (3 Separate Models) ---
    
    # Model 1: Time
    print("Training Time/Pace Model")
    y_time = df['time_hr']

    # Optional bias: weight faster examples more heavily so the model
    # is less likely to systematically overestimate time (i.e., predict too slow).
    # Normalize weights to mean 1 and clamp to avoid extreme influence.
    weights = (1.0 / y_time).to_numpy()
    weights = weights / np.mean(weights)
    weights = np.clip(weights, 0.5, 2.0)

    model_pipeline.fit(X, y_time, regressor__sample_weight=weights)
    model_path = os.path.join(base_dir, 'model_time.pkl')
    joblib.dump(model_pipeline, model_path)
    print(f"Success. Created '{model_path}'")

if __name__ == "__main__":
    train_models()