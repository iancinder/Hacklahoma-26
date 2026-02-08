#include <Arduino.h>
#include <HardwareSerial.h>

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
  Serial.print(" lon=");
  Serial.print(lon, 7);
  Serial.print("  speed=");
  Serial.print(speed_mps, 2);
  Serial.print(" m/s (");
  Serial.print(speed_mph, 2);
  Serial.println(" mph)");
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

void setup() {
  Serial.begin(115200);
  delay(300);

  Serial.println("\n--- UBX NAV-PVT GPS TEST (lat/lon/speed) ---");
  Serial.println("Using GPS baud = 230400 (detected).");
  Serial.println("Wiring: GPS TX->D7, GPS RX->D6, 5V->5V, GND->GND\n");

  GPS.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
}

void loop() {
  while (GPS.available()) {
    uint8_t b = (uint8_t)GPS.read();
    parseUbxByte(b);
  }
}