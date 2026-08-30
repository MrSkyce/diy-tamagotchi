#pragma once

#include <Arduino.h>

struct PetSaveData {
  uint8_t hunger;
  uint8_t happiness;
  uint8_t health;
  uint8_t cleanliness;
  uint8_t fatigue;
  uint8_t appetite;
  uint8_t playfulness;
  uint8_t stubbornness;
  unsigned long ageMs;
};

bool loadPetSave(PetSaveData& data);
bool savePetSave(const PetSaveData& data);
bool clearPetSave();
