import serial
import time

SERIAL_PORT = 'COM4'  # <--- CHECK THIS!
BAUD_RATE = 115200

try:
    print(f"🔌 Connecting to {SERIAL_PORT}...")
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
    time.sleep(2) # Wait for reboot
    
    # 1. FLUSH the pipes (clear old garbage)
    arduino.reset_input_buffer()

    # 2. SEND the data
    test_pace = "12.5"
    print(f"📤 Sending Pace: {test_pace}")
    arduino.write(f"{test_pace}\n".encode('utf-8'))
    time.sleep(0.5) # Give it a moment to reply

    # 3. READ the reply (The "Spy" part)
    if arduino.in_waiting > 0:
        response = arduino.read(arduino.in_waiting).decode('utf-8').strip()
        print(f"✅ ESP32 SAID: {response}")
    else:
        print("⚠️ No response received (Did you upload the listener code?)")

    arduino.close()

except Exception as e:
    print(f"❌ Error: {e}")