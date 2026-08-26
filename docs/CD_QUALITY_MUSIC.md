# CD-Quality Music — Implementation (Issue #19)

Status: **IMPLEMENTED + VERIFIED** on `main` (commits `c224a98e` code,
`57da8cef` docs+tools). Drop-in WAV replacement for iMUSE Digital music:
whenever a matching WAV exists in `hd/audio/`, the engine streams the
lossless CD-quality track instead of the compressed bundle audio.
Everything else stays on the original music.

## How it works (high level)

For each music cue, the engine asks the bundle for the IMX track
(e.g. `1099-M~1.IMX`). The override checks: does
`hd/audio/<IMX-name>.wav` exist? If yes → stream that WAV through the
iMUSE streamer. If no → original bundle audio, unchanged. The override is
**additive and per-file** — no settings, no config, automatic fallback.

## Implementation

All new logic lives in `dimuse_bndmgr.h/.cpp`:

| Method | What it does |
|--------|--------------|
| `readFile()` | Checks `Common::File::exists(name + ".wav")` FIRST (before the bundle bsearch). If present → `openExternal()` + route to `readFileExternal()`. |
| `openExternal()` | Parses the WAV (RIFF/fmt/data chunks), validates 16-bit PCM, builds a synthetic iMUS/MAP/FRMT header, opens the raw PCM stream. |
| `seekFile()` | External branch: sets `_curDecompressedFilePos` = PCM byte offset (SEEK_SET) / `dataLen + offset` (SEEK_END). |
| `readFileExternal()` | First `openSound` read (0x2000) serves the 52-byte header (+ appended audio to fill the stream buffer); every later read serves raw PCM from `_curDecompressedFilePos`, looping to 0 at end. |
| `closeExternal()` | On track change / `close()`. |

### CRITICAL: iMUSE streamer architecture

The streamer does NOT read audio through `readFile` in one shot:

1. `ImuseDigiSndMgr::openSound()` calls `bundle->readFile(soundName,
   0x2000, ...)` ONCE — this is only the **map-header validation read**.
2. `dispatchGetMap()` reads iMUS/MAP/FRMT from the **stream buffer**
   (`streamerGetStreamBufferAtOffset(stream, 0, 0x10)` then
   `streamerGetStreamBuffer(stream, size)`). Empty buffer → returns **-3**,
   which `dispatchAllocateSound()` treats as "buffer not filled yet, retry
   later" — **NOT an error**. Do not panic on -3.
3. Actual audio is fetched per-frame by `streamerProcessStreams()` →
   `streamerFetchData()` → `_filesHandler->read(soundId, buf, size, bufId)`
   (dimuse_files.cpp) → `curSnd->bundle->readFile(fileName, 0x4000, ...)`.
4. Position is set via `_filesHandler->seek()` → `bundle->seekFile(offset,
   mode)` BEFORE each read.

**Consequence:** the external track must be **positionally streamed** like
the bundle (seekFile sets pos, readFileExternal serves from pos). Serving
"header + all audio" in one call does NOT work — the streamer pulls
0x4000-byte chunks via its own seek/read cycle.

### The synthetic header (52 bytes, exact layout)

`dispatchGetMap()` reads `iMUS`(4) + mapSize(4) at 0..8, checks `MAP ` at
8, then `size = mapSize + 24` bytes as the map. **`map[4]` (stream offset
24) MUST equal `size` (= mapSize + 24 = 52)** — it marks where audio data
begins. Big-endian:

```
 0: 'iMUS'   4: mapSize(28)   8: 'MAP '  12: mapSize(28)
16: 'FRMT'  20: blkSize-8(20) 24: offset(52)  28: empty(0)
32: wordSize(16) 36: rate    40: channels      44..51: 0
```

Pitfalls (all hit during implementation):

- **Header buffer member was `byte _extHeader[32]` but the header is 52
  bytes → buffer overflow.** Use `[64]`.
- **Skip the 12-byte RIFF header first** (`f.skip(12)` after open) — the
  chunk walk must start at the first chunk, not offset 0 (else the first
  "chunk" reads 'RIFF' and `data` is never found).
- **fmt chunk field order:** formatTag(2) channels(2) sampleRate(4)
  **byteRate(4) blockAlign(2)** bits(2). Must `f.skip(6)` after
  sampleRate before reading bits — else bits reads the sampleRate
  (symptom: `not 16-bit PCM (44100 bit)`).
- Compute chunk positions from `chunkStart = f.pos() - 8` (before reading
  the chunk header), not from the post-header pos.

### File naming gotcha

- Bundle short names have NO dot: `1099-M~1IMX` (8.3 style).
- `readFile()` receives names WITH the dot: `1099-M~1.IMX`.
- External file must be `1099-M~1.IMX.wav` (**dot before IMX**).
  `convert_ost.py` normalizes `~1IMX` → `~1.IMX`. If the game doesn't
  pick up a WAV, check the dot first.

## Mapping (IMX → OST tracks)

**Use audfprint, NOT custom chroma fingerprinting.**

- Custom chroma/FFT correlation FAILED (tested): scores 0.33/0.59 looked
  like matches but 10s listen-tests were completely different pieces.
  Chroma is too coarse (same key/mood → similar vectors).
- **audfprint (dpwe/audfprint, Shazam-style landmarks) WORKS**:
  125/129 IMX tracks matched to OST with time offsets. Install: clone
  from GitHub (no setup.py; add repo dir to sys.path), deps numpy scipy
  docopt joblib psutil. Python-2-era `dejavu` on PyPI does NOT run on
  Python 3.13.
- API: `Analyzer(density).wavfile2hashes(file)` → store in
  `HashTable(hashbits=20)`, `Matcher().match_file(analyzer, ht, query)`
  returns `[id, filteredmatches, timoffs, rawmatches, ...]`; offset =
  `timoffs * 128 / 11025` seconds. `filtered >= 10` = confident.
- The archive.org OST ("The Curse of Monkey Island Soundtrack", 79
  tracks) covers the state cues (1xxx) but NOT the 41 sequence cues
  (2xxx: zaps, interludes, stingers) — those keep the original bundle
  music (the override is per-file additive; fallback automatic).
- audfprint offsets are mostly -2..-3s (IMX pre-roll before OST start);
  some cues map mid-track (e.g. 1289-R at 122s).

## IMX decoding (for the mapping pipeline)

- IMX = IMA-ADPCM variant (codec 15 stereo / 13 mono), 16-bit, 22050 Hz.
- Decode via the fork's own `dimuse_codecs.cpp` — a C++ harness linking
  against it is the **ground truth** (a from-scratch Python
  reimplementation had an offset bug and clipped at ±32768, sounding like
  noise).
- Block 0 of each track contains a raw prefix (firstWord =
  `(b[0]<<8)|b[1]`, typically 282 bytes) holding the iMUS/MAP/FRMT map;
  skip it to get pure audio.
- Best decode architecture: ONE harness process with a `--manifest` file
  (`path codec` per line), all ~115k blocks in a single run (~30s), not
  one subprocess per block (~30 min).

## Verification (proven 2026-08)

1. Streaming: headless `-d 3`, grep `HQ-MUSIC.*served.*bytes at pos` —
   positions climb 0 → dataLen in 0x4000 (44000) chunks.
2. Byte identity: FNV-ish hash (`h = h*33 + b`) of first 256 served bytes
   must equal same hash over the WAV PCM. Proven: `0a35c231` matched.
3. No FPS loss: FRAME-TIMING avg 20-21ms with and without the WAV.
4. Normal operation silent — all HQ-MUSIC logs are `debug(3, ...)`
   (visible only with `-d 3`).

## Repo artifacts

| File | Purpose |
|------|---------|
| `tools/music_map/hq_music_map.json` | 125 IMX cues → OST tracks + offsets (audfprint) |
| `tools/music_map/convert_ost.py` | Batch-converts OST FLACs to game WAVs (normalizes the `~1.IMX` dot, optional `--offset` trim) |
| `scummvm/fork/engines/scumm/imuse_digi/dimuse_bndmgr.h/.cpp` | The override (readFile → external WAV streaming) |
| `README.md` | End-user section: archive.org link, ffmpeg conversion, cue→OST table, install |

## User workflow (end user)

1. Download the OST from archive.org (FLAC + MP3).
2. Convert tracks to 16-bit PCM WAV (`ffmpeg -i "18 The Voodoo Lady.flac" -ac 2 "18 The Voodoo Lady.wav"`), keeping the original names.
3. Copy into `hd/audio/`.
4. Play — matching cues use the CD-quality WAV automatically.

16-bit PCM WAV at any sample rate works (22.05 kHz and 44.1 kHz both
tested). Stereo or mono both work.
