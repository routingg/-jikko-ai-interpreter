#include <LiquidCrystal.h>
// Pins already confirmed to work: RS,E,D4,D5,D6,D7
LiquidCrystal lcd(7, 8, 9, 10, 11, 12);
void setup() {
  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("LCD READY");
  lcd.setCursor(0,1);
  lcd.print("HELLO WORLD!");
}
void loop() {}
