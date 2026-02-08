import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

def train_models():
    print("Loading dataset...")
    try:
        df = pd.read_csv('hiking_dataset_100k.csv')
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
    print("Training Pace Model")
    model_pipeline.fit(X, df['time_hr'])
    joblib.dump(model_pipeline, 'model_time.pkl')

    # Model 2: Calories
    print("Training Calorie Model")
    model_pipeline.fit(X, df['calories'])
    joblib.dump(model_pipeline, 'model_calories.pkl')

    # Model 3: Fatigue
    print("Training Fatigue Model")
    model_pipeline.fit(X, df['fatigue_score'])
    joblib.dump(model_pipeline, 'model_fatigue.pkl')

    print("Success. Created 'model_time.pkl', 'model_calories.pkl', and 'model_fatigue.pkl'")

if __name__ == "__main__":
    train_models()