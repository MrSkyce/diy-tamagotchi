import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


def test_real_embedded_reader_all_frames_cache_and_failures(tmp_path):
    compiler = shutil.which("c++")
    if not compiler:
        pytest.skip("Native C++ compiler unavailable")
    codec = runpy.run_path(str(ROOT / "tools/generate_tft_assets.py"))
    paths = sorted((ROOT / "assets/tft").glob("*.bmp"))
    assets, expected = {}, bytearray()
    for path in paths:
        width, height, pixels = codec["read_color_bmp"](path)
        pixels, _ = codec["normalize_transparent_matte"](width, height, pixels)
        assets[path.stem] = width, height, pixels
        expected.extend(codec["pixels_as_bytes"]([codec["rgb565"](*rgb) for rgb in pixels]))
    image, _, _ = codec["build_flash_image"](paths, assets)
    (tmp_path / "flash.bin").write_bytes(image)
    (tmp_path / "expected.bin").write_bytes(expected)
    (tmp_path / "Arduino.h").write_text(
        "#pragma once\n#include <stdint.h>\n#include <stddef.h>\n"
        "#include <algorithm>\nusing std::min;\n")
    source = r'''
    #include "tft_asset_store.h"
    #include <cassert>
    #include <cstring>
    #include <fstream>
    #include <iterator>
    #include <vector>
    std::vector<uint8_t> flashBytes;
    bool detected=true;
    unsigned reads=0;
    bool W25Q64Flash::isExpectedDevice(){return detected;}
    void W25Q64Flash::readBytes(uint32_t address,uint8_t* dest,size_t length){
      assert(address<=flashBytes.size() && length<=flashBytes.size()-address);
      std::memcpy(dest,flashBytes.data()+address,length);++reads;
    }
    std::vector<uint8_t> file(const char* path){
      std::ifstream f(path,std::ios::binary);assert(f.good());
      return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
    }
    uint32_t le32(size_t offset){
      return uint32_t(flashBytes[offset]) | uint32_t(flashBytes[offset+1])<<8 |
             uint32_t(flashBytes[offset+2])<<16 | uint32_t(flashBytes[offset+3])<<24;
    }
    void put32(size_t offset,uint32_t value){
      for(unsigned i=0;i<4;++i)flashBytes[offset+i]=uint8_t(value>>(i*8));
    }
    int main(int argc,char** argv){
      assert(argc==3);flashBytes=file(argv[1]);auto expected=file(argv[2]);
      const auto good=flashBytes;
      W25Q64Flash flash; TftAssetStore store;
      assert(!store.load(TftAssetId::INVALID));
      assert(!store.load(static_cast<TftAssetId>(0)) && reads==0);
      assert(store.begin(flash));
      const uint16_t* buffer=store.pixels();
      for(unsigned i=0;i<TFT_ASSET_COUNT;++i){
        auto id=static_cast<TftAssetId>(i);
        assert(store.load(id) && store.loadedAsset()==id && store.pixels()==buffer);
        for(size_t p=0;p<TFT_ASSET_PIXEL_COUNT;++p){
          size_t offset=(i*TFT_ASSET_PIXEL_COUNT+p)*2;
          uint16_t word=uint16_t(expected[offset]) | uint16_t(expected[offset+1])<<8;
          assert(buffer[p]==word);
        }
        unsigned before=reads;assert(store.load(id) && reads==before);
      }
      assert(!store.load(TftAssetId::INVALID));
      assert(store.load(static_cast<TftAssetId>(TFT_ASSET_COUNT-1)));
      assert(std::strcmp(store.error(),"none")==0);
      // A rejected reinitialization must not leave the previous cache/device usable.
      for(unsigned offset : {0u,8u,10u,12u,16u}){
        flashBytes=good;flashBytes[offset]^=1;
        assert(!store.begin(flash));unsigned before=reads;
        assert(!store.load(static_cast<TftAssetId>(TFT_ASSET_COUNT-1)) && reads==before);
      }
      flashBytes=good;detected=false;assert(!store.begin(flash));detected=true;
      assert(!store.load(TftAssetId::INVALID));
      // Invalid entry offset/size/dimensions, truncated runs and damaged CRC.
      for(unsigned scenario=0;scenario<6;++scenario){
        flashBytes=good;assert(store.begin(flash));
        if(scenario==0)put32(24,0); // points into header
        if(scenario==1)put32(28,0); // zero compressed size
        if(scenario==2)flashBytes[36]=0; // wrong width
        if(scenario==3)put32(28,1); // truncated first packet
        if(scenario==4)flashBytes[32]^=1; // wrong decoded CRC
        if(scenario==5)put32(24,0xFFFFFFF0u); // offset wrap risk
        assert(!store.load(static_cast<TftAssetId>(0)));
        assert(store.loadedAsset()==TftAssetId::INVALID);
        assert(!store.load(TftAssetId::INVALID));
        flashBytes=good;assert(store.begin(flash));assert(store.load(static_cast<TftAssetId>(0)));
      }
    }
    '''
    binary = tmp_path / "asset-reader-test"
    built = subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(tmp_path), "-I", str(ROOT / "include"),
                            str(ROOT / "src/tft_asset_store.cpp"), "-x", "c++", "-", "-o", str(binary)],
                           input=source, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary), str(tmp_path / "flash.bin"), str(tmp_path / "expected.bin")],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
