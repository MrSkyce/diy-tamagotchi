#include <Arduino.h>

constexpr uint8_t TFT_DC = 7;
constexpr uint8_t TFT_MOSI = 6;
constexpr uint8_t TFT_SCLK = 4;
constexpr uint8_t TFT_RST = 20;
constexpr uint16_t TFT_SIZE = 240;
constexpr unsigned int SPI_HALF_PERIOD_US = 5;

void writeSpiByte(uint8_t value) {
  for (uint8_t bit = 0x80; bit != 0; bit >>= 1) {
    // SPI mode 3 : horloge au repos à HIGH, premier front descendant.
    digitalWrite(TFT_SCLK, LOW);
    digitalWrite(TFT_MOSI, value & bit ? HIGH : LOW);
    delayMicroseconds(SPI_HALF_PERIOD_US);
    digitalWrite(TFT_SCLK, HIGH);
    delayMicroseconds(SPI_HALF_PERIOD_US);
  }
}

void command(uint8_t value) {
  digitalWrite(TFT_DC, LOW);
  writeSpiByte(value);
  digitalWrite(TFT_DC, HIGH);
}

void data(uint8_t value) { writeSpiByte(value); }

void setAddressWindow(uint16_t rowStart) {
  command(0x2A); // CASET
  data(0);
  data(0);
  data(0);
  data(TFT_SIZE - 1);

  const uint16_t rowEnd = rowStart + TFT_SIZE - 1;
  command(0x2B); // RASET
  data(rowStart >> 8);
  data(rowStart);
  data(rowEnd >> 8);
  data(rowEnd);
  command(0x2C); // RAMWR
}

void fill(uint16_t rowStart, uint16_t color) {
  setAddressWindow(rowStart);
  for (uint32_t pixel = 0; pixel < TFT_SIZE * TFT_SIZE; ++pixel) {
    data(color >> 8);
    data(color);
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
  data(0x55);     // RGB565
  command(0x36); // MADCTL
  data(0x00);
  command(0x21); // INVON : requis par cette dalle IPS
  command(0x13); // NORON
  delay(10);
  command(0x29); // DISPON
  delay(20);
}

void setup() {
  for (const uint8_t pin : {TFT_DC, TFT_MOSI, TFT_SCLK, TFT_RST}) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  digitalWrite(TFT_SCLK, HIGH);
  initialiseTft();
}

void loop() {
  // Cette dalle 240 x 240 utilise directement les lignes 0 à 239.
  // Chaque remplissage prend environ dix secondes à cette fréquence.
  fill(0, 0x07E0); // vert, identique en RGB et BGR
  delay(3000);
  fill(0, 0xF800); // rouge en RGB
  delay(3000);
}
