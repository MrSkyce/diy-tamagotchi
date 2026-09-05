#include <Arduino.h>

#include "config.h"

constexpr uint8_t TEST_PINS[] = {
    TFT_SCLK_PIN, TFT_MOSI_PIN, TFT_DC_PIN, TFT_RST_PIN};
constexpr const char* TEST_PIN_NAMES[] = {
    "SCLK GPIO4", "MOSI GPIO6", "DC GPIO7", "RST GPIO20"};
constexpr size_t TEST_PIN_COUNT = sizeof(TEST_PINS) / sizeof(TEST_PINS[0]);
constexpr unsigned long LOW_INTERVAL_MS = 2000;
constexpr unsigned long HIGH_INTERVAL_MS = 10000;

void setAllPinsLow() {
  for (const uint8_t pin : TEST_PINS) digitalWrite(pin, LOW);
}

void setup() {
  Serial.begin(115200);
  for (const uint8_t pin : TEST_PINS) pinMode(pin, OUTPUT);
  setAllPinsLow();
}

void loop() {
  for (size_t index = 0; index < TEST_PIN_COUNT; ++index) {
    setAllPinsLow();
    Serial.printf("%s LOW\n", TEST_PIN_NAMES[index]);
    delay(LOW_INTERVAL_MS);

    digitalWrite(TEST_PINS[index], HIGH);
    Serial.printf("%s HIGH\n", TEST_PIN_NAMES[index]);
    delay(HIGH_INTERVAL_MS);
  }
}
