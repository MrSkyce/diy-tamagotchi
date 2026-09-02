#include <Arduino.h>
#include <SPI.h>

constexpr uint8_t TFT_DC = 7;
constexpr uint8_t TFT_MOSI = 6;
constexpr uint8_t TFT_MISO = 5; // Non connecte, requis par SPI.begin().
constexpr uint8_t TFT_SCLK = 4;
constexpr uint8_t TFT_RST = 20;
constexpr uint16_t TFT_SIZE = 240;
constexpr uint32_t TFT_SPI_FREQUENCY = 32000000;

void writeSpiByte(uint8_t value) { SPI.transfer(value); }

void command(uint8_t value) {
  digitalWrite(TFT_DC, LOW);
  writeSpiByte(value);
  digitalWrite(TFT_DC, HIGH);
}

void data(uint8_t value) { writeSpiByte(value); }

void setAddressWindow() {
  command(0x2A); // CASET : colonnes 0 a 239
  data(0);
  data(0);
  data(0);
  data(TFT_SIZE - 1);

  command(0x2B); // RASET : lignes 0 a 239
  data(0);
  data(0);
  data(0);
  data(TFT_SIZE - 1);
  command(0x2C); // RAMWR
}

void fill(uint16_t color) {
  uint8_t line[TFT_SIZE * 2];
  for (uint16_t pixel = 0; pixel < TFT_SIZE; ++pixel) {
    line[pixel * 2] = color >> 8;
    line[pixel * 2 + 1] = color;
  }

  setAddressWindow();
  for (uint16_t row = 0; row < TFT_SIZE; ++row) {
    SPI.writeBytes(line, sizeof(line));
  }
}

void initialiseTft() {
  digitalWrite(TFT_RST, HIGH);
  delay(5);
  digitalWrite(TFT_RST, LOW);
  delay(20);
  digitalWrite(TFT_RST, HIGH);
  delay(150);

  command(0x01); // SWRESET
  delay(150);
  command(0x11); // SLPOUT
  delay(120);
  command(0x3A); // COLMOD
  data(0x55);    // RGB565
  command(0x36); // MADCTL
  data(0x00);
  command(0x21); // INVON : requis par cette dalle IPS
  command(0x13); // NORON
  delay(10);
  command(0x29); // DISPON
  delay(20);
}

void setup() {
  pinMode(TFT_DC, OUTPUT);
  pinMode(TFT_RST, OUTPUT);
  digitalWrite(TFT_DC, HIGH);

  SPI.begin(TFT_SCLK, TFT_MISO, TFT_MOSI, -1);
  SPI.beginTransaction(
      SPISettings(TFT_SPI_FREQUENCY, MSBFIRST, SPI_MODE3));
  initialiseTft();
}

void loop() {
  fill(0x07E0); // vert
  delay(1000);
  fill(0xF800); // rouge
  delay(1000);
}
