#include <Wire.h>

// Prints the I2C address of every device found on A4(SDA)/A5(SCL).
// Open the Serial Monitor at 9600 baud after uploading.
void setup() {
  Serial.begin(9600);
  Wire.begin();
}

void loop() {
  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found I2C device at 0x");
      if (addr < 16) Serial.print('0');
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (found == 0) Serial.println("No I2C device found. Check GND/5V/SDA(A4)/SCL(A5).");
  Serial.println("---");
  delay(3000);
}
