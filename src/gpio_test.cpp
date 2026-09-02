#include <Arduino.h>

constexpr uint8_t TEST_PINS[] = {5, 6, 7, 20};
constexpr const char* TEST_PIN_NAMES[] = {"SCL GPIO5", "SDA GPIO6", "DC GPIO7",
                                          "RES GPIO20"};
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
