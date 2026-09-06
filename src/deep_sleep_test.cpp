#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include <driver/gpio.h>
#include <esp_sleep.h>

#include "config.h"

namespace {

Adafruit_ST7789 tft(&SPI, TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);

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

void initialiseDisplay() {
  pinMode(FLASH_CS_PIN, OUTPUT);
  digitalWrite(FLASH_CS_PIN, HIGH);
  pinMode(TFT_CS_PIN, OUTPUT);
  digitalWrite(TFT_CS_PIN, HIGH);
  pinMode(TFT_BLK_PIN, OUTPUT);
  digitalWrite(TFT_BLK_PIN, HIGH);

  SPI.begin(TFT_SCLK_PIN, SPI_MISO_PIN, TFT_MOSI_PIN, -1);
  tft.init(TFT_WIDTH, TFT_HEIGHT, SPI_MODE3);
  tft.setRotation(0);
  tft.invertDisplay(true);
  tft.setSPISpeed(TFT_SPI_FREQUENCY);
  tft.fillScreen(ST77XX_BLACK);
  tft.drawRect(0, 0, TFT_WIDTH, TFT_HEIGHT, ST77XX_WHITE);
}

void enterTestSleep() {
  drawCentered("BACKLIGHT OFF", 102, 2, ST77XX_YELLOW);
  delay(1000);
  tft.enableDisplay(false);
  digitalWrite(TFT_BLK_PIN, LOW);

  const esp_err_t holdResult =
      gpio_hold_en(static_cast<gpio_num_t>(TFT_BLK_PIN));
  if (holdResult != ESP_OK) {
    digitalWrite(TFT_BLK_PIN, HIGH);
    tft.enableDisplay(true);
    tft.fillScreen(ST77XX_BLACK);
    drawCentered("BLK HOLD FAIL", 105, 2, ST77XX_RED);
    Serial.printf("BLK hold failed: %d\n", holdResult);
    return;
  }
  gpio_deep_sleep_hold_en();

  const esp_err_t wakeResult = esp_deep_sleep_enable_gpio_wakeup(
      1ULL << BTN_OK, ESP_GPIO_WAKEUP_GPIO_LOW);
  if (wakeResult != ESP_OK) {
    gpio_deep_sleep_hold_dis();
    gpio_hold_dis(static_cast<gpio_num_t>(TFT_BLK_PIN));
    digitalWrite(TFT_BLK_PIN, HIGH);
    tft.enableDisplay(true);
    tft.fillScreen(ST77XX_BLACK);
    drawCentered("WAKE SETUP FAIL", 105, 2, ST77XX_RED);
    Serial.printf("Wake setup failed: %d\n", wakeResult);
    return;
  }

  Serial.println("Entering deep sleep; press OK to wake");
  Serial.flush();
  esp_deep_sleep_start();
}

} // namespace

void setup() {
  gpio_deep_sleep_hold_dis();
  gpio_hold_dis(static_cast<gpio_num_t>(TFT_BLK_PIN));
  pinMode(BTN_OK, INPUT_PULLUP);

  Serial.begin(115200);
  delay(500);
  const esp_sleep_wakeup_cause_t wakeCause = esp_sleep_get_wakeup_cause();
  initialiseDisplay();

  if (wakeCause == ESP_SLEEP_WAKEUP_GPIO) {
    drawCentered("DEEP SLEEP", 60, 2, ST77XX_CYAN);
    drawCentered("WAKE OK", 105, 3, ST77XX_GREEN);
    drawCentered("BLK ON", 158, 2, ST77XX_WHITE);
    Serial.println("Deep sleep wake OK; BLK restored");
    return;
  }

  drawCentered("DEEP SLEEP TEST", 36, 2, ST77XX_CYAN);
  drawCentered("SLEEP IN 5 SEC", 86, 2, ST77XX_WHITE);
  drawCentered("THEN PRESS OK", 142, 2, ST77XX_YELLOW);
  Serial.println("Deep sleep test starts in 5 seconds");
  delay(5000);
  enterTestSleep();
}

void loop() {
  delay(1000);
}
