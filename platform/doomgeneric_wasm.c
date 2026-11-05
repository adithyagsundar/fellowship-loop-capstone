// WebAssembly platform layer for doomgeneric (Emscripten, Asyncify).
//
// - Rendering: DG_DrawFrame converts the engine's B,G,R,0 pixels to opaque
//   RGBA and blits to <canvas id="canvas"> via putImageData.
// - Timing: DG_GetTicksMs uses emscripten_get_now(); DG_SleepMs yields to the
//   browser with emscripten_sleep (Asyncify) so wipe/tic waits don't freeze it.
// - Input: JS calls dg_key(pressed, doomKey); DG_GetKey drains a ring buffer.
// - Entry: main() creates the game then ticks forever, yielding every frame.

#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <emscripten.h>

#include "doomgeneric.h"
#include "doomstat.h"

#define KEYQ_SIZE 256
static struct { unsigned char pressed, key; } keyq[KEYQ_SIZE];
static unsigned keyq_r, keyq_w;

static uint32_t rgba[DOOMGENERIC_RESX * DOOMGENERIC_RESY];
static uint32_t frame_count, tick_count;

EM_JS(void, js_present, (const uint32_t *px, int w, int h), {
    var c = Module.canvas || document.getElementById('canvas');
    if (!c) return;
    if (!Module.__ctx) {
        Module.__ctx = c.getContext('2d');
        Module.__img = null;
    }
    if (!Module.__img || Module.__img.width != w || Module.__img.height != h)
        Module.__img = Module.__ctx.createImageData(w, h);
    Module.__img.data.set(HEAPU8.subarray(px, px + w * h * 4));
    Module.__ctx.putImageData(Module.__img, 0, 0);
});

EM_JS(void, js_title, (const char *t), {
    document.title = UTF8ToString(t);
});

void DG_Init() {}

void DG_DrawFrame()
{
    const uint32_t *src = (const uint32_t *)DG_ScreenBuffer;
    for (int i = 0; i < DOOMGENERIC_RESX * DOOMGENERIC_RESY; i++) {
        uint32_t p = src[i];                       // 0x00RRGGBB
        rgba[i] = 0xFF000000u | ((p & 0xFF) << 16) | (p & 0xFF00) |
                  ((p >> 16) & 0xFF);              // bytes R,G,B,255
    }
    js_present(rgba, DOOMGENERIC_RESX, DOOMGENERIC_RESY);
    frame_count++;
}

void DG_SleepMs(uint32_t ms)
{
    emscripten_sleep(ms);
}

uint32_t DG_GetTicksMs()
{
    return (uint32_t)emscripten_get_now();
}

int DG_GetKey(int *pressed, unsigned char *key)
{
    if (keyq_r == keyq_w) return 0;
    *pressed = keyq[keyq_r % KEYQ_SIZE].pressed;
    *key = keyq[keyq_r % KEYQ_SIZE].key;
    keyq_r++;
    return 1;
}

void DG_SetWindowTitle(const char *title)
{
    js_title(title);
}

EMSCRIPTEN_KEEPALIVE void dg_key(int pressed, int key)
{
    if (keyq_w - keyq_r >= KEYQ_SIZE || key <= 0 || key > 255) return;
    keyq[keyq_w % KEYQ_SIZE].pressed = pressed ? 1 : 0;
    keyq[keyq_w % KEYQ_SIZE].key = (unsigned char)key;
    keyq_w++;
}

EMSCRIPTEN_KEEPALIVE uint32_t dg_frame_count(void) { return frame_count; }
EMSCRIPTEN_KEEPALIVE uint32_t dg_tick_count(void) { return tick_count; }

// Read-only observations for browser verification. gametic counts simulation
// tics; tick_count above counts outer loop calls and is not a timing metric.
EMSCRIPTEN_KEEPALIVE int dg_game_tics(void) { return gametic; }
EMSCRIPTEN_KEEPALIVE int dg_menu_active(void) { return menuactive; }
EMSCRIPTEN_KEEPALIVE int dg_in_level(void) {
    return gamestate == GS_LEVEL && !demoplayback && players[consoleplayer].mo != NULL;
}
EMSCRIPTEN_KEEPALIVE int dg_player_x(void) {
    return players[consoleplayer].mo ? players[consoleplayer].mo->x : 0;
}
EMSCRIPTEN_KEEPALIVE int dg_player_y(void) {
    return players[consoleplayer].mo ? players[consoleplayer].mo->y : 0;
}
EMSCRIPTEN_KEEPALIVE uint32_t dg_player_angle(void) {
    return players[consoleplayer].mo ? players[consoleplayer].mo->angle : 0;
}
EMSCRIPTEN_KEEPALIVE int dg_bullets(void) { return players[consoleplayer].ammo[am_clip]; }
EMSCRIPTEN_KEEPALIVE int dg_use_down(void) { return players[consoleplayer].usedown; }
EMSCRIPTEN_KEEPALIVE int dg_paused(void) { return paused; }
EMSCRIPTEN_KEEPALIVE int dg_automap(void) { return automapactive; }
EMSCRIPTEN_KEEPALIVE int dg_weapon(void) { return players[consoleplayer].readyweapon; }
EMSCRIPTEN_KEEPALIVE int dg_forward(void) { return players[consoleplayer].cmd.forwardmove; }
EMSCRIPTEN_KEEPALIVE int dg_side(void) { return players[consoleplayer].cmd.sidemove; }

EM_JS(void, js_fatal, (const char *t), {
    var m = UTF8ToString(t);
    var s = document.getElementById('status');
    if (s) s.textContent = m;
    console.error(m);
    Module.__fatal = m;
});

int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    // Fail visibly if the preloaded WAD is missing or not an IWAD.
    FILE *wf = fopen("/doom1.wad", "rb");
    char magic[4] = {0};
    if (!wf || fread(magic, 1, 4, wf) != 4 || memcmp(magic, "IWAD", 4) != 0) {
        js_fatal("Cannot start: /doom1.wad is missing or not a valid IWAD. Serve doom.data next to doom.js.");
        if (wf) fclose(wf);
        return 1;
    }
    fclose(wf);
    char *args[] = { "doom", "-iwad", "/doom1.wad", "-nogui", NULL };
    doomgeneric_Create(4, args);
    for (;;) {
        doomgeneric_Tick();
        tick_count++;
        emscripten_sleep(0);   // let the browser handle events/paint
    }
    return 0;
}
