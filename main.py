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
import serial
import time

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

SERIAL_PORT = 'COM3' 
BAUD_RATE = 115200

# Try to connect to Arduino on startup
arduino = None
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Wait for Arduino to reset/wake up
    print(f"✅ Successfully connected to Arduino on {SERIAL_PORT}")
except Exception as e:
    print(f"⚠️ Could not connect to Arduino: {e}")
    print("Server will run, but Pace won't be sent to watch.")

app = Flask(__name__)
CORS(app)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        print(f"Received Inputs: {data}")

        # 1. Parse Inputs
        p_age = float(data.get('age') or 22)
        p_weight = float(data.get('weight_lb') or 160)
        p_flat_speed = float(data.get('flat_speed_mph') or 3.0)
        p_vert_speed = float(data.get('vertical_speed_fph') or 1000)
        p_fitness = float(data.get('fitness_level') or 0.5)
        p_dist = float(data.get('distance_mi') or 5.0)
        p_gain = float(data.get('elevation_gain_ft') or 1000)
        p_diff = data.get('difficulty') if data.get('difficulty') else 'moderate'
        p_activity = data.get('activity_type') if data.get('activity_type') else 'hiking'

        # 2. Run Math
        calc_time = estimate_time(p_dist, p_gain, p_flat_speed, p_vert_speed, p_diff, p_fitness, p_activity)
        calc_cals = estimate_calories(p_weight, p_dist, p_gain, p_flat_speed, p_activity, p_diff)
        calc_fatigue = estimate_fatigue(calc_cals, p_weight, p_age, p_fitness)

        # 3. Calculate Pace
        if p_dist > 0:
            pace_val = round((calc_time * 60) / p_dist, 0)
        else:
            pace_val = 0

        # --- SEND TO ARDUINO (USB) ---
        if arduino and arduino.is_open:
            # We send the number followed by a newline so Arduino knows it's done
            msg = f"{pace_val}\n"
            arduino.write(msg.encode('utf-8'))
            print(f"Sent to Watch: {msg.strip()}")
        else:
            print("Skipping USB send (Arduino not connected)")

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

if __name__ == '__main__':
    print("Server is running on Port 5001")
    app.run(debug=True, use_reloader=False, port=5001)