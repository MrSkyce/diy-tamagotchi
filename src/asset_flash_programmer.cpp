#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>

#include "config.h"
#include "external_flash.h"
#include "generated_tft_asset_blob.h"
#include "generated_tft_assets.h"

namespace {

Adafruit_ST7789 tft(&SPI, TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);
W25Q64Flash flash;

void drawStatus(const char* title, const char* detail, uint16_t color,
                uint8_t percent = 0) {
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextWrap(false);
  tft.setTextSize(2);
  tft.setTextColor(color);
  tft.setCursor(12, 30);
  tft.print(title);
  tft.setTextSize(1);
  tft.setTextColor(ST77XX_WHITE);
  tft.setCursor(12, 72);
  tft.print(detail);
  tft.drawRect(12, 112, 216, 20, ST77XX_WHITE);
  if (percent > 0) {
    tft.fillRect(15, 115, (210 * percent) / 100, 14, color);
  }
  tft.setCursor(12, 150);
  tft.printf("%u assets / %lu bytes", TFT_ASSET_COUNT,
             static_cast<unsigned long>(tft_asset_flash_image_size));
}

bool imageMatchesFlash() {
  uint8_t actual[256];
  for (size_t offset = 0; offset < tft_asset_flash_image_size;
       offset += sizeof(actual)) {
    const size_t length = min(sizeof(actual), tft_asset_flash_image_size - offset);
    flash.readBytes(offset, actual, length);
    for (size_t index = 0; index < length; ++index) {
      const uint8_t expected =
          pgm_read_byte(tft_asset_flash_image + offset + index);
      if (actual[index] != expected) {
        return false;
      }
    }
  }
  return true;
}

bool programImage() {
  if (tft_asset_flash_image_size != TFT_ASSET_FLASH_IMAGE_SIZE) {
    Serial.println("Generated asset size mismatch");
    return false;
  }
  if (imageMatchesFlash()) {
    Serial.println("The exact asset image is already present; no erase needed");
    return true;
  }

  drawStatus("ERASING", "W25Q64 asset area", ST77XX_YELLOW);
  Serial.printf("Erasing %lu bytes...\n",
                static_cast<unsigned long>(tft_asset_flash_image_size));
  if (!flash.eraseRange(0, tft_asset_flash_image_size)) {
    Serial.println("Erase failed or timed out");
    return false;
  }

  uint8_t page[256];
  uint8_t lastPercent = 0;
  for (size_t offset = 0; offset < tft_asset_flash_image_size;) {
    const size_t length = min(sizeof(page), tft_asset_flash_image_size - offset);
    for (size_t index = 0; index < length; ++index) {
      page[index] = pgm_read_byte(tft_asset_flash_image + offset + index);
    }
    if (!flash.programPage(offset, page, length)) {
      Serial.printf("Programming failed at 0x%06lX\n",
                    static_cast<unsigned long>(offset));
      return false;
    }
    offset += length;
    const uint8_t percent = (offset * 100UL) / tft_asset_flash_image_size;
    if (percent >= lastPercent + 10) {
      lastPercent = percent;
      drawStatus("PROGRAMMING", "Writing compressed sprites", ST77XX_CYAN,
                 percent);
      Serial.printf("Programming: %u%%\n", percent);
    }
  }

  drawStatus("VERIFYING", "Reading every byte", ST77XX_CYAN);
  Serial.println("Verifying every programmed byte...");
  if (!imageMatchesFlash()) {
    Serial.println("Full byte-for-byte verification failed");
    return false;
  }
  return true;
}

}  // namespace

void setup() {
  Serial.begin(115200);
  // Laisse le temps au moniteur USB CDC de se reconnecter après l'upload.
  delay(10000);
  pinMode(TFT_BLK_PIN, OUTPUT);
  digitalWrite(TFT_BLK_PIN, HIGH);
  flash.configureChipSelects();
  SPI.begin(TFT_SCLK_PIN, SPI_MISO_PIN, TFT_MOSI_PIN, -1);
  tft.init(TFT_WIDTH, TFT_HEIGHT, SPI_MODE3);
  tft.setRotation(0);
  tft.invertDisplay(true);
  tft.setSPISpeed(TFT_SPI_FREQUENCY);

  const W25QJedecId id = flash.readJedecId();
  Serial.printf("W25Q64 JEDEC: %02X %02X %02X\n", id.manufacturer,
                id.memoryType, id.capacity);
  if (!flash.isExpectedDevice()) {
    drawStatus("FLASH ERROR", "Expected EF 40 17", ST77XX_RED);
    Serial.println("Expected W25Q64 EF 40 17; programming aborted");
    return;
  }

  if (!programImage()) {
    drawStatus("WRITE FAILED", "See serial monitor", ST77XX_RED);
    return;
  }

  drawStatus("ASSETS READY", "Full verify passed", ST77XX_GREEN, 100);
  Serial.printf("ASSET FLASH OK: %u assets, %lu bytes, catalog %08lX\n",
                TFT_ASSET_COUNT,
                static_cast<unsigned long>(tft_asset_flash_image_size),
                static_cast<unsigned long>(TFT_ASSET_CATALOG_CRC32));
}

void loop() {
  delay(1000);
}
