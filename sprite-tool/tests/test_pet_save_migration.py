import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


def test_native_v7_migration_v8_roundtrip_and_corruption(tmp_path):
    compiler = shutil.which("c++")
    if not compiler:
        pytest.skip("Native C++ compiler unavailable")
    source = r'''
    #include "pet_save_codec.h"
    #include "mascot_walks.h"
    #include <cassert>
    #include <cstring>
    #include <cstddef>
    // Exact original firmware layout, deliberately independent of v8 encoder.
    struct Legacy {
      uint32_t magic; uint16_t version;
      uint8_t hunger,happiness,health,cleanliness,fatigue;
      uint8_t appetite,playfulness,stubbornness,lifeStage,warmth;
      uint64_t ageMs,stageStartedAgeMs;
      uint32_t rtcUnixTime,checksum;
    };
    static_assert(sizeof(Legacy)==40 && offsetof(Legacy,ageMs)==16 &&
                  offsetof(Legacy,checksum)==36, "legacy layout");
    static_assert(PetSaveCodec::kMascotCount == static_cast<uint8_t>(MascotId::COUNT),
                  "identity validation agrees with runtime registry");
    uint32_t legacyChecksum(const Legacy& p) {
      uint32_t c=0x54414D41u ^ 7u;
      const uint32_t values[]={p.hunger,p.happiness,p.health,p.cleanliness,p.fatigue,
        p.appetite,p.playfulness,p.stubbornness,p.lifeStage,p.warmth,
        uint32_t(p.ageMs),uint32_t(p.ageMs>>32),uint32_t(p.stageStartedAgeMs),
        uint32_t(p.stageStartedAgeMs>>32),p.rtcUnixTime};
      for(auto v:values)c=(c*31u)^v;
      return c;
    }
    int main() {
      Legacy legacy{0x54414D41u,7,81,72,63,54,45,2,1,0,3,2,
                    0x123456789ABULL,0x10000002345ULL,1789000000,0};
      legacy.checksum=legacyChecksum(legacy);
      PetSaveData migrated{};
      assert(PetSaveCodec::decode(reinterpret_cast<uint8_t*>(&legacy),40,migrated));
      assert(migrated.mascot==0 && migrated.ageMs==legacy.ageMs &&
        migrated.stageStartedAgeMs==legacy.stageStartedAgeMs &&
        migrated.rtcUnixTime==legacy.rtcUnixTime && migrated.hunger==81 &&
        migrated.happiness==72 && migrated.health==63 && migrated.cleanliness==54 &&
        migrated.fatigue==45 && migrated.appetite==2 && migrated.playfulness==1 &&
        migrated.stubbornness==0 && migrated.lifeStage==3 && migrated.warmth==2);
      uint8_t bytes[44], again[44];
      for(uint8_t species=0;species<6;++species) {
        migrated.mascot=species;
        assert(PetSaveCodec::encode(migrated,bytes,44));
        PetSaveData loaded{};
        assert(PetSaveCodec::decode(bytes,44,loaded));
        assert(loaded.mascot==species && loaded.ageMs==legacy.ageMs);
        assert(PetSaveCodec::encode(loaded,again,44));
        assert(std::memcmp(bytes,again,44)==0);
        for(size_t n=0;n<44;++n) {
          PetSaveData untouched=migrated;
          assert(!PetSaveCodec::decode(bytes,n,untouched));
          assert(untouched.mascot==species && untouched.ageMs==legacy.ageMs);
        }
        for(size_t i=0;i<44;++i) {
          bytes[i]^=1;
          PetSaveData untouched=migrated;
          assert(!PetSaveCodec::decode(bytes,44,untouched));
          assert(untouched.mascot==species && untouched.ageMs==legacy.ageMs);
          bytes[i]^=1;
        }
      }
      migrated.mascot=6;
      assert(!PetSaveCodec::encode(migrated,bytes,44));
      // Even a valid checksum must not permit an unsupported identity.
      bytes[36]=6;
      PetSaveCodec::write(bytes+40,PetSaveCodec::checksum(migrated,8),4);
      PetSaveData unchanged{};
      assert(!PetSaveCodec::decode(bytes,44,unchanged));
      legacy.checksum^=1;
      assert(!PetSaveCodec::decode(reinterpret_cast<uint8_t*>(&legacy),40,unchanged));
    }
    '''
    binary = tmp_path / "migration-test"
    built = subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror",
                            "-x", "c++", "-I", str(ROOT / "include"), "-", "-o", str(binary)],
                           input=source, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr


def test_real_persistence_adapter_preserves_save_on_read_and_failed_write(tmp_path):
    compiler = shutil.which("c++")
    if not compiler:
        pytest.skip("Native C++ compiler unavailable")
    (tmp_path / "Arduino.h").write_text("#pragma once\n#include <stdint.h>\n")
    (tmp_path / "nvs.h").write_text(r'''
    #pragma once
    #include <vector>
    #include <cstring>
    #include <cstddef>
    #include <cstdint>
    using nvs_handle_t = unsigned;
    using esp_err_t = int;
    constexpr int ESP_OK=0, ESP_FAIL=-1, ESP_ERR_NVS_NOT_FOUND=2, NVS_READONLY=1;
    extern std::vector<uint8_t> nvs;
    extern bool failOpen, shortRead;
    inline int nvs_open(const char*, int, nvs_handle_t* handle) {
      if(failOpen)return ESP_FAIL;
      *handle=1;return ESP_OK;
    }
    inline int nvs_get_blob(nvs_handle_t, const char*, void* dest, size_t* size) {
      if(nvs.empty())return ESP_ERR_NVS_NOT_FOUND;
      if(!dest){*size=nvs.size();return ESP_OK;}
      if(shortRead)--*size;
      std::memcpy(dest,nvs.data(),*size);return ESP_OK;
    }
    inline void nvs_close(nvs_handle_t) {}
    ''')
    (tmp_path / "Preferences.h").write_text(r'''
    #pragma once
    #include <vector>
    #include <cstring>
    #include <cstddef>
    #include <cstdint>
    extern std::vector<uint8_t> nvs;
    extern bool failOpen, failWrite, shortRead;
    extern unsigned writes;
    class Preferences {
      bool readOnly=false;
     public:
      bool begin(const char*, bool ro) {readOnly=ro; return !failOpen;}
      void end() {}
      size_t getBytesLength(const char*) {return nvs.size();}
      size_t getBytes(const char*,void* output,size_t size) {
        size_t n=shortRead?size-1:size;
        std::memcpy(output,nvs.data(),n); return n;
      }
      size_t putBytes(const char*,const void* data,size_t size) {
        if(readOnly || failWrite)return 0;
        auto p=static_cast<const uint8_t*>(data);
        nvs.assign(p,p+size);++writes;return size;
      }
      bool remove(const char*) {
        if(readOnly || nvs.empty())return false;
        nvs.clear();return true;
      }
    };
    ''')
    source = r'''
    #include "Preferences.h"
    #include "pet_save_codec.h"
    #include <cassert>
    std::vector<uint8_t> nvs;
    bool failOpen=false, failWrite=false, shortRead=false;
    unsigned writes=0;
    int main() {
      PetSaveData p{}; p.hunger=80;p.health=100;p.ageMs=123456;p.rtcUnixTime=1234567;
      assert(readPetSave(p)==PetLoadStatus::Missing && writes==0);
      uint8_t bytes[44];assert(PetSaveCodec::encode(p,bytes,44));
      PetSaveCodec::write(bytes+4,7,2);
      PetSaveCodec::write(bytes+36,PetSaveCodec::checksum(p,7),4);
      nvs.assign(bytes,bytes+40);
      auto legacy=nvs;
      PetSaveData loaded{};
      assert(loadPetSave(loaded) && loaded.mascot==0 && loaded.ageMs==123456);
      assert(nvs==legacy && writes==0); // Migration read never writes or clears.
      failWrite=true;
      assert(!savePetSave(loaded) && nvs==legacy);
      failWrite=false;
      assert(savePetSave(loaded) && writes==1 && nvs.size()==44);
      for(uint8_t id=0;id<6;++id) {
        loaded.mascot=id;
        assert(savePetSave(loaded));
        PetSaveData restored{};
        assert(loadPetSave(restored) && restored.mascot==id && restored.ageMs==123456);
      }
      auto good=nvs;
      unsigned before=writes;
      shortRead=true; assert(readPetSave(loaded)==PetLoadStatus::Unavailable); shortRead=false;
      failOpen=true; assert(readPetSave(loaded)==PetLoadStatus::Unavailable && !savePetSave(loaded));failOpen=false;
      assert(nvs==good && writes==before);
      loaded.mascot=255;
      assert(!savePetSave(loaded) && nvs==good);
      nvs[8]^=1; auto damaged=nvs;
      assert(readPetSave(loaded)==PetLoadStatus::Invalid && nvs==damaged && writes==before);
      assert(clearPetSave() && nvs.empty());
      assert(!loadPetSave(loaded));
    }
    '''
    binary = tmp_path / "adapter-test"
    built = subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(tmp_path), "-I", str(ROOT / "include"),
                            str(ROOT / "src/persistence.cpp"), "-x", "c++", "-", "-o", str(binary)],
                           input=source, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
