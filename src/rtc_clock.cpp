#include "rtc_clock.h"

#include "config.h"

namespace {

constexpr uint16_t MIN_RTC_YEAR = 2024;
constexpr uint16_t MAX_RTC_YEAR = 2099;
constexpr uint32_t COMPILE_TIME_TOLERANCE_SECONDS = 5UL * 60UL;

}  // namespace

bool RtcClock::begin(TwoWire& wire) {
  wire_ = &wire;
  status_ = {};
  if (!device_.begin(&wire)) return false;

  status_.detected = true;
  status_.wasInitialized = device_.initialized();
  status_.lostPower = device_.lostPower();

  const DateTime compiled(F(__DATE__), F(__TIME__));
  RtcDateTime current;
  const bool readable = readDevice(current);
  const bool olderThanFirmware =
      readable && current.unixTime + COMPILE_TIME_TOLERANCE_SECONDS <
                      compiled.unixtime();
  if (!status_.wasInitialized || status_.lostPower || !readable ||
      olderThanFirmware) {
    // The build timestamp gives the RTC a deterministic starting point after
    // first battery installation or oscillator loss. Subsequent boots leave a
    // valid clock untouched.
    device_.adjust(compiled);
    status_.adjusted = true;
  }

  // Clearing STOP is safe on every boot and is required if the oscillator was
  // stopped while the backup battery remained connected.
  device_.start();
  status_.running = device_.isrunning() != 0;
  status_.valid = readDevice(current) && status_.running;
  return status_.valid;
}

bool RtcClock::read(RtcDateTime& dateTime) {
  if (!status_.detected || !status_.running) return false;
  const bool valid = readDevice(dateTime);
  status_.valid = valid;
  return valid;
}

bool RtcClock::readUnixTime(uint32_t& unixTime) {
  RtcDateTime dateTime;
  if (!read(dateTime)) return false;
  unixTime = dateTime.unixTime;
  return true;
}

bool RtcClock::readDevice(RtcDateTime& dateTime) {
  if (wire_ == nullptr) return false;
  wire_->beginTransmission(RTC_ADDRESS);
  if (wire_->endTransmission() != 0) return false;

  const DateTime value = device_.now();
  dateTime.year = value.year();
  dateTime.month = value.month();
  dateTime.day = value.day();
  dateTime.hour = value.hour();
  dateTime.minute = value.minute();
  dateTime.second = value.second();
  dateTime.unixTime = value.unixtime();
  return isReasonable(dateTime);
}

bool RtcClock::isReasonable(const RtcDateTime& dateTime) const {
  return dateTime.year >= MIN_RTC_YEAR && dateTime.year <= MAX_RTC_YEAR &&
         dateTime.month >= 1 && dateTime.month <= 12 && dateTime.day >= 1 &&
         dateTime.day <= 31 && dateTime.hour <= 23 && dateTime.minute <= 59 &&
         dateTime.second <= 59;
}
