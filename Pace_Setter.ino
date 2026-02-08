#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <math.h>
#include <Arduino.h>
#include <HardwareSerial.h>

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

double longitude = 0;
double latitude = 0;
double lastLongitude = 0;
double lastLatitude = 0;
bool firstLoop = true;
long lastTime = 0;
long currentTime = 0;

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

// XIAO ESP32-C3 pins
#define GPS_RX_PIN D7   // GPS TX -> D7
#define GPS_TX_PIN D6   // GPS RX -> D6 (optional)
#define GPS_BAUD   230400

HardwareSerial GPS(1);

// UBX parser state
enum UbxState { WAIT_SYNC1, WAIT_SYNC2, READ_CLASS, READ_ID, READ_LEN1, READ_LEN2, READ_PAYLOAD, READ_CKA, READ_CKB };
UbxState st = WAIT_SYNC1;

uint8_t msgClass = 0, msgId = 0;
uint16_t msgLen = 0;
uint16_t payloadIdx = 0;
uint8_t payload[128];     // NAV-PVT is 92 bytes
uint8_t ckA = 0, ckB = 0;

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

// SETUP
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

  GPS.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
}

// LOOP
void loop() {
  // Always keep motor + display service running
  updateMotor();
  updateDisplay();

  // Wait for target pace from Python (seconds per mile) BEFORE starting
  if (!targetPaceLocked) {
    checkForTargetPace();

    // While waiting, show prompt; keep motor off
    statusText = "SND PCE";
    setMotorState(ON_PACE);

    delayWithMotor(10);
    return;
  }

  // Start run once target pace is obtained
  if (!runStarted) {
    runStarted = true;

    // Reset run metrics as run begins
    metersTraveled = 0.0;
    CURRENT_PACE = TARGET_PACE; // initialize as on-pace

    statusText = "START";
    showStatusNow(); // hold status at least 1 second
  }

  if (GPS.available()) {
    currentTime = millis();
    uint8_t b = (uint8_t)GPS.read();
    parseUbxByte(b);
  }

  gpsToScreenTest(lastLongitude, lastLatitude, longitude, latitude, lastTime, currentTime); // need to change time from int to long
  // delayWithMotor(3000);

  lastLongitude = longitude;
  lastLatitude = latitude;
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

  if (secPerMile <= 0 || secPerMile > 7200) return;

  TARGET_PACE = secPerMile; 
  targetPaceLocked = true;

  statusText = "READY";
  showStatusNow();            // show READY immediately and hold >=1s

  Serial.println("PACE RECEIVED"); // optional ack
}

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

void gpsToScreenTest(double lastLon, double lastLat, double oneLon, double oneLat,
                     long lastTime, long oneTime) {
  double metersCovered = haversineMeters(lastLat, lastLon, oneLat, oneLon);
  metersTraveled += metersCovered;
  int timeDiff = int(oneTime - lastTime);
  CURRENT_PACE = metersAndSecToSecPerMile(metersCovered, timeDiff);

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

static inline void ckUpdate(uint8_t b) { ckA = ckA + b; ckB = ckB + ckA; }

static inline uint32_t u32le(const uint8_t* p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static inline int32_t i32le(const uint8_t* p) {
  return (int32_t)u32le(p);
}

void handleNavPvt(const uint8_t* p) {
  // NAV-PVT offsets:
  // 0  iTOW   U4 (ms)
  // 20 fixType U1 (0..5)
  // 23 numSV   U1
  // 24 lon     I4 (1e-7 deg)
  // 28 lat     I4 (1e-7 deg)
  // 60 gSpeed  I4 (mm/s)

  uint32_t iTOW = u32le(p + 0);
  uint8_t fixType = p[20];
  uint8_t numSV = p[23];
  int32_t lon_e7 = i32le(p + 24);
  int32_t lat_e7 = i32le(p + 28);
  int32_t gSpeed_mms = i32le(p + 60);

  double lat = lat_e7 * 1e-7;
  double lon = lon_e7 * 1e-7;
  double speed_mps = gSpeed_mms / 1000.0;
  double speed_mph = speed_mps * 2.2369362920544;

  // Print at ~1 Hz (NAV-PVT may arrive faster; this throttles output)
  static uint32_t lastPrintTow = 0;
  if (iTOW - lastPrintTow < 900) return;
  lastPrintTow = iTOW;

  Serial.print("fixType=");
  Serial.print(fixType);
  Serial.print(" SV=");
  Serial.print(numSV);
  Serial.print("  lat=");
  Serial.print(lat, 7);
  latitude = lat;
  Serial.print(" lon=");
  Serial.print(lon, 7);
  longitude = lon;
  Serial.print("  speed=");
  Serial.print(speed_mps, 2);
  Serial.print(" m/s (");
  Serial.print(speed_mph, 2);
  Serial.println(" mph)");

  if (firstLoop) {
    lastLongitude = longitude;
    lastLatitude = latitude;
    firstLoop = false;
  }
}

bool parseUbxByte(uint8_t b) {
  switch (st) {
    case WAIT_SYNC1:
      if (b == 0xB5) st = WAIT_SYNC2;
      break;

    case WAIT_SYNC2:
      if (b == 0x62) {
        st = READ_CLASS;
        ckA = ckB = 0;
      } else {
        st = WAIT_SYNC1;
      }
      break;

    case READ_CLASS:
      msgClass = b; ckUpdate(b); st = READ_ID;
      break;

    case READ_ID:
      msgId = b; ckUpdate(b); st = READ_LEN1;
      break;

    case READ_LEN1:
      msgLen = b; ckUpdate(b); st = READ_LEN2;
      break;

    case READ_LEN2:
      msgLen |= ((uint16_t)b << 8);
      ckUpdate(b);

      if (msgLen > sizeof(payload)) { st = WAIT_SYNC1; break; }
      payloadIdx = 0;
      st = (msgLen == 0) ? READ_CKA : READ_PAYLOAD;
      break;

    case READ_PAYLOAD:
      payload[payloadIdx++] = b;
      ckUpdate(b);
      if (payloadIdx >= msgLen) st = READ_CKA;
      break;

    case READ_CKA:
      if (b == ckA) st = READ_CKB;
      else st = WAIT_SYNC1;
      break;

    case READ_CKB:
      if (b == ckB) {
        // NAV-PVT is class 0x01 id 0x07 length 92
        if (msgClass == 0x01 && msgId == 0x07 && msgLen >= 92) {
          handleNavPvt(payload);
          st = WAIT_SYNC1;
          return true;
        }
      }
      st = WAIT_SYNC1;
      break;
  }
  return false;
}