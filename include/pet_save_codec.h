#pragma once

#include <stddef.h>
#include <stdint.h>
#include "persistence.h"

// Explicit little-endian records: no compiler padding in new saves.
// v7 ESP32 records were 40 bytes: age at 16, RTC at 32, checksum at 36.
namespace PetSaveCodec {
constexpr uint32_t kMagic = 0x54414D41;
constexpr uint16_t kVersion = 8;
constexpr size_t kLegacySize = 40;
constexpr size_t kSize = 44;
constexpr uint8_t kMascotCount = 6;

inline uint64_t read(const uint8_t* p, size_t n) {
  uint64_t result = 0;
  for (size_t i = 0; i < n; ++i) result |= uint64_t(p[i]) << (i*8);
  return result;
}
inline void write(uint8_t* p, uint64_t value, size_t n) {
  for (size_t i = 0; i < n; ++i) p[i] = static_cast<uint8_t>(value >> (i*8));
}
inline uint32_t mix(uint32_t sum, uint32_t value) { return (sum*31U) ^ value; }
inline bool valid(const PetSaveData& p) {
  return p.hunger <= 100 && p.happiness <= 100 && p.health <= 100 &&
         p.cleanliness <= 100 && p.fatigue <= 100 && p.appetite <= 2 &&
         p.playfulness <= 2 && p.stubbornness <= 2 && p.lifeStage <= 3 &&
         p.warmth <= 3 && p.stageStartedAgeMs <= p.ageMs && p.mascot < kMascotCount;
}
inline uint32_t checksum(const PetSaveData& p, uint16_t version) {
  uint32_t sum = kMagic ^ version;
  const uint8_t stats[] = {p.hunger, p.happiness, p.health, p.cleanliness, p.fatigue,
                          p.appetite, p.playfulness, p.stubbornness, p.lifeStage, p.warmth};
  for (uint8_t stat : stats) sum = mix(sum, stat);
  sum = mix(sum, static_cast<uint32_t>(p.ageMs));
  sum = mix(sum, static_cast<uint32_t>(p.ageMs >> 32));
  sum = mix(sum, static_cast<uint32_t>(p.stageStartedAgeMs));
  sum = mix(sum, static_cast<uint32_t>(p.stageStartedAgeMs >> 32));
  sum = mix(sum, p.rtcUnixTime);
  return version == 7 ? sum : mix(sum, p.mascot);
}
inline bool decode(const uint8_t* bytes, size_t length, PetSaveData& output) {
  if (!bytes || (length != kLegacySize && length != kSize)) return false;
  const auto version = static_cast<uint16_t>(read(bytes+4, 2));
  if (read(bytes, 4) != kMagic || !((version == 7 && length == kLegacySize) ||
                                   (version == kVersion && length == kSize))) return false;
  PetSaveData p{};
  p.hunger = bytes[6]; p.happiness = bytes[7]; p.health = bytes[8];
  p.cleanliness = bytes[9]; p.fatigue = bytes[10]; p.appetite = bytes[11];
  p.playfulness = bytes[12]; p.stubbornness = bytes[13];
  p.lifeStage = bytes[14]; p.warmth = bytes[15];
  p.ageMs = read(bytes+16, 8); p.stageStartedAgeMs = read(bytes+24, 8);
  p.rtcUnixTime = static_cast<uint32_t>(read(bytes+32, 4));
  p.mascot = version == 7 ? 0 : bytes[36];
  if (version == kVersion && (bytes[37] || bytes[38] || bytes[39])) return false;
  if (!valid(p) || checksum(p, version) != read(bytes+(version == 7 ? 36 : 40), 4)) return false;
  output = p;
  return true;
}
inline bool encode(const PetSaveData& p, uint8_t* bytes, size_t length) {
  if (!bytes || length != kSize || !valid(p)) return false;
  for (size_t i = 0; i < length; ++i) bytes[i] = 0;
  write(bytes, kMagic, 4); write(bytes+4, kVersion, 2);
  const uint8_t stats[] = {p.hunger, p.happiness, p.health, p.cleanliness, p.fatigue,
                          p.appetite, p.playfulness, p.stubbornness, p.lifeStage, p.warmth};
  for (size_t i = 0; i < sizeof(stats); ++i) bytes[6+i] = stats[i];
  write(bytes+16, p.ageMs, 8); write(bytes+24, p.stageStartedAgeMs, 8);
  write(bytes+32, p.rtcUnixTime, 4); bytes[36] = p.mascot;
  write(bytes+40, checksum(p, kVersion), 4);
  return true;
}
}  // namespace PetSaveCodec
