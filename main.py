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

# Import necessary libraries for running the Flask web application and handling CORS
from flask import Flask, request, jsonify
from flask_cors import CORS


# Declare engine package files
from engine.pace import estimate_time
from engine.energy import estimate_calories
from engine.fatigue import estimate_fatigue


# Define user inputs
user = {
    "age": 22,                          # [years]
    "weight_lb": 160,                   # [pounds]
    "flat_speed_mph": 3.0,              # Typical hiking pace [miles per hour]
    "vertical_speed_fph": 1000,         # Typical climbing rate [feet per hour]
    "fitness_level": 0.5                # 0-1 scale
}

# Define trail inputs
trail = {
    "distance_mi": 5.0,             # [miles]
    "elevation_gain_ft": 1500,        # [feet]
    "difficulty": "easy"            # Categories: easy, moderate, hard
}

# Define application inputs
app_inputs = {
    "activity_type": "hiking"           # Categories: hiking, running, walking
}


# Call calculation functions
time_hr = estimate_time(trail["distance_mi"], trail["elevation_gain_ft"],
                        user["flat_speed_mph"], user["vertical_speed_fph"],
                        trail["difficulty"], user["fitness_level"], app_inputs["activity_type"])

calories = estimate_calories(user["weight_lb"], trail["distance_mi"], trail["elevation_gain_ft"],
                         user["flat_speed_mph"], app_inputs["activity_type"], trail["difficulty"])

fatigue = estimate_fatigue(calories, user["weight_lb"], user["age"], user["fitness_level"])


# Print calculation outputs for verification
print(f"Estimated time: {time_hr:.2f} hours")
print(f"Estimated calories: {calories:.0f} kcal")
print(f"Estimated fatigue: {fatigue:.2f}")

# Web server to handle requests from the website (Ian Sendelbach 2/7/2026)
app = Flask(__name__)
CORS(app)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        #Receive data from the website
        data = request.json
        print(f"Received Inputs: {data}")

        # Extract variables using defaults if inputs are empty
        # We cast to float/int because data from HTML usually strings
        p_age = float(data.get('age') or 22)
        p_weight = float(data.get('weight_lb') or 160)
        p_flat_speed = float(data.get('flat_speed_mph') or 3.0)
        p_vert_speed = float(data.get('vertical_speed_fph') or 1000)
        p_fitness = float(data.get('fitness_level') or 0.5)
        
        p_dist = float(data.get('distance_mi') or 5.0)
        p_gain = float(data.get('elevation_gain_ft') or 1000)
        p_diff = data.get('difficulty', 'moderate')
        p_activity = data.get('activity_type', 'hiking')

        # 3. Call keegans functions to perform calculations
        
        calc_time = estimate_time(p_dist, p_gain, p_flat_speed, p_vert_speed, p_diff, p_fitness, p_activity)
        
        calc_cals = estimate_calories(p_weight, p_dist, p_gain, p_flat_speed, p_activity, p_diff)
        
        calc_fatigue = estimate_fatigue(calc_cals, p_weight, p_age, p_fitness)

        # 4. Return the results to the website
        return jsonify({
            "time_hr": round(calc_time, 2),
            "calories": int(calc_cals),
            "fatigue": round(calc_fatigue * 10, 1), # Multiply by 10 for 1-10 scale
            "pace": round((calc_time * 60) / p_dist, 0) if p_dist > 0 else 0
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Server is running")
    app.run(debug=True, port=5001)


    # --- NEW: The "Mailbox" for the Arduino ---
# This global variable stores the last calculated pace.
# The website updates it -> The Arduino reads it.
current_pace = 0.0 

@app.route('/predict', methods=['POST'])
def predict():
    global current_pace # <--- Tell Python we want to write to the global var
    try:
        data = request.json
        print(f"Received Inputs: {data}")

        # 1. Parse Inputs (Same as before)
        p_age = float(data.get('age') or 22)
        p_weight = float(data.get('weight_lb') or 160)
        p_flat_speed = float(data.get('flat_speed_mph') or 3.0)
        p_vert_speed = float(data.get('vertical_speed_fph') or 1000)
        p_fitness = float(data.get('fitness_level') or 0.5)
        p_dist = float(data.get('distance_mi') or 5.0)
        p_gain = float(data.get('elevation_gain_ft') or 1000)
        p_diff = data.get('difficulty') if data.get('difficulty') else 'moderate'
        p_activity = data.get('activity_type') if data.get('activity_type') else 'hiking'

        # 2. Run the Math (Same as before)
        calc_time = estimate_time(p_dist, p_gain, p_flat_speed, p_vert_speed, p_diff, p_fitness, p_activity)
        calc_cals = estimate_calories(p_weight, p_dist, p_gain, p_flat_speed, p_activity, p_diff)
        calc_fatigue = estimate_fatigue(calc_cals, p_weight, p_age, p_fitness)

        # 3. Calculate Pace for the Watch
        if p_dist > 0:
            pace_val = round((calc_time * 60) / p_dist, 0)
        else:
            pace_val = 0

        # --- NEW: Update the Global Variable ---
        current_pace = pace_val
        print(f"Updated Watch Pace: {current_pace} min/mi")

        # 4. Reply to Website
        return jsonify({
            "time_hr": round(calc_time, 2),
            "calories": int(calc_cals),
            "fatigue": round(calc_fatigue * 10, 1),
            "pace": pace_val
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# --- NEW: The Arduino Route ---
# The ESP32 calls this function to get the number.
@app.route('/get_pace', methods=['GET'])
def get_pace():
    # We return the number as a simple string (e.g., "12.0")
    return str(current_pace)

if __name__ == '__main__':
    print("Server is running on Port 5001")
    # --- CHANGED: host='0.0.0.0' allows external connections! ---
    app.run(debug=True, host='0.0.0.0', port=5001)