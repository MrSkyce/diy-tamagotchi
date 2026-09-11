#pragma once

#include <stdint.h>

// Shared by the HOME player and native tests. No allocations or persistence.
class WalkCycle {
 public:
  static constexpr uint8_t kFrames = 8;
  static constexpr uint32_t kDurationMs = 120;
  static constexpr int16_t kStepPixels = 3;
  static constexpr int16_t kMinX = 4;
  static constexpr int16_t kMaxX = 124;

  bool update(uint32_t now, bool enabled) {
    if (!enabled) {
      const bool changed = running_;
      running_ = false;
      turning_ = false;
      lastTick_ = now;
      return changed;
    }
    if (!running_) {
      running_ = true;
      phase_ = 0;
      lastTick_ = now;
      return true;
    }
    if (static_cast<uint32_t>(now - lastTick_) < kDurationMs) return false;
    // Never jump several poses after a stall: pose and position advance together.
    lastTick_ = now;
    const int16_t next = x_ + (right_ ? kStepPixels : -kStepPixels);
    if (next < kMinX || next > kMaxX) {
      right_ = !right_;
      phase_ = 0;
      turning_ = true;  // One stationary beat at the edge, then walk away.
    } else {
      x_ = next;
      phase_ = (phase_ + 1) % kFrames;
      turning_ = false;
    }
    return true;
  }

  int16_t x() const { return x_; }
  uint8_t phase() const { return phase_; }
  bool right() const { return right_; }
  bool turning() const { return turning_; }

 private:
  int16_t x_ = 64;
  uint8_t phase_ = 0;
  bool right_ = true;
  bool running_ = false;
  bool turning_ = false;
  uint32_t lastTick_ = 0;
};

inline bool homeWalkEnabled(bool home, bool hatched, int health, int hunger,
                            int happiness, int fatigue, bool blink) {
  return home && hatched && health >= 30 && hunger >= 25 &&
         happiness >= 25 && happiness < 95 && fatigue < 50 && !blink;
}
