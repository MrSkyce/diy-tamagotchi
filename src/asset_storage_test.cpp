#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>

#include "config.h"
#include "external_flash.h"
#include "generated_tft_assets.h"
#include "tft_asset_store.h"

namespace {

Adafruit_ST7789 tft(&SPI, TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);
W25Q64Flash flash;
TftAssetStore assets;
bool assetsReady = false;
uint16_t currentAsset = 0;
uint32_t lastFrameAt = 0;

void drawCentered(const char* text, int16_t y, uint8_t size,
                  uint16_t color) {
  int16_t x1;
  int16_t y1;
  uint16_t width;
  uint16_t height;
  tft.setTextSize(size);
  tft.getTextBounds(text, 0, y, &x1, &y1, &width, &height);
  tft.setTextColor(color);
  tft.setCursor((TFT_WIDTH - width) / 2, y);
  tft.print(text);
}

bool drawAsset(uint16_t index) {
  const TftAssetId id = static_cast<TftAssetId>(index);
  const uint32_t startedAt = micros();
  if (!assets.load(id)) return false;
  const uint32_t loadUs = micros() - startedAt;
  Serial.printf("asset %02u load %lu us\n", index,
                static_cast<unsigned long>(loadUs));

  constexpr int16_t x0 = (TFT_WIDTH - TFT_ASSET_WIDTH) / 2;
  constexpr int16_t y0 = 55;
  constexpr uint16_t background = 0x1085;
  const uint16_t* pixels = assets.pixels();
  uint16_t line[TFT_ASSET_WIDTH];
  tft.fillRect(0, 36, TFT_WIDTH, 178, background);
  tft.startWrite();
  tft.setAddrWindow(x0, y0, TFT_ASSET_WIDTH, TFT_ASSET_HEIGHT);
  for (int16_t y = 0; y < TFT_ASSET_HEIGHT; ++y) {
    for (int16_t x = 0; x < TFT_ASSET_WIDTH; ++x) {
      const uint16_t pixel = pixels[y * TFT_ASSET_WIDTH + x];
      line[x] = pixel == TFT_ASSET_TRANSPARENT ? background : pixel;
    }
    tft.writePixels(line, TFT_ASSET_WIDTH);
  }
  tft.endWrite();
  char label[24];
  snprintf(label, sizeof(label), "ASSET %02u / %02u", index + 1,
           TFT_ASSET_COUNT);
  drawCentered(label, 190, 1, ST77XX_WHITE);
  return true;
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(10000);
  pinMode(TFT_BLK_PIN, OUTPUT);
  digitalWrite(TFT_BLK_PIN, HIGH);
  flash.configureChipSelects();
  SPI.begin(TFT_SCLK_PIN, SPI_MISO_PIN, TFT_MOSI_PIN, -1);
  tft.init(TFT_WIDTH, TFT_HEIGHT, SPI_MODE3);
  tft.setRotation(0);
  tft.invertDisplay(true);
  tft.setSPISpeed(TFT_SPI_FREQUENCY);
  tft.fillScreen(ST77XX_BLACK);
  drawCentered("ASSET STORE TEST", 12, 2, ST77XX_CYAN);

  assetsReady = assets.begin(flash);
  if (!assetsReady) {
    drawCentered("FAILED", 96, 2, ST77XX_RED);
    drawCentered(assets.error(), 130, 1, ST77XX_WHITE);
    Serial.printf("ASSET STORE ERROR: %s\n", assets.error());
    return;
  }

  uint32_t totalUs = 0;
  uint32_t maximumUs = 0;
  for (uint16_t index = 0; index < TFT_ASSET_COUNT; ++index) {
    const uint32_t startedAt = micros();
    if (!assets.load(static_cast<TftAssetId>(index))) {
      assetsReady = false;
      Serial.printf("ASSET %u FAILED: %s\n", index, assets.error());
      break;
    }
    const uint32_t elapsed = micros() - startedAt;
    totalUs += elapsed;
    maximumUs = max(maximumUs, elapsed);
  }
  if (!assetsReady) {
    drawCentered("CRC FAILED", 96, 2, ST77XX_RED);
    return;
  }

  Serial.printf("ASSET STORE OK: %u/%u CRC valid, total %lu us, max %lu us\n",
                TFT_ASSET_COUNT, TFT_ASSET_COUNT,
                static_cast<unsigned long>(totalUs),
                static_cast<unsigned long>(maximumUs));
  drawCentered("33 CRC OK", 218, 2, ST77XX_GREEN);
  drawAsset(currentAsset);
  lastFrameAt = millis();
}

void loop() {
  if (!assetsReady || millis() - lastFrameAt < 300) return;
  lastFrameAt += 300;
  currentAsset = (currentAsset + 1) % TFT_ASSET_COUNT;
  if (!drawAsset(currentAsset)) {
    assetsReady = false;
    Serial.printf("ASSET %u FAILED DURING LOOP: %s\n", currentAsset,
                  assets.error());
  }
}

