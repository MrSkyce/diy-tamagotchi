#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include <Wire.h>
#include <driver/gpio.h>
#include <esp_sleep.h>
#include <esp_system.h>

#include "config.h"
#include "external_flash.h"
#include "generated_tft_assets.h"
#include "mascot_walks.h"
#include "persistence.h"
#include "rtc_clock.h"
#include "tft_asset_store.h"
#include "walk_cycle.h"

Adafruit_ST7789 spiTft(&SPI, TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);
W25Q64Flash externalFlash;
RtcClock rtcClock;
TftAssetStore tftAssets;
bool tftAssetsReady = false;

struct ExternalHardwareStatus {
  bool flashDetected = false;
  uint8_t flashManufacturer = 0;
  uint8_t flashMemoryType = 0;
  uint8_t flashCapacity = 0;
  bool rtcDetected = false;
  bool rtcClockRunning = false;
  bool rtcAdjusted = false;
  bool rtcValid = false;
};

ExternalHardwareStatus externalHardware;
RtcDateTime rtcBootDateTime;
bool rtcBootTimeValid = false;

void probeExternalHardware() {
  Wire.begin(RTC_SDA_PIN, RTC_SCL_PIN);
  rtcClock.begin(Wire);
  const RtcClockStatus& rtcStatus = rtcClock.status();
  externalHardware.rtcDetected = rtcStatus.detected;
  externalHardware.rtcClockRunning = rtcStatus.running;
  externalHardware.rtcAdjusted = rtcStatus.adjusted;
  externalHardware.rtcValid = rtcStatus.valid;
  rtcBootTimeValid = rtcClock.read(rtcBootDateTime);

  const W25QJedecId jedec = externalFlash.readJedecId();
  externalHardware.flashManufacturer = jedec.manufacturer;
  externalHardware.flashMemoryType = jedec.memoryType;
  externalHardware.flashCapacity = jedec.capacity;

  const bool flashAllZero = externalHardware.flashManufacturer == 0x00 &&
                            externalHardware.flashMemoryType == 0x00 &&
                            externalHardware.flashCapacity == 0x00;
  const bool flashAllHigh = externalHardware.flashManufacturer == 0xFF &&
                            externalHardware.flashMemoryType == 0xFF &&
                            externalHardware.flashCapacity == 0xFF;
  externalHardware.flashDetected = !flashAllZero && !flashAllHigh;

  Serial.printf("W25Q64 JEDEC: %02X %02X %02X (%s)\n",
                externalHardware.flashManufacturer,
                externalHardware.flashMemoryType,
                externalHardware.flashCapacity,
                externalHardware.flashDetected ? "detected" : "missing");
  Serial.printf("PCF8523: %s, oscillator %s, time %s%s\n",
                externalHardware.rtcDetected ? "detected" : "missing",
                externalHardware.rtcClockRunning ? "running" : "stopped",
                rtcBootTimeValid ? "valid" : "invalid",
                externalHardware.rtcAdjusted ? " (set from firmware build)" : "");
  if (rtcBootTimeValid) {
    Serial.printf("RTC time: %04u-%02u-%02u %02u:%02u:%02u (%lu)\n",
                  rtcBootDateTime.year, rtcBootDateTime.month,
                  rtcBootDateTime.day, rtcBootDateTime.hour,
                  rtcBootDateTime.minute, rtcBootDateTime.second,
                  static_cast<unsigned long>(rtcBootDateTime.unixTime));
  }
}

void drawTftUi();

void presentDisplay() {
  if (!tftAssetsReady) {
    static bool errorDrawn = false;
    if (!errorDrawn) {
      spiTft.fillScreen(ST77XX_BLACK);
      spiTft.setTextColor(ST77XX_RED);
      spiTft.setTextSize(2);
      spiTft.setCursor(20, 54);
      spiTft.print("ASSET ERROR");
      spiTft.setTextColor(ST77XX_WHITE);
      spiTft.setTextSize(1);
      spiTft.setCursor(20, 92);
      spiTft.print(tftAssets.error());
      spiTft.setCursor(20, 116);
      spiTft.print("Run asset-flash-programmer");
      errorDrawn = true;
    }
    return;
  }
  drawTftUi();
}

enum LifeStage : uint8_t { STAGE_EGG, STAGE_BABY, STAGE_YOUNG, STAGE_ADULT };

constexpr uint8_t EGG_WARMTH_REQUIRED = 3;
// Durées volontairement courtes pour valider le cycle sur le prototype.
constexpr unsigned long BABY_STAGE_DURATION = 5UL * 60UL * 1000UL;
constexpr unsigned long YOUNG_STAGE_DURATION = 15UL * 60UL * 1000UL;

struct Pet {
  MascotId mascot = MascotId::DRAGON;
  int hunger = 80;
  int happiness = 80;
  int health = 100;
  int cleanliness = 100;
  int fatigue = 0;
  uint8_t appetite = 1;
  uint8_t playfulness = 1;
  uint8_t stubbornness = 1;
  LifeStage lifeStage = STAGE_EGG;
  uint8_t warmth = 0;
  uint64_t stageStartedAgeMs = 0;
};
Pet pet;
bool petRestored = false;
bool creationPending = false;
bool startupSaveError = false;
bool creationWriteFailed = false;
uint8_t lastCreationPhase = 255;
uint64_t petAgeAtBootMs = 0;
unsigned long petAgeBootMillis = 0;
uint32_t restoredRtcElapsedSeconds = 0;
esp_sleep_wakeup_cause_t bootWakeCause = ESP_SLEEP_WAKEUP_UNDEFINED;
unsigned long lastRtcDiagnosticAt = 0;

enum ScreenState {
  SCREEN_MAIN,
  SCREEN_FOOD,
  SCREEN_PLAY,
  SCREEN_MEDICINE,
  SCREEN_CLEAN,
  SCREEN_REST,
  SCREEN_STATUS,
};
ScreenState currentScreen = SCREEN_MAIN;

enum MenuItem {
  MENU_FOOD,
  MENU_PLAY,
  MENU_MEDICINE,
  MENU_CLEAN,
  MENU_SLEEP,
  MENU_STATUS,
};
MenuItem selectedMenu = MENU_FOOD;
constexpr int MENU_COUNT = 6;

const char* menuTitle(MenuItem menu);

struct Button {
  uint8_t pin;
  bool stableState = HIGH;
  bool lastReading = HIGH;
  unsigned long lastTransitionTime = 0;

  explicit Button(uint8_t buttonPin) : pin(buttonPin) {}
};

Button leftButton{BTN_LEFT};
Button okButton{BTN_OK};
Button rightButton{BTN_RIGHT};

struct SoundStep {
  uint16_t frequency;
  unsigned long duration;
};

constexpr SoundStep SOUND_OK[] = {{1200, 50}, {0, 10}, {1800, 70}};
constexpr SoundStep SOUND_FOOD[] = {{800, 60}, {0, 20}, {1000, 60}};
constexpr SoundStep SOUND_PLAY[] = {
    {1200, 60}, {0, 10}, {1600, 60}, {0, 10}, {2000, 80}};
constexpr SoundStep SOUND_BIRTH[] = {
    {800, 110}, {0, 30}, {1050, 110}, {0, 30},
    {1350, 110}, {0, 30}, {1750, 180}, {0, 40}};
constexpr SoundStep SOUND_WAKE[] = {{1400, 60}, {0, 40}, {1900, 90}};
constexpr SoundStep SOUND_EGG_CRACK[] = {
    {2300, 30}, {0, 25}, {1500, 45}, {0, 20}, {700, 80}};
constexpr SoundStep SOUND_MEDICINE[] = {{900, 50}, {0, 25}, {1300, 80}};
constexpr SoundStep SOUND_CLEAN[] = {{1700, 40}, {0, 20}, {2100, 65}};
constexpr SoundStep SOUND_REST[] = {{700, 70}, {0, 35}, {550, 100}};

struct SoundPlayer {
  const SoundStep* steps = nullptr;
  size_t stepCount = 0;
  size_t stepIndex = 0;
  unsigned long stepStartedAt = 0;
  const SoundStep* queuedSteps = nullptr;
  size_t queuedStepCount = 0;
  bool active = false;
};
SoundPlayer soundPlayer;

enum BootPhase { BOOT_EGG_ROLL, BOOT_CRACKED_EGG, BOOT_CLEAR, BOOT_HELLO, BOOT_DONE };
BootPhase bootPhase = BOOT_EGG_ROLL;
unsigned long bootPhaseStartedAt = 0;
int bootFrame = 0;
int bootEggX = 4;
bool wokeFromDeepSleep = false;
constexpr int BOOT_EGG_END_X = 104;
constexpr unsigned long BOOT_EGG_ROLL_INTERVAL = 60;

enum PowerState { POWER_ACTIVE, POWER_PREPARING_SLEEP };
PowerState powerState = POWER_ACTIVE;
unsigned long lastUserActivityAt = 0;
unsigned long sleepNoticeStartedAt = 0;

unsigned long lastHungerTick = 0;
unsigned long lastHappyTick = 0;
unsigned long lastHealthTick = 0;
unsigned long lastCleanlinessTick = 0;
unsigned long lastFatigueTick = 0;
unsigned long screenTimer = 0;
constexpr unsigned long HUNGER_INTERVAL = 10000;
constexpr unsigned long HAPPY_INTERVAL = 15000;
constexpr unsigned long HEALTH_INTERVAL = 12000;
constexpr unsigned long CLEANLINESS_INTERVAL = 20000;
constexpr unsigned long FATIGUE_INTERVAL = 15000;
constexpr uint32_t MAX_RTC_ELAPSED_SECONDS = 366UL * 24UL * 60UL * 60UL;
constexpr uint32_t MAX_OFFLINE_SIMULATION_SECONDS = 24UL * 60UL * 60UL;

unsigned long lastAnimTick = 0;
unsigned long lastBlinkTick = 0;
constexpr unsigned long ANIM_FRAME_INTERVAL = 180;
constexpr unsigned long BLINK_INTERVAL = 3500;
constexpr unsigned long BLINK_DURATION = 140;
WalkCycle homeWalk;
bool creatureBlink = false;
unsigned long blinkStart = 0;
uint8_t animationPhase = 0;
bool medicineHelped = false;
bool sleepAccepted = false;
bool hatchedThisAction = false;

bool savePending = false;
unsigned long saveRequestedAt = 0;
unsigned long lastPetSaveAt = 0;
unsigned long resetChordStartedAt = 0;

int clampStat(int value) {
  if (value < 0) return 0;
  if (value > 100) return 100;
  return value;
}

uint8_t clampTrait(uint8_t value) {
  return value > 2 ? 2 : value;
}

uint64_t petAgeMs() {
  return petAgeAtBootMs +
         static_cast<uint32_t>(millis() - petAgeBootMillis);
}

uint64_t petAgeMinutes() {
  return petAgeMs() / 60000ULL;
}

uint64_t stageAgeMs() {
  return petAgeMs() - pet.stageStartedAgeMs;
}

const char* lifeStageLabel() {
  switch (pet.lifeStage) {
    case STAGE_EGG: return "EGG";
    case STAGE_BABY: return "BABY";
    case STAGE_YOUNG: return "YOUNG";
    case STAGE_ADULT: return "ADULT";
  }
  return "?";
}

const char* tftScreenLabel() {
  if (bootPhase != BOOT_DONE) return "DRAGON TAMAGOTCHI";
  if (powerState == POWER_PREPARING_SLEEP) return "GOOD NIGHT";
  switch (currentScreen) {
    case SCREEN_MAIN: return "HOME";
    case SCREEN_FOOD: return pet.lifeStage == STAGE_EGG ? "WARM" : "FOOD";
    case SCREEN_PLAY: return "PLAY";
    case SCREEN_MEDICINE: return "MEDICINE";
    case SCREEN_CLEAN: return "CLEAN";
    case SCREEN_REST: return "SLEEP";
    case SCREEN_STATUS: return "STATUS";
  }
  return "";
}

constexpr uint16_t TFT_UI_BACKGROUND = 0x0841;
constexpr uint16_t TFT_HOME_SKY = 0x5D7F;
constexpr uint16_t TFT_HOME_SKY_LIGHT = 0x9E9F;
constexpr uint16_t TFT_HOME_GRASS = 0x6D64;
constexpr uint16_t TFT_HOME_GRASS_DARK = 0x34A3;
constexpr uint16_t TFT_HOME_CREAM = 0xFF39;
constexpr uint16_t TFT_HOME_NAVY = 0x0863;

uint16_t tftAccentColor() {
  if (bootPhase != BOOT_DONE) return ST77XX_MAGENTA;
  switch (currentScreen) {
    case SCREEN_MAIN: return ST77XX_CYAN;
    case SCREEN_FOOD: return 0xFD20; // orange
    case SCREEN_PLAY: return ST77XX_MAGENTA;
    case SCREEN_MEDICINE: return ST77XX_RED;
    case SCREEN_CLEAN: return 0x051F; // bleu clair
    case SCREEN_REST: return 0x4810; // violet sombre
    case SCREEN_STATUS: return ST77XX_GREEN;
  }
  return ST77XX_WHITE;
}

void drawTftCenteredText(const char* text, int16_t y, uint8_t size,
                         uint16_t color) {
  int16_t boundsX;
  int16_t boundsY;
  uint16_t width;
  uint16_t height;
  spiTft.setTextSize(size);
  spiTft.getTextBounds(text, 0, y, &boundsX, &boundsY, &width, &height);
  spiTft.setTextColor(color);
  spiTft.setCursor((TFT_WIDTH - width) / 2, y);
  spiTft.print(text);
}

void drawTftIcon(MenuItem item, int16_t centerX, int16_t centerY,
                 uint16_t color, uint16_t background) {
  switch (item) {
    case MENU_FOOD:
      spiTft.fillCircle(centerX - 3, centerY - 2, 4, color);
      spiTft.fillCircle(centerX + 2, centerY + 2, 4, color);
      spiTft.drawLine(centerX + 4, centerY + 4, centerX + 8, centerY + 8, color);
      spiTft.fillCircle(centerX + 9, centerY + 9, 2, color);
      break;
    case MENU_PLAY:
      spiTft.fillTriangle(centerX, centerY - 8, centerX + 3, centerY - 2,
                          centerX + 9, centerY - 1, color);
      spiTft.fillTriangle(centerX + 7, centerY + 2, centerX + 4, centerY + 8,
                          centerX, centerY + 4, color);
      spiTft.fillTriangle(centerX, centerY + 4, centerX - 4, centerY + 8,
                          centerX - 7, centerY + 2, color);
      spiTft.fillTriangle(centerX - 9, centerY - 1, centerX - 3, centerY - 2,
                          centerX, centerY - 8, color);
      spiTft.fillCircle(centerX, centerY, 4, color);
      break;
    case MENU_MEDICINE:
      spiTft.fillRoundRect(centerX - 4, centerY - 10, 8, 20, 2, color);
      spiTft.fillRoundRect(centerX - 10, centerY - 4, 20, 8, 2, color);
      break;
    case MENU_CLEAN:
      spiTft.fillTriangle(centerX, centerY - 10, centerX - 8, centerY + 3,
                          centerX + 8, centerY + 3, color);
      spiTft.fillCircle(centerX, centerY + 3, 8, color);
      break;
    case MENU_SLEEP:
      spiTft.fillCircle(centerX, centerY, 10, color);
      spiTft.fillCircle(centerX + 5, centerY - 4, 9, background);
      break;
    case MENU_STATUS:
      spiTft.drawRect(centerX - 9, centerY - 9, 18, 18, color);
      spiTft.fillRect(centerX - 5, centerY + 2, 3, 5, color);
      spiTft.fillRect(centerX - 1, centerY - 2, 3, 9, color);
      spiTft.fillRect(centerX + 3, centerY - 6, 3, 13, color);
      break;
  }
}

void drawTftHomeStat(MenuItem icon, int value, int16_t slot,
                     uint16_t color) {
  const int16_t x = slot * 40;
  drawTftIcon(icon, x + 20, 11, color, TFT_HOME_CREAM);
  spiTft.fillRect(x + 2, 23, 36, 8, TFT_HOME_CREAM);
  const int filledSegments = (constrain(value, 0, 100) + 19) / 20;
  for (int segment = 0; segment < 5; ++segment) {
    const int16_t segmentX = x + 3 + segment * 7;
    if (segment < filledSegments) {
      spiTft.fillRect(segmentX, 24, 6, 6, color);
    } else {
      spiTft.drawRect(segmentX, 24, 6, 6, TFT_HOME_NAVY);
    }
  }
}

int tftLifeStageProgress() {
  return pet.lifeStage == STAGE_BABY ? 33 :
         pet.lifeStage == STAGE_YOUNG ? 66 : 100;
}

struct TftDragonFrame {
  TftAssetId asset;
  int8_t yOffset;

  TftDragonFrame(TftAssetId assetId, int8_t verticalOffset = 0)
      : asset(assetId), yOffset(verticalOffset) {}
};

constexpr int8_t tftAnimationBob(uint8_t phase) {
  return phase == 1 || phase == 2 ? -1 : 0;
}

TftDragonFrame tftAnimatedPair(TftAssetId first, TftAssetId second,
                               uint8_t phase) {
  // Four rendered phases preserve both validated keyframes exactly while a
  // one-pixel lift adds an intermediate motion without redrawing the dragon:
  // A, A lifted, B lifted, B.
  phase %= 4;
  return {phase < 2 ? first : second, tftAnimationBob(phase)};
}

TftDragonFrame currentTftHomeDragonFrame() {
  if (pet.mascot != MascotId::DRAGON) {
    const bool walking = homeWalkEnabled(true, pet.lifeStage != STAGE_EGG,
        pet.health, pet.hunger, pet.happiness, pet.fatigue, creatureBlink);
    return {mascotWalkFrame(pet.mascot, homeWalk.right(),
                            walking && !homeWalk.turning() ? homeWalk.phase() : 0)};
  }
  if (pet.health < 30) return {TftAssetId::DRAGON_SICK};
  if (pet.hunger < 25) return {TftAssetId::DRAGON_HUNGRY};
  if (pet.happiness < 25) return {TftAssetId::DRAGON_SAD};
  if (pet.fatigue >= 50) {
    return tftAnimatedPair(TftAssetId::DRAGON_TIRED_01,
                           TftAssetId::DRAGON_TIRED_02, animationPhase);
  }
  if (creatureBlink) return {TftAssetId::DRAGON_BLINK};
  if (pet.happiness >= 95) return {TftAssetId::DRAGON_HAPPY};
  if (homeWalk.turning()) {
    return tftAnimatedPair(TftAssetId::DRAGON_IDLE1,
                           TftAssetId::DRAGON_IDLE2, animationPhase);
  }
  return {mascotWalkFrame(MascotId::DRAGON, homeWalk.right(), homeWalk.phase())};
}

int16_t tftCreatureX() {
  return homeWalk.x();
}

bool tftPointInCircle(int16_t x, int16_t y, int16_t centerX,
                      int16_t centerY, int16_t radius) {
  const int32_t dx = x - centerX;
  const int32_t dy = y - centerY;
  return dx * dx + dy * dy <= radius * radius;
}

uint16_t tftHomeBackgroundAt(int16_t x, int16_t y) {
  uint16_t color = y < 102 ? TFT_HOME_SKY_LIGHT :
                   y < 150 ? TFT_HOME_SKY : TFT_HOME_GRASS;
  const bool leftCloud =
      tftPointInCircle(x, y, 28, 63, 12) ||
      tftPointInCircle(x, y, 42, 62, 16) ||
      tftPointInCircle(x, y, 57, 66, 10) ||
      (x >= 28 && x < 57 && y >= 66 && y < 73);
  const bool rightCloud =
      tftPointInCircle(x, y, 203, 82, 10) ||
      tftPointInCircle(x, y, 215, 80, 13) ||
      (x >= 203 && x < 228 && y >= 83 && y < 89);
  if (leftCloud || rightCloud) color = ST77XX_WHITE;

  const bool bush = tftPointInCircle(x, y, 22, 176, 16) ||
                    tftPointInCircle(x, y, 45, 181, 20) ||
                    tftPointInCircle(x, y, 214, 177, 22);
  if (bush) color = TFT_HOME_GRASS_DARK;
  return color;
}

void drawTftHomeDragon(const TftDragonFrame& frame, int16_t dragonX,
                       int16_t previousX = -1) {
  constexpr int16_t DRAGON_Y = 63;
  // The extra row covers both y=-1 and y=0 phases and clears the previous
  // position, including sprites whose opaque pixels touch a canvas boundary.
  constexpr int16_t DRAW_TOP = DRAGON_Y - 1;
  constexpr int16_t DRAW_HEIGHT = TFT_ASSET_HEIGHT + 1;
  if (!tftAssets.load(frame.asset)) return;
  const uint16_t* pixels = tftAssets.pixels();
  const int16_t left = previousX < 0 ? dragonX : min(dragonX, previousX);
  const int16_t right = previousX < 0
      ? dragonX + TFT_ASSET_WIDTH
      : max(dragonX, previousX) + TFT_ASSET_WIDTH;
  const int16_t regionWidth = right - left;
  uint16_t line[TFT_WIDTH];

  spiTft.startWrite();
  spiTft.setAddrWindow(left, DRAW_TOP, regionWidth, DRAW_HEIGHT);
  for (int16_t screenY = DRAW_TOP;
       screenY < DRAW_TOP + DRAW_HEIGHT; ++screenY) {
    const int16_t spriteY = screenY - DRAGON_Y - frame.yOffset;
    for (int16_t screenX = left; screenX < right; ++screenX) {
      const int16_t spriteX = screenX - dragonX;
      const uint16_t pixel =
          spriteX >= 0 && spriteX < TFT_ASSET_WIDTH &&
                  spriteY >= 0 && spriteY < TFT_ASSET_HEIGHT
          ? pixels[spriteY * TFT_ASSET_WIDTH + spriteX]
          : TFT_ASSET_TRANSPARENT;
      line[screenX - left] = pixel != TFT_ASSET_TRANSPARENT
          ? pixel : tftHomeBackgroundAt(screenX, screenY);
    }
    spiTft.writePixels(line, regionWidth);
  }
  spiTft.endWrite();
}

void drawTftDragonOnSolid(const TftDragonFrame& frame, int16_t dragonY,
                          uint16_t background) {
  constexpr int16_t DRAGON_X = (TFT_WIDTH - TFT_ASSET_WIDTH) / 2;
  // Keep the output window fixed across both animation offsets so a lifted
  // frame cannot leave stale pixels or clip the top of a 112 px asset.
  constexpr int16_t EXTRA_TOP = 1;
  constexpr int16_t DRAW_HEIGHT = TFT_ASSET_HEIGHT + EXTRA_TOP;
  if (!tftAssets.load(frame.asset)) return;
  const uint16_t* pixels = tftAssets.pixels();
  uint16_t line[TFT_ASSET_WIDTH];

  spiTft.startWrite();
  spiTft.setAddrWindow(DRAGON_X, dragonY - EXTRA_TOP,
                       TFT_ASSET_WIDTH, DRAW_HEIGHT);
  for (int16_t outputY = 0; outputY < DRAW_HEIGHT; ++outputY) {
    const int16_t screenY = dragonY - EXTRA_TOP + outputY;
    const int16_t spriteY = screenY - dragonY - frame.yOffset;
    for (int16_t x = 0; x < TFT_ASSET_WIDTH; ++x) {
      const uint16_t pixel = spriteY >= 0 && spriteY < TFT_ASSET_HEIGHT
          ? pixels[spriteY * TFT_ASSET_WIDTH + x]
          : TFT_ASSET_TRANSPARENT;
      line[x] = pixel != TFT_ASSET_TRANSPARENT ? pixel : background;
    }
    spiTft.writePixels(line, TFT_ASSET_WIDTH);
  }
  spiTft.endWrite();
}

void drawTftSpriteOnSolid(const TftDragonFrame& frame, int16_t spriteX,
                          int16_t spriteY, uint16_t background) {
  if (!tftAssets.load(frame.asset)) return;
  const uint16_t* pixels = tftAssets.pixels();
  uint16_t line[TFT_ASSET_WIDTH];

  spiTft.startWrite();
  spiTft.setAddrWindow(spriteX, spriteY, TFT_ASSET_WIDTH, TFT_ASSET_HEIGHT);
  for (int16_t y = 0; y < TFT_ASSET_HEIGHT; ++y) {
    for (int16_t x = 0; x < TFT_ASSET_WIDTH; ++x) {
      const uint16_t pixel = pixels[y * TFT_ASSET_WIDTH + x];
      line[x] = pixel != TFT_ASSET_TRANSPARENT ? pixel : background;
    }
    spiTft.writePixels(line, TFT_ASSET_WIDTH);
  }
  spiTft.endWrite();
}

void drawTftMovingSpriteOnSolid(const TftDragonFrame& frame,
                                int16_t spriteX, int16_t previousX,
                                int16_t spriteY, uint16_t background) {
  if (!tftAssets.load(frame.asset)) return;
  const uint16_t* pixels = tftAssets.pixels();
  const int16_t left = previousX < 0 ? spriteX : min(spriteX, previousX);
  const int16_t right = previousX < 0
      ? spriteX + TFT_ASSET_WIDTH
      : max(spriteX, previousX) + TFT_ASSET_WIDTH;
  const int16_t regionWidth = right - left;
  uint16_t line[TFT_WIDTH];

  spiTft.startWrite();
  spiTft.setAddrWindow(left, spriteY, regionWidth, TFT_ASSET_HEIGHT);
  for (int16_t y = 0; y < TFT_ASSET_HEIGHT; ++y) {
    for (int16_t screenX = left; screenX < right; ++screenX) {
      const int16_t frameX = screenX - spriteX;
      bool opaque = false;
      uint16_t pixel = TFT_ASSET_TRANSPARENT;
      if (frameX >= 0 && frameX < TFT_ASSET_WIDTH) {
        pixel = pixels[y * TFT_ASSET_WIDTH + frameX];
      }
      opaque = pixel != TFT_ASSET_TRANSPARENT;
      line[screenX - left] = opaque ? pixel : background;
    }
    spiTft.writePixels(line, regionWidth);
  }
  spiTft.endWrite();
}

void drawTftHomeMenuItem(MenuItem item, bool selected) {
  const int16_t x = static_cast<int>(item) * 40;
  const uint16_t background = selected ? TFT_HOME_CREAM : TFT_HOME_NAVY;
  const uint16_t foreground = selected ? 0xFD20 : TFT_HOME_CREAM;
  spiTft.fillRect(x, 196, 40, 44, background);
  if (selected) spiTft.drawRect(x + 1, 197, 38, 42, 0xFD20);
  drawTftIcon(item, x + 20, 218, foreground, background);
}

void drawTftHomeNative() {
  spiTft.fillRect(0, 0, TFT_WIDTH, 32, TFT_HOME_CREAM);
  drawTftHomeStat(MENU_FOOD, pet.hunger, 0, 0xFD20);
  drawTftHomeStat(MENU_PLAY, pet.happiness, 1, 0xF81F);
  drawTftHomeStat(MENU_MEDICINE, pet.health, 2, 0xF940);
  drawTftHomeStat(MENU_CLEAN, pet.cleanliness, 3, 0x05FF);
  drawTftHomeStat(MENU_SLEEP, 100 - pet.fatigue, 4, 0xA81F);
  drawTftHomeStat(MENU_STATUS, tftLifeStageProgress(), 5, 0x07F0);

  spiTft.fillRect(0, 32, TFT_WIDTH, 70, TFT_HOME_SKY_LIGHT);
  spiTft.fillRect(0, 102, TFT_WIDTH, 48, TFT_HOME_SKY);
  spiTft.fillRect(0, 150, TFT_WIDTH, 46, TFT_HOME_GRASS);
  spiTft.fillRect(0, 188, TFT_WIDTH, 8, TFT_HOME_GRASS_DARK);
  spiTft.fillCircle(28, 63, 12, ST77XX_WHITE);
  spiTft.fillCircle(42, 62, 16, ST77XX_WHITE);
  spiTft.fillCircle(57, 66, 10, ST77XX_WHITE);
  spiTft.fillRect(28, 66, 29, 7, ST77XX_WHITE);
  spiTft.fillCircle(203, 82, 10, ST77XX_WHITE);
  spiTft.fillCircle(215, 80, 13, ST77XX_WHITE);
  spiTft.fillRect(203, 83, 25, 6, ST77XX_WHITE);
  spiTft.fillCircle(22, 176, 16, TFT_HOME_GRASS_DARK);
  spiTft.fillCircle(45, 181, 20, TFT_HOME_GRASS_DARK);
  spiTft.fillCircle(214, 177, 22, TFT_HOME_GRASS_DARK);

  drawTftHomeDragon(currentTftHomeDragonFrame(), tftCreatureX());

  for (int item = 0; item < MENU_COUNT; ++item) {
    drawTftHomeMenuItem(static_cast<MenuItem>(item),
                        item == static_cast<int>(selectedMenu));
  }
}

TftDragonFrame currentTftActionFrame() {
  // Temporary identity-preserving fallback, not a new approved action animation.
  if (pet.mascot != MascotId::DRAGON) return {mascotWalkFrame(pet.mascot, true, 0)};
  const uint8_t phase =
      ((millis() - screenTimer) / ANIM_FRAME_INTERVAL) % 4;
  switch (currentScreen) {
    case SCREEN_FOOD:
      return tftAnimatedPair(TftAssetId::DRAGON_FOOD_01,
                             TftAssetId::DRAGON_FOOD_02, phase);
    case SCREEN_PLAY:
      return tftAnimatedPair(TftAssetId::DRAGON_PLAY_01,
                             TftAssetId::DRAGON_PLAY_02, phase);
    case SCREEN_MEDICINE:
      return tftAnimatedPair(TftAssetId::DRAGON_MEDICINE_01,
                             TftAssetId::DRAGON_MEDICINE_02, phase);
    case SCREEN_CLEAN:
      return tftAnimatedPair(TftAssetId::DRAGON_CLEAN_01,
                             TftAssetId::DRAGON_CLEAN_02, phase);
    case SCREEN_REST:
      if (sleepAccepted) {
        return tftAnimatedPair(TftAssetId::DRAGON_SLEEP_01,
                               TftAssetId::DRAGON_SLEEP_02, phase);
      }
      return tftAnimatedPair(TftAssetId::DRAGON_SLEEP_REFUSE_01,
                             TftAssetId::DRAGON_SLEEP_REFUSE_02, phase);
    default:
      return {TftAssetId::DRAGON_IDLE1};
  }
}

uint16_t tftActionBackground() {
  switch (currentScreen) {
    case SCREEN_FOOD: return 0xFE8C;
    case SCREEN_PLAY: return 0xF59F;
    case SCREEN_MEDICINE: return 0x7E9F;
    case SCREEN_CLEAN: return 0xBFFF;
    case SCREEN_REST: return 0xDE7F;
    default: return TFT_UI_BACKGROUND;
  }
}

const char* tftActionMessage() {
  switch (currentScreen) {
    case SCREEN_FOOD: return "MIAM!";
    case SCREEN_PLAY: return "YAY!";
    case SCREEN_MEDICINE:
      return medicineHelped ? "FEEL BETTER!" : "NO MEDICINE";
    case SCREEN_CLEAN: return "ALL CLEAN!";
    case SCREEN_REST:
      if (sleepAccepted) return "Zzz...";
      return pet.stubbornness == 2 ? "ONE MORE!" : "NOT TIRED!";
    default: return "";
  }
}

void drawTftActionNative(const TftDragonFrame& frame) {
  const uint16_t background = tftActionBackground();
  spiTft.fillScreen(background);
  spiTft.fillRect(0, 0, TFT_WIDTH, 32, tftAccentColor());
  drawTftCenteredText(tftScreenLabel(), 9, 2, ST77XX_WHITE);
  drawTftDragonOnSolid(frame, 43, background);

  drawTftCenteredText(tftActionMessage(), 166, 2, TFT_HOME_NAVY);
  for (int item = 0; item < MENU_COUNT; ++item) {
    drawTftHomeMenuItem(static_cast<MenuItem>(item),
                        item == static_cast<int>(selectedMenu));
  }
}

void drawTftStatusRow(const char* label, int value, int16_t y,
                      uint16_t color) {
  spiTft.setTextSize(2);
  spiTft.setTextColor(TFT_HOME_NAVY, TFT_HOME_CREAM);
  spiTft.setCursor(12, y + 5);
  spiTft.print(label);
  spiTft.setCursor(92, y + 5);
  if (value < 100) spiTft.print(' ');
  if (value < 10) spiTft.print(' ');
  spiTft.print(value);

  const int filledSegments = (constrain(value, 0, 100) + 19) / 20;
  for (int segment = 0; segment < 5; ++segment) {
    const int16_t x = 134 + segment * 19;
    if (segment < filledSegments) {
      spiTft.fillRoundRect(x, y + 4, 15, 16, 2, color);
    } else {
      spiTft.drawRoundRect(x, y + 4, 15, 16, 2, TFT_HOME_NAVY);
    }
  }
}

void drawTftStatusNative() {
  spiTft.fillScreen(TFT_HOME_CREAM);
  spiTft.fillRect(0, 0, TFT_WIDTH, 32, tftAccentColor());
  drawTftCenteredText("STATUS", 9, 2, ST77XX_WHITE);

  drawTftStatusRow("FOOD", pet.hunger, 38, 0xFD20);
  drawTftStatusRow("HAPPY", pet.happiness, 66, 0xF81F);
  drawTftStatusRow("HP", pet.health, 94, 0xF940);
  drawTftStatusRow("CLEAN", pet.cleanliness, 122, 0x05FF);
  drawTftStatusRow("REST", 100 - pet.fatigue, 150, 0xA81F);
  drawTftStatusRow("GROW", tftLifeStageProgress(), 178, 0x07F0);

  spiTft.fillRect(0, 210, TFT_WIDTH, 30, TFT_HOME_NAVY);
  spiTft.setTextSize(1);
  spiTft.setTextColor(TFT_HOME_CREAM, TFT_HOME_NAVY);
  spiTft.setCursor(12, 221);
  spiTft.print(lifeStageLabel());
  RtcDateTime dateTime;
  spiTft.setCursor(82, 221);
  if (rtcClock.read(dateTime)) {
    char timeLabel[6];
    snprintf(timeLabel, sizeof(timeLabel), "%02u:%02u",
             dateTime.hour, dateTime.minute);
    spiTft.print(timeLabel);
  } else {
    spiTft.print("--:--");
  }
  spiTft.setCursor(150, 221);
  spiTft.print("AGE ");
  spiTft.print(static_cast<unsigned long long>(petAgeMinutes()));
  spiTft.print(" MIN");
}

TftDragonFrame tftRollingEggFrame(int frame);

void drawTftSleepNoticeNative() {
  constexpr uint16_t NIGHT_BACKGROUND = 0x1085;
  spiTft.fillScreen(NIGHT_BACKGROUND);
  spiTft.fillCircle(196, 42, 22, 0xFFE0);
  spiTft.fillCircle(205, 35, 22, NIGHT_BACKGROUND);
  drawTftCenteredText("GOOD NIGHT", 14, 2, ST77XX_WHITE);
  if (pet.lifeStage == STAGE_EGG) {
    drawTftSpriteOnSolid(tftRollingEggFrame(0), 64, 58, NIGHT_BACKGROUND);
  } else {
    drawTftDragonOnSolid({pet.mascot == MascotId::DRAGON ? TftAssetId::DRAGON_SLEEPING
                          : mascotWalkFrame(pet.mascot, true, 0)}, 58,
                         NIGHT_BACKGROUND);
  }
  drawTftCenteredText("Zzz...", 184, 2, 0xDE7F);
}

TftDragonFrame tftRollingEggFrame(int frame) {
  switch (frame % 4) {
    case 0: return {TftAssetId::EGG_ROLL_01};
    case 1: return {TftAssetId::EGG_ROLL_02};
    case 2: return {TftAssetId::EGG_ROLL_03};
    default: return {TftAssetId::EGG_ROLL_04};
  }
}

TftDragonFrame tftCrackingEggFrame(int frame) {
  switch (constrain(frame, 0, 2)) {
    case 0: return {TftAssetId::EGG_CRACK_01};
    case 1: return {TftAssetId::EGG_CRACK_02};
    default: return {TftAssetId::EGG_CRACKED};
  }
}

void drawTftBootNative() {
  constexpr uint16_t BOOT_BACKGROUND = 0x1085;
  static int lastPhase = -1;
  static int16_t lastRollX = -1;
  const bool phaseChanged = lastPhase != static_cast<int>(bootPhase);
  if (phaseChanged) {
    spiTft.fillScreen(BOOT_BACKGROUND);
    spiTft.fillRect(0, 0, TFT_WIDTH, 34, 0x4810);
    drawTftCenteredText("TAMAGOTCHI", 10, 2, ST77XX_WHITE);
    lastPhase = static_cast<int>(bootPhase);
    lastRollX = -1;
  }

  if (bootPhase == BOOT_EGG_ROLL) {
    const int16_t x = map(bootEggX, 4, BOOT_EGG_END_X, 4, 124);
    drawTftMovingSpriteOnSolid(tftRollingEggFrame(bootFrame), x, lastRollX,
                               58, BOOT_BACKGROUND);
    lastRollX = x;
    if (phaseChanged)
      drawTftCenteredText("A NEW FRIEND IS COMING...", 202, 1, 0xFFE0);
  } else if (bootPhase == BOOT_CRACKED_EGG) {
    drawTftSpriteOnSolid(tftCrackingEggFrame(bootFrame), 64, 58,
                         BOOT_BACKGROUND);
    if (phaseChanged) drawTftCenteredText("CRACK!", 199, 2, 0xFFE0);
  } else if (bootPhase == BOOT_HELLO) {
    if (pet.lifeStage == STAGE_EGG) {
      drawTftSpriteOnSolid(tftRollingEggFrame(0), 64, 56, BOOT_BACKGROUND);
      drawTftCenteredText("OK: WARM ME", 190, 2, ST77XX_WHITE);
    } else {
      drawTftSpriteOnSolid({pet.mascot == MascotId::DRAGON ? TftAssetId::DRAGON_IDLE1
                            : mascotWalkFrame(pet.mascot, true, 0)}, 64, 52,
                           BOOT_BACKGROUND);
      drawTftCenteredText(petRestored ? "WELCOME BACK!" : "HELLO!", 188, 2,
                          ST77XX_WHITE);
    }
  }
}

void drawTftEggHomeDetails() {
  constexpr uint16_t NEST_BACKGROUND = 0xFE8C;
  spiTft.fillRect(0, 160, TFT_WIDTH, 56, NEST_BACKGROUND);
  drawTftCenteredText(menuTitle(selectedMenu), 166, 1, TFT_HOME_NAVY);
  drawTftCenteredText("WARMTH", 182, 1, TFT_HOME_NAVY);
  for (int segment = 0; segment < EGG_WARMTH_REQUIRED; ++segment) {
    const int16_t x = 83 + segment * 27;
    if (segment < pet.warmth) spiTft.fillRoundRect(x, 196, 20, 13, 3, 0xFD20);
    else spiTft.drawRoundRect(x, 196, 20, 13, 3, TFT_HOME_NAVY);
  }
}

void drawTftEggHomeNative(const TftDragonFrame& frame) {
  constexpr uint16_t NEST_BACKGROUND = 0xFE8C;
  spiTft.fillScreen(NEST_BACKGROUND);
  spiTft.fillRect(0, 0, TFT_WIDTH, 34, 0xFD20);
  drawTftCenteredText("DRAGON EGG", 10, 2, ST77XX_WHITE);
  drawTftSpriteOnSolid(frame, 64, 48, NEST_BACKGROUND);
  drawTftEggHomeDetails();
  spiTft.fillRect(0, 216, TFT_WIDTH, 24, TFT_HOME_NAVY);
  drawTftCenteredText("SELECT FOOD + OK", 224, 1, TFT_HOME_CREAM);
}

TftDragonFrame currentTftEggActionFrame() {
  if (!hatchedThisAction) return tftRollingEggFrame(pet.warmth);
  const int crackFrame = min(static_cast<int>((millis() - screenTimer) / 350),
                             2);
  return tftCrackingEggFrame(crackFrame);
}

void drawTftEggActionNative(const TftDragonFrame& frame) {
  constexpr uint16_t NEST_BACKGROUND = 0xFE8C;
  spiTft.fillScreen(NEST_BACKGROUND);
  spiTft.fillRect(0, 0, TFT_WIDTH, 34, 0xFD20);
  drawTftCenteredText(hatchedThisAction ? "HATCHED!" : "WARM", 10, 2,
                      ST77XX_WHITE);
  drawTftSpriteOnSolid(frame, 64, 52, NEST_BACKGROUND);
  if (hatchedThisAction) {
    drawTftCenteredText("WELCOME, BABY DRAGON!", 184, 1, TFT_HOME_NAVY);
  } else if (selectedMenu == MENU_FOOD) {
    char warmthLabel[16];
    snprintf(warmthLabel, sizeof(warmthLabel), "WARM %u/%u", pet.warmth,
             EGG_WARMTH_REQUIRED);
    drawTftCenteredText(warmthLabel, 182, 2, TFT_HOME_NAVY);
  } else {
    drawTftCenteredText("FOOD: WARM FIRST", 184, 1, TFT_HOME_NAVY);
  }
}

void beginTftUi() {
  externalFlash.configureChipSelects();
  pinMode(TFT_BLK_PIN, OUTPUT);
  digitalWrite(TFT_BLK_PIN, HIGH);

  SPI.begin(TFT_SCLK_PIN, SPI_MISO_PIN, TFT_MOSI_PIN, -1);
  spiTft.init(TFT_WIDTH, TFT_HEIGHT, SPI_MODE3);
  // Rotation 0 conserve l'image retournee adaptee au montage sur breadboard
  // et l'offset natif Adafruit de 80 lignes valide sur cette orientation.
  spiTft.setRotation(0);
  spiTft.invertDisplay(true);
  spiTft.setSPISpeed(TFT_SPI_FREQUENCY);
  spiTft.fillScreen(ST77XX_BLACK);
}

void drawTftUi() {
  static int lastHunger = -1;
  static int lastHappiness = -1;
  static int lastHealth = -1;
  static int lastCleanliness = -1;
  static int lastLifeStage = -1;
  static int lastTftScreen = -1;
  static int lastTftBootPhase = -1;
  static int lastSelectedMenu = -1;
  static int lastFatigue = -1;
  static int lastWarmth = -1;
  static int lastTftDragonX = -1;
  static int8_t lastTftDragonYOffset = 0;
  static TftAssetId lastTftAsset = TftAssetId::INVALID;

  if (bootPhase != BOOT_DONE) {
    drawTftBootNative();
    lastTftScreen = -1;
    lastTftDragonX = -1;
    lastTftDragonYOffset = 0;
    lastTftBootPhase = static_cast<int>(bootPhase);
    lastTftAsset = TftAssetId::INVALID;
    return;
  }

  const bool nativeSleepNotice = powerState == POWER_PREPARING_SLEEP;
  if (nativeSleepNotice) {
    drawTftSleepNoticeNative();
    lastTftScreen = -1;
    lastTftAsset = pet.mascot == MascotId::DRAGON ? TftAssetId::DRAGON_SLEEPING
                    : mascotWalkFrame(pet.mascot, true, 0);
    lastTftDragonYOffset = 0;
    return;
  }

  const bool nativeEggAction = powerState == POWER_ACTIVE &&
                               currentScreen == SCREEN_FOOD &&
                               (pet.lifeStage == STAGE_EGG ||
                                hatchedThisAction);
  if (nativeEggAction) {
    const TftDragonFrame eggFrame = currentTftEggActionFrame();
    const bool fullRedraw =
        lastTftScreen != static_cast<int>(currentScreen) ||
        lastTftBootPhase != static_cast<int>(bootPhase);
    if (fullRedraw) drawTftEggActionNative(eggFrame);
    else if (lastTftAsset != eggFrame.asset)
      drawTftSpriteOnSolid(eggFrame, 64, 52, 0xFE8C);
    lastTftScreen = static_cast<int>(currentScreen);
    lastTftBootPhase = static_cast<int>(bootPhase);
    lastTftAsset = eggFrame.asset;
    lastTftDragonYOffset = 0;
    lastWarmth = pet.warmth;
    lastTftDragonX = -1;
    return;
  }

  const bool nativeEggHome = powerState == POWER_ACTIVE &&
                             currentScreen == SCREEN_MAIN &&
                             pet.lifeStage == STAGE_EGG;
  if (nativeEggHome) {
    const TftDragonFrame eggFrame =
        tftRollingEggFrame((millis() / 300) % 4);
    const bool fullRedraw =
        lastTftScreen != static_cast<int>(currentScreen) ||
        lastTftBootPhase != static_cast<int>(bootPhase) ||
        lastWarmth < 0;
    if (fullRedraw) drawTftEggHomeNative(eggFrame);
    else {
      if (lastTftAsset != eggFrame.asset)
        drawTftSpriteOnSolid(eggFrame, 64, 48, 0xFE8C);
      if (lastSelectedMenu != static_cast<int>(selectedMenu) ||
          lastWarmth != pet.warmth) drawTftEggHomeDetails();
    }
    lastTftScreen = static_cast<int>(currentScreen);
    lastTftBootPhase = static_cast<int>(bootPhase);
    lastSelectedMenu = static_cast<int>(selectedMenu);
    lastWarmth = pet.warmth;
    lastTftAsset = eggFrame.asset;
    lastTftDragonYOffset = 0;
    lastTftDragonX = -1;
    return;
  }

  const bool nativeStatus = powerState == POWER_ACTIVE &&
                            currentScreen == SCREEN_STATUS;
  if (nativeStatus) {
    if (lastTftScreen != static_cast<int>(currentScreen) ||
        lastTftBootPhase != static_cast<int>(bootPhase)) {
      drawTftStatusNative();
    }
    lastTftScreen = static_cast<int>(currentScreen);
    lastTftBootPhase = static_cast<int>(bootPhase);
    lastTftAsset = TftAssetId::INVALID;
    lastTftDragonYOffset = 0;
    lastTftDragonX = -1;
    return;
  }

  const bool nativeAction = bootPhase == BOOT_DONE &&
                            powerState == POWER_ACTIVE &&
                            pet.lifeStage != STAGE_EGG &&
                            !hatchedThisAction &&
                            (currentScreen == SCREEN_FOOD ||
                             currentScreen == SCREEN_PLAY ||
                             currentScreen == SCREEN_MEDICINE ||
                             currentScreen == SCREEN_CLEAN ||
                             currentScreen == SCREEN_REST);
  if (nativeAction) {
    const TftDragonFrame dragonFrame = currentTftActionFrame();
    const bool fullRedraw =
        lastTftScreen != static_cast<int>(currentScreen) ||
        lastTftBootPhase != static_cast<int>(bootPhase);
    if (fullRedraw) drawTftActionNative(dragonFrame);
    else if (lastTftAsset != dragonFrame.asset ||
             lastTftDragonYOffset != dragonFrame.yOffset)
      drawTftDragonOnSolid(dragonFrame, 43, tftActionBackground());
    lastTftScreen = static_cast<int>(currentScreen);
    lastTftBootPhase = static_cast<int>(bootPhase);
    lastTftAsset = dragonFrame.asset;
    lastTftDragonYOffset = dragonFrame.yOffset;
    lastTftDragonX = -1;
    return;
  }

  const bool nativeHome = bootPhase == BOOT_DONE &&
                          powerState == POWER_ACTIVE &&
                          currentScreen == SCREEN_MAIN &&
                          pet.lifeStage != STAGE_EGG;
  if (nativeHome) {
    const TftDragonFrame dragonFrame = currentTftHomeDragonFrame();
    const int16_t dragonX = tftCreatureX();
    const bool fullRedraw =
        lastTftScreen != static_cast<int>(currentScreen) ||
        lastTftBootPhase != static_cast<int>(bootPhase) ||
        lastLifeStage < 0;
    if (fullRedraw) {
      drawTftHomeNative();
    } else {
      if (lastHunger != pet.hunger)
        drawTftHomeStat(MENU_FOOD, pet.hunger, 0, 0xFD20);
      if (lastHappiness != pet.happiness)
        drawTftHomeStat(MENU_PLAY, pet.happiness, 1, 0xF81F);
      if (lastHealth != pet.health)
        drawTftHomeStat(MENU_MEDICINE, pet.health, 2, 0xF940);
      if (lastCleanliness != pet.cleanliness)
        drawTftHomeStat(MENU_CLEAN, pet.cleanliness, 3, 0x05FF);
      if (lastFatigue != pet.fatigue)
        drawTftHomeStat(MENU_SLEEP, 100 - pet.fatigue, 4, 0xA81F);
      if (lastLifeStage != static_cast<int>(pet.lifeStage))
        drawTftHomeStat(MENU_STATUS, tftLifeStageProgress(), 5, 0x07F0);
      if (lastSelectedMenu != static_cast<int>(selectedMenu)) {
        if (lastSelectedMenu >= 0 && lastSelectedMenu < MENU_COUNT) {
          drawTftHomeMenuItem(static_cast<MenuItem>(lastSelectedMenu), false);
        }
        drawTftHomeMenuItem(selectedMenu, true);
      }
      if (lastTftAsset != dragonFrame.asset ||
          lastTftDragonYOffset != dragonFrame.yOffset ||
          lastTftDragonX != dragonX) {
        drawTftHomeDragon(dragonFrame, dragonX, lastTftDragonX);
      }
    }
    lastTftScreen = static_cast<int>(currentScreen);
    lastTftBootPhase = static_cast<int>(bootPhase);
    lastSelectedMenu = static_cast<int>(selectedMenu);
    lastHunger = pet.hunger;
    lastHappiness = pet.happiness;
    lastHealth = pet.health;
    lastCleanliness = pet.cleanliness;
    lastFatigue = pet.fatigue;
    lastLifeStage = static_cast<int>(pet.lifeStage);
    lastTftAsset = dragonFrame.asset;
    lastTftDragonYOffset = dragonFrame.yOffset;
    lastTftDragonX = dragonX;
    return;
  }

}

bool saveCurrentPet() {
  uint32_t rtcUnixTime = 0;
  rtcClock.readUnixTime(rtcUnixTime);
  const PetSaveData data{
      static_cast<uint8_t>(pet.hunger),
      static_cast<uint8_t>(pet.happiness),
      static_cast<uint8_t>(pet.health),
      static_cast<uint8_t>(pet.cleanliness),
      static_cast<uint8_t>(pet.fatigue),
      pet.appetite,
      pet.playfulness,
      pet.stubbornness,
      static_cast<uint8_t>(pet.lifeStage),
      pet.warmth,
      petAgeMs(),
      pet.stageStartedAgeMs,
      rtcUnixTime,
      static_cast<uint8_t>(pet.mascot),
  };
  if (!savePetSave(data)) {
    Serial.println("Pet save failed");
    return false;
  }

  savePending = false;
  lastPetSaveAt = millis();
  Serial.println("Pet saved");
  return true;
}

void markPetDirty() {
  savePending = true;
  saveRequestedAt = millis();
}

void updatePersistence() {
  const unsigned long now = millis();
  if (savePending && now - saveRequestedAt >= PET_SAVE_DEBOUNCE_INTERVAL) {
    saveCurrentPet();
  } else if (!savePending && now - lastPetSaveAt >= PET_SAVE_CHECKPOINT_INTERVAL) {
    saveCurrentPet();
  }
}

void startSoundStep(unsigned long now) {
  const SoundStep& step = soundPlayer.steps[soundPlayer.stepIndex];
  soundPlayer.stepStartedAt = now;
  if (step.frequency == 0) noTone(BUZZER_PIN);
  else tone(BUZZER_PIN, step.frequency, step.duration);
}

void playSound(const SoundStep* steps, size_t stepCount) {
  soundPlayer.steps = steps;
  soundPlayer.stepCount = stepCount;
  soundPlayer.stepIndex = 0;
  soundPlayer.queuedSteps = nullptr;
  soundPlayer.queuedStepCount = 0;
  soundPlayer.active = true;
  startSoundStep(millis());
}

void queueSound(const SoundStep* steps, size_t stepCount) {
  if (!soundPlayer.active) {
    playSound(steps, stepCount);
    return;
  }
  soundPlayer.queuedSteps = steps;
  soundPlayer.queuedStepCount = stepCount;
}

void updateAudio() {
  if (!soundPlayer.active) return;

  const unsigned long now = millis();
  while (soundPlayer.active && now - soundPlayer.stepStartedAt >=
                                   soundPlayer.steps[soundPlayer.stepIndex].duration) {
    soundPlayer.stepStartedAt += soundPlayer.steps[soundPlayer.stepIndex].duration;
    soundPlayer.stepIndex++;
    if (soundPlayer.stepIndex < soundPlayer.stepCount) {
      const SoundStep& step = soundPlayer.steps[soundPlayer.stepIndex];
      if (step.frequency == 0) noTone(BUZZER_PIN);
      else tone(BUZZER_PIN, step.frequency, step.duration);
      continue;
    }
    if (soundPlayer.queuedSteps != nullptr) {
      soundPlayer.steps = soundPlayer.queuedSteps;
      soundPlayer.stepCount = soundPlayer.queuedStepCount;
      soundPlayer.stepIndex = 0;
      soundPlayer.queuedSteps = nullptr;
      soundPlayer.queuedStepCount = 0;
      const SoundStep& step = soundPlayer.steps[0];
      if (step.frequency == 0) noTone(BUZZER_PIN);
      else tone(BUZZER_PIN, step.frequency, step.duration);
      continue;
    }
    noTone(BUZZER_PIN);
    soundPlayer.active = false;
  }
}

void soundMenu() { tone(BUZZER_PIN, 1800, 30); }
void soundOk() { playSound(SOUND_OK, sizeof(SOUND_OK) / sizeof(SOUND_OK[0])); }
void soundFood() { queueSound(SOUND_FOOD, sizeof(SOUND_FOOD) / sizeof(SOUND_FOOD[0])); }
void soundPlay() { queueSound(SOUND_PLAY, sizeof(SOUND_PLAY) / sizeof(SOUND_PLAY[0])); }
void soundWake() { playSound(SOUND_WAKE, sizeof(SOUND_WAKE) / sizeof(SOUND_WAKE[0])); }
void soundMedicine() { queueSound(SOUND_MEDICINE, sizeof(SOUND_MEDICINE) / sizeof(SOUND_MEDICINE[0])); }
void soundClean() { queueSound(SOUND_CLEAN, sizeof(SOUND_CLEAN) / sizeof(SOUND_CLEAN[0])); }
void soundRest() { queueSound(SOUND_REST, sizeof(SOUND_REST) / sizeof(SOUND_REST[0])); }

void goToScreen(ScreenState newScreen);

const char* menuTitle(MenuItem menu) {
  if (pet.lifeStage == STAGE_EGG) {
    return menu == MENU_FOOD ? "WARM" : "WARM ME FIRST";
  }
  switch (menu) {
    case MENU_FOOD: return pet.lifeStage == STAGE_BABY ? "MILK" : "FOOD";
    case MENU_PLAY: return pet.lifeStage == STAGE_BABY ? "CUDDLE" : "PLAY";
    case MENU_MEDICINE: return "MEDICINE";
    case MENU_CLEAN: return "CLEAN";
    case MENU_SLEEP: return "SLEEP";
    case MENU_STATUS: return "STATUS";
  }
  return "";
}


void drawBootEggFrame() {
  presentDisplay();
}

void drawBootCrackedEgg() {
  presentDisplay();
}

void drawBootHello() {
  presentDisplay();
}

void drawSleepScreen() {
  presentDisplay();
}

void startBootAnimation() {
  bootPhaseStartedAt = millis();
  bootFrame = 0;
  if (wokeFromDeepSleep || pet.lifeStage == STAGE_EGG) {
    bootPhase = BOOT_HELLO;
    drawBootHello();
    if (wokeFromDeepSleep) soundWake();
    return;
  }

  bootPhase = BOOT_EGG_ROLL;
  bootEggX = 4;
  drawBootEggFrame();
}

void enterDeepSleep() {
  saveCurrentPet();
  spiTft.enableDisplay(false);
  digitalWrite(TFT_BLK_PIN, LOW);

  const esp_err_t backlightHeld =
      gpio_hold_en(static_cast<gpio_num_t>(TFT_BLK_PIN));
  if (backlightHeld != ESP_OK) {
    Serial.println("Backlight hold setup failed");
    digitalWrite(TFT_BLK_PIN, HIGH);
    spiTft.enableDisplay(true);
    powerState = POWER_ACTIVE;
    lastUserActivityAt = millis();
    return;
  }
  gpio_deep_sleep_hold_en();

  const uint64_t wakePinMask = 1ULL << BTN_OK;
  const esp_err_t wakeupConfigured = esp_deep_sleep_enable_gpio_wakeup(
      wakePinMask, ESP_GPIO_WAKEUP_GPIO_LOW);
  if (wakeupConfigured != ESP_OK) {
    Serial.println("Deep sleep wake setup failed");
    gpio_deep_sleep_hold_dis();
    gpio_hold_dis(static_cast<gpio_num_t>(TFT_BLK_PIN));
    digitalWrite(TFT_BLK_PIN, HIGH);
    spiTft.enableDisplay(true);
    powerState = POWER_ACTIVE;
    lastUserActivityAt = millis();
    return;
  }

  Serial.println("Entering deep sleep");
  Serial.flush();
  esp_deep_sleep_start();
}

void updatePowerManagement() {
  const unsigned long now = millis();
  if (powerState == POWER_ACTIVE &&
      now - lastUserActivityAt >= INACTIVITY_SLEEP_INTERVAL) {
    powerState = POWER_PREPARING_SLEEP;
    sleepNoticeStartedAt = now;
    drawSleepScreen();
    return;
  }

  if (powerState == POWER_PREPARING_SLEEP &&
      now - sleepNoticeStartedAt >= SLEEP_NOTICE_DURATION) {
    enterDeepSleep();
  }
}

void updateBootAnimation() {
  const unsigned long now = millis();
  switch (bootPhase) {
    case BOOT_EGG_ROLL:
      if (now - bootPhaseStartedAt >= BOOT_EGG_ROLL_INTERVAL) {
        bootPhaseStartedAt += BOOT_EGG_ROLL_INTERVAL;
        bootFrame++;
        bootEggX += 2;
        if (bootEggX >= BOOT_EGG_END_X) {
          bootEggX = BOOT_EGG_END_X;
          bootPhase = BOOT_CRACKED_EGG;
          bootFrame = 0;
          drawBootCrackedEgg();
          playSound(SOUND_EGG_CRACK, sizeof(SOUND_EGG_CRACK) / sizeof(SOUND_EGG_CRACK[0]));
        } else drawBootEggFrame();
      }
      break;
    case BOOT_CRACKED_EGG:
      if (now - bootPhaseStartedAt >= 260) {
        bootPhaseStartedAt += 260;
        if (++bootFrame < 3) drawBootCrackedEgg();
        else {
          bootPhase = BOOT_CLEAR;
          presentDisplay();
        }
      }
      break;
    case BOOT_CLEAR:
      if (now - bootPhaseStartedAt >= 120) {
        bootPhase = BOOT_HELLO;
        bootPhaseStartedAt = now;
        drawBootHello();
        if (!petRestored) {
          playSound(SOUND_BIRTH, sizeof(SOUND_BIRTH) / sizeof(SOUND_BIRTH[0]));
        }
      }
      break;
    case BOOT_HELLO:
      if (now - bootPhaseStartedAt >= 1340) {
        bootPhase = BOOT_DONE;
        lastUserActivityAt = now;
        goToScreen(SCREEN_MAIN);
      }
      break;
    case BOOT_DONE:
      break;
  }
}

void drawMainScreen() {
  presentDisplay();
}

void drawFoodScreen() {
  presentDisplay();
}

void drawPlayScreen() {
  presentDisplay();
}

void drawMedicineScreen() {
  presentDisplay();
}

void drawCleanScreen() {
  presentDisplay();
}

void drawRestScreen() {
  presentDisplay();
}

void drawStatusScreen() {
  presentDisplay();
}

void goToScreen(ScreenState newScreen) {
  currentScreen = newScreen;
  screenTimer = millis();
  switch (currentScreen) {
    case SCREEN_MAIN: drawMainScreen(); break;
    case SCREEN_FOOD: drawFoodScreen(); break;
    case SCREEN_PLAY: drawPlayScreen(); break;
    case SCREEN_MEDICINE: drawMedicineScreen(); break;
    case SCREEN_CLEAN: drawCleanScreen(); break;
    case SCREEN_REST: drawRestScreen(); break;
    case SCREEN_STATUS: drawStatusScreen(); break;
  }
}

void feedPet() {
  hatchedThisAction = false;
  if (pet.lifeStage == STAGE_EGG) {
    pet.warmth++;
    if (pet.warmth >= EGG_WARMTH_REQUIRED) {
      pet.warmth = EGG_WARMTH_REQUIRED;
      pet.lifeStage = STAGE_BABY;
      pet.stageStartedAgeMs = petAgeMs();
      hatchedThisAction = true;
      queueSound(SOUND_BIRTH, sizeof(SOUND_BIRTH) / sizeof(SOUND_BIRTH[0]));
      Serial.println("Egg hatched: baby dragon");
    } else {
      soundFood();
    }
    markPetDirty();
    goToScreen(SCREEN_FOOD);
    return;
  }
  constexpr int FOOD_RECOVERY[] = {15, 20, 25};
  pet.hunger = clampStat(pet.hunger + FOOD_RECOVERY[pet.appetite]);
  markPetDirty();
  soundFood();
  goToScreen(SCREEN_FOOD);
}

void playWithPet() {
  if (pet.lifeStage == STAGE_EGG) {
    hatchedThisAction = false;
    goToScreen(SCREEN_FOOD);
    return;
  }
  constexpr int PLAY_HAPPINESS[] = {10, 15, 20};
  constexpr int PLAY_FATIGUE[] = {8, 12, 16};
  pet.happiness = clampStat(pet.happiness + PLAY_HAPPINESS[pet.playfulness]);
  pet.fatigue = clampStat(pet.fatigue + PLAY_FATIGUE[pet.playfulness]);
  pet.hunger = clampStat(pet.hunger - 3);
  pet.cleanliness = clampStat(pet.cleanliness - 5);
  markPetDirty();
  soundPlay();
  goToScreen(SCREEN_PLAY);
}

void giveMedicine() {
  if (pet.lifeStage == STAGE_EGG) {
    hatchedThisAction = false;
    goToScreen(SCREEN_FOOD);
    return;
  }
  medicineHelped = pet.health < 70;
  if (medicineHelped) {
    pet.health = clampStat(pet.health + 25);
    pet.happiness = clampStat(pet.happiness - 2);
    markPetDirty();
  }
  soundMedicine();
  goToScreen(SCREEN_MEDICINE);
}

void cleanPet() {
  if (pet.lifeStage == STAGE_EGG) {
    hatchedThisAction = false;
    goToScreen(SCREEN_FOOD);
    return;
  }
  pet.cleanliness = clampStat(pet.cleanliness + 40);
  markPetDirty();
  soundClean();
  goToScreen(SCREEN_CLEAN);
}

void letPetRest() {
  if (pet.lifeStage == STAGE_EGG) {
    hatchedThisAction = false;
    goToScreen(SCREEN_FOOD);
    return;
  }
  constexpr int SLEEP_THRESHOLD[] = {50, 65, 80};
  sleepAccepted = pet.fatigue >= SLEEP_THRESHOLD[pet.stubbornness];
  if (sleepAccepted) {
    pet.fatigue = clampStat(pet.fatigue - 50);
    pet.happiness = clampStat(pet.happiness + 3);
    pet.hunger = clampStat(pet.hunger - 1);
    markPetDirty();
  }
  soundRest();
  goToScreen(SCREEN_REST);
}

void updateLifeCycle() {
  if (pet.lifeStage == STAGE_BABY && stageAgeMs() >= BABY_STAGE_DURATION) {
    pet.lifeStage = STAGE_YOUNG;
    pet.stageStartedAgeMs += BABY_STAGE_DURATION;
    markPetDirty();
    Serial.println("Life stage: young dragon");
  }
  if (pet.lifeStage == STAGE_YOUNG && stageAgeMs() >= YOUNG_STAGE_DURATION) {
    pet.lifeStage = STAGE_ADULT;
    pet.stageStartedAgeMs += YOUNG_STAGE_DURATION;
    markPetDirty();
    Serial.println("Life stage: adult dragon");
  }
}

void applyOfflineSimulation(uint32_t elapsedSeconds) {
  const uint32_t simulatedSeconds =
      min(elapsedSeconds, MAX_OFFLINE_SIMULATION_SECONDS);
  const uint32_t elapsedMs = simulatedSeconds * 1000UL;
  if (elapsedMs == 0) return;

  uint32_t nextHunger = HUNGER_INTERVAL;
  uint32_t nextHappy = HAPPY_INTERVAL;
  uint32_t nextCleanliness = CLEANLINESS_INTERVAL;
  uint32_t nextFatigue = FATIGUE_INTERVAL;
  uint32_t nextHealth = HEALTH_INTERVAL;

  while (true) {
    const uint32_t nextEvent =
        min(min(nextHunger, nextHappy),
            min(min(nextCleanliness, nextFatigue), nextHealth));
    if (nextEvent > elapsedMs) break;

    // Preserve the same ordering as the live simulation when events coincide.
    if (nextHunger == nextEvent) {
      pet.hunger = clampStat(pet.hunger - 1);
      nextHunger += HUNGER_INTERVAL;
    }
    if (nextHappy == nextEvent) {
      pet.happiness = clampStat(pet.happiness - 1);
      if (pet.fatigue >= 80) {
        pet.happiness = clampStat(pet.happiness - 1);
      }
      nextHappy += HAPPY_INTERVAL;
    }
    if (nextCleanliness == nextEvent) {
      pet.cleanliness = clampStat(pet.cleanliness - 1);
      nextCleanliness += CLEANLINESS_INTERVAL;
    }
    if (nextFatigue == nextEvent) {
      pet.fatigue = clampStat(pet.fatigue + 1);
      nextFatigue += FATIGUE_INTERVAL;
    }
    if (nextHealth == nextEvent) {
      if (pet.hunger < 25) pet.health--;
      if (pet.happiness < 20) pet.health--;
      if (pet.cleanliness < 25) pet.health--;
      if (pet.fatigue >= 80) pet.health--;
      pet.health = clampStat(pet.health);
      nextHealth += HEALTH_INTERVAL;
    }
  }

  Serial.printf("Offline simulation: %lu s applied%s\n",
                static_cast<unsigned long>(simulatedSeconds),
                elapsedSeconds > simulatedSeconds ? " (24 h cap)" : "");
  markPetDirty();
}

void updateSimulation() {
  unsigned long now = millis();
  bool petChanged = false;
  if (now - lastHungerTick >= HUNGER_INTERVAL) {
    lastHungerTick = now;
    pet.hunger = clampStat(pet.hunger - 1);
    petChanged = true;
    Serial.print("Hunger: "); Serial.println(pet.hunger);
  }
  if (now - lastHappyTick >= HAPPY_INTERVAL) {
    lastHappyTick = now;
    pet.happiness = clampStat(pet.happiness - 1);
    if (pet.fatigue >= 80) pet.happiness = clampStat(pet.happiness - 1);
    petChanged = true;
    Serial.print("Happy: "); Serial.println(pet.happiness);
  }
  if (now - lastCleanlinessTick >= CLEANLINESS_INTERVAL) {
    lastCleanlinessTick = now;
    pet.cleanliness = clampStat(pet.cleanliness - 1);
    petChanged = true;
    Serial.print("Cleanliness: "); Serial.println(pet.cleanliness);
  }
  if (now - lastFatigueTick >= FATIGUE_INTERVAL) {
    lastFatigueTick = now;
    pet.fatigue = clampStat(pet.fatigue + 1);
    petChanged = true;
    Serial.print("Fatigue: "); Serial.println(pet.fatigue);
  }
  if (now - lastHealthTick >= HEALTH_INTERVAL) {
    lastHealthTick = now;
    if (pet.hunger < 25) pet.health--;
    if (pet.happiness < 20) pet.health--;
    if (pet.cleanliness < 25) pet.health--;
    if (pet.fatigue >= 80) pet.health--;
    pet.health = clampStat(pet.health);
    petChanged = true;
    Serial.print("Health: "); Serial.println(pet.health);
  }
  if (petChanged) markPetDirty();
}

void updateRtcDiagnostics() {
  if (RTC_DIAGNOSTIC_REPORT_INTERVAL == 0) return;
  const unsigned long now = millis();
  if (now - lastRtcDiagnosticAt < RTC_DIAGNOSTIC_REPORT_INTERVAL) return;
  lastRtcDiagnosticAt = now;

  RtcDateTime dateTime;
  const bool valid = rtcClock.read(dateTime);
  Serial.printf("RTC SUMMARY: wake=%d elapsed=%lu s age=%llu ms time=",
                static_cast<int>(bootWakeCause),
                static_cast<unsigned long>(restoredRtcElapsedSeconds),
                static_cast<unsigned long long>(petAgeMs()));
  if (valid) {
    Serial.printf("%04u-%02u-%02u %02u:%02u:%02u\n",
                  dateTime.year, dateTime.month, dateTime.day,
                  dateTime.hour, dateTime.minute, dateTime.second);
  } else {
    Serial.println("INVALID");
  }
}

void updateCreatureAnimation() {
  unsigned long now = millis();
  bool redraw = false;
  if (now - lastAnimTick >= ANIM_FRAME_INTERVAL) {
    lastAnimTick = now;
    animationPhase = (animationPhase + 1) % 4;
    redraw = true;
  }
  if (!creatureBlink && now - lastBlinkTick >= BLINK_INTERVAL) {
    creatureBlink = true;
    blinkStart = now;
    lastBlinkTick = now;
    redraw = true;
  }
  if (creatureBlink && now - blinkStart >= BLINK_DURATION) {
    creatureBlink = false;
    redraw = true;
  }
  const bool walking = homeWalkEnabled(
      currentScreen == SCREEN_MAIN, pet.lifeStage != STAGE_EGG,
      pet.health, pet.hunger, pet.happiness, pet.fatigue, creatureBlink);
  if (homeWalk.update(now, walking)) redraw = true;
  if (!redraw) return;
  if (currentScreen == SCREEN_MAIN) drawMainScreen();
  else if (currentScreen == SCREEN_FOOD) drawFoodScreen();
  else if (currentScreen == SCREEN_PLAY) drawPlayScreen();
  else if (currentScreen == SCREEN_MEDICINE) drawMedicineScreen();
  else if (currentScreen == SCREEN_CLEAN) drawCleanScreen();
  else if (currentScreen == SCREEN_REST) drawRestScreen();
}

void updateScreenState() {
  unsigned long now = millis();
  if ((currentScreen == SCREEN_FOOD || currentScreen == SCREEN_PLAY ||
       currentScreen == SCREEN_MEDICINE || currentScreen == SCREEN_CLEAN ||
       currentScreen == SCREEN_REST) &&
      now - screenTimer >= ACTION_SCREEN_DURATION) {
    goToScreen(SCREEN_MAIN);
  }
  if (currentScreen == SCREEN_STATUS && now - screenTimer >= STATUS_SCREEN_DURATION) {
    goToScreen(SCREEN_MAIN);
  }
}

bool buttonPressed(Button& button, unsigned long now) {
  const bool reading = digitalRead(button.pin);

  if (reading != button.lastReading) {
    button.lastReading = reading;
    button.lastTransitionTime = now;
  }

  if (now - button.lastTransitionTime < BUTTON_DEBOUNCE_INTERVAL ||
      reading == button.stableState) {
    return false;
  }

  button.stableState = reading;
  return button.stableState == LOW;
}

bool handleResetChord(unsigned long now) {
  const bool chordHeld = leftButton.stableState == LOW &&
                         rightButton.stableState == LOW;
  if (!chordHeld) {
    resetChordStartedAt = 0;
    return false;
  }

  lastUserActivityAt = now;
  if (resetChordStartedAt == 0) {
    resetChordStartedAt = now;
    return true;
  }
  if (now - resetChordStartedAt < PET_RESET_HOLD_INTERVAL) return true;

  Serial.println("Reset chord accepted");
  if (!clearPetSave()) {
    Serial.println("Pet reset failed");
    resetChordStartedAt = now;
    return true;
  }

  noTone(BUZZER_PIN);
  Serial.println("Pet save cleared; restarting");
  Serial.flush();
  esp_restart();
  return true;
}

void handleButtons() {
  const unsigned long now = millis();
  const bool leftPressed = buttonPressed(leftButton, now);
  const bool okPressed = buttonPressed(okButton, now);
  const bool rightPressed = buttonPressed(rightButton, now);

  if (leftPressed || okPressed || rightPressed) lastUserActivityAt = now;
  if (handleResetChord(now)) return;

  if (currentScreen == SCREEN_MAIN) {
    if (leftPressed) {
      soundMenu();
      int menu = static_cast<int>(selectedMenu) - 1;
      if (menu < 0) menu = MENU_COUNT - 1;
      selectedMenu = static_cast<MenuItem>(menu);
      drawMainScreen();
    }
    if (rightPressed) {
      soundMenu();
      int menu = static_cast<int>(selectedMenu) + 1;
      if (menu >= MENU_COUNT) menu = 0;
      selectedMenu = static_cast<MenuItem>(menu);
      drawMainScreen();
    }
    if (okPressed) {
      soundOk();
      switch (selectedMenu) {
        case MENU_FOOD: feedPet(); break;
        case MENU_PLAY: playWithPet(); break;
        case MENU_MEDICINE: giveMedicine(); break;
        case MENU_CLEAN: cleanPet(); break;
        case MENU_SLEEP: letPetRest(); break;
        case MENU_STATUS: goToScreen(SCREEN_STATUS); break;
      }
    }
  }
}

void drawStartupSaveError() {
  spiTft.fillScreen(0x1085);
  drawTftCenteredText("SAVE PROTECTED", 30, 2, ST77XX_RED);
  drawTftCenteredText("Read/write error", 82, 1, ST77XX_WHITE);
  drawTftCenteredText("No data overwritten", 103, 1, ST77XX_WHITE);
  drawTftCenteredText("OK: retry boot", 150, 1, ST77XX_CYAN);
  drawTftCenteredText("L+R 5s: ERASE PET", 190, 1, ST77XX_RED);
}

void drawCreationChoice(uint8_t phase) {
  constexpr uint16_t background = 0x1085;
  spiTft.fillScreen(background);
  drawTftCenteredText("CHOOSE YOUR PET", 12, 2, ST77XX_CYAN);
  if (tftAssetsReady) {
    drawTftSpriteOnSolid({mascotWalkFrame(pet.mascot, true, phase)}, 64, 42, background);
  } else {
    drawTftCenteredText("ASSETS UNAVAILABLE", 90, 1, ST77XX_RED);
  }
  drawTftCenteredText(mascotWalk(pet.mascot).label, 166, 2, ST77XX_WHITE);
  drawTftCenteredText("< LEFT     RIGHT >", 196, 1, ST77XX_WHITE);
  drawTftCenteredText(creationWriteFailed ? "SAVE FAILED - OK RETRY" : "OK: CREATE (FINAL CHOICE)",
                      218, 1, creationWriteFailed ? ST77XX_RED : ST77XX_CYAN);
  lastCreationPhase = phase;
}

void updateStartupChoice() {
  const uint32_t now = millis();
  const bool left = buttonPressed(leftButton, now);
  const bool right = buttonPressed(rightButton, now);
  const bool ok = buttonPressed(okButton, now);
  if (handleResetChord(now)) return;
  if (startupSaveError) {
    if (ok) esp_restart();
    return;
  }
  if (left != right) {
    const uint8_t count = static_cast<uint8_t>(MascotId::COUNT);
    pet.mascot = static_cast<MascotId>((static_cast<uint8_t>(pet.mascot) +
                                      (right ? 1 : count-1)) % count);
    lastCreationPhase = 255;
  }
  if (ok && tftAssetsReady) {
    // No simulation or NVS pet record exists before confirmation. Start its
    // age and all decay clocks now, not when the choice screen first appeared.
    petAgeAtBootMs = 0;
    petAgeBootMillis = now;
    lastHungerTick = lastHappyTick = lastHealthTick = now;
    lastCleanlinessTick = lastFatigueTick = now;
    lastAnimTick = lastBlinkTick = lastUserActivityAt = now;
    if (saveCurrentPet()) {
      creationPending = false;
      creationWriteFailed = false;
      soundOk();
      startBootAnimation();
      return;
    }
    creationWriteFailed = true;
    lastCreationPhase = 255;
  }
  const uint8_t phase = (now / WalkCycle::kDurationMs) % WalkCycle::kFrames;
  if (phase != lastCreationPhase) drawCreationChoice(phase);
}

void setup() {
  gpio_deep_sleep_hold_dis();
  gpio_hold_dis(static_cast<gpio_num_t>(TFT_BLK_PIN));
  Serial.begin(115200);
  if (STARTUP_SERIAL_DELAY > 0) delay(STARTUP_SERIAL_DELAY);
  bootWakeCause = esp_sleep_get_wakeup_cause();
  wokeFromDeepSleep = bootWakeCause != ESP_SLEEP_WAKEUP_UNDEFINED;
  Serial.printf("Wake cause: %d\n", bootWakeCause);
  beginTftUi();
  probeExternalHardware();
  tftAssetsReady = tftAssets.begin(externalFlash);
  Serial.printf("TFT assets: %s%s%s\n", tftAssetsReady ? "ready" : "error",
                tftAssetsReady ? "" : " - ",
                tftAssetsReady ? "" : tftAssets.error());
  pinMode(BTN_LEFT, INPUT_PULLUP);
  pinMode(BTN_OK, INPUT_PULLUP);
  pinMode(BTN_RIGHT, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);

  const unsigned long now = millis();
  petAgeBootMillis = now;
  for (Button* button : {&leftButton, &okButton, &rightButton}) {
    button->stableState = digitalRead(button->pin);
    button->lastReading = button->stableState;
    button->lastTransitionTime = now;
  }

  PetSaveData restoredData{};
  const PetLoadStatus loadStatus = readPetSave(restoredData);
  petRestored = loadStatus == PetLoadStatus::Loaded;
  if (!petRestored && loadStatus != PetLoadStatus::Missing) {
    startupSaveError = true;
    Serial.println("Save read failed: preserving NVS; explicit retry/reset required");
    drawStartupSaveError();
    return;
  }
  if (petRestored) {
    pet.mascot = static_cast<MascotId>(restoredData.mascot);
    pet.hunger = restoredData.hunger;
    pet.happiness = restoredData.happiness;
    pet.health = restoredData.health;
    pet.cleanliness = restoredData.cleanliness;
    pet.fatigue = clampStat(restoredData.fatigue);
    pet.appetite = clampTrait(restoredData.appetite);
    pet.playfulness = clampTrait(restoredData.playfulness);
    pet.stubbornness = clampTrait(restoredData.stubbornness);
    pet.lifeStage = static_cast<LifeStage>(restoredData.lifeStage);
    pet.warmth = restoredData.warmth;
    petAgeAtBootMs = restoredData.ageMs;
    pet.stageStartedAgeMs = restoredData.stageStartedAgeMs;
    if (rtcBootTimeValid && !externalHardware.rtcAdjusted &&
        restoredData.rtcUnixTime != 0) {
      if (rtcBootDateTime.unixTime >= restoredData.rtcUnixTime) {
        const uint32_t elapsed =
            rtcBootDateTime.unixTime - restoredData.rtcUnixTime;
        if (elapsed <= MAX_RTC_ELAPSED_SECONDS) {
          restoredRtcElapsedSeconds = elapsed;
          petAgeAtBootMs += static_cast<uint64_t>(elapsed) * 1000ULL;
        } else {
          Serial.printf("RTC elapsed rejected: %lu s exceeds safety limit\n",
                        static_cast<unsigned long>(elapsed));
        }
      } else {
        Serial.println("RTC elapsed rejected: clock moved backwards");
      }
    } else if (externalHardware.rtcAdjusted) {
      Serial.println("RTC elapsed skipped after clock adjustment");
    } else {
      Serial.println("RTC elapsed unavailable; active-time fallback used");
    }
    Serial.printf("Pet restored: age=%llu ms, RTC elapsed=%lu s\n",
                  static_cast<unsigned long long>(petAgeAtBootMs),
                  static_cast<unsigned long>(restoredRtcElapsedSeconds));
    applyOfflineSimulation(restoredRtcElapsedSeconds);
    updateLifeCycle();
  } else {
    petAgeAtBootMs = 0;
    pet.appetite = esp_random() % 3;
    pet.playfulness = esp_random() % 3;
    pet.stubbornness = esp_random() % 3;
    pet.lifeStage = STAGE_EGG;
    pet.warmth = 0;
    pet.stageStartedAgeMs = 0;
    Serial.println("New pet created");
  }
  lastHungerTick = now;
  lastHappyTick = now;
  lastHealthTick = now;
  lastCleanlinessTick = now;
  lastFatigueTick = now;
  lastAnimTick = now;
  lastBlinkTick = now;
  lastPetSaveAt = now;
  lastUserActivityAt = now;
  lastRtcDiagnosticAt = now;

  // Save once after boot to establish a fresh RTC anchor and avoid replaying
  // already-applied offline time after an immediate reset.
  if (!petRestored) {
    creationPending = true;
    drawCreationChoice(0);
    return;
  }
  if (!saveCurrentPet()) {
    startupSaveError = true;
    drawStartupSaveError();
    return;
  }

  startBootAnimation();
  Serial.println("Dragon Tamagotchi started");
}

void loop() {
  updateAudio();
  if (startupSaveError || creationPending) {
    updateStartupChoice();
    delay(5);
    return;
  }
  if (bootPhase != BOOT_DONE) {
    updateBootAnimation();
    delay(5);
    return;
  }
  if (powerState == POWER_PREPARING_SLEEP) {
    updatePowerManagement();
    delay(5);
    return;
  }
  updateSimulation();
  updateRtcDiagnostics();
  updateLifeCycle();
  updateScreenState();
  updateCreatureAnimation();
  handleButtons();
  updatePersistence();
  updatePowerManagement();
  delay(5);
}
