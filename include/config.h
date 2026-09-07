#pragma once

#include <Arduino.h>

constexpr uint8_t BTN_LEFT = 21;
constexpr uint8_t BTN_OK = 3;
constexpr uint8_t BTN_RIGHT = 8;
constexpr uint8_t BUZZER_PIN = 5;

// Bus SPI partagé par le TFT ZJY154S0800TG01 et le W25Q64.
constexpr uint8_t FLASH_CS_PIN = 2;
constexpr uint8_t SPI_MISO_PIN = 20;
constexpr uint8_t TFT_DC_PIN = 7;
constexpr uint8_t TFT_MOSI_PIN = 6;
constexpr uint8_t TFT_SCLK_PIN = 4;
constexpr uint8_t TFT_BLK_PIN = 10;
constexpr uint8_t TFT_CS_PIN = 9;
// Le reset matériel est assuré par le réseau RC externe.
constexpr int8_t TFT_RST_PIN = -1;
constexpr uint16_t TFT_WIDTH = 240;
constexpr uint16_t TFT_HEIGHT = 240;
constexpr uint32_t TFT_SPI_FREQUENCY = 32000000;
constexpr uint32_t FLASH_SPI_FREQUENCY = 8000000;

constexpr uint8_t RTC_SDA_PIN = 0;
constexpr uint8_t RTC_SCL_PIN = 1;
constexpr uint8_t RTC_ADDRESS = 0x68;

#ifndef STARTUP_SERIAL_DELAY_MS
#define STARTUP_SERIAL_DELAY_MS 0UL
#endif
constexpr unsigned long STARTUP_SERIAL_DELAY = STARTUP_SERIAL_DELAY_MS;

#ifndef RTC_DIAGNOSTIC_REPORT_INTERVAL_MS
#define RTC_DIAGNOSTIC_REPORT_INTERVAL_MS 0UL
#endif
constexpr unsigned long RTC_DIAGNOSTIC_REPORT_INTERVAL =
    RTC_DIAGNOSTIC_REPORT_INTERVAL_MS;

// Affiche discretement dans le coin droit des ecrans de transition.
constexpr char FIRMWARE_VERSION[] = "v0.7";
// Schéma NVS associé à la version affichée v0.7.
constexpr uint16_t FIRMWARE_SAVE_VERSION = 7;

// A press is accepted only after this duration at a stable logic level.
constexpr unsigned long BUTTON_DEBOUNCE_INTERVAL = 35;

constexpr unsigned long PET_SAVE_DEBOUNCE_INTERVAL = 3000;
constexpr unsigned long PET_SAVE_CHECKPOINT_INTERVAL = 300000;
constexpr unsigned long PET_RESET_HOLD_INTERVAL = 5000;
constexpr unsigned long ACTION_SCREEN_DURATION = 1500;
constexpr unsigned long STATUS_SCREEN_DURATION = 4000;

#ifndef INACTIVITY_SLEEP_INTERVAL_MS
#define INACTIVITY_SLEEP_INTERVAL_MS (10UL * 60UL * 1000UL)
#endif
constexpr unsigned long INACTIVITY_SLEEP_INTERVAL = INACTIVITY_SLEEP_INTERVAL_MS;
constexpr unsigned long SLEEP_NOTICE_DURATION = 1000;
