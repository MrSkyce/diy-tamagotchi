#include <Preferences.h>

#include "config.h"
#include "persistence.h"

namespace {
constexpr char NVS_NAMESPACE[] = "tamagotchi";
constexpr char NVS_PET_KEY[] = "pet";
constexpr uint32_t PET_SAVE_MAGIC = 0x54414D41;  // "TAMA"
constexpr uint16_t PET_SAVE_VERSION = FIRMWARE_SAVE_VERSION;

struct StoredPet {
  uint32_t magic;
  uint16_t version;
  uint8_t hunger;
  uint8_t happiness;
  uint8_t health;
  uint8_t cleanliness;
  uint8_t fatigue;
  uint8_t appetite;
  uint8_t playfulness;
  uint8_t stubbornness;
  uint32_t ageMs;
  uint32_t checksum;
};

uint32_t petChecksum(const StoredPet& pet) {
  uint32_t checksum = PET_SAVE_MAGIC ^ PET_SAVE_VERSION;
  checksum = (checksum * 31U) ^ pet.hunger;
  checksum = (checksum * 31U) ^ pet.happiness;
  checksum = (checksum * 31U) ^ pet.health;
  checksum = (checksum * 31U) ^ pet.cleanliness;
  checksum = (checksum * 31U) ^ pet.fatigue;
  checksum = (checksum * 31U) ^ pet.appetite;
  checksum = (checksum * 31U) ^ pet.playfulness;
  checksum = (checksum * 31U) ^ pet.stubbornness;
  checksum = (checksum * 31U) ^ pet.ageMs;
  return checksum;
}

bool hasValidStats(const StoredPet& pet) {
  return pet.hunger <= 100 && pet.happiness <= 100 && pet.health <= 100 &&
         pet.cleanliness <= 100 && pet.fatigue <= 100 && pet.appetite <= 2 &&
         pet.playfulness <= 2 && pet.stubbornness <= 2;
}

bool hasValidSaveData(const PetSaveData& data) {
  return data.hunger <= 100 && data.happiness <= 100 && data.health <= 100 &&
         data.cleanliness <= 100 && data.fatigue <= 100 && data.appetite <= 2 &&
         data.playfulness <= 2 && data.stubbornness <= 2;
}
}  // namespace

bool loadPetSave(PetSaveData& data) {
  Preferences preferences;
  if (!preferences.begin(NVS_NAMESPACE, true)) return false;

  const size_t storedSize = preferences.getBytesLength(NVS_PET_KEY);
  if (storedSize != sizeof(StoredPet)) {
    preferences.end();
    return false;
  }

  StoredPet stored{};
  const size_t readSize = preferences.getBytes(NVS_PET_KEY, &stored, sizeof(stored));
  preferences.end();
  if (readSize != sizeof(stored) || stored.magic != PET_SAVE_MAGIC ||
      stored.version != PET_SAVE_VERSION || !hasValidStats(stored) ||
      stored.checksum != petChecksum(stored)) {
    return false;
  }

  data.hunger = stored.hunger;
  data.happiness = stored.happiness;
  data.health = stored.health;
  data.cleanliness = stored.cleanliness;
  data.fatigue = stored.fatigue;
  data.appetite = stored.appetite;
  data.playfulness = stored.playfulness;
  data.stubbornness = stored.stubbornness;
  data.ageMs = stored.ageMs;
  return true;
}

bool savePetSave(const PetSaveData& data) {
  if (!hasValidSaveData(data)) return false;

  StoredPet stored{};
  stored.magic = PET_SAVE_MAGIC;
  stored.version = PET_SAVE_VERSION;
  stored.hunger = data.hunger;
  stored.happiness = data.happiness;
  stored.health = data.health;
  stored.cleanliness = data.cleanliness;
  stored.fatigue = data.fatigue;
  stored.appetite = data.appetite;
  stored.playfulness = data.playfulness;
  stored.stubbornness = data.stubbornness;
  stored.ageMs = data.ageMs;
  stored.checksum = petChecksum(stored);

  Preferences preferences;
  if (!preferences.begin(NVS_NAMESPACE, false)) return false;
  const size_t writtenSize = preferences.putBytes(NVS_PET_KEY, &stored, sizeof(stored));
  preferences.end();
  return writtenSize == sizeof(stored);
}

bool clearPetSave() {
  Preferences preferences;
  if (!preferences.begin(NVS_NAMESPACE, false)) return false;
  const bool removed = preferences.remove(NVS_PET_KEY);
  preferences.end();
  return removed;
}
