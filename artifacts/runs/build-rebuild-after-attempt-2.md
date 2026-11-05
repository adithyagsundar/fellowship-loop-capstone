# Rebuild after attempt-2 review/test
- Base commit: e500c440656622db5ab3f8fb7df73d8b5998eeb3 (working tree has uncommitted changes to platform/doomgeneric_wasm.c, web/index.html, build.sh)
- Command: source ~/Developer/emsdk/emsdk_env.sh && ./build.sh  (emcc 4.0.18)
- Result: success; dist/{doom.js,doom.wasm,doom.data,index.html} regenerated 2026-11-03T01:41:17Z
- dist/index.html identical to web/index.html (diff clean) -> stale-dist finding fixed.
- md5: 669b2d1596b30a30ba0627a0fd3a77c9 index.html; ee200d2d5b29d37ee96a02e0b74b8a2c doom.wasm
## Not done
- No headless-browser test or screenshots: tests/ is outside the coder's remit; needs tester/loop.
- Audio, mouse, save persistence not implemented.
