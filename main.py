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
import serial.tools.list_ports
import time
import pandas as pd # Needed to format data for the AI
import joblib       # Needed to load the .pkl brain files
import os

# --- Trail module (OpenRouteService) ---
# Wrapped in try/except so the server still starts even if trail.py has issues.
try:
    from engine.trail import set_api_key, fetch_route, analyze_profile, compute_elevation_vs_time, generate_elevation_time_graph
    TRAIL_MODULE_OK = True
except Exception as e:
    print(f"[WARN] Trail module failed to load: {e}")
    TRAIL_MODULE_OK = False

# --- CONFIGURATION ---
BAUD_RATE = 115200

# --- OpenRouteService API Key ---
# Set your key here OR as an environment variable: ORS_API_KEY
if TRAIL_MODULE_OK:
    ORS_KEY = os.environ.get('ORS_API_KEY', None)
    if ORS_KEY:
        set_api_key(ORS_KEY)

app = Flask(__name__)
CORS(app)

# --- LOAD THE AI MODELS ---
# We load these once when the server starts so it's fast.
try:
    # Load the "Brains"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    MODEL_TIME_PATH = os.path.join(base_dir, 'model_time.pkl')
    MODEL_CALS_PATH = os.path.join(base_dir, 'model_calories.pkl')
    MODEL_FATIGUE_PATH = os.path.join(base_dir, 'model_fatigue.pkl')

    model_time = joblib.load(MODEL_TIME_PATH)
    model_cals = joblib.load(MODEL_CALS_PATH)
    model_fatigue = joblib.load(MODEL_FATIGUE_PATH)

    # Track mtimes so we can hot-reload the time model after retraining
    model_time_mtime = os.path.getmtime(MODEL_TIME_PATH)
    print("[OK] AI Models Loaded Successfully!")
except Exception as e:
    print(f"[ERROR] Could not load models. {e}")
    print("Did you run 'train_model.py'?")
    # If models fail, we set them to None and handle it later
    model_time = None
    model_cals = None
    model_fatigue = None

    MODEL_TIME_PATH = None
    model_time_mtime = None


def maybe_reload_time_model():
    """
    If `model_time.pkl` was retrained while the server is running,
    reload it so the website reflects changes without restarting Flask.
    """
    global model_time, model_time_mtime
    if MODEL_TIME_PATH is None or model_time is None:
        return
    try:
        cur_mtime = os.path.getmtime(MODEL_TIME_PATH)
        if model_time_mtime is None or cur_mtime > model_time_mtime:
            model_time = joblib.load(MODEL_TIME_PATH)
            model_time_mtime = cur_mtime
            print(f"[RELOAD] Reloaded time model from disk (mtime={model_time_mtime})")
    except Exception as e:
        print(f"[WARN] Could not reload time model: {e}")

# --- PERSISTENT ARDUINO CONNECTION ---
# We scan all COM ports at startup to find the ESP32 automatically.
# The connection stays open so there's no 2-second reset on every request.
arduino_conn = None

# Keywords that typically appear in ESP32 / Arduino USB serial device descriptions
ESP32_KEYWORDS = ['esp32', 'cp210', 'ch340', 'ch910', 'usb serial', 'uart', 'usb-serial']

def connect_arduino():
    """Auto-detect and connect to the Arduino/ESP32 on any COM port."""
    global arduino_conn

    ports = serial.tools.list_ports.comports()
    if not ports:
        print("[WARN] No COM ports found. Server will run without hardware.")
        arduino_conn = None
        return False

    print(f"[SCAN] Scanning {len(ports)} COM port(s) for Arduino/ESP32...")

    # Pass 1: Try ports whose description matches known ESP32 / USB-serial chips
    for port in ports:
        desc = (port.description or '').lower()
        print(f"   {port.device}: {port.description}")
        if any(kw in desc for kw in ESP32_KEYWORDS):
            if _try_connect(port.device):
                return True

    # Pass 2: If no known device matched, try every remaining port as fallback
    for port in ports:
        desc = (port.description or '').lower()
        if not any(kw in desc for kw in ESP32_KEYWORDS):
            if _try_connect(port.device):
                return True

    print("[WARN] Could not connect to any COM port. Server will run without hardware.")
    print("   Plug in the ESP32 and restart to enable.")
    arduino_conn = None
    return False

def _try_connect(port_name):
    """Attempt to open a serial connection on the given port."""
    global arduino_conn
    try:
        arduino_conn = serial.Serial(port_name, BAUD_RATE, timeout=2)
        time.sleep(2)  # wait for ESP32 to boot after initial connection
        print(f"[OK] Arduino connected on {port_name}")

        # Drain any startup messages from the Arduino
        while arduino_conn.in_waiting > 0:
            line = arduino_conn.readline().decode('utf-8', errors='replace').strip()
            if line:
                print(f"   [Arduino boot] {line}")

        return True
    except Exception as e:
        print(f"   ✗ {port_name} failed: {e}")
        arduino_conn = None
        return False

def send_pace_to_arduino(pace_value):
    """
    Sends the calculated pace to the watch via persistent USB connection.
    Also reads back any response from the Arduino for debugging.
    """
    global arduino_conn
    if arduino_conn is None:
        print("   [Arduino] Skipped — not connected")
        return False

    try:
        msg = f"PACE,{pace_value}\n"
        arduino_conn.write(msg.encode('utf-8'))
        print(f"   [Arduino] Sent: {msg.strip()}")

        # Give Arduino a moment to process and respond
        time.sleep(0.1)

        # Read back any debug/ACK messages from Arduino
        while arduino_conn.in_waiting > 0:
            response = arduino_conn.readline().decode('utf-8', errors='replace').strip()
            if response:
                print(f"   [Arduino] Received: {response}")

        return True
    except Exception as e:
        print(f"   [Arduino] Send failed: {e}")
        # Connection may be broken — try to reconnect next time
        try:
            arduino_conn.close()
        except:
            pass
        arduino_conn = None
        print("   [Arduino] Connection lost. Will skip until server restart.")
        return False

# Try to connect at startup (non-blocking if no device)
connect_arduino()

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Ensure latest time model is used after retraining
        maybe_reload_time_model()

        data = request.json
        print(f"Received Inputs: {data}")

        # ---- OPTIONAL: Fetch trail from OpenRouteService ----
        trail_data = None
        trail_segments = None

        start_lat = data.get('start_lat')
        start_lon = data.get('start_lon')
        end_lat   = data.get('end_lat')
        end_lon   = data.get('end_lon')

        # Only call ORS if ALL four coordinate fields are filled AND trail module loaded
        has_coords = (start_lat and start_lon and end_lat and end_lon)

        if has_coords and TRAIL_MODULE_OK:
            try:
                print("Fetching trail from OpenRouteService...")
                coords = fetch_route(
                    float(start_lon), float(start_lat),
                    float(end_lon),   float(end_lat)
                )
                trail_data = analyze_profile(coords)
                trail_segments = trail_data["segments"]
                print(f"Trail fetched: {trail_data['distance_mi']} mi, "
                      f"{trail_data['elevation_gain_ft']} ft gain")
            except Exception as trail_err:
                print(f"[WARN] Trail fetch failed (falling back to manual inputs): {trail_err}")
        elif has_coords and not TRAIL_MODULE_OK:
            print("[WARN] Coordinates provided but trail module not loaded, using manual inputs.")

        # 1. PARSE INPUTS
        # If we got trail data from ORS, use it; otherwise fall back to manual inputs.
        distance_mi      = trail_data["distance_mi"]      if trail_data else float(data.get('distance_mi') or 5.0)
        elevation_gain_ft = trail_data["elevation_gain_ft"] if trail_data else float(data.get('elevation_gain_ft') or 1000)

        input_df = pd.DataFrame([{
            'weight_lb':          float(data.get('weight_lb') or 160),
            'age':                float(data.get('age') or 22),
            'fitness_level':      float(data.get('fitness_level') or 0.5),
            'distance_mi':        distance_mi,
            'elevation_gain_ft':  elevation_gain_ft,
            'flat_speed_mph':     float(data.get('flat_speed_mph') or 3.0),
            'vertical_speed_fph': float(data.get('vertical_speed_fph') or 1000),
            'difficulty':         data.get('difficulty') or 'moderate',
            'activity_type':      data.get('activity_type') or 'hiking'
        }])

        # 2. ASK THE AI FOR PREDICTIONS
        if model_time is not None:
            pred_time    = model_time.predict(input_df)[0]
            pred_cals    = model_cals.predict(input_df)[0]
            pred_fatigue = model_fatigue.predict(input_df)[0]
        else:
            return jsonify({"error": "Models are not loaded on the server."}), 500

        # 3. CALCULATE PACE (Derived from Time)
        dist = input_df['distance_mi'][0]
        pace_val = 0
        # 3600 converts hours to seconds
        # round() gets us to the nearest whole number
        # int() ensures the data type is strictly an integer
        if dist > 0:
            pace_val = int(round((pred_time * 3600) / dist))
        else:
            pace_val = 0

        # For UI convenience, also provide formatted pace in min/mi.
        pace_min = pace_val // 60
        pace_sec = pace_val % 60
        pace_min_per_mi_str = f"{pace_min}:{pace_sec:02d}"
        pace_min_per_mi_float = round(pace_val / 60.0, 2) if pace_val > 0 else 0.0

        # --- SEND TO ARDUINO ---
        print(f"   [Arduino] Pace to send: {pace_val} sec/mi "
              f"({pace_val // 60}:{pace_val % 60:02d} min/mi)")
        send_pace_to_arduino(pace_val)

        # 4. BUILD RESPONSE
        response = {
            "time_hr":  round(pred_time, 2),
            "calories": int(pred_cals),
            "fatigue":  round(pred_fatigue * 10, 1),
            # Keep explicit units in response:
            "pace_sec_per_mi": pace_val,
            "pace_min_per_mi": pace_min_per_mi_float,
            "pace_min_per_mi_str": pace_min_per_mi_str,
            # Debug: helps confirm which model the server used
            "time_model_mtime": model_time_mtime,
            "method":   "AI_Prediction"
        }

        # 5. If we have trail segments, auto-fill trail info + generate graph
        if trail_segments and pace_val > 0:
            response["trail_distance_mi"]      = trail_data["distance_mi"]
            response["trail_elevation_gain_ft"] = trail_data["elevation_gain_ft"]
            response["trail_elevation_loss_ft"] = trail_data["elevation_loss_ft"]

            try:
                # ORS graph expects pace in minutes per mile (not seconds)
                time_elev = compute_elevation_vs_time(trail_segments, pace_val / 60.0)
                response["elevation_graph"] = generate_elevation_time_graph(time_elev)
                print(f"Graph generated: {len(response['elevation_graph'])} chars")
            except Exception as graph_err:
                print(f"[WARN] Graph generation failed: {graph_err}")

        print(f"Sending Response (graph included: {('elevation_graph' in response)})")
        return jsonify(response)

    except Exception as e:
        print(f"[ERROR] Error during prediction: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Server is running on Port 5001")
    app.run(debug=True, use_reloader=False, port=5001)