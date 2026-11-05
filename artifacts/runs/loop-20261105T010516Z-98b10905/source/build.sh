#!/usr/bin/env bash
# Build the DOOM WebAssembly port into dist/. Needs emcc (4.0.18) on PATH:
#   source ~/Developer/emsdk/emsdk_env.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$ROOT/third_party/doomgeneric"
OUT="$ROOT/dist"
mkdir -p "$OUT"

# Engine sources, excluding files that are not part of a platform-less build.
SRCS=$(ls "$ENGINE"/*.c | grep -v '/i_sdl\|/i_allegro\|/doomgeneric_.*\.c' )

emcc $SRCS "$ROOT/platform/doomgeneric_wasm.c" "$ROOT/platform/doom_audio.c" \
  -I"$ROOT/platform" -I"$ENGINE" -DFEATURE_SOUND -O2 -w \
  -sASYNCIFY -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=64MB -sSTACK_SIZE=1MB \
  -sEXIT_RUNTIME=0 \
  -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,HEAPU8 \
  --preload-file "$ROOT/assets/doom1.wad@/doom1.wad" \
  -o "$OUT/doom.js"

cp "$ROOT/web/index.html" "$OUT/index.html"
cp "$ROOT/web/audio.js" "$OUT/audio.js"
echo "built $OUT"
