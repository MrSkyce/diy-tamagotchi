#include "tft_asset_store.h"

#include <cstring>

namespace {

constexpr uint8_t EXPECTED_MAGIC[8] = {'T', 'A', 'M', 'A', 'S', 'P', 'R', 0};
constexpr uint32_t HEADER_SIZE = 24;
constexpr uint32_t ENTRY_SIZE = 16;
constexpr size_t READ_BUFFER_SIZE = 256;

uint16_t readLe16(const uint8_t* data) {
  return static_cast<uint16_t>(data[0]) |
         static_cast<uint16_t>(data[1]) << 8;
}

uint32_t readLe32(const uint8_t* data) {
  return static_cast<uint32_t>(data[0]) |
         static_cast<uint32_t>(data[1]) << 8 |
         static_cast<uint32_t>(data[2]) << 16 |
         static_cast<uint32_t>(data[3]) << 24;
}

uint32_t updateCrc32(uint32_t crc, uint8_t value) {
  crc ^= value;
  for (uint8_t bit = 0; bit < 8; ++bit) {
    crc = (crc >> 1) ^ (0xEDB88320UL & (0UL - (crc & 1)));
  }
  return crc;
}

class BufferedFlashReader {
 public:
  BufferedFlashReader(W25Q64Flash& flash, uint32_t address, uint32_t length)
      : flash_(flash), address_(address), remaining_(length) {}

  bool read(uint8_t& value) {
    if (bufferOffset_ >= bufferLength_ && !refill()) return false;
    value = buffer_[bufferOffset_++];
    return true;
  }

  bool finished() const {
    return remaining_ == 0 && bufferOffset_ == bufferLength_;
  }

 private:
  bool refill() {
    if (remaining_ == 0) return false;
    bufferLength_ = min(static_cast<uint32_t>(READ_BUFFER_SIZE), remaining_);
    flash_.readBytes(address_, buffer_, bufferLength_);
    address_ += bufferLength_;
    remaining_ -= bufferLength_;
    bufferOffset_ = 0;
    return true;
  }

  W25Q64Flash& flash_;
  uint32_t address_;
  uint32_t remaining_;
  uint8_t buffer_[READ_BUFFER_SIZE]{};
  size_t bufferOffset_ = 0;
  size_t bufferLength_ = 0;
};

}  // namespace

bool TftAssetStore::begin(W25Q64Flash& flash) {
  flash_ = &flash;
  loadedAsset_ = TftAssetId::INVALID;
  if (!flash.isExpectedDevice()) {
    error_ = "W25Q64 not detected";
    return false;
  }

  uint8_t header[HEADER_SIZE];
  flash.readBytes(0, header, sizeof(header));
  if (memcmp(header, EXPECTED_MAGIC, sizeof(EXPECTED_MAGIC)) != 0) {
    error_ = "asset image missing";
    return false;
  }
  if (readLe16(header + 8) != TFT_ASSET_FORMAT_VERSION) {
    error_ = "asset format mismatch";
    return false;
  }
  if (readLe16(header + 10) != TFT_ASSET_COUNT) {
    error_ = "asset count mismatch";
    return false;
  }
  if (readLe32(header + 12) != TFT_ASSET_CATALOG_CRC32) {
    error_ = "asset catalog mismatch";
    return false;
  }
  imageSize_ = readLe32(header + 16);
  if (imageSize_ != TFT_ASSET_FLASH_IMAGE_SIZE) {
    error_ = "asset image size mismatch";
    return false;
  }
  error_ = "none";
  return true;
}

bool TftAssetStore::load(TftAssetId assetId) {
  if (assetId == loadedAsset_) return true;
  const uint16_t index = static_cast<uint16_t>(assetId);
  if (flash_ == nullptr || index >= TFT_ASSET_COUNT) {
    error_ = "invalid asset id";
    return false;
  }

  uint8_t entry[ENTRY_SIZE];
  flash_->readBytes(HEADER_SIZE + index * ENTRY_SIZE, entry, sizeof(entry));
  const uint32_t offset = readLe32(entry);
  const uint32_t compressedSize = readLe32(entry + 4);
  const uint32_t expectedCrc = readLe32(entry + 8);
  const uint16_t width = readLe16(entry + 12);
  const uint16_t height = readLe16(entry + 14);
  if (width != TFT_ASSET_WIDTH || height != TFT_ASSET_HEIGHT ||
      offset < HEADER_SIZE + ENTRY_SIZE * TFT_ASSET_COUNT ||
      compressedSize == 0 || offset > imageSize_ ||
      compressedSize > imageSize_ - offset) {
    error_ = "invalid asset entry";
    loadedAsset_ = TftAssetId::INVALID;
    return false;
  }

  BufferedFlashReader reader(*flash_, offset, compressedSize);
  size_t output = 0;
  uint32_t crc = 0xFFFFFFFFUL;
  while (output < TFT_ASSET_PIXEL_COUNT) {
    uint8_t control;
    if (!reader.read(control)) {
      error_ = "truncated asset data";
      loadedAsset_ = TftAssetId::INVALID;
      return false;
    }
    const size_t count = (control & 0x7F) + 1;
    if (count > TFT_ASSET_PIXEL_COUNT - output) {
      error_ = "asset RLE overflow";
      loadedAsset_ = TftAssetId::INVALID;
      return false;
    }

    if (control & 0x80) {
      uint8_t low;
      uint8_t high;
      if (!reader.read(low) || !reader.read(high)) {
        error_ = "truncated RLE run";
        loadedAsset_ = TftAssetId::INVALID;
        return false;
      }
      const uint16_t pixel = static_cast<uint16_t>(low) |
                             static_cast<uint16_t>(high) << 8;
      for (size_t item = 0; item < count; ++item) {
        pixels_[output++] = pixel;
        crc = updateCrc32(updateCrc32(crc, low), high);
      }
    } else {
      for (size_t item = 0; item < count; ++item) {
        uint8_t low;
        uint8_t high;
        if (!reader.read(low) || !reader.read(high)) {
          error_ = "truncated RLE literal";
          loadedAsset_ = TftAssetId::INVALID;
          return false;
        }
        pixels_[output++] = static_cast<uint16_t>(low) |
                            static_cast<uint16_t>(high) << 8;
        crc = updateCrc32(updateCrc32(crc, low), high);
      }
    }
  }

  if (!reader.finished() || (crc ^ 0xFFFFFFFFUL) != expectedCrc) {
    error_ = "asset CRC mismatch";
    loadedAsset_ = TftAssetId::INVALID;
    return false;
  }
  loadedAsset_ = assetId;
  error_ = "none";
  return true;
}
