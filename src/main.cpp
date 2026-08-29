#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include "config.h"
#include "sprites.h"

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

struct Pet {
  int hunger = 80;
  int happiness = 80;
  int health = 100;
  unsigned long birthTime = 0;
};
Pet pet;

enum ScreenState { SCREEN_MAIN, SCREEN_FOOD, SCREEN_PLAY, SCREEN_STATUS };
ScreenState currentScreen = SCREEN_MAIN;

enum MenuItem { MENU_FOOD, MENU_PLAY, MENU_STATUS };
MenuItem selectedMenu = MENU_FOOD;
constexpr int MENU_COUNT = 3;

bool lastLeft = HIGH;
bool lastOk = HIGH;
bool lastRight = HIGH;

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

int clampStat(int value) {
  if (value < 0) return 0;
  if (value > 100) return 100;
  return value;
}

unsigned long petAgeMinutes() {
  return (millis() - pet.birthTime) / 60000;
}

void soundMenu() { tone(BUZZER_PIN, 1800, 30); }
void soundOk() { tone(BUZZER_PIN, 1200, 50); delay(60); tone(BUZZER_PIN, 1800, 70); }
void soundFood() { tone(BUZZER_PIN, 800, 60); delay(80); tone(BUZZER_PIN, 1000, 60); }
void soundPlay() { tone(BUZZER_PIN, 1200, 60); delay(70); tone(BUZZER_PIN, 1600, 60); delay(70); tone(BUZZER_PIN, 2000, 80); }
void soundBirth() {
  tone(BUZZER_PIN, 800, 110); delay(140);
  tone(BUZZER_PIN, 1050, 110); delay(140);
  tone(BUZZER_PIN, 1350, 110); delay(140);
  tone(BUZZER_PIN, 1750, 180); delay(220);
  noTone(BUZZER_PIN);
}

void drawHeader(const char* rightText) {
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(2, 4);
  display.print("TAMAGOTCHI");
  display.setCursor(100, 4);
  display.print(rightText);
}

void drawCreature(int x, int y, bool blink = false) {
  const unsigned char* sprite;
  if (pet.health < 30 || pet.hunger < 25 || pet.happiness < 25) sprite = dragon_sad;
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

void bootAnimation() {
  const int x = 52;
  const int y = 26;
  for (int i = 0; i < 10; i++) {
    display.clearDisplay();
    drawHeader("EGG");
    int dx = 0;
    if (i % 4 == 0) dx = -2;
    else if (i % 4 == 2) dx = 2;
    drawEgg(x + dx, y);
    display.display();
    delay(160);
  }
  for (int i = 0; i < 3; i++) {
    display.clearDisplay();
    drawHeader("EGG");
    drawCrackedEgg(x, y);
    display.display();
    delay(260);
  }
  display.clearDisplay(); display.display(); delay(120);
  display.clearDisplay();
  drawHeader("HI!");
  drawCreature(52, 22, false);
  display.setTextSize(1);
  display.setCursor(44, 55);
  display.print("Hello!");
  display.display();
  soundBirth();
  delay(700);
}

void drawMainScreen() {
  display.clearDisplay();
  drawHeader("PET");
  drawCreature(52 + creatureOffsetX, 22, creatureBlink);
  display.setTextSize(1);
  display.setCursor(3, 55); display.print(selectedMenu == MENU_FOOD ? ">" : " "); display.print("FOOD");
  display.setCursor(46, 55); display.print(selectedMenu == MENU_PLAY ? ">" : " "); display.print("PLAY");
  display.setCursor(88, 55); display.print(selectedMenu == MENU_STATUS ? ">" : " "); display.print("STAT");
  display.display();
}

void drawFoodScreen() {
  display.clearDisplay();
  drawHeader("FOOD");
  drawCreature(52, 20, false);
  display.setTextSize(1);
  display.setCursor(35, 53);
  display.print("Nom nom!");
  display.display();
}

void drawPlayScreen() {
  display.clearDisplay();
  drawHeader("PLAY");
  drawCreature(52, 18, false);
  display.setTextSize(1);
  display.setCursor(43, 53);
  display.print("Wheee!");
  display.display();
}

void drawStatusScreen() {
  display.clearDisplay();
  drawHeader("STAT");
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
  soundFood();
  goToScreen(SCREEN_FOOD);
}

void playWithPet() {
  pet.happiness = clampStat(pet.happiness + 15);
  pet.hunger = clampStat(pet.hunger - 3);
  soundPlay();
  goToScreen(SCREEN_PLAY);
}

void updateSimulation() {
  unsigned long now = millis();
  if (now - lastHungerTick >= HUNGER_INTERVAL) {
    lastHungerTick = now;
    pet.hunger = clampStat(pet.hunger - 1);
    Serial.print("Hunger: "); Serial.println(pet.hunger);
  }
  if (now - lastHappyTick >= HAPPY_INTERVAL) {
    lastHappyTick = now;
    pet.happiness = clampStat(pet.happiness - 1);
    Serial.print("Happy: "); Serial.println(pet.happiness);
  }
  if (now - lastHealthTick >= HEALTH_INTERVAL) {
    lastHealthTick = now;
    if (pet.hunger < 25) pet.health--;
    if (pet.happiness < 20) pet.health--;
    pet.health = clampStat(pet.health);
    Serial.print("Health: "); Serial.println(pet.health);
  }
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

void handleButtons() {
  bool left = digitalRead(BTN_LEFT);
  bool ok = digitalRead(BTN_OK);
  bool right = digitalRead(BTN_RIGHT);

  if (currentScreen == SCREEN_MAIN) {
    if (lastLeft == HIGH && left == LOW) {
      soundMenu();
      int menu = static_cast<int>(selectedMenu) - 1;
      if (menu < 0) menu = MENU_COUNT - 1;
      selectedMenu = static_cast<MenuItem>(menu);
      drawMainScreen();
    }
    if (lastRight == HIGH && right == LOW) {
      soundMenu();
      int menu = static_cast<int>(selectedMenu) + 1;
      if (menu >= MENU_COUNT) menu = 0;
      selectedMenu = static_cast<MenuItem>(menu);
      drawMainScreen();
    }
    if (lastOk == HIGH && ok == LOW) {
      soundOk();
      switch (selectedMenu) {
        case MENU_FOOD: feedPet(); break;
        case MENU_PLAY: playWithPet(); break;
        case MENU_STATUS: goToScreen(SCREEN_STATUS); break;
      }
    }
  }

  lastLeft = left;
  lastOk = ok;
  lastRight = right;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("OLED error");
    while (true);
  }
  pinMode(BTN_LEFT, INPUT_PULLUP);
  pinMode(BTN_OK, INPUT_PULLUP);
  pinMode(BTN_RIGHT, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);

  pet.birthTime = millis();
  unsigned long now = millis();
  lastHungerTick = now;
  lastHappyTick = now;
  lastHealthTick = now;
  lastAnimTick = now;
  lastBlinkTick = now;

  bootAnimation();
  goToScreen(SCREEN_MAIN);
  Serial.println("Dragon Tamagotchi started");
}

void loop() {
  updateSimulation();
  updateScreenState();
  updateCreatureAnimation();
  handleButtons();
  delay(5);
}
