#include <Preferences.h>

#include "persistence.h"

namespace {
constexpr char NVS_NAMESPACE[] = "tamagotchi";
constexpr char NVS_PET_KEY[] = "pet";
constexpr uint32_t PET_SAVE_MAGIC = 0x54414D41;  // "TAMA"
constexpr uint16_t PET_SAVE_VERSION = 3;

struct StoredPetHeader {
  uint32_t magic;
  uint16_t version;
};

struct StoredPetV1 {
  uint32_t magic;
  uint16_t version;
  uint8_t hunger;
  uint8_t happiness;
  uint8_t health;
  uint32_t ageMs;
  uint32_t checksum;
};

struct StoredPetV2 {
  uint32_t magic;
  uint16_t version;
  uint8_t hunger;
  uint8_t happiness;
  uint8_t health;
  uint8_t cleanliness;
  uint32_t ageMs;
  uint32_t checksum;
};

struct StoredPetV3 {
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

uint32_t petChecksumV3(const StoredPetV3& pet) {
  uint32_t checksum = PET_SAVE_MAGIC ^ 3U;
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

uint32_t petChecksumV2(const StoredPetV2& pet) {
  uint32_t checksum = PET_SAVE_MAGIC ^ 2U;
  checksum = (checksum * 31U) ^ pet.hunger;
  checksum = (checksum * 31U) ^ pet.happiness;
  checksum = (checksum * 31U) ^ pet.health;
  checksum = (checksum * 31U) ^ pet.cleanliness;
  checksum = (checksum * 31U) ^ pet.ageMs;
  return checksum;
}

uint32_t petChecksumV1(const StoredPetV1& pet) {
  uint32_t checksum = PET_SAVE_MAGIC ^ 1U;
  checksum = (checksum * 31U) ^ pet.hunger;
  checksum = (checksum * 31U) ^ pet.happiness;
  checksum = (checksum * 31U) ^ pet.health;
  checksum = (checksum * 31U) ^ pet.ageMs;
  return checksum;
}

bool hasValidStatsV2(const StoredPetV2& pet) {
  return pet.hunger <= 100 && pet.happiness <= 100 && pet.health <= 100 &&
         pet.cleanliness <= 100;
}

bool hasValidStatsV3(const StoredPetV3& pet) {
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
  if (storedSize < sizeof(StoredPetHeader)) {
    preferences.end();
    return false;
  }

  StoredPetHeader header{};
  const size_t headerReadSize =
      preferences.getBytes(NVS_PET_KEY, &header, sizeof(header));
  if (headerReadSize != sizeof(header) || header.magic != PET_SAVE_MAGIC) {
    preferences.end();
    return false;
  }

  if (header.version == 1 && storedSize == sizeof(StoredPetV1)) {
    StoredPetV1 legacy{};
    const size_t readSize = preferences.getBytes(NVS_PET_KEY, &legacy, sizeof(legacy));
    preferences.end();
    if (readSize != sizeof(legacy)) return false;
    if (legacy.hunger > 100 || legacy.happiness > 100 || legacy.health > 100 ||
        legacy.checksum != petChecksumV1(legacy)) {
      return false;
    }
    data.hunger = legacy.hunger;
    data.happiness = legacy.happiness;
    data.health = legacy.health;
    data.cleanliness = 100;
    data.fatigue = 0;
    data.appetite = 1;
    data.playfulness = 1;
    data.stubbornness = 1;
    data.ageMs = legacy.ageMs;
    return true;
  }

  if (header.version == 2 && storedSize == sizeof(StoredPetV2)) {
    StoredPetV2 legacy{};
    const size_t readSize = preferences.getBytes(NVS_PET_KEY, &legacy, sizeof(legacy));
    preferences.end();
    if (readSize != sizeof(legacy) || !hasValidStatsV2(legacy) ||
        legacy.checksum != petChecksumV2(legacy)) {
      return false;
    }
    data.hunger = legacy.hunger;
    data.happiness = legacy.happiness;
    data.health = legacy.health;
    data.cleanliness = legacy.cleanliness;
    data.fatigue = 0;
    data.appetite = 1;
    data.playfulness = 1;
    data.stubbornness = 1;
    data.ageMs = legacy.ageMs;
    return true;
  }

  if (header.version != PET_SAVE_VERSION || storedSize != sizeof(StoredPetV3)) {
    preferences.end();
    return false;
  }

  StoredPetV3 stored{};
  const size_t readSize = preferences.getBytes(NVS_PET_KEY, &stored, sizeof(stored));
  preferences.end();
  if (readSize != sizeof(stored) || !hasValidStatsV3(stored) ||
      stored.checksum != petChecksumV3(stored)) {
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

  StoredPetV3 stored{};
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
  stored.checksum = petChecksumV3(stored);

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
