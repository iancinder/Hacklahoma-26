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
import pandas as pd # Needed to format data for the AI
import joblib       # Needed to load the .pkl brain files
import os

# --- CONFIGURATION ---
SERIAL_PORT = 'COM3'  # make sure this is the correct port
BAUD_RATE = 115200

app = Flask(__name__)
CORS(app)

# --- LOAD THE AI MODELS ---
# We load these once when the server starts so it's fast.
try:
    # Load the "Brains"
    model_time = joblib.load('model_time.pkl')
    model_cals = joblib.load('model_calories.pkl')
    model_fatigue = joblib.load('model_fatigue.pkl')
    print("✅ AI Models Loaded Successfully!")
except Exception as e:
    print(f"❌ Could not load models. {e}")
    print("Did you run 'train_model.py'?")
    # If models fail, we set them to None and handle it later
    model_time = None
    model_cals = None
    model_fatigue = None

def send_pace_to_arduino(pace_value):
    """
    Sends the calculated pace to the watch via USB.
    """
    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2) 
        msg = f"{pace_value}\n"
        arduino.write(msg.encode('utf-8'))
        print(f"Sent to Watch: {msg.strip()}")
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

        # 1. PARSE INPUTS
        # We need to grab the data and put it into a format the AI understands.
        # The AI expects a "DataFrame" with specific column names.
        
        # Create a single-row DataFrame with the exact column names from training
        input_df = pd.DataFrame([{
            'weight_lb': float(data.get('weight_lb') or 160),
            'age': float(data.get('age') or 22),
            'fitness_level': float(data.get('fitness_level') or 0.5),
            'distance_mi': float(data.get('distance_mi') or 5.0),
            'elevation_gain_ft': float(data.get('elevation_gain_ft') or 1000),
            'flat_speed_mph': float(data.get('flat_speed_mph') or 3.0),
            'vertical_speed_fph': float(data.get('vertical_speed_fph') or 1000),
            'difficulty': data.get('difficulty') or 'moderate',      # Pass string directly!
            'activity_type': data.get('activity_type') or 'hiking'   # Pass string directly!
        }])

        # 2. ASK THE AI FOR PREDICTIONS
        if model_time is not None:
            # .predict() returns a list, so we take the first item [0]
            pred_time = model_time.predict(input_df)[0]
            pred_cals = model_cals.predict(input_df)[0]
            pred_fatigue = model_fatigue.predict(input_df)[0]
        else:
            return jsonify({"error": "Models are not loaded on the server."}), 500

        # 3. CALCULATE PACE (Derived from Time)
        # Pace = (Total Minutes) / Distance
        dist = input_df['distance_mi'][0]
        if dist > 0:
            pace_val = round((pred_time * 60) / dist, 1)
        else:
            pace_val = 0.0

        # --- SEND TO ARDUINO ---
        # Only send if we are running locally with a USB device attached
        # send_pace_to_arduino(pace_val) 

        # 4. REPLY TO FRONTEND
        response = {
            "time_hr": round(pred_time, 2),
            "calories": int(pred_cals),
            "fatigue": round(pred_fatigue * 10, 1), # Scale 0-1 to 0-10 for UI
            "pace": pace_val,
            "method": "AI_Prediction" # Just for debugging so you know it worked
        }
        
        print(f"Sending Response: {response}")
        return jsonify(response)

    except Exception as e:
        print(f"❌ Error during prediction: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Server is running on Port 5001")
    app.run(debug=True, use_reloader=False, port=5001)