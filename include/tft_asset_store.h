#pragma once

#include <Arduino.h>

#include "external_flash.h"
#include "generated_tft_assets.h"

class TftAssetStore {
 public:
  bool begin(W25Q64Flash& flash);
  bool load(TftAssetId assetId);
  const uint16_t* pixels() const { return pixels_; }
  TftAssetId loadedAsset() const { return loadedAsset_; }
  const char* error() const { return error_; }

 private:
  W25Q64Flash* flash_ = nullptr;
  TftAssetId loadedAsset_ = TftAssetId::INVALID;
  const char* error_ = "not initialized";
  uint32_t imageSize_ = 0;
  uint16_t pixels_[TFT_ASSET_PIXEL_COUNT]{};
};

