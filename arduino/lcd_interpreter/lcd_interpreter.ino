#include <string.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// I2C backpack wiring: GND, 5V, SDA=A4, SCL=A5.
// Serial protocol: "ROW1|ROW2\n" -> "OK".
// The LCD address (0x20..0x3F, usually 0x27 or 0x3F) is detected at startup.
LiquidCrystal_I2C* lcd = nullptr;
const uint8_t MAX_LINE = 40;
char packet[MAX_LINE];
uint8_t pos = 0;
bool overflow = false;

uint8_t findLcdAddress() {
  for (uint8_t addr = 0x20; addr <= 0x3F; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) return addr;
  }
  return 0;
}

void writeRow(uint8_t row, const char* text) {
  if (!lcd) return;
  lcd->setCursor(0, row);
  for (uint8_t i = 0; i < 16; i++) {
    char c = text[i];
    if (c == '\0') {
      for (; i < 16; i++) lcd->write(' ');
      return;
    }
    lcd->write((uint8_t)c);
  }
}

void onPacket() {
  if (overflow) {
    Serial.println("ERR:LONG");
  } else {
    packet[pos] = '\0';
    char* delimiter = strchr(packet, '|');
    if (!delimiter || strchr(delimiter + 1, '|') ||
        delimiter - packet > 16 || strlen(delimiter + 1) > 16) {
      Serial.println("ERR:FORMAT");
    } else if (!lcd) {
      Serial.println("ERR:NOLCD");
    } else {
      *delimiter = '\0';
      writeRow(0, packet);
      writeRow(1, delimiter + 1);
      Serial.println("OK");
    }
  }
  pos = 0;
  overflow = false;
}

void setup() {
  Serial.begin(9600);
  Wire.begin();
  uint8_t addr = findLcdAddress();
  if (addr) {
    lcd = new LiquidCrystal_I2C(addr, 16, 2);
    lcd->init();
    lcd->backlight();
    lcd->clear();
    writeRow(0, "AI TRANSLATOR");
    writeRow(1, "READY");
    Serial.print("LCD at 0x");
    Serial.println(addr, HEX);
  } else {
    Serial.println("NO I2C LCD FOUND");
  }
  Serial.println("READY");
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') { onPacket(); continue; }
    if (!overflow) {
      if (pos < MAX_LINE - 1) packet[pos++] = c;
      else overflow = true;
    }
  }
}
