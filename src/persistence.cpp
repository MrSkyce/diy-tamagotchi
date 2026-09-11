#include <Preferences.h>
#include <nvs.h>

#include "config.h"
#include "pet_save_codec.h"

namespace {
constexpr char NVS_NAMESPACE[] = "tamagotchi";
constexpr char NVS_PET_KEY[] = "pet";
static_assert(FIRMWARE_SAVE_VERSION == PetSaveCodec::kVersion, "save schema mismatch");
}

PetLoadStatus readPetSave(PetSaveData& data) {
  nvs_handle_t handle;
  esp_err_t result = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
  if (result == ESP_ERR_NVS_NOT_FOUND) return PetLoadStatus::Missing;
  if (result != ESP_OK) return PetLoadStatus::Unavailable;
  size_t size = 0;
  result = nvs_get_blob(handle, NVS_PET_KEY, nullptr, &size);
  if (result != ESP_OK) {
    nvs_close(handle);
    return result == ESP_ERR_NVS_NOT_FOUND ? PetLoadStatus::Missing : PetLoadStatus::Unavailable;
  }
  if (size != PetSaveCodec::kLegacySize && size != PetSaveCodec::kSize) {
    nvs_close(handle);
    return PetLoadStatus::Invalid;
  }
  uint8_t bytes[PetSaveCodec::kSize]{};
  size_t readSize = size;
  result = nvs_get_blob(handle, NVS_PET_KEY, bytes, &readSize);
  nvs_close(handle);
  if (result != ESP_OK || readSize != size) return PetLoadStatus::Unavailable;
  return PetSaveCodec::decode(bytes, size, data) ? PetLoadStatus::Loaded : PetLoadStatus::Invalid;
}

bool loadPetSave(PetSaveData& data) {
  return readPetSave(data) == PetLoadStatus::Loaded;
}

bool savePetSave(const PetSaveData& data) {
  uint8_t bytes[PetSaveCodec::kSize]{};
  if (!PetSaveCodec::encode(data, bytes, sizeof(bytes))) return false;
  Preferences preferences;
  if (!preferences.begin(NVS_NAMESPACE, false)) return false;
  // One NVS blob write: the identity cannot commit separately from the pet.
  const size_t written = preferences.putBytes(NVS_PET_KEY, bytes, sizeof(bytes));
  preferences.end();
  return written == sizeof(bytes);
}

bool clearPetSave() {
  Preferences preferences;
  if (!preferences.begin(NVS_NAMESPACE, false)) return false;
  const bool removed = preferences.remove(NVS_PET_KEY);
  preferences.end();
  return removed;
}
