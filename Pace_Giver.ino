#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

#define WALKING 1
#define RUNNING 2
#define HIKING 3

int PACE_TOLERANCE;
int CURRENT_PACE;
int TARGET_PACE;

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

void loop() {
  delay(1000);
  drawScreen("Target: 7:00", "SPD UP", "Current: 8:00");
  delay(1000);
  drawScreen("Target: 8:45", "ON PACE", "Current: 8:47");
  delay(1000);
  drawScreen("Target: 8:45", "SLW DWN", "Current: 8:47");
}

int setScreen() {

}

/* -------- Screen Drawing -------- */
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