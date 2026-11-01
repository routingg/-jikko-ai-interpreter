#include <string.h>
#include <LiquidCrystal.h>

// Verified user wiring: RS=7, E=8, D4=9, D5=10, D6=11, D7=12.
LiquidCrystal lcd(7, 8, 9, 10, 11, 12);
const uint8_t MAX_LINE = 40;
char packet[MAX_LINE];
uint8_t pos = 0;
bool overflow = false;

void writeRow(uint8_t row, const char* text) {
  lcd.setCursor(0, row);
  for (uint8_t i = 0; i < 16; i++) {
    char c = text[i];
    if (c == '\0') {
      for (; i < 16; i++) lcd.write(' ');
      return;
    }
    lcd.write((uint8_t)c);
  }
}
void onPacket() {
  if (overflow) {
    Serial.println("ERR:LONG");
  } else {
    packet[pos] = '\0';
    // Protocol: two ASCII rows, separated by '|', newline-terminated.
    char* delimiter = strchr(packet, '|');
    if (!delimiter || strchr(delimiter + 1, '|') ||
        delimiter - packet > 16 || strlen(delimiter + 1) > 16) {
      Serial.println("ERR:FORMAT");
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
  lcd.begin(16, 2);
  lcd.clear();
  writeRow(0, "AI TRANSLATOR");
  writeRow(1, "READY");
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
