const int feedbackPin = 8; 

float currentPace = 0.0;

void setup() {
  // 115200 MUST match the Python script
  Serial.begin(115200);
  
  pinMode(feedbackPin, OUTPUT);
  
  // Blink once on startup to show it's alive
  digitalWrite(feedbackPin, HIGH);
  delay(200);
  digitalWrite(feedbackPin, LOW);
}

void loop() {
  // 1. LISTEN: Is Python talking to us?
  if (Serial.available() > 0) {
    // Read the incoming number (e.g. "12.0")
    String data = Serial.readStringUntil('\n');
    
    // Convert to float and save it
    currentPace = data.toFloat();
    
    // Quick blink to confirm we got it
    digitalWrite(feedbackPin, HIGH);
    delay(100);
    digitalWrite(feedbackPin, LOW);
  }

  // 2. ACT: Do something based on the stored pace
  // This runs forever, even if you unplug the USB (if you have a battery)
  if (currentPace > 0) {
    
    // Example Logic:
    // Fast Pace (< 10 min/mile) -> Fast Blinks
    // Slow Pace (> 10 min/mile) -> Slow Blinks
    
    if (currentPace < 10) {
      digitalWrite(feedbackPin, HIGH);
      delay(200); // Fast
      digitalWrite(feedbackPin, LOW);
      delay(200);
    } else {
      digitalWrite(feedbackPin, HIGH);
      delay(1000); // Slow
      digitalWrite(feedbackPin, LOW);
      delay(1000);
    }
  }
}