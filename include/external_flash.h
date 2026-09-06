#pragma once

#include <Arduino.h>

struct W25QJedecId {
  uint8_t manufacturer;
  uint8_t memoryType;
  uint8_t capacity;
};

class W25Q64Flash {
 public:
  void configureChipSelects();
  W25QJedecId readJedecId();
  bool isExpectedDevice();
  void readBytes(uint32_t address, uint8_t* destination, size_t length);
  bool eraseRange(uint32_t address, size_t length);
  bool programPage(uint32_t address, const uint8_t* data, size_t length);
  bool waitUntilReady(uint32_t timeoutMs);

 private:
  uint8_t readStatus();
  void writeEnable();
  void beginCommand(uint8_t command, uint32_t address);
  void endCommand();
};

