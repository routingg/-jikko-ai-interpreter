#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_NeoPixel.h>

// Finds which Arduino pin the NeoPixel data line is wired to.
// Every few seconds it lights the 4 pixels dim red on the next candidate pin
// and shows that pin number on the LCD, then turns them off again. Note the
// number shown while the pixels are lit. Pins 0/1 (USB serial) and A4/A5 (LCD I2C) are skipped.
const uint8_t PINS[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, A0, A1, A2, A3};
const uint8_t PIN_COUNT = sizeof(PINS) / sizeof(PINS[0]);
const uint8_t PIXELS = 4;
const unsigned long HOLD_MS = 4000;

Adafruit_NeoPixel strip(PIXELS, 6, NEO_GRB + NEO_KHZ800);
LiquidCrystal_I2C* lcd = nullptr;

void showPin(uint8_t pin) {
  if (!lcd) return;
  lcd->clear();
  lcd->setCursor(0, 0);
  lcd->print("NeoPixel pin:");
  lcd->setCursor(0, 1);
  if (pin >= A0) { lcd->print("A"); lcd->print(pin - A0); }
  else lcd->print(pin);
}

void setup() {
  Wire.begin();
  for (uint8_t addr = 0x20; addr <= 0x3F && !lcd; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      lcd = new LiquidCrystal_I2C(addr, 16, 2);
      lcd->init();
      lcd->backlight();
    }
  }
  strip.begin();
  strip.setBrightness(40);
}

void loop() {
  for (uint8_t i = 0; i < PIN_COUNT; i++) {
    strip.setPin(PINS[i]);
    for (uint8_t p = 0; p < PIXELS; p++) strip.setPixelColor(p, strip.Color(255, 0, 0));
    showPin(PINS[i]);
    unsigned long until = millis() + HOLD_MS;
    while (millis() < until) {
      strip.show();  // resend so a late-connected strip still latches
      delay(50);
    }
    // NeoPixels keep their last color, so switch them off on this same pin before
    // moving on. That way they are lit only while the correct pin is active.
    strip.clear();
    strip.show();
    delay(50);
  }
}
