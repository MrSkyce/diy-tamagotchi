#pragma once

#include <Arduino.h>

constexpr uint8_t SCREEN_WIDTH = 128;
constexpr uint8_t SCREEN_HEIGHT = 64;
constexpr uint8_t SDA_PIN = 0;
constexpr uint8_t SCL_PIN = 1;
constexpr uint8_t OLED_ADDR = 0x3C;
constexpr uint8_t BTN_LEFT = 21;
constexpr uint8_t BTN_OK = 3;
constexpr uint8_t BTN_RIGHT = 10;
constexpr uint8_t BUZZER_PIN = 4;

// Affiche discretement dans le coin droit des ecrans de transition.
constexpr char FIRMWARE_VERSION[] = "v0.5";
// Schéma NVS associé à la version affichée v0.5.
constexpr uint16_t FIRMWARE_SAVE_VERSION = 5;

// A press is accepted only after this duration at a stable logic level.
constexpr unsigned long BUTTON_DEBOUNCE_INTERVAL = 35;

constexpr unsigned long PET_SAVE_DEBOUNCE_INTERVAL = 3000;
constexpr unsigned long PET_SAVE_CHECKPOINT_INTERVAL = 300000;
constexpr unsigned long ACTION_SCREEN_DURATION = 1500;
constexpr unsigned long STATUS_SCREEN_DURATION = 4000;

// Valeurs courtes pour valider la veille sur le prototype ; à augmenter pour la batterie.
constexpr unsigned long INACTIVITY_SLEEP_INTERVAL = 30000;
constexpr unsigned long SLEEP_NOTICE_DURATION = 1000;
