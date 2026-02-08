#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <math.h>
#include <Arduino.h>

/*
Goal:
- Receive TARGET_PACE (seconds per mile) once from Python over USB Serial before the run starts.
- Lock it (do NOT change every loop).
- After target pace is obtained, start the run logic.
- Screen alternates every second between STATUS (ON PACE / SPD UP / SLW DWN) and DISTANCE (mi).
- When state changes, screen snaps to STATUS first and holds it for at least 1 second.
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

int PACE_TOLERANCE = 10; // percent tolerance band

int CURRENT_PACE = 0; // seconds per mile
int TARGET_PACE  = 0; // seconds per mile (locked once received)

// Motor pattern state
int MOTOR_STATE = ON_PACE;
unsigned long motorNextMs = 0;
int motorStep = 0;

// Distance
double metersTraveled = 0.0;

// Display flip state
unsigned long displayNextMs = 0;
bool showDistance = false;
const char* statusText = "BOOT";

// Run state / serial target locking
bool targetPaceLocked = false;
bool runStarted = false;

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ---------- Forward declarations ----------
void updateMotor();
void updateDisplay();
void delayWithMotor(unsigned long ms);
void showStatusNow();
void setMotorState(int state);
void gpsToScreenTest(double lastLon, double lastLat, double oneLon, double oneLat,
                     int lastTime, int oneTime);

static inline double deg2rad(double deg);
int metersAndSecToSecPerMile(double meters, int seconds);
int percentFromTarget();
String intSecondsToStringMinutes(int seconds);
double haversineMeters(double lat1, double lon1, double lat2, double lon2);
void drawScreen(const char* top, const char* middle, const char* bottom);
void checkForTargetPace();

// ---------- Setup ----------
void setup() {
  Serial.begin(115200);

  // XIAO ESP32-C6 I2C pins
  Wire.begin(D4, D5);
  delay(100);

  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println("SSD1306 init failed");
    while (1) {}
  }

  pinMode(MOTOR_PIN, OUTPUT);
  analogWrite(MOTOR_PIN, 0);

  drawScreen("Target: --:--", "BOOTING", "Current: --:--");
}

// ---------- Main loop ----------
void loop() {
  // Always keep motor + display service running
  updateMotor();
  updateDisplay();

  // 1) Wait for target pace from Python (seconds per mile) BEFORE starting
  if (!targetPaceLocked) {
    checkForTargetPace();

    // While waiting, show prompt; keep motor off
    statusText = "SND PCE";
    setMotorState(ON_PACE);

    delayWithMotor(10);
    return;
  }

  // 2) Start run once target pace is obtained (only once)
  if (!runStarted) {
    runStarted = true;

    // Reset run metrics as run begins
    metersTraveled = 0.0;
    CURRENT_PACE = TARGET_PACE; // initialize as on-pace

    statusText = "START";
    showStatusNow(); // hold status at least 1 second
  }

  // 3) ----- TEMP TEST BLOCKS (replace later with iPhone GPS packets) -----

  // Speed Up Test
  {
    int lastTime = 0;
    double lastLat = 35.205000;
    double lastLon = -97.445000;

    int oneTime = 1;
    double oneLat = 35.205025;
    double oneLon = -97.445000;

    gpsToScreenTest(lastLon, lastLat, oneLon, oneLat, lastTime, oneTime);
    delayWithMotor(3000);
  }

  // On Pace Test
  {
    int lastTime = 0;
    double lastLat = 35.205000;
    double lastLon = -97.445000;

    int oneTime = 1;
    double oneLat = 35.205030;
    double oneLon = -97.445000;

    gpsToScreenTest(lastLon, lastLat, oneLon, oneLat, lastTime, oneTime);
    delayWithMotor(3000);
  }

  // Slow Down Test
  {
    int lastTime = 0;
    double lastLat = 35.205000;
    double lastLon = -97.445000;

    int oneTime = 1;
    double oneLat = 35.205040;
    double oneLon = -97.445000;

    gpsToScreenTest(lastLon, lastLat, oneLon, oneLat, lastTime, oneTime);
    delayWithMotor(3000);
  }
}

// ---------- Receive target pace from Python over USB Serial ----------
// Expected: "PACE,480\n" where 480 is seconds per mile.
void checkForTargetPace() {
  if (targetPaceLocked) return;
  if (!Serial.available()) return;

  String msg = Serial.readStringUntil('\n');
  msg.trim();

  if (!msg.startsWith("PACE,")) return;

  int secPerMile = msg.substring(5).toInt();

  // Optional sanity check (0 < pace < 2 hours/mi)
  if (secPerMile <= 0 || secPerMile > 7200) return;

  TARGET_PACE = secPerMile;   // ✅ already seconds per mile
  targetPaceLocked = true;

  statusText = "READY";
  showStatusNow();            // show READY immediately and hold >=1s

  Serial.println("PACE RECEIVED"); // optional ack
}

// ---------- Helpers ----------
static inline double deg2rad(double deg) {
  return deg * (M_PI / 180.0);
}

int metersAndSecToSecPerMile(double meters, int seconds) {
  if (meters <= 0.0 || seconds <= 0) return 9999;
  return (int)round((1609.344 * seconds) / meters);
}

int percentFromTarget() {
  if (TARGET_PACE == 0) return 0;
  return (CURRENT_PACE - TARGET_PACE) * 100 / TARGET_PACE;
}

String intSecondsToStringMinutes(int seconds) {
  int minutes = seconds / 60;
  int leftoverSeconds = seconds % 60;
  String str = String(minutes) + ":";
  if (leftoverSeconds < 10) str += "0";
  str += String(leftoverSeconds);
  return str;
}

double haversineMeters(double lat1, double lon1, double lat2, double lon2) {
  const double R = 6371000.0;
  double dLat = deg2rad(lat2 - lat1);
  double dLon = deg2rad(lon2 - lon1);

  double a = sin(dLat/2) * sin(dLat/2) +
             cos(deg2rad(lat1)) * cos(deg2rad(lat2)) *
             sin(dLon/2) * sin(dLon/2);

  double c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a));
  return R * c;
}

// ---------- Screen ----------
void drawScreen(const char* top, const char* middle, const char* bottom) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(1);
  display.setCursor(0, 2);
  display.println(top);

  display.setTextSize(3);
  int16_t x1, y1;
  uint16_t w, h;
  display.getTextBounds(middle, 0, 0, &x1, &y1, &w, &h);

  int midX = (SCREEN_WIDTH - w) / 2;
  int midY = 22;
  display.setCursor(midX, midY);
  display.println(middle);

  display.setTextSize(1);
  display.setCursor(0, 54);
  display.println(bottom);

  display.display();
}

void updateDisplay() {
  unsigned long now = millis();
  if (now < displayNextMs) return;
  displayNextMs = now + 1000;

  showDistance = !showDistance;

  String top = (TARGET_PACE > 0)
    ? ("Target: " + intSecondsToStringMinutes(TARGET_PACE))
    : "Target: --:--";

  String bottom = (CURRENT_PACE > 0 && CURRENT_PACE < 9000)
    ? ("Current: " + intSecondsToStringMinutes(CURRENT_PACE))
    : "Current: --:--";

  if (!showDistance) {
    drawScreen(top.c_str(), statusText, bottom.c_str());
  } else {
    double miles = metersTraveled / 1609.34;
    String distStr = String(miles, 2) + " mi";
    drawScreen(top.c_str(), distStr.c_str(), bottom.c_str());
  }
}

void showStatusNow() {
  showDistance = false;              // status first
  displayNextMs = millis() + 1000;   // hold status for at least 1s

  String top = (TARGET_PACE > 0)
    ? ("Target: " + intSecondsToStringMinutes(TARGET_PACE))
    : "Target: --:--";

  String bottom = (CURRENT_PACE > 0 && CURRENT_PACE < 9000)
    ? ("Current: " + intSecondsToStringMinutes(CURRENT_PACE))
    : "Current: --:--";

  drawScreen(top.c_str(), statusText, bottom.c_str());
}

// ---------- Pace -> status + motor ----------
void gpsToScreenTest(double lastLon, double lastLat, double oneLon, double oneLat,
                     int lastTime, int oneTime) {
  double metersCovered = haversineMeters(lastLat, lastLon, oneLat, oneLon);
  metersTraveled += metersCovered;

  CURRENT_PACE = metersAndSecToSecPerMile(metersCovered, (oneTime - lastTime));

  int percent = percentFromTarget();

  if (abs(percent) < PACE_TOLERANCE) {
    statusText = "ON PACE";
    setMotorState(ON_PACE);
  } else if (percent > PACE_TOLERANCE) {
    statusText = "SPD UP";
    setMotorState(SPEED_UP);
  } else {
    statusText = "SLW DWN";
    setMotorState(SLOW_DOWN);
  }
}

// ---------- Motor ----------
void setMotorState(int state) {
  if (MOTOR_STATE == state) return;

  MOTOR_STATE = state;
  motorNextMs = 0;
  motorStep = 0;
  analogWrite(MOTOR_PIN, 0);

  showStatusNow(); // snap to status screen on changes
}

void updateMotor() {
  unsigned long now = millis();
  if (now < motorNextMs) return;

  if (MOTOR_STATE == SPEED_UP) {
    // ON 250, OFF 250, ON 250, OFF 500
    if (motorStep == 0) { analogWrite(MOTOR_PIN, 255); motorNextMs = now + 250; motorStep = 1; }
    else if (motorStep == 1) { analogWrite(MOTOR_PIN, 0); motorNextMs = now + 250; motorStep = 2; }
    else if (motorStep == 2) { analogWrite(MOTOR_PIN, 255); motorNextMs = now + 250; motorStep = 3; }
    else { analogWrite(MOTOR_PIN, 0); motorNextMs = now + 500; motorStep = 0; }
  }
  else if (MOTOR_STATE == SLOW_DOWN) {
    // ON 500, OFF 500
    if (motorStep == 0) { analogWrite(MOTOR_PIN, 255); motorNextMs = now + 500; motorStep = 1; }
    else { analogWrite(MOTOR_PIN, 0); motorNextMs = now + 500; motorStep = 0; }
  }
  else {
    analogWrite(MOTOR_PIN, 0);
    motorNextMs = now + 200;
    motorStep = 0;
  }
}

void delayWithMotor(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    updateMotor();
    updateDisplay();
    delay(1);
  }
}