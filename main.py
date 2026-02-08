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

from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import time

# Import engine files
from engine.pace import estimate_time
from engine.energy import estimate_calories
from engine.fatigue import estimate_fatigue

# --- CONFIGURATION ---
SERIAL_PORT = 'COM3'  # <--- DOUBLE CHECK THIS IS CORRECT!
BAUD_RATE = 115200

app = Flask(__name__)
CORS(app)

def send_pace_to_arduino(pace_value):
    """
    Opens the USB connection, sends the number, and closes it.
    This is safer than keeping it open forever.
    """
    try:
        # 1. Open Connection
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2) # Wait for Arduino to reset
        
        # 2. Send Data
        msg = f"{pace_value}\n"
        arduino.write(msg.encode('utf-8'))
        print(f"✅ Sent to Watch: {msg.strip()}")
        
        # 3. Close Connection
        arduino.close()
        return True
    except Exception as e:
        print(f"USB Error: {e}")
        return False

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
            pace_val = round((calc_time * 60) / p_dist, 1) # Round to 1 decimal place
        else:
            pace_val = 0.0

        # --- SEND TO ARDUINO ---
        # We do this in a separate function to keep the code clean
        send_pace_to_arduino(pace_val)

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
    # use_reloader=False prevents the "Double Start" bug that locks the USB port
    app.run(debug=True, use_reloader=False, port=5001)