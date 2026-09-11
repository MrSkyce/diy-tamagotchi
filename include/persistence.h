#pragma once

#include <stdint.h>

struct PetSaveData {
  uint8_t hunger;
  uint8_t happiness;
  uint8_t health;
  uint8_t cleanliness;
  uint8_t fatigue;
  uint8_t appetite;
  uint8_t playfulness;
  uint8_t stubbornness;
  uint8_t lifeStage;
  uint8_t warmth;
  uint64_t ageMs;
  uint64_t stageStartedAgeMs;
  uint32_t rtcUnixTime;
  uint8_t mascot;  // Stable species ID: legacy saves always restore the dragon.
};

enum class PetLoadStatus { Loaded, Missing, Invalid, Unavailable };
PetLoadStatus readPetSave(PetSaveData& data);
bool loadPetSave(PetSaveData& data);
bool savePetSave(const PetSaveData& data);
bool clearPetSave();
