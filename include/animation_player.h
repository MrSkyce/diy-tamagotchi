#pragma once

#include <cstdint>

// Asset identifiers are supplied by the caller's catalogue, never persisted.
struct AnimationFrame {
  uint16_t asset;
  uint16_t durationMs;
  int8_t yOffset;
};

struct AnimationClip {
  const AnimationFrame* frames;
  uint8_t count;
  bool loop;
};

// No allocation, I/O, delays or gameplay side effects. A late update selects
// the current pose directly; it never renders a backlog of missed frames.
class AnimationPlayer {
 public:
  bool play(const AnimationClip& clip, uint32_t now, bool restart = false) {
    if (clip_ == &clip && !restart) return false;
    stop();
    if (clip.frames == nullptr || clip.count == 0) return false;
    uint32_t duration = 0;
    for (uint16_t i = 0; i < clip.count; ++i) {
      if (clip.frames[i].durationMs == 0) return false;
      duration += clip.frames[i].durationMs;
    }
    clip_ = &clip;
    duration_ = duration;
    lastTick_ = now;
    return true;
  }

  bool update(uint32_t now) {
    if (clip_ == nullptr) return false;
    const uint32_t delta = now - lastTick_;  // millis() rollover-safe.
    lastTick_ = now;
    const uint8_t previous = index_;
    const bool wasFinished = finished_;
    if (clip_->loop) {
      // At most 255 * 65535 ms per clip, so this addition cannot overflow.
      position_ = (position_ + delta % duration_) % duration_;
    } else if (delta >= duration_ - position_) {
      position_ = duration_;
      finished_ = true;
    } else {
      position_ += delta;
    }
    uint32_t remaining = position_;
    index_ = 0;
    while (index_ + 1 < clip_->count &&
           remaining >= clip_->frames[index_].durationMs) {
      remaining -= clip_->frames[index_].durationMs;
      ++index_;
    }
    return index_ != previous || wasFinished != finished_;
  }

  void stop() {
    clip_ = nullptr;
    duration_ = position_ = lastTick_ = 0;
    index_ = 0;
    finished_ = false;
  }

  const AnimationFrame* frame() const {
    return clip_ == nullptr ? nullptr : &clip_->frames[index_];
  }
  uint8_t index() const { return index_; }
  bool finished() const { return finished_; }

 private:
  // The caller owns immutable clips/frames and keeps them alive during play.
  const AnimationClip* clip_ = nullptr;
  uint32_t duration_ = 0;
  uint32_t position_ = 0;
  uint32_t lastTick_ = 0;
  uint8_t index_ = 0;
  bool finished_ = false;
};
