#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// I2C backpack wiring: GND, 5V, SDA=A4, SCL=A5. Address is 0x27 or 0x3F
// (find it with arduino/i2c_scanner). Shows a static message, no Serial.
const uint8_t LCD_ADDRESS = 0x27;
LiquidCrystal_I2C lcd(LCD_ADDRESS, 16, 2);

void setup() {
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("LCD READY");
  lcd.setCursor(0, 1);
  lcd.print("HELLO WORLD!");
}
void loop() {}
