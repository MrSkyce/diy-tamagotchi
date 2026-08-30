#pragma once

#include <Arduino.h>

struct PetSaveData {
  uint8_t hunger;
  uint8_t happiness;
  uint8_t health;
  uint8_t cleanliness;
  unsigned long ageMs;
};

bool loadPetSave(PetSaveData& data);
bool savePetSave(const PetSaveData& data);
bool clearPetSave();
