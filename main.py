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

# Import necessary libraries
from flask import Flask, request, jsonify
from flask_cors import CORS

# Declare engine package files
from engine.pace import estimate_time
from engine.energy import estimate_calories
from engine.fatigue import estimate_fatigue

# --- 1. INITIAL SETUP & TESTING ---
# We run a quick test calculation on startup to make sure math works
print("--- RUNNING STARTUP DIAGNOSTICS ---")

user = {
    "age": 22, "weight_lb": 160, "flat_speed_mph": 3.0,
    "vertical_speed_fph": 1000, "fitness_level": 0.5
}
trail = { "distance_mi": 5.0, "elevation_gain_ft": 1500, "difficulty": "easy" }
app_inputs = { "activity_type": "hiking" }

# Call functions to verify imports work
try:
    t_test = estimate_time(trail["distance_mi"], trail["elevation_gain_ft"],
                           user["flat_speed_mph"], user["vertical_speed_fph"],
                           trail["difficulty"], user["fitness_level"], app_inputs["activity_type"])
    c_test = estimate_calories(user["weight_lb"], trail["distance_mi"], trail["elevation_gain_ft"],
                               user["flat_speed_mph"], app_inputs["activity_type"], trail["difficulty"])
    f_test = estimate_fatigue(c_test, user["weight_lb"], user["age"], user["fitness_level"])
    
    print(f"Diagnostics Passed: Time={t_test:.2f}h, Cals={c_test:.0f}, Fatigue={f_test:.2f}")
except Exception as e:
    print(f"!!! DIAGNOSTICS FAILED: {e} !!!")

# --- 2. WEB SERVER SETUP ---
app = Flask(__name__)
CORS(app)

# GLOBAL VARIABLE: Stores the latest pace for the Arduino
# The website updates this -> The Arduino reads it.
current_pace = 0.0 

@app.route('/predict', methods=['POST'])
def predict():
    global current_pace # <--- Tell Python we want to write to the global var
    try:
        data = request.json
        print(f"Received Inputs: {data}")

        # Extract variables (using defaults if inputs are missing)
        p_age = float(data.get('age') or 22)
        p_weight = float(data.get('weight_lb') or 160)
        p_flat_speed = float(data.get('flat_speed_mph') or 3.0)
        p_vert_speed = float(data.get('vertical_speed_fph') or 1000)
        p_fitness = float(data.get('fitness_level') or 0.5)
        
        p_dist = float(data.get('distance_mi') or 5.0)
        p_gain = float(data.get('elevation_gain_ft') or 1000)
        p_diff = data.get('difficulty') if data.get('difficulty') else 'moderate'
        p_activity = data.get('activity_type') if data.get('activity_type') else 'hiking'

        # --- CALCULATIONS ---
        
        # 1. Time
        calc_time = estimate_time(p_dist, p_gain, p_flat_speed, p_vert_speed, p_diff, p_fitness, p_activity)
        
        # 2. Calories
        calc_cals = estimate_calories(p_weight, p_dist, p_gain, p_flat_speed, p_activity, p_diff)
        
        # 3. Fatigue
        calc_fatigue = estimate_fatigue(calc_cals, p_weight, p_age, p_fitness)

        # 4. Pace for Arduino
        if p_dist > 0:
            pace_val = round((calc_time * 60) / p_dist, 0)
        else:
            pace_val = 0

        # Update the Global Variable for the Watch
        current_pace = pace_val
        print(f"Updated Watch Pace: {current_pace} min/mi")

        # Return results to Website
        return jsonify({
            "time_hr": round(calc_time, 2),
            "calories": int(calc_cals),
            "fatigue": round(calc_fatigue * 10, 1),
            "pace": pace_val
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ARDUINO ROUTE ---
# The ESP32 calls this to get the number
@app.route('/get_pace', methods=['GET'])
def get_pace():
    # Return just the number as text (e.g., "12.0")
    return str(current_pace)

if __name__ == '__main__':
    print("Server is running on Port 5001")
    # host='0.0.0.0' allows the Arduino (external device) to connect
    app.run(debug=True, host='0.0.0.0', port=5001)