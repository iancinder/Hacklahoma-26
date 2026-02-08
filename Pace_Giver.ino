#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <math.h>
#include <Arduino.h>

/*
From program to watch
Pace (in seconds)
Activity: run, hike

From phone to watch
GPS coordinates
*/

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

#define RUNNING 1
#define HIKING 2

#define SPEED_UP 1
#define SLOW_DOWN 2
#define ON_PACE 3

#define MOTOR_PIN D2

int PACE_TOLERANCE = 10; // in percent
int CURRENT_PACE; // in seconds
int TARGET_PACE; // in seconds

int MOTOR_STATE = ON_PACE; // default
unsigned long motorNextMs = 0;
int motorStep = 0;

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void setup() {
  Serial.begin(115200);

  // XIAO ESP32-C6 I2C pins
  Wire.begin(D4, D5);
  delay(100);
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println("SSD1306 init failed");
    while (1)
      ;
  }
  drawScreen("Target: ", "BOOTING", "Current: ");

  pinMode(MOTOR_PIN, OUTPUT);
  analogWrite(MOTOR_PIN, 0);
}

/////////////LOOP/////////////
void loop() {
  updateMotor();

  int targetPace = 8 * 60; // minutes per mile

  //////////// Speed Up Test /////////////
  // Time 1
  int lastTime = 0; // in seconds
  double lastLat = 35.205000;
  double lastLon = -97.445000;
  // Time 2
  int oneTime = 1; // in seconds
  double oneLat = 35.205025;
  double oneLon = -97.445000;
  // Screen
  gpsToScreenTest(lastLon, lastLat, oneLon, oneLat, lastTime, oneTime, targetPace);
  // speedUpMotor();
  delayWithMotor(3000);

  //////////// On Pace Test /////////////
  // Time 1
  lastTime = 0; // in seconds
  lastLat = 35.205000;
  lastLon = -97.445000;
  // Time 2
  oneTime = 1; // in seconds
  oneLat = 35.205030;
  oneLon = -97.445000;
  // Screen
  gpsToScreenTest(lastLon, lastLat, oneLon, oneLat, lastTime, oneTime, targetPace);
  delayWithMotor(3000);

  //////////// Slow Down Test /////////////
  // Time 1
  lastTime = 0; // in seconds
  lastLat = 35.205000;
  lastLon = -97.445000;
  // Time 2
  oneTime = 1; // in seconds
  oneLat = 35.205040;
  oneLon = -97.445000;
  // Screen
  gpsToScreenTest(lastLon, lastLat, oneLon, oneLat, lastTime, oneTime, targetPace);
  // slowDownMotor();
  delayWithMotor(3000);
}
/////////////LOOP/////////////

// ---------- Helpers ----------
static inline double deg2rad(double deg) {
  return deg * (M_PI / 180.0);
}
static inline double mpsToKph(double mps) { 
  return mps * 3.6; 
}
static inline double mpsToMph(double mps) { 
  return mps * 2.2369362920544; 
}
int metersAndSecToSecPerMile(double meters, int seconds) {
  if (meters <= 0.0 || seconds <= 0) return 9999;  // invalid / stopped
  return (int)round((1609.344 * seconds) / meters);
}
int percentFromTarget() {
  // negative percent means you're going faster so slow down
  // positive percent means you're going slower so speed up
  if (TARGET_PACE == 0) { return 0; }
  return (CURRENT_PACE - TARGET_PACE) * 100 / TARGET_PACE;
}
String intSecondsToStringMinutes(int seconds) {
  int minutes = seconds / 60;
  int leftoverSeconds = seconds % 60;
  String str = String(minutes) + ":";
  if (leftoverSeconds < 10) { str += "0"; }
  str += String(leftoverSeconds);
  return str;
}

// meters between two lat/lon points (degrees)
double haversineMeters(double lat1, double lon1, double lat2, double lon2) {
  const double R = 6371000.0; // Earth radius (m)
  double dLat = deg2rad(lat2 - lat1);
  double dLon = deg2rad(lon2 - lon1);

  double a = sin(dLat/2) * sin(dLat/2) +
             cos(deg2rad(lat1)) * cos(deg2rad(lat2)) *
             sin(dLon/2) * sin(dLon/2);

  double c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a));
  return R * c;
}

// returns speed in meters/second, or NAN if unusable
double speedMpsFromFixes(double lastLat, double lastLon, uint32_t lastMs,
                         double curLat,  double curLon,  uint32_t curMs) {
  uint32_t dtMs = curMs - lastMs;  // ok with uint32 wrap if curMs is later
  if (dtMs < 300) return NAN;      // too soon (GPS jitter dominates)

  double dt = dtMs / 1000.0;
  double d  = haversineMeters(lastLat, lastLon, curLat, curLon);

  // jitter guard: ignore tiny motion over short windows
  if (d < 0.7 && dt < 2.0) return 0.0;

  return d / dt;
}
// ---------- End Helpers ----------


// Chooses what to set the screen based on pace metrics
void setScreen(int percent) {
  String curPace = "Current: " + intSecondsToStringMinutes(CURRENT_PACE);
  String tarPace = "Target: " + intSecondsToStringMinutes(TARGET_PACE);
  // use ".c_str()" to convert from String to "const char*"

  if (abs(percent) < PACE_TOLERANCE) {
    drawScreen(tarPace.c_str(), "ON PACE", curPace.c_str());
    setMotorState(ON_PACE);
  }
  else if (percent > PACE_TOLERANCE) {
    drawScreen(tarPace.c_str(), "SPD UP", curPace.c_str());
    setMotorState(SPEED_UP);
  }
  else if (percent < -PACE_TOLERANCE) {
    drawScreen(tarPace.c_str(), "SLW DWN", curPace.c_str());
    setMotorState(SLOW_DOWN);
  }
  else { // failsafe
    drawScreen("ERROR", "ERROR", "ERROR");
    analogWrite(MOTOR_PIN, 0);
  }
}

// Draws three lines of text on the screen
void drawScreen(const char* top,
                const char* middle,
                const char* bottom) {

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  /* ---------- Top (Yellow Area ~0–15 px) ---------- */
  display.setTextSize(1);
  display.setCursor(0, 2);
  display.println(top);

  /* ---------- Middle (Big Text, Blue Area) ---------- */
  display.setTextSize(3);

  int16_t x1, y1;
  uint16_t w, h;
  display.getTextBounds(middle, 0, 0, &x1, &y1, &w, &h);

  int midX = (SCREEN_WIDTH - w) / 2;
  int midY = 22;  // visually centered in blue region

  display.setCursor(midX, midY);
  display.println(middle);

  /* ---------- Bottom (Small Text, Blue Area) ---------- */
  display.setTextSize(1);
  display.setCursor(0, 54);
  display.println(bottom);

  display.display();
}

void timeToScreenTest(int current, int target) {
  CURRENT_PACE = current;
  TARGET_PACE = target;

  setScreen(percentFromTarget());
}

void gpsToScreenTest(double lastLon, double lastLat, double oneLon, double oneLat, int lastTime, int oneTime, int targetPace) {
  double metersCovered = haversineMeters(lastLat, lastLon, oneLat, oneLon); // gives meters
  int currentPace = metersAndSecToSecPerMile(metersCovered, (oneTime - lastTime));
  CURRENT_PACE = currentPace;
  TARGET_PACE = targetPace;
  setScreen(percentFromTarget());
}

// void slowDownMotor() {
//   // Ramp DOWN
//   for (int duty = 255; duty >= 0; duty -= 5) {
//     analogWrite(MOTOR_PIN, duty);
//     delay(20);
//   }
// }

// void speedUpMotor() {
//   // Ramp UP
//   for (int duty = 0; duty <= 255; duty += 5) {
//     analogWrite(MOTOR_PIN, duty);
//     delay(20);
//   }
// }

void setMotorState(int state) {
  // Only reset the pattern if the state changes
  if (MOTOR_STATE == state) return;

  MOTOR_STATE = state;
  motorNextMs = 0;
  motorStep = 0;
  analogWrite(MOTOR_PIN, 0); // ensure off
}

// Call this EVERY loop (non-blocking)
void updateMotor() {
  unsigned long now = millis();
  if (now < motorNextMs) return;

  // ---------- SPEED UP ----------
  if (MOTOR_STATE == SPEED_UP) {
    if (motorStep == 0) { analogWrite(MOTOR_PIN, 255); motorNextMs = now + 250; motorStep = 1; }
    else               { analogWrite(MOTOR_PIN, 0);   motorNextMs = now + 500; motorStep = 0; }
  }

  // ---------- SLOW DOWN ----------
  else if (MOTOR_STATE == SLOW_DOWN) {
    if (motorStep == 0) { analogWrite(MOTOR_PIN, 255); motorNextMs = now + 500; motorStep = 1; }
    else               { analogWrite(MOTOR_PIN, 0);   motorNextMs = now + 500; motorStep = 0; }
  }

  // ---------- ON PACE ----------
  else {
    analogWrite(MOTOR_PIN, 0);
    motorNextMs = now + 200;
    motorStep = 0;
  }
}

void delayWithMotor(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    updateMotor();   // keep stepping the vibration pattern
    delay(1);        // yield a tiny bit
  }
}