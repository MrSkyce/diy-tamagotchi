#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <esp_sleep.h>

#include "config.h"
#include "persistence.h"
#include "sprites.h"

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

struct Pet {
  int hunger = 80;
  int happiness = 80;
  int health = 100;
  int cleanliness = 100;
  unsigned long birthTime = 0;
};
Pet pet;
bool petRestored = false;

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

enum CreatureExpression {
  EXPRESSION_AUTO,
  EXPRESSION_HAPPY,
  EXPRESSION_SLEEPING,
};

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
constexpr int BOOT_EGG_Y = 28;
constexpr int BOOT_EGG_END_X = SCREEN_WIDTH - EGG_SPRITE_WIDTH;
constexpr unsigned long BOOT_EGG_ROLL_INTERVAL = 60;

enum PowerState { POWER_ACTIVE, POWER_PREPARING_SLEEP };
PowerState powerState = POWER_ACTIVE;
unsigned long lastUserActivityAt = 0;
unsigned long sleepNoticeStartedAt = 0;

unsigned long lastHungerTick = 0;
unsigned long lastHappyTick = 0;
unsigned long lastHealthTick = 0;
unsigned long lastCleanlinessTick = 0;
unsigned long screenTimer = 0;
unsigned long menuTitleShownAt = 0;
constexpr unsigned long HUNGER_INTERVAL = 10000;
constexpr unsigned long HAPPY_INTERVAL = 15000;
constexpr unsigned long HEALTH_INTERVAL = 12000;
constexpr unsigned long CLEANLINESS_INTERVAL = 20000;
constexpr unsigned long MENU_TITLE_DURATION = 1000;

unsigned long lastAnimTick = 0;
unsigned long lastMoveTick = 0;
unsigned long lastBlinkTick = 0;
constexpr unsigned long ANIM_INTERVAL = 450;
constexpr unsigned long CREATURE_MOVE_INTERVAL = 120;
constexpr unsigned long BLINK_INTERVAL = 3500;
constexpr unsigned long BLINK_DURATION = 140;
constexpr int CREATURE_MIN_X = 4;
constexpr int CREATURE_MAX_X = SCREEN_WIDTH - DRAGON_SPRITE_WIDTH - 4;
int creatureX = (SCREEN_WIDTH - DRAGON_SPRITE_WIDTH) / 2;
bool creatureMoveRight = true;
bool creatureBlink = false;
unsigned long blinkStart = 0;
bool idleFrame = false;
bool actionFrame = false;
bool medicineHelped = false;

bool savePending = false;
unsigned long saveRequestedAt = 0;
unsigned long lastPetSaveAt = 0;

int clampStat(int value) {
  if (value < 0) return 0;
  if (value > 100) return 100;
  return value;
}

unsigned long petAgeMinutes() {
  return (millis() - pet.birthTime) / 60000;
}

unsigned long petAgeMs() {
  return millis() - pet.birthTime;
}

bool saveCurrentPet() {
  const PetSaveData data{
      static_cast<uint8_t>(pet.hunger),
      static_cast<uint8_t>(pet.happiness),
      static_cast<uint8_t>(pet.health),
      static_cast<uint8_t>(pet.cleanliness),
      petAgeMs(),
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

void drawHeader(const char* screenLabel) {
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(2, 4);
  display.print(screenLabel);
  display.setCursor(SCREEN_WIDTH - 24, 4);
  display.print(FIRMWARE_VERSION);
}

void drawMainMenuItem(int x, const char* label, bool selected) {
  display.setCursor(x, 4);
  display.print(selected ? ">" : " ");
  display.print(label);
}

void drawMainMenu() {
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  drawMainMenuItem(0, "FD", selectedMenu == MENU_FOOD);
  drawMainMenuItem(21, "PL", selectedMenu == MENU_PLAY);
  drawMainMenuItem(42, "MD", selectedMenu == MENU_MEDICINE);
  drawMainMenuItem(63, "CL", selectedMenu == MENU_CLEAN);
  drawMainMenuItem(84, "SL", selectedMenu == MENU_SLEEP);
  drawMainMenuItem(105, "ST", selectedMenu == MENU_STATUS);
}

const char* menuTitle(MenuItem menu) {
  switch (menu) {
    case MENU_FOOD: return "FOOD";
    case MENU_PLAY: return "PLAY";
    case MENU_MEDICINE: return "MEDICINE";
    case MENU_CLEAN: return "CLEAN";
    case MENU_SLEEP: return "SLEEP";
    case MENU_STATUS: return "STATUS";
  }
  return "";
}

void drawCenteredText(const char* text, int yPosition) {
  int16_t x;
  int16_t y;
  uint16_t width;
  uint16_t height;
  display.getTextBounds(text, 0, yPosition, &x, &y, &width, &height);
  display.setCursor((SCREEN_WIDTH - width) / 2, yPosition);
  display.print(text);
}

void drawMenuTitle(MenuItem menu) {
  drawCenteredText(menuTitle(menu), 16);
}

void drawCreature(int x, int y, bool blink = false,
                  CreatureExpression expression = EXPRESSION_AUTO,
                  bool walking = false) {
  const unsigned char* sprite;
  if (expression == EXPRESSION_HAPPY) sprite = dragon_happy;
  else if (expression == EXPRESSION_SLEEPING) sprite = dragon_sleeping;
  else if (pet.health < 30) sprite = dragon_sick;
  else if (pet.hunger < 25) sprite = dragon_hungry;
  else if (pet.happiness < 25) sprite = dragon_sad;
  else if (blink) sprite = dragon_blink;
  else if (walking && creatureMoveRight) {
    sprite = idleFrame ? dragon_walk_right_02 : dragon_walk_right_01;
  } else if (walking) {
    sprite = idleFrame ? dragon_walk_left_02 : dragon_walk_left_01;
  }
  else if (idleFrame) sprite = dragon_idle2;
  else sprite = dragon_idle1;
  display.drawBitmap(x, y, sprite, DRAGON_SPRITE_WIDTH, DRAGON_SPRITE_HEIGHT, SSD1306_WHITE);
}

void drawBootEggFrame() {
  display.clearDisplay();
  drawHeader("EGG");
  const unsigned char* eggFrames[] = {
      egg_roll_01, egg_roll_02, egg_roll_03, egg_roll_04};
  const unsigned char* egg = eggFrames[bootFrame % 4];
  display.drawBitmap(bootEggX, BOOT_EGG_Y, egg,
                     EGG_SPRITE_WIDTH, EGG_SPRITE_HEIGHT, SSD1306_WHITE);
  display.display();
}

void drawBootCrackedEgg() {
  display.clearDisplay();
  drawHeader("EGG");
  const unsigned char* crackFrames[] = {egg_crack_01, egg_crack_02, egg_cracked};
  display.drawBitmap(BOOT_EGG_END_X, BOOT_EGG_Y, crackFrames[bootFrame],
                     EGG_SPRITE_WIDTH, EGG_SPRITE_HEIGHT, SSD1306_WHITE);
  display.display();
}

void drawBootHello() {
  display.clearDisplay();
  drawHeader(petRestored ? "BACK" : "HI!");
  drawCreature(44, 16, false);
  display.setTextSize(1);
  display.setCursor(petRestored ? 28 : 44, 56);
  display.print(petRestored ? "Welcome back!" : "Hello!");
  display.display();
}

void drawSleepScreen() {
  display.clearDisplay();
  drawHeader("SLEEP");
  drawCreature(44, 16, false, EXPRESSION_SLEEPING);
  display.setTextSize(1);
  display.setCursor(46, 56);
  display.print("Zzz...");
  display.display();
}

void startBootAnimation() {
  bootPhaseStartedAt = millis();
  bootFrame = 0;
  if (wokeFromDeepSleep) {
    bootPhase = BOOT_HELLO;
    drawBootHello();
    soundWake();
    return;
  }

  bootPhase = BOOT_EGG_ROLL;
  bootEggX = 4;
  drawBootEggFrame();
}

void enterDeepSleep() {
  saveCurrentPet();
  display.ssd1306_command(SSD1306_DISPLAYOFF);

  const uint64_t wakePinMask = 1ULL << BTN_OK;
  const esp_err_t wakeupConfigured = esp_deep_sleep_enable_gpio_wakeup(
      wakePinMask, ESP_GPIO_WAKEUP_GPIO_LOW);
  if (wakeupConfigured != ESP_OK) {
    Serial.println("Deep sleep wake setup failed");
    display.ssd1306_command(SSD1306_DISPLAYON);
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
          display.clearDisplay();
          display.display();
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
  display.clearDisplay();
  drawMainMenu();
  if (millis() - menuTitleShownAt < MENU_TITLE_DURATION) {
    drawMenuTitle(selectedMenu);
  }
  drawCreature(creatureX, 24, creatureBlink, EXPRESSION_AUTO, true);
  display.display();
}

void drawFoodScreen() {
  display.clearDisplay();
  drawMainMenu();
  const bool foodFrame = ((millis() - screenTimer) / 300) % 2 != 0;
  const unsigned char* foodSprite = foodFrame ? dragon_food_02 : dragon_food_01;
  display.drawBitmap(44, 20, foodSprite,
                     DRAGON_SPRITE_WIDTH, DRAGON_SPRITE_HEIGHT, SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 40);
  display.print("MIAM!");
  display.display();
}

void drawPlayScreen() {
  display.clearDisplay();
  drawMainMenu();
  drawCreature(44, actionFrame ? 16 : 20, false, EXPRESSION_HAPPY);
  display.setTextSize(1);
  display.setCursor(94, 40);
  display.print("YAY!");
  display.display();
}

void drawMedicineScreen() {
  display.clearDisplay();
  drawMainMenu();
  const unsigned char* medicineSprite =
      actionFrame ? dragon_medicine_02 : dragon_medicine_01;
  display.drawBitmap(44, 24, medicineSprite,
                     DRAGON_SPRITE_WIDTH, DRAGON_SPRITE_HEIGHT, SSD1306_WHITE);
  display.setTextSize(1);
  drawCenteredText(medicineHelped ? "FEEL BETTER!" : "NO MEDICINE", 16);
  display.display();
}

void drawCleanScreen() {
  display.clearDisplay();
  drawMainMenu();
  const unsigned char* cleanSprite = actionFrame ? dragon_clean_02 : dragon_clean_01;
  display.drawBitmap(44, 24, cleanSprite,
                     DRAGON_SPRITE_WIDTH, DRAGON_SPRITE_HEIGHT, SSD1306_WHITE);
  display.setTextSize(1);
  drawCenteredText("ALL CLEAN!", 16);
  display.display();
}

void drawRestScreen() {
  display.clearDisplay();
  drawMainMenu();
  const unsigned char* sleepSprite = actionFrame ? dragon_sleep_02 : dragon_sleep_01;
  display.drawBitmap(44, 24, sleepSprite,
                     DRAGON_SPRITE_WIDTH, DRAGON_SPRITE_HEIGHT, SSD1306_WHITE);
  display.setTextSize(1);
  drawCenteredText("Zzz...", 16);
  display.display();
}

void drawStatusScreen() {
  display.clearDisplay();
  drawMainMenu();
  display.setTextSize(1);
  display.setCursor(3, 18); display.print("FOOD "); display.print(pet.hunger);
  display.setCursor(70, 18); display.print("HAPPY "); display.print(pet.happiness);
  display.setCursor(3, 33); display.print("HP "); display.print(pet.health);
  display.setCursor(70, 33); display.print("CLEAN "); display.print(pet.cleanliness);
  display.setCursor(35, 49); display.print("AGE "); display.print(petAgeMinutes()); display.print(" MIN");
  display.display();
}

void goToScreen(ScreenState newScreen) {
  currentScreen = newScreen;
  screenTimer = millis();
  if (newScreen == SCREEN_MAIN) menuTitleShownAt = screenTimer;
  if (newScreen == SCREEN_FOOD || newScreen == SCREEN_PLAY) actionFrame = false;
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
  pet.hunger = clampStat(pet.hunger + 20);
  markPetDirty();
  soundFood();
  goToScreen(SCREEN_FOOD);
}

void playWithPet() {
  pet.happiness = clampStat(pet.happiness + 15);
  pet.hunger = clampStat(pet.hunger - 3);
  markPetDirty();
  soundPlay();
  goToScreen(SCREEN_PLAY);
}

void giveMedicine() {
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
  pet.cleanliness = clampStat(pet.cleanliness + 40);
  markPetDirty();
  soundClean();
  goToScreen(SCREEN_CLEAN);
}

void letPetRest() {
  pet.happiness = clampStat(pet.happiness + 8);
  pet.health = clampStat(pet.health + 5);
  pet.hunger = clampStat(pet.hunger - 2);
  markPetDirty();
  soundRest();
  goToScreen(SCREEN_REST);
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
    petChanged = true;
    Serial.print("Happy: "); Serial.println(pet.happiness);
  }
  if (now - lastCleanlinessTick >= CLEANLINESS_INTERVAL) {
    lastCleanlinessTick = now;
    pet.cleanliness = clampStat(pet.cleanliness - 1);
    petChanged = true;
    Serial.print("Cleanliness: "); Serial.println(pet.cleanliness);
  }
  if (now - lastHealthTick >= HEALTH_INTERVAL) {
    lastHealthTick = now;
    if (pet.hunger < 25) pet.health--;
    if (pet.happiness < 20) pet.health--;
    if (pet.cleanliness < 25) pet.health--;
    pet.health = clampStat(pet.health);
    petChanged = true;
    Serial.print("Health: "); Serial.println(pet.health);
  }
  if (petChanged) markPetDirty();
}

void updateCreatureAnimation() {
  unsigned long now = millis();
  bool redraw = false;
  if (now - lastAnimTick >= ANIM_INTERVAL) {
    lastAnimTick = now;
    idleFrame = !idleFrame;
    redraw = true;
  }
  if (now - lastMoveTick >= CREATURE_MOVE_INTERVAL) {
    lastMoveTick = now;
    actionFrame = !actionFrame;
    if (creatureMoveRight) {
      creatureX++;
      if (creatureX >= CREATURE_MAX_X) creatureMoveRight = false;
    } else {
      creatureX--;
      if (creatureX <= CREATURE_MIN_X) creatureMoveRight = true;
    }
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

void handleButtons() {
  const unsigned long now = millis();
  const bool leftPressed = buttonPressed(leftButton, now);
  const bool okPressed = buttonPressed(okButton, now);
  const bool rightPressed = buttonPressed(rightButton, now);

  if (leftPressed || okPressed || rightPressed) lastUserActivityAt = now;

  if (currentScreen == SCREEN_MAIN) {
    if (leftPressed) {
      soundMenu();
      int menu = static_cast<int>(selectedMenu) - 1;
      if (menu < 0) menu = MENU_COUNT - 1;
      selectedMenu = static_cast<MenuItem>(menu);
      menuTitleShownAt = now;
      drawMainScreen();
    }
    if (rightPressed) {
      soundMenu();
      int menu = static_cast<int>(selectedMenu) + 1;
      if (menu >= MENU_COUNT) menu = 0;
      selectedMenu = static_cast<MenuItem>(menu);
      menuTitleShownAt = now;
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

void setup() {
  Serial.begin(115200);
  const esp_sleep_wakeup_cause_t wakeCause = esp_sleep_get_wakeup_cause();
  wokeFromDeepSleep = wakeCause != ESP_SLEEP_WAKEUP_UNDEFINED;
  Serial.printf("Wake cause: %d\n", wakeCause);
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("OLED error");
    while (true);
  }
  pinMode(BTN_LEFT, INPUT_PULLUP);
  pinMode(BTN_OK, INPUT_PULLUP);
  pinMode(BTN_RIGHT, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);

  const unsigned long now = millis();
  for (Button* button : {&leftButton, &okButton, &rightButton}) {
    button->stableState = digitalRead(button->pin);
    button->lastReading = button->stableState;
    button->lastTransitionTime = now;
  }

  PetSaveData restoredData{};
  petRestored = loadPetSave(restoredData);
  if (petRestored) {
    pet.hunger = restoredData.hunger;
    pet.happiness = restoredData.happiness;
    pet.health = restoredData.health;
    pet.cleanliness = restoredData.cleanliness;
    pet.birthTime = now - restoredData.ageMs;
    Serial.println("Pet restored");
  } else {
    pet.birthTime = now;
    Serial.println("New pet created");
  }
  lastHungerTick = now;
  lastHappyTick = now;
  lastHealthTick = now;
  lastCleanlinessTick = now;
  lastAnimTick = now;
  lastMoveTick = now;
  lastBlinkTick = now;
  lastPetSaveAt = now;
  lastUserActivityAt = now;

  if (!petRestored) saveCurrentPet();

  startBootAnimation();
  Serial.println("Dragon Tamagotchi started");
}

void loop() {
  updateAudio();
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
  updateScreenState();
  updateCreatureAnimation();
  handleButtons();
  updatePersistence();
  updatePowerManagement();
  delay(5);
}
