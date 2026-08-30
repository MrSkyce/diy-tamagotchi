#include <Preferences.h>

#include "persistence.h"

namespace {
constexpr char NVS_NAMESPACE[] = "tamagotchi";
constexpr char NVS_PET_KEY[] = "pet";
constexpr uint32_t PET_SAVE_MAGIC = 0x54414D41;  // "TAMA"
constexpr uint16_t PET_SAVE_VERSION = 1;

struct StoredPet {
  uint32_t magic;
  uint16_t version;
  uint8_t hunger;
  uint8_t happiness;
  uint8_t health;
  uint32_t ageMs;
  uint32_t checksum;
};

uint32_t petChecksum(const StoredPet& pet) {
  uint32_t checksum = PET_SAVE_MAGIC ^ PET_SAVE_VERSION;
  checksum = (checksum * 31U) ^ pet.hunger;
  checksum = (checksum * 31U) ^ pet.happiness;
  checksum = (checksum * 31U) ^ pet.health;
  checksum = (checksum * 31U) ^ pet.ageMs;
  return checksum;
}

bool hasValidStats(const StoredPet& pet) {
  return pet.hunger <= 100 && pet.happiness <= 100 && pet.health <= 100;
}
}  // namespace

bool loadPetSave(PetSaveData& data) {
  Preferences preferences;
  if (!preferences.begin(NVS_NAMESPACE, true)) return false;

  if (preferences.getBytesLength(NVS_PET_KEY) != sizeof(StoredPet)) {
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
  data.ageMs = stored.ageMs;
  return true;
}

bool savePetSave(const PetSaveData& data) {
  StoredPet stored{};
  stored.magic = PET_SAVE_MAGIC;
  stored.version = PET_SAVE_VERSION;
  stored.hunger = data.hunger;
  stored.happiness = data.happiness;
  stored.health = data.health;
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
