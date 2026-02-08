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

int PACE_TOLERANCE = 10; // in percent
int CURRENT_PACE; // in seconds
int TARGET_PACE; // in seconds

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
}

/////////////LOOP/////////////
void loop() {
  slowDownTest();
  delay(2000);
  onPaceTest();
  delay(2000);
  speedUpTest();
  delay(2000);
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
// ---------- End Helpers ----------


// Chooses what to set the screen based on pace metrics
void setScreen(int percent) {
  String curPace = "Current: " + intSecondsToStringMinutes(CURRENT_PACE);
  String tarPace = "Target: " + intSecondsToStringMinutes(TARGET_PACE);
  // use ".c_str()" to convert from String to "const char*"

  if (abs(percent) < PACE_TOLERANCE) {
    drawScreen(tarPace.c_str(), "ON PACE", curPace.c_str());
  }
  else if (percent > PACE_TOLERANCE) {
    drawScreen(tarPace.c_str(), "SPD UP", curPace.c_str());
  }
  else if (percent < -PACE_TOLERANCE) {
    drawScreen(tarPace.c_str(), "SLW DWN", curPace.c_str());
  }
  else { // failsafe
    drawScreen("ERROR", "ERROR", "ERROR");
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

void speedUpTest(){
  int current = 9*60; // 9 min
  int target = 8*60; // 8 min

  CURRENT_PACE = current;
  TARGET_PACE = target;

  setScreen(percentFromTarget());
}

void onPaceTest(){
  int current = 9*60; // 9 min
  int target = 9*60; // 9 min

  CURRENT_PACE = current;
  TARGET_PACE = target;

  setScreen(percentFromTarget());
}

void slowDownTest(){
  int current = 8*60; // 9 min
  int target = 9*60; // 9 min

  CURRENT_PACE = current;
  TARGET_PACE = target;

  setScreen(percentFromTarget());
}