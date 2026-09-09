#include <cassert>
#include <cstdint>
#include <cstdio>

#include "animation_player.h"

int main() {
  constexpr AnimationFrame poses[] = {{7, 80, 0}, {19, 140, -1}, {4, 250, 0}};
  constexpr AnimationFrame single[] = {{9, 30, 0}};
  const AnimationClip loop{poses, 3, true};
  const AnimationClip once{poses, 3, false};
  const AnimationClip hold{single, 1, true};
  AnimationPlayer player;
  assert(!player.update(123));
  assert(player.frame() == nullptr);
  assert(player.play(loop, 1000));
  assert(player.frame()->asset == 7);
  assert(!player.update(1079));
  assert(player.update(1080));
  assert(player.frame()->asset == 19 && player.frame()->yOffset == -1);
  // Re-selecting the same clip during rendering must not restart its timer.
  assert(!player.play(loop, 1090));
  assert(!player.update(1219));
  assert(player.update(1220) && player.frame()->asset == 4);
  assert(player.update(1470) && player.frame()->asset == 7);
  // A long stall skips whole cycles, without a loop per missed pose/cycle.
  assert(player.update(1470 + 4700000 + 90));
  assert(player.frame()->asset == 19);
  assert(!player.finished());

  assert(player.play(once, 100));
  assert(player.update(570));
  assert(player.finished() && player.frame()->asset == 4);
  assert(!player.update(0xFFFFFFF0));
  assert(player.frame()->asset == 4);
  assert(player.play(once, 200, true));
  assert(!player.finished() && player.index() == 0);

  // Tick rollover: 0xfffffff0 -> 64 is exactly 80 milliseconds.
  player.play(loop, UINT32_MAX - 15);
  assert(!player.update(63));
  assert(player.update(64) && player.index() == 1);
  player.play(loop, 0, true);
  player.update(UINT32_MAX);
  uint32_t phase = UINT32_MAX % 470;
  assert(player.index() == (phase < 80 ? 0 : phase < 220 ? 1 : 2));

  // No shared state between home/action/preview players.
  AnimationPlayer other;
  other.play(hold, 0);
  other.update(1000000);
  assert(other.frame()->asset == 9 && other.index() == 0);
  assert(player.frame()->asset != other.frame()->asset);

  const AnimationClip empty{nullptr, 0, true};
  assert(!player.play(empty, 0));
  assert(player.frame() == nullptr && !player.update(1));
  constexpr AnimationFrame invalid[] = {{1, 20, 0}, {2, 0, 0}};
  const AnimationClip invalidClip{invalid, 2, true};
  assert(!player.play(invalidClip, 0));
  assert(player.frame() == nullptr);
  assert(player.play(loop, 10));
  player.stop();
  assert(player.frame() == nullptr && !player.finished());
  puts("PASS: variable durations, boundaries, loop, one-shot, restart, rollover, long stalls, independent players, invalid clips");
}
