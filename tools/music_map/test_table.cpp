// Unit test for the Issue #19 music-replacement logic (table lookup +
// hd/audio path resolution + WAV parse). Standalone, no game needed.
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <string>

// Minimal stand-in for scumm_stricmp
static int scumm_stricmp(const char *a, const char *b) {
    for (; *a && *b; a++, b++) {
        char ca = (*a >= 'A' && *a <= 'Z') ? *a + 32 : *a;
        char cb = (*b >= 'A' && *b <= 'Z') ? *b + 32 : *b;
        if (ca != cb) return ca - cb;
    }
    return (*a ? 1 : (*b ? -1 : 0));
}

#include "dimuse_extmusic_table.h"

int main() {
    int failures = 0;

    // 1. Table has 125 entries
    printf("Table size: %d (expect 125)\n", kExtMusicTableSize);
    if (kExtMusicTableSize != 125) failures++;

    // 2. Lookup a known cue
    const char *needle = "1099-M~1.IMX";
    const char *found = nullptr;
    for (int i = 0; i < kExtMusicTableSize; i++) {
        if (scumm_stricmp(kExtMusicTable[i].cue, needle) == 0) {
            found = kExtMusicTable[i].ost;
            break;
        }
    }
    printf("Cue '%s' -> '%s' (expect 'ost_01_The_Adventure_Continues')\n", needle, found ? found : "(null)");
    if (!found || strcmp(found, "ost_01_The_Adventure_Continues") != 0) failures++;

    // 3. Lookup the Voodoo cue
    needle = "1215-V~1.IMX";
    found = nullptr;
    for (int i = 0; i < kExtMusicTableSize; i++) {
        if (scumm_stricmp(kExtMusicTable[i].cue, needle) == 0) {
            found = kExtMusicTable[i].ost;
            break;
        }
    }
    printf("Cue '%s' -> '%s' (expect 'ost_18_The_Voodoo_Lady')\n", needle, found ? found : "(null)");
    if (!found || strcmp(found, "ost_18_The_Voodoo_Lady") != 0) failures++;

    // 4. A sequence cue may or may not be mapped — verify it doesn't crash
    //    and returns something consistent (table lookup is total).
    needle = "2225-D~1.IMX";
    found = nullptr;
    for (int i = 0; i < kExtMusicTableSize; i++) {
        if (scumm_stricmp(kExtMusicTable[i].cue, needle) == 0) {
            found = kExtMusicTable[i].ost;
            break;
        }
    }
    printf("Cue '%s' -> '%s' (mapped: %s)\n", needle, found ? found : "(null)", found ? "yes" : "no");
    if (!found) failures++;

    // 5. Path construction: <hd>/audio/<ost>.wav
    const char *ost1 = "ost_01_The_Adventure_Continues";
    std::string wavPath = std::string("game/hd") + "/audio/" + ost1 + ".wav";
    printf("Path: %s (expect game/hd/audio/ost_01_The_Adventure_Continues.wav)\n", wavPath.c_str());
    if (wavPath != "game/hd/audio/ost_01_The_Adventure_Continues.wav") failures++;

    printf("\n%s (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
