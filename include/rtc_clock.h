#pragma once

#include <Arduino.h>
#include <RTClib.h>

struct RtcDateTime {
  uint16_t year = 0;
  uint8_t month = 0;
  uint8_t day = 0;
  uint8_t hour = 0;
  uint8_t minute = 0;
  uint8_t second = 0;
  uint32_t unixTime = 0;
};

struct RtcClockStatus {
  bool detected = false;
  bool wasInitialized = false;
  bool lostPower = false;
  bool adjusted = false;
  bool running = false;
  bool valid = false;
};

class RtcClock {
 public:
  bool begin(TwoWire& wire);
  bool read(RtcDateTime& dateTime);
  bool readUnixTime(uint32_t& unixTime);
  const RtcClockStatus& status() const { return status_; }

 private:
  bool readDevice(RtcDateTime& dateTime);
  bool isReasonable(const RtcDateTime& dateTime) const;

  RTC_PCF8523 device_;
  TwoWire* wire_ = nullptr;
  RtcClockStatus status_;
};
