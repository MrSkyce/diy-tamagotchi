#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include <Wire.h>

#include "config.h"
#include "rtc_clock.h"

namespace {

Adafruit_ST7789 tft(&SPI, TFT_CS_PIN, TFT_DC_PIN, -1);
RtcClock rtcClock;

bool rtcDetected = false;
bool rtcClockRunning = false;
bool rtcAdjusted = false;
bool rtcTimeValid = false;
RtcDateTime rtcDateTime;
uint32_t rtcFirstUnixTime = 0;
unsigned long rtcFirstReadAt = 0;
bool rtcTickObserved = false;
uint8_t flashManufacturer = 0;
uint8_t flashMemoryType = 0;
uint8_t flashCapacity = 0;
bool flashDetected = false;
uint8_t detectedI2cAddresses[8]{};
uint8_t detectedI2cCount = 0;
int rtcSdaLevel = LOW;
int rtcSclLevel = LOW;

void scanI2cBus() {
  detectedI2cCount = 0;
  for (uint8_t address = 1; address < 127; ++address) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0 &&
        detectedI2cCount < sizeof(detectedI2cAddresses)) {
      detectedI2cAddresses[detectedI2cCount++] = address;
    }
  }
}

void beginRtc() {
  rtcClock.begin(Wire);
  const RtcClockStatus& status = rtcClock.status();
  rtcDetected = status.detected;
  rtcClockRunning = status.running;
  rtcAdjusted = status.adjusted;
  rtcTimeValid = rtcClock.read(rtcDateTime);
  if (rtcTimeValid) rtcFirstUnixTime = rtcDateTime.unixTime;
  rtcFirstReadAt = millis();
}

void refreshRtc() {
  rtcTimeValid = rtcClock.read(rtcDateTime);
  const RtcClockStatus& status = rtcClock.status();
  rtcDetected = status.detected;
  rtcClockRunning = status.running;
  if (rtcTimeValid && rtcDateTime.unixTime > rtcFirstUnixTime) {
    rtcTickObserved = true;
  }
}

void readFlashJedecId() {
  digitalWrite(TFT_CS_PIN, HIGH);
  SPI.beginTransaction(
      SPISettings(FLASH_SPI_FREQUENCY, MSBFIRST, SPI_MODE0));
  digitalWrite(FLASH_CS_PIN, LOW);
  SPI.transfer(0x9F); // JEDEC ID, lecture seule.
  flashManufacturer = SPI.transfer(0x00);
  flashMemoryType = SPI.transfer(0x00);
  flashCapacity = SPI.transfer(0x00);
  digitalWrite(FLASH_CS_PIN, HIGH);
  SPI.endTransaction();

  const bool allZero = flashManufacturer == 0x00 && flashMemoryType == 0x00 &&
                       flashCapacity == 0x00;
  const bool allHigh = flashManufacturer == 0xFF && flashMemoryType == 0xFF &&
                       flashCapacity == 0xFF;
  flashDetected = !allZero && !allHigh;
}

void printSerialReport() {
  Serial.println();
  Serial.println("=== TAMAGOTCHI CABLING TEST ===");
  Serial.println("TFT CS  : GPIO9");
  Serial.println("TFT RST : RC + software reset");
  Serial.println("TFT BLK : GPIO10 (HIGH=ON, LOW=OFF)");
  Serial.println("SPI     : SCLK=4 MOSI=6 MISO=20");
  Serial.printf("FLASH   : %s\n", flashDetected ? "JEDEC ID received"
                                               : "NOT DETECTED");
  Serial.printf("JEDEC ID: %02X %02X %02X\n", flashManufacturer,
                flashMemoryType, flashCapacity);
  Serial.printf("RTC     : %s\n", rtcDetected ? "PCF8523 detected at 0x68"
                                                : "NOT DETECTED");
  if (rtcDetected) {
    Serial.printf("RTC OSC : %s\n", rtcClockRunning ? "RUNNING" : "STOPPED");
    Serial.printf("RTC SET : %s\n", rtcAdjusted ? "BUILD TIME APPLIED"
                                                 : "TIME PRESERVED");
    if (rtcTimeValid) {
      Serial.printf("RTC TIME: %04u-%02u-%02u %02u:%02u:%02u (%lu)\n",
                    rtcDateTime.year, rtcDateTime.month, rtcDateTime.day,
                    rtcDateTime.hour, rtcDateTime.minute, rtcDateTime.second,
                    static_cast<unsigned long>(rtcDateTime.unixTime));
    }
    Serial.printf("RTC TICK: %s\n", rtcTickObserved ? "OK"
                                                   : "WAITING");
  }
  Serial.printf("I2C SCAN: %u device(s)", detectedI2cCount);
  for (uint8_t index = 0; index < detectedI2cCount; ++index) {
    Serial.printf(" 0x%02X", detectedI2cAddresses[index]);
  }
  Serial.println();
  Serial.printf("I2C IDLE: SDA=%s SCL=%s\n", rtcSdaLevel ? "HIGH" : "LOW",
                rtcSclLevel ? "HIGH" : "LOW");
  Serial.println("Flash access is read-only; no write or erase command sent.");
  Serial.println("================================");
}

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

void drawRtcReport() {
  // Only redraw the changing RTC rows; a full-screen refresh every second
  // would make the diagnostic itself introduce visible flicker.
  tft.fillRect(17, 165, TFT_WIDTH - 34, 39, ST77XX_BLACK);
  tft.setTextSize(2);
  tft.setCursor(18, 166);
  tft.setTextColor(rtcTimeValid ? ST77XX_GREEN : ST77XX_YELLOW);
  if (rtcTimeValid) {
    char timeLabel[20];
    snprintf(timeLabel, sizeof(timeLabel), "TIME %02u:%02u:%02u",
             rtcDateTime.hour, rtcDateTime.minute, rtcDateTime.second);
    tft.print(timeLabel);
  } else {
    tft.print("CLOCK INVALID");
  }

  tft.setTextSize(1);
  tft.setCursor(18, 194);
  const bool tickFailed = rtcTimeValid && !rtcTickObserved &&
                          millis() - rtcFirstReadAt >= 3000;
  tft.setTextColor(rtcTickObserved ? ST77XX_GREEN :
                   tickFailed ? ST77XX_RED : ST77XX_YELLOW);
  tft.print(rtcTickObserved ? "TICK OK" : tickFailed ? "TICK FAIL" : "TICK WAIT");
  tft.print(rtcAdjusted ? " | BUILD TIME SET" : " | TIME PRESERVED");
}

void drawReport() {
  tft.fillScreen(ST77XX_BLACK);
  tft.drawRect(0, 0, TFT_WIDTH, TFT_HEIGHT, ST77XX_WHITE);
  drawCentered("CABLING TEST", 14, 2, ST77XX_CYAN);

  tft.setTextSize(2);
  tft.setCursor(18, 54);
  tft.setTextColor(ST77XX_GREEN);
  tft.print("TFT    OK");

  tft.setCursor(18, 82);
  tft.setTextColor(rtcDetected ? ST77XX_GREEN : ST77XX_RED);
  tft.print("RTC    ");
  tft.print(rtcDetected ? "OK" : "FAIL");

  tft.setCursor(18, 110);
  tft.setTextColor(flashDetected ? ST77XX_GREEN : ST77XX_RED);
  tft.print("FLASH  ");
  tft.print(flashDetected ? "OK" : "FAIL");

  tft.setCursor(18, 138);
  tft.setTextColor(ST77XX_YELLOW);
  char jedecLabel[20];
  snprintf(jedecLabel, sizeof(jedecLabel), "ID %02X %02X %02X",
           flashManufacturer, flashMemoryType, flashCapacity);
  tft.print(jedecLabel);

  drawRtcReport();

  drawCentered("CHECK SCREEN + SERIAL", 211, 1, ST77XX_WHITE);
}

void testBacklight() {
  for (uint8_t cycle = 0; cycle < 2; ++cycle) {
    delay(350);
    digitalWrite(TFT_BLK_PIN, LOW);
    delay(350);
    digitalWrite(TFT_BLK_PIN, HIGH);
  }
}

} // namespace

void setup() {
  // Les périphériques SPI doivent être désélectionnés avant le démarrage du bus.
  pinMode(FLASH_CS_PIN, OUTPUT);
  digitalWrite(FLASH_CS_PIN, HIGH);
  pinMode(TFT_CS_PIN, OUTPUT);
  digitalWrite(TFT_CS_PIN, HIGH);

  pinMode(TFT_BLK_PIN, OUTPUT);
  digitalWrite(TFT_BLK_PIN, HIGH);
  pinMode(SPI_MISO_PIN, INPUT);

  Serial.begin(115200);
  delay(1200);

  Wire.begin(RTC_SDA_PIN, RTC_SCL_PIN);
  scanI2cBus();
  rtcSdaLevel = digitalRead(RTC_SDA_PIN);
  rtcSclLevel = digitalRead(RTC_SCL_PIN);
  beginRtc();

  SPI.begin(TFT_SCLK_PIN, SPI_MISO_PIN, TFT_MOSI_PIN, -1);
  tft.init(TFT_WIDTH, TFT_HEIGHT, SPI_MODE3);
  tft.setRotation(0);
  tft.invertDisplay(true);
  tft.setSPISpeed(TFT_SPI_FREQUENCY);

  readFlashJedecId();
  drawReport();
  testBacklight();
  printSerialReport();
}

void loop() {
  static unsigned long lastDisplayAt = 0;
  static unsigned long lastReportAt = 0;
  const unsigned long now = millis();
  if (now - lastDisplayAt >= 1000) {
    lastDisplayAt = now;
    refreshRtc();
    drawRtcReport();
  }
  if (now - lastReportAt >= 5000) {
    lastReportAt = now;
    printSerialReport();
  }
  delay(20);
}
