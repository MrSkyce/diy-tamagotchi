#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>

#include "config.h"

Adafruit_ST7789 tft(&SPI, TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);

void setup() {
  pinMode(FLASH_CS_PIN, OUTPUT);
  digitalWrite(FLASH_CS_PIN, HIGH);
  pinMode(TFT_BLK_PIN, OUTPUT);
  digitalWrite(TFT_BLK_PIN, HIGH);
  SPI.begin(TFT_SCLK_PIN, SPI_MISO_PIN, TFT_MOSI_PIN, -1);
  // La bibliothèque initialise le bus matériel à 32 MHz.
  tft.init(TFT_WIDTH, TFT_HEIGHT, SPI_MODE3);
  // En rotation 0 (image retournee de 180 degres), l'offset Adafruit de
  // 80 lignes correspond au raccordement interne de cette dalle.
  tft.setRotation(0);
  tft.invertDisplay(true);
  tft.setSPISpeed(TFT_SPI_FREQUENCY);

  tft.fillScreen(ST77XX_BLACK);
  tft.drawRect(0, 0, TFT_WIDTH, TFT_HEIGHT, ST77XX_WHITE);

  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(3);
  tft.setCursor(48, 18);
  tft.print("IPS");

  tft.setTextSize(2);
  tft.setTextColor(ST77XX_CYAN);
  tft.setCursor(66, 55);
  tft.print("ADA");
  tft.setTextColor(ST77XX_MAGENTA);
  tft.print("FRUIT");

  tft.setTextColor(ST77XX_YELLOW);
  tft.setCursor(54, 82);
  tft.print("MODE 3");
  tft.setCursor(54, 104);
  tft.print("32 MHz");

  tft.setTextColor(ST77XX_RED);
  tft.setCursor(18, 140);
  tft.print("ROUGE");
  tft.setTextColor(ST77XX_GREEN);
  tft.setCursor(126, 140);
  tft.print("VERT");

  tft.setTextColor(ST77XX_BLUE);
  tft.setCursor(18, 169);
  tft.print("BLEU");
  tft.setTextColor(ST77XX_CYAN);
  tft.setCursor(126, 169);
  tft.print("CYAN");

  tft.setTextColor(ST77XX_MAGENTA);
  tft.setCursor(66, 204);
  tft.print("OK !");
}

void loop() {}
