// Opt-in visual diagnostic. Reads its pixels from internal program memory;
// never initializes NVS/RTC or writes/erases the external asset flash.
#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include <driver/gpio.h>

#include "config.h"
#include "animation_player.h"
#include "generated_walk_preview.h"

namespace {
Adafruit_ST7789 display(&SPI, TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);
AnimationPlayer player;
constexpr uint16_t BACKGROUNDS[] = {0x1085, 0x07FF, 0x07E0};
constexpr uint16_t TRANSPARENT = 0xF81F;
uint8_t backgroundIndex = 0;
bool paused = false;
uint32_t lastRenderUs = 0;
uint32_t maxRenderUs = 0;
uint32_t renderCount = 0;
bool audioEnabled = false;
uint8_t note = 0;
uint32_t noteStarted = 0;
constexpr uint16_t NOTES[] = {523, 659, 784, 0};
struct Button {
  uint8_t pin;
  bool reading = HIGH;
  bool stable = HIGH;
  uint32_t changedAt = 0;
  explicit Button(uint8_t gpio) : pin(gpio) {}
};
Button left{BTN_LEFT}, ok{BTN_OK}, right{BTN_RIGHT};

bool pressed(Button& button, uint32_t now) {
  const bool value = digitalRead(button.pin);
  if (value != button.reading) {
    button.reading = value;
    button.changedAt = now;
  }
  if (now - button.changedAt < 35 || value == button.stable) return false;
  button.stable = value;
  return value == LOW;
}

void drawFrame() {
  const AnimationFrame* frame = player.frame();
  if (frame == nullptr) return;
  const uint32_t started = micros();
  const uint16_t* pixels = WALK_PIXELS[frame->asset];
  uint16_t line[112];
  // Fixed 113-row union covers both offsets, including the preceding frame.
  display.startWrite();
  display.setAddrWindow(64, 51, 112, 113);
  for (int y = -1; y < 112; ++y) {
    const int sourceY = y - frame->yOffset;
    for (int x = 0; x < 112; ++x) {
      const uint16_t color = sourceY >= 0 && sourceY < 112
          ? pixels[sourceY * 112 + x] : TRANSPARENT;
      line[x] = color == TRANSPARENT ? BACKGROUNDS[backgroundIndex] : color;
    }
    display.writePixels(line, 112);
  }
  display.endWrite();
  lastRenderUs = micros() - started;
  if (lastRenderUs > maxRenderUs) maxRenderUs = lastRenderUs;
  ++renderCount;
  display.fillRect(8, 178, 224, 18, ST77XX_BLACK);
  display.setCursor(8, 181);
  display.setTextColor(ST77XX_WHITE);
  display.setTextSize(1);
  display.printf("POSE %u/%u %ums %s", player.index()+1,
                 WALK_CLIP.count, frame->durationMs,
                 paused ? "PAUSE" : "PLAY");
}

void updateAudio(uint32_t now) {
  if (!audioEnabled || now - noteStarted < 180) return;
  noteStarted = now;
  note = (note + 1) % 4;
  if (NOTES[note] == 0) noTone(BUZZER_PIN);
  else tone(BUZZER_PIN, NOTES[note], 140);
}
}  // namespace

void setup() {
  gpio_deep_sleep_hold_dis();
  gpio_hold_dis(static_cast<gpio_num_t>(TFT_BLK_PIN));
  Serial.begin(115200);
  pinMode(FLASH_CS_PIN, OUTPUT);
  digitalWrite(FLASH_CS_PIN, HIGH);
  pinMode(TFT_CS_PIN, OUTPUT);
  digitalWrite(TFT_CS_PIN, HIGH);
  pinMode(TFT_BLK_PIN, OUTPUT);
  digitalWrite(TFT_BLK_PIN, HIGH);
  pinMode(BUZZER_PIN, OUTPUT);
  for (Button* button : {&left, &ok, &right}) {
    pinMode(button->pin, INPUT_PULLUP);
    button->reading = button->stable = digitalRead(button->pin);
  }
  SPI.begin(TFT_SCLK_PIN, SPI_MISO_PIN, TFT_MOSI_PIN, -1);
  display.init(TFT_WIDTH, TFT_HEIGHT, SPI_MODE3);
  display.setRotation(0);
  display.invertDisplay(true);
  display.setSPISpeed(TFT_SPI_FREQUENCY);
  display.fillScreen(ST77XX_BLACK);
  display.setTextColor(ST77XX_WHITE);
  display.setTextSize(2);
  display.setCursor(8, 12);
  display.print("WALK PREVIEW");
  display.setTextSize(1);
  display.setCursor(8, 205);
  display.print("LEFT:BG OK:PAUSE RIGHT:AUDIO");
  player.play(WALK_CLIP, millis());
  drawFrame();
  Serial.printf("WALK PREVIEW: %u candidate poses, internal pixels, no NVS/flash writes\n", WALK_CLIP.count);
}

void loop() {
  const uint32_t now = millis();
  bool redraw = false;
  if (pressed(left, now)) {
    backgroundIndex = (backgroundIndex + 1) % 3;
    redraw = true;
  }
  if (pressed(ok, now)) {
    paused = !paused;
    if (!paused) player.play(WALK_CLIP, now, true);
    redraw = true;
  }
  if (pressed(right, now)) {
    audioEnabled = !audioEnabled;
    noteStarted = now;
    note = 0;
    if (audioEnabled) tone(BUZZER_PIN, NOTES[0], 140);
    else noTone(BUZZER_PIN);
    Serial.printf("AUDIO %s\n", audioEnabled ? "ON" : "OFF");
  }
  updateAudio(now);
  if (!paused && player.update(now)) redraw = true;
  if (redraw) drawFrame();
  static uint32_t lastReport = 0;
  if (now - lastReport >= 2000) {
    lastReport = now;
    Serial.printf("WALK frames=%lu draw_us=%lu max_us=%lu pose=%u audio=%u paused=%u\n",
                  static_cast<unsigned long>(renderCount),
                  static_cast<unsigned long>(lastRenderUs),
                  static_cast<unsigned long>(maxRenderUs), player.index()+1,
                  audioEnabled, paused);
  }
  delay(1);
}
