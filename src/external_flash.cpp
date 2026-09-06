#include "external_flash.h"

#include <SPI.h>

#include "config.h"

namespace {

constexpr uint8_t COMMAND_READ_DATA = 0x03;
constexpr uint8_t COMMAND_PAGE_PROGRAM = 0x02;
constexpr uint8_t COMMAND_SECTOR_ERASE = 0x20;
constexpr uint8_t COMMAND_READ_STATUS_1 = 0x05;
constexpr uint8_t COMMAND_WRITE_ENABLE = 0x06;
constexpr uint8_t COMMAND_JEDEC_ID = 0x9F;
constexpr uint8_t STATUS_BUSY = 0x01;
constexpr uint8_t STATUS_WRITE_ENABLE_LATCH = 0x02;
constexpr uint32_t SECTOR_SIZE = 4096;
constexpr uint32_t PAGE_SIZE = 256;

SPISettings flashSettings(FLASH_SPI_FREQUENCY, MSBFIRST, SPI_MODE0);

}  // namespace

void W25Q64Flash::configureChipSelects() {
  pinMode(TFT_CS_PIN, OUTPUT);
  digitalWrite(TFT_CS_PIN, HIGH);
  pinMode(FLASH_CS_PIN, OUTPUT);
  digitalWrite(FLASH_CS_PIN, HIGH);
}

void W25Q64Flash::beginCommand(uint8_t command, uint32_t address) {
  digitalWrite(TFT_CS_PIN, HIGH);
  SPI.beginTransaction(flashSettings);
  digitalWrite(FLASH_CS_PIN, LOW);
  SPI.transfer(command);
  SPI.transfer(static_cast<uint8_t>(address >> 16));
  SPI.transfer(static_cast<uint8_t>(address >> 8));
  SPI.transfer(static_cast<uint8_t>(address));
}

void W25Q64Flash::endCommand() {
  digitalWrite(FLASH_CS_PIN, HIGH);
  SPI.endTransaction();
}

W25QJedecId W25Q64Flash::readJedecId() {
  digitalWrite(TFT_CS_PIN, HIGH);
  SPI.beginTransaction(flashSettings);
  digitalWrite(FLASH_CS_PIN, LOW);
  SPI.transfer(COMMAND_JEDEC_ID);
  const W25QJedecId id{
      SPI.transfer(0x00), SPI.transfer(0x00), SPI.transfer(0x00)};
  digitalWrite(FLASH_CS_PIN, HIGH);
  SPI.endTransaction();
  return id;
}

bool W25Q64Flash::isExpectedDevice() {
  const W25QJedecId id = readJedecId();
  return id.manufacturer == 0xEF && id.memoryType == 0x40 &&
         id.capacity == 0x17;
}

void W25Q64Flash::readBytes(uint32_t address, uint8_t* destination,
                            size_t length) {
  beginCommand(COMMAND_READ_DATA, address);
  while (length-- > 0) *destination++ = SPI.transfer(0x00);
  endCommand();
}

uint8_t W25Q64Flash::readStatus() {
  digitalWrite(TFT_CS_PIN, HIGH);
  SPI.beginTransaction(flashSettings);
  digitalWrite(FLASH_CS_PIN, LOW);
  SPI.transfer(COMMAND_READ_STATUS_1);
  const uint8_t status = SPI.transfer(0x00);
  digitalWrite(FLASH_CS_PIN, HIGH);
  SPI.endTransaction();
  return status;
}

bool W25Q64Flash::waitUntilReady(uint32_t timeoutMs) {
  const uint32_t startedAt = millis();
  while (readStatus() & STATUS_BUSY) {
    if (millis() - startedAt >= timeoutMs) return false;
    delay(1);
  }
  return true;
}

void W25Q64Flash::writeEnable() {
  digitalWrite(TFT_CS_PIN, HIGH);
  SPI.beginTransaction(flashSettings);
  digitalWrite(FLASH_CS_PIN, LOW);
  SPI.transfer(COMMAND_WRITE_ENABLE);
  digitalWrite(FLASH_CS_PIN, HIGH);
  SPI.endTransaction();
}

bool W25Q64Flash::eraseRange(uint32_t address, size_t length) {
  if (address % SECTOR_SIZE != 0) return false;
  const uint32_t end = address + length;
  for (uint32_t sector = address; sector < end; sector += SECTOR_SIZE) {
    if (!waitUntilReady(5000)) return false;
    writeEnable();
    if ((readStatus() & STATUS_WRITE_ENABLE_LATCH) == 0) return false;
    beginCommand(COMMAND_SECTOR_ERASE, sector);
    endCommand();
    if (!waitUntilReady(5000)) return false;
  }
  return true;
}

bool W25Q64Flash::programPage(uint32_t address, const uint8_t* data,
                              size_t length) {
  if (length == 0 || length > PAGE_SIZE ||
      address / PAGE_SIZE != (address + length - 1) / PAGE_SIZE) {
    return false;
  }
  if (!waitUntilReady(1000)) return false;
  writeEnable();
  if ((readStatus() & STATUS_WRITE_ENABLE_LATCH) == 0) return false;
  beginCommand(COMMAND_PAGE_PROGRAM, address);
  while (length-- > 0) SPI.transfer(*data++);
  endCommand();
  return waitUntilReady(1000);
}

