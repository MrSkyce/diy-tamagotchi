#pragma once

#include <Arduino.h>

constexpr uint8_t SCREEN_WIDTH = 128;
constexpr uint8_t SCREEN_HEIGHT = 64;
constexpr uint8_t SDA_PIN = 0;
constexpr uint8_t SCL_PIN = 1;
constexpr uint8_t OLED_ADDR = 0x3C;
constexpr uint8_t BTN_LEFT = 21;
constexpr uint8_t BTN_OK = 20;
constexpr uint8_t BTN_RIGHT = 10;
constexpr uint8_t BUZZER_PIN = 4;

// A press is accepted only after this duration at a stable logic level.
constexpr unsigned long BUTTON_DEBOUNCE_INTERVAL = 35;

constexpr unsigned long PET_SAVE_DEBOUNCE_INTERVAL = 3000;
constexpr unsigned long PET_SAVE_CHECKPOINT_INTERVAL = 300000;
