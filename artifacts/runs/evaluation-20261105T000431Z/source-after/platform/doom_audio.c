#include <stdint.h>
#include <stdio.h>
#include <emscripten.h>
#include "i_sound.h"
#include "w_wad.h"
#include "z_zone.h"

int use_libsamplerate = 0;
float libsamplerate_scale = 1.0f;
static boolean prefix;
static snddevice_t devices[] = { SNDDEVICE_SB };
static boolean Init(boolean p) { prefix = p; return true; }
static void Shutdown(void) { EM_ASM({ DoomAudio.stopAll(); }); }
static int Lump(sfxinfo_t *sfx) {
    char name[16];
    if (sfx->link) sfx = sfx->link;
    snprintf(name, sizeof(name), "%s%s", prefix ? "ds" : "", sfx->name);
    return W_GetNumForName(name);
}
static void Update(void) {}
static void Params(int channel, int vol, int sep) {
    EM_ASM({ DoomAudio.params($0, $1, $2); }, channel, vol, sep);
}
static int Start(sfxinfo_t *sfx, int channel, int vol, int sep) {
    int lump = Lump(sfx), len = W_LumpLength(lump);
    const unsigned char *data = W_CacheLumpNum(lump, PU_STATIC);
    int result = EM_ASM_INT({
        return DoomAudio.effect($0, $1, $2, $3, HEAPU8.slice($4, $4 + $5), UTF8ToString($6));
    }, channel, vol, sep, lump, data, len, sfx->link ? sfx->link->name : sfx->name);
    W_ReleaseLumpNum(lump);
    return result;
}
static void Stop(int channel) { EM_ASM({ DoomAudio.stop($0); }, channel); }
static boolean Playing(int channel) { return EM_ASM_INT({ return DoomAudio.playing($0); }, channel); }
sound_module_t DG_sound_module = { devices, 1, Init, Shutdown, Lump, Update, Params, Start, Stop, Playing, NULL };

static boolean MusicInit(void) { return true; }
static void MusicVolume(int v) { EM_ASM({ DoomAudio.musicVolume($0 / 127); }, v); }
static void Pause(void) { EM_ASM({ DoomAudio.pauseMusic(); }); }
static void Resume(void) { EM_ASM({ DoomAudio.resumeMusic(); }); }
static void *Register(void *data, int len) {
    return (void *)(intptr_t)EM_ASM_INT({ return DoomAudio.register(HEAPU8.slice($0, $0 + $1)); }, data, len);
}
static void Unregister(void *handle) { EM_ASM({ DoomAudio.unregister($0); }, handle); }
static void Play(void *handle, boolean loop) { EM_ASM({ DoomAudio.playMusic($0, !!$1); }, handle, loop); }
static void MusicStop(void) { EM_ASM({ DoomAudio.stopMusic(); }); }
static boolean MusicPlaying(void) { return EM_ASM_INT({ return !!DoomAudio.song; }); }
music_module_t DG_music_module = { devices, 1, MusicInit, MusicStop, MusicVolume, Pause, Resume, Register, Unregister, Play, MusicStop, MusicPlaying, NULL };
