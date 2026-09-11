import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


def test_actual_creation_handler_confirmation_failure_and_protection(tmp_path):
    compiler = shutil.which("c++")
    if not compiler:
        pytest.skip("Native C++ compiler unavailable")
    main = (ROOT / "src/main.cpp").read_text()
    # Compile the actual firmware handler, replacing only hardware services.
    handler = main[main.index("void updateStartupChoice() {"):main.index("\nvoid setup() {")]
    source = r'''
    #include "mascot_walks.h"
    #include <cassert>
    uint32_t now=1000;
    uint32_t millis(){return now;}
    struct Button{bool pressed=false;};
    Button leftButton, rightButton, okButton;
    bool buttonPressed(Button& b,uint32_t){bool p=b.pressed;b.pressed=false;return p;}
    bool chord=false;
    bool handleResetChord(uint32_t){return chord;}
    bool startupSaveError=false, creationPending=true, creationWriteFailed=false;
    bool tftAssetsReady=true, saveWorks=true;
    uint8_t lastCreationPhase=255;
    struct Pet{MascotId mascot=MascotId::DRAGON;} pet;
    uint64_t petAgeAtBootMs=0;
    uint32_t petAgeBootMillis=0,lastHungerTick=0,lastHappyTick=0,lastHealthTick=0;
    uint32_t lastCleanlinessTick=0,lastFatigueTick=0,lastAnimTick=0,lastBlinkTick=0,lastUserActivityAt=0;
    unsigned saves=0, boots=0, restarts=0, sounds=0, draws=0;
    bool saveCurrentPet(){++saves;return saveWorks;}
    void soundOk(){++sounds;}
    void startBootAnimation(){++boots;}
    void esp_restart(){++restarts;}
    void drawCreationChoice(uint8_t phase){++draws;lastCreationPhase=phase;}
    ''' + handler + r'''
    int main(){
      updateStartupChoice();assert(saves==0 && boots==0 && draws==1);
      leftButton.pressed=true;updateStartupChoice();
      assert(pet.mascot==MascotId::PURPLE_SALAMANDER && saves==0);
      rightButton.pressed=true;updateStartupChoice();assert(pet.mascot==MascotId::DRAGON);
      for(unsigned i=0;i<4;++i){rightButton.pressed=true;updateStartupChoice();}
      assert(pet.mascot==MascotId::YELLOW_BIRD && saves==0);
      now=60000;tftAssetsReady=false;okButton.pressed=true;updateStartupChoice();
      assert(saves==0 && creationPending);
      tftAssetsReady=true;saveWorks=false;okButton.pressed=true;updateStartupChoice();
      assert(saves==1 && boots==0 && creationPending && creationWriteFailed);
      updateStartupChoice();assert(saves==1); // no automatic write retry
      saveWorks=true;now=70000;okButton.pressed=true;updateStartupChoice();
      assert(saves==2 && boots==1 && !creationPending && !creationWriteFailed);
      assert(petAgeAtBootMs==0 && petAgeBootMillis==now && lastHungerTick==now &&
        lastHappyTick==now && lastHealthTick==now && lastCleanlinessTick==now &&
        lastFatigueTick==now && lastAnimTick==now && lastBlinkTick==now);
      startupSaveError=true;rightButton.pressed=true;updateStartupChoice();
      assert(pet.mascot==MascotId::YELLOW_BIRD && saves==2);
      okButton.pressed=true;updateStartupChoice();assert(restarts==1 && saves==2);
      chord=true;okButton.pressed=true;updateStartupChoice();assert(restarts==1 && saves==2);
    }
    '''
    binary = tmp_path / "creation-test"
    compiled = subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror",
                               "-I", str(ROOT / "include"), "-x", "c++", "-", "-o", str(binary)],
                              input=source, capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run([str(binary)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
