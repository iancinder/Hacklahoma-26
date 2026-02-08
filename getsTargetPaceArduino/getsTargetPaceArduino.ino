// ESP32-C6 USB Receiver & Saver

// This variable stores the target pace PERMANENTLY (in RAM)
float savedPace = 0.0;

void setup() {
  Serial.begin(115200);
}

void loop() {
  // 1. RECEIVE & SAVE
  // Check if Python sent a new number
  if (Serial.available() > 0) {
    
    // Read the text (e.g., "12.5")
    String receivedString = Serial.readStringUntil('\n');
    
    // Convert text to a math number (float)
    float newPace = receivedString.toFloat();
    
    // Verify it's a valid number before saving
    if (newPace > 0) {
      savedPace = newPace;
      
      // Echo back to Python (Optional, for debugging)
      // Serial.print("UPDATED PACE TO: ");
      // Serial.println(savedPace);
    }
  }

  // 2. USE THE SAVED NUMBER
  // This part runs continuously using the LAST saved number.
  
  if (savedPace > 0) {
    // --- YOUR HARDWARE LOGIC GOES HERE ---
    // Since we don't know your LED pin, this part is empty for now.
    // But the variable 'savedPace' DOES hold the number 12.5 (or whatever).
    
    // Example Logic you can add later:
    // if (currentSpeed < savedPace) { vibrate(); }
  }
  
  // distinct delay to prevent crashing the chip
  delay(10); 
}