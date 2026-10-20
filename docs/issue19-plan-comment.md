## Implementation plan: CD-quality music (WAV/FLAC/OGG/MP3 drop-in)

Here's a concrete, repo-compatible plan. It reuses the existing Digital iMUSE machinery — no new engine state, no parallel audio player.

### Current state (verified)

- COMI music is played by Digital iMUSE (`engines/scumm/imuse_digi/`). Every music cue is a file inside `MUSDISK1.BUN`/`MUSDISK2.BUN`, named like `1100-H~1.IMX` (IMX = IMA-ADPCM variant, 16-bit, 22050 Hz stereo — all 129 tracks checked).
- The state/sequence tables in `imuse_digi/dimuse_tables.cpp` map SCUMM state/sequence ids to those IMX filenames. `IMuseDigiFilesHandler::getFilenameFromSoundId()` already returns the right IMX name for every cue.
- `SoundCD`/`DefaultAudioCDManager` (the `track01.wav`-style CD-audio emulation used by Loom/MI1/MI2) is NOT wired up for COMI — COMI has no `GF_AUDIOTRACKS` flag, so that path is never taken.

### The core idea: one small hook in `BundleMgr::readFile()`

`BundleMgr::readFile(name, ...)` looks up `name` (e.g. `1100-H~1.IMX`) in the bundle. If a file with that name is NOT in the bundle, it currently fails → music silently missing.

**Plan:** before failing, try to open an external file `<name>.<audio-ext>` (e.g. `1100-H~1.IMX.wav`, or `.flac`/`.ogg`/`.mp3` when those codecs are enabled in the build) via `Audio::SeekableAudioStream::openStreamFile()`. If found, decode it to PCM and feed it into the same output buffer the bundle path uses.

Consequences:
- **Drop-in:** the player copies the CD-quality OST files into the game directory with the IMX names + audio extension. No bundle editing, no table changes.
- **Partial coverage is fine:** only cues with a matching external file are replaced; everything else (e.g. the short 2xxx sequence stingers that the OST album doesn't contain) keeps playing from the bundle automatically.
- **All iMUSE behavior is preserved:** fades, crossfades (`diMUSESwitchStream`), triggers, save/load, pause — because the data still flows through the exact same streamer/dispatch path.

### Key technical points

1. **The map stays in the bundle.** The iMUSE dispatch parser expects an `iMUS`/`MAP`/`FRMT` header in the stream. Only the *audio data portion* is replaced by the external file's PCM. The FRMT block (word size / sample rate / channels) must match the external file — for v1 require 16-bit stereo and set the FRMT rate to the file's rate (or resample to 22050/44100).
2. **Formats:** WAV is always compiled in (no external lib). FLAC/OGG/MP3 need `USE_FLAC`/`USE_VORBIS`/`USE_MAD` in the build (currently disabled in `config.h`). v1 can ship WAV-only; a setup script converts the OST (FLAC on archive.org) to 44.1 kHz 16-bit stereo WAV.
3. **File naming:** use the exact table filenames from `dimuse_tables.cpp` (`1100-H~1.IMX.wav`), lowercase for the demo table (`in1.imx.wav`).

### Mapping the OST to the game — automatically (no human listening)

The archive.org OST has 79 tracks; the game has 129 IMX cues (88 state 1xxx + 41 sequence 2xxx). The OST covers the state music, not the 2xxx stingers.

Instead of hand-mapping, we can fingerprint-match: the IMX tracks are the *same recordings* as the OST (verified by decoding a few with a harness linked against the fork's own `dimuse_codecs.cpp` — the output is real music, not noise).

Approach (Shazam-lite):
1. Decode every IMX track (the repo's own codec) to mono 22050 PCM.
2. Compute a compact signature per ~1s window (chroma/band-energy).
3. Cross-correlate each IMX signature against every OST track signature (FFT) → best offset + similarity.
4. Confident matches (similarity above threshold) produce `config/hq_music_map.json`: `{ "1100-H~1.IMX": "04 Ye Pining of a Rotten Heart.flac", ... }`.
5. A setup script converts + renames the matched OST files into the game dir.

Unmatched cues (all 2xxx sequences, and any state without a confident match) fall back to the original bundle audio automatically.

### Files touched (estimate)

- `engines/scumm/imuse_digi/dimuse_bndmgr.h/.cpp` — external-stream members + `readFile()` override
- `engines/scumm/imuse_digi/dimuse_dispatch.cpp` — FRMT rate patch when an external stream is active
- `config/hq_music_map.json` (new) + `scripts/` conversion/fingerprint tooling
- README section + release notes

### Test plan

1. Linux build, no override files → identical behavior to today (bundle path untouched).
2. Add one `1100-H~1.IMX.wav` → the deck hold music plays the WAV (verify via log + audio).
3. State change while an external track plays → fade/switch works (same stream path).
4. Save/load reopens the external file correctly.
5. Demo detection (`comi` demo) uses the lowercase table — same override applies.

Happy to implement this — open to feedback on the approach first.
