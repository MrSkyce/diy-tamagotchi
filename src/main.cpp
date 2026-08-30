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
  unsigned long birthTime = 0;
};
Pet pet;
bool petRestored = false;

enum ScreenState { SCREEN_MAIN, SCREEN_FOOD, SCREEN_PLAY, SCREEN_STATUS };
ScreenState currentScreen = SCREEN_MAIN;

enum MenuItem { MENU_FOOD, MENU_PLAY, MENU_STATUS };
MenuItem selectedMenu = MENU_FOOD;
constexpr int MENU_COUNT = 3;

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

enum BootPhase { BOOT_EGG, BOOT_CRACKED_EGG, BOOT_CLEAR, BOOT_HELLO, BOOT_DONE };
BootPhase bootPhase = BOOT_EGG;
unsigned long bootPhaseStartedAt = 0;
int bootFrame = 0;

enum PowerState { POWER_ACTIVE, POWER_PREPARING_SLEEP };
PowerState powerState = POWER_ACTIVE;
unsigned long lastUserActivityAt = 0;
unsigned long sleepNoticeStartedAt = 0;

unsigned long lastHungerTick = 0;
unsigned long lastHappyTick = 0;
unsigned long lastHealthTick = 0;
unsigned long screenTimer = 0;
constexpr unsigned long HUNGER_INTERVAL = 10000;
constexpr unsigned long HAPPY_INTERVAL = 15000;
constexpr unsigned long HEALTH_INTERVAL = 12000;

unsigned long lastAnimTick = 0;
unsigned long lastBlinkTick = 0;
constexpr unsigned long ANIM_INTERVAL = 450;
constexpr unsigned long BLINK_INTERVAL = 3500;
constexpr unsigned long BLINK_DURATION = 140;
int creatureOffsetX = 0;
bool creatureMoveRight = true;
bool creatureBlink = false;
unsigned long blinkStart = 0;
bool idleFrame = false;

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

void goToScreen(ScreenState newScreen);

void drawHeader(const char* rightText) {
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(2, 4);
  display.print("TAMAGOTCHI");
  display.setCursor(100, 4);
  display.print(rightText);
}

void drawMainMenuItem(int x, const char* label, bool selected) {
  display.setCursor(x, 4);
  display.print(selected ? ">" : " ");
  display.print(label);
}

void drawMainMenu() {
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  drawMainMenuItem(0, "FOOD", selectedMenu == MENU_FOOD);
  drawMainMenuItem(43, "PLAY", selectedMenu == MENU_PLAY);
  drawMainMenuItem(86, "STAT", selectedMenu == MENU_STATUS);
}

void drawCreature(int x, int y, bool blink = false,
                  CreatureExpression expression = EXPRESSION_AUTO) {
  const unsigned char* sprite;
  if (expression == EXPRESSION_HAPPY) sprite = dragon_happy;
  else if (expression == EXPRESSION_SLEEPING) sprite = dragon_sleeping;
  else if (pet.health < 30) sprite = dragon_sick;
  else if (pet.hunger < 25) sprite = dragon_hungry;
  else if (pet.happiness < 25) sprite = dragon_sad;
  else if (blink) sprite = dragon_blink;
  else if (idleFrame) sprite = dragon_idle2;
  else sprite = dragon_idle1;
  display.drawBitmap(x, y, sprite, DRAGON_SPRITE_WIDTH, DRAGON_SPRITE_HEIGHT, SSD1306_WHITE);
}

void drawEgg(int x, int y) {
  display.fillCircle(x + 12, y + 8, 7, SSD1306_WHITE);
  display.fillCircle(x + 12, y + 16, 10, SSD1306_WHITE);
  display.fillRect(x + 3, y + 8, 18, 9, SSD1306_WHITE);
  display.drawPixel(x + 9, y + 6, SSD1306_BLACK);
  display.drawPixel(x + 8, y + 8, SSD1306_BLACK);
  display.drawPixel(x + 8, y + 10, SSD1306_BLACK);
  display.drawPixel(x + 9, y + 12, SSD1306_BLACK);
}

void drawCrackedEgg(int x, int y) {
  drawEgg(x, y);
  display.drawLine(x + 5, y + 15, x + 9, y + 12, SSD1306_BLACK);
  display.drawLine(x + 9, y + 12, x + 12, y + 16, SSD1306_BLACK);
  display.drawLine(x + 12, y + 16, x + 16, y + 12, SSD1306_BLACK);
  display.drawLine(x + 16, y + 12, x + 20, y + 15, SSD1306_BLACK);
}

void drawBootEggFrame(int frame) {
  const int x = 52;
  const int y = 26;
  display.clearDisplay();
  drawHeader("EGG");
  int dx = 0;
  if (frame % 4 == 0) dx = -2;
  else if (frame % 4 == 2) dx = 2;
  drawEgg(x + dx, y);
  display.display();
}

void drawBootCrackedEgg() {
  display.clearDisplay();
  drawHeader("EGG");
  drawCrackedEgg(52, 26);
  display.display();
}

void drawBootHello() {
  display.clearDisplay();
  drawHeader(petRestored ? "BACK" : "HI!");
  drawCreature(52, 22, false);
  display.setTextSize(1);
  display.setCursor(petRestored ? 28 : 44, 55);
  display.print(petRestored ? "Welcome back!" : "Hello!");
  display.display();
}

void drawSleepScreen() {
  display.clearDisplay();
  drawHeader("SLEEP");
  drawCreature(52, 22, false, EXPRESSION_SLEEPING);
  display.setTextSize(1);
  display.setCursor(46, 55);
  display.print("Zzz...");
  display.display();
}

void startBootAnimation() {
  bootPhase = BOOT_EGG;
  bootPhaseStartedAt = millis();
  bootFrame = 0;
  drawBootEggFrame(bootFrame);
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
    case BOOT_EGG:
      if (now - bootPhaseStartedAt >= 160) {
        bootPhaseStartedAt += 160;
        if (++bootFrame < 10) drawBootEggFrame(bootFrame);
        else {
          bootPhase = BOOT_CRACKED_EGG;
          bootFrame = 0;
          drawBootCrackedEgg();
        }
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
  drawCreature(52 + creatureOffsetX, 28, creatureBlink);
  display.display();
}

void drawFoodScreen() {
  display.clearDisplay();
  drawMainMenu();
  drawCreature(52, 20, false, EXPRESSION_HAPPY);
  display.setTextSize(1);
  display.setCursor(35, 53);
  display.print("Nom nom!");
  display.display();
}

void drawPlayScreen() {
  display.clearDisplay();
  drawMainMenu();
  drawCreature(52, 18, false, EXPRESSION_HAPPY);
  display.setTextSize(1);
  display.setCursor(43, 53);
  display.print("Wheee!");
  display.display();
}

void drawStatusScreen() {
  display.clearDisplay();
  drawMainMenu();
  display.setTextSize(1);
  display.setCursor(5, 21); display.print("Food : "); display.print(pet.hunger);
  display.setCursor(5, 31); display.print("Happy: "); display.print(pet.happiness);
  display.setCursor(5, 41); display.print("HP   : "); display.print(pet.health);
  display.setCursor(5, 51); display.print("Age  : "); display.print(petAgeMinutes()); display.print(" min");
  display.display();
}

void goToScreen(ScreenState newScreen) {
  currentScreen = newScreen;
  screenTimer = millis();
  switch (currentScreen) {
    case SCREEN_MAIN: drawMainScreen(); break;
    case SCREEN_FOOD: drawFoodScreen(); break;
    case SCREEN_PLAY: drawPlayScreen(); break;
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
  if (now - lastHealthTick >= HEALTH_INTERVAL) {
    lastHealthTick = now;
    if (pet.hunger < 25) pet.health--;
    if (pet.happiness < 20) pet.health--;
    pet.health = clampStat(pet.health);
    petChanged = true;
    Serial.print("Health: "); Serial.println(pet.health);
  }
  if (petChanged) markPetDirty();
}

void updateCreatureAnimation() {
  unsigned long now = millis();
  if (now - lastAnimTick >= ANIM_INTERVAL) {
    lastAnimTick = now;
    idleFrame = !idleFrame;
    if (creatureMoveRight) {
      creatureOffsetX++;
      if (creatureOffsetX >= 3) creatureMoveRight = false;
    } else {
      creatureOffsetX--;
      if (creatureOffsetX <= -3) creatureMoveRight = true;
    }
    if (currentScreen == SCREEN_MAIN) drawMainScreen();
  }
  if (!creatureBlink && now - lastBlinkTick >= BLINK_INTERVAL) {
    creatureBlink = true;
    blinkStart = now;
    lastBlinkTick = now;
    if (currentScreen == SCREEN_MAIN) drawMainScreen();
  }
  if (creatureBlink && now - blinkStart >= BLINK_DURATION) {
    creatureBlink = false;
    if (currentScreen == SCREEN_MAIN) drawMainScreen();
  }
}

void updateScreenState() {
  unsigned long now = millis();
  if ((currentScreen == SCREEN_FOOD || currentScreen == SCREEN_PLAY) && now - screenTimer >= 900) {
    goToScreen(SCREEN_MAIN);
  }
  if (currentScreen == SCREEN_STATUS && now - screenTimer >= 2500) {
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
        case MENU_STATUS: goToScreen(SCREEN_STATUS); break;
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.printf("Wake cause: %d\n", esp_sleep_get_wakeup_cause());
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
    pet.birthTime = now - restoredData.ageMs;
    Serial.println("Pet restored");
  } else {
    pet.birthTime = now;
    Serial.println("New pet created");
  }
  lastHungerTick = now;
  lastHappyTick = now;
  lastHealthTick = now;
  lastAnimTick = now;
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
