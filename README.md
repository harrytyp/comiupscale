# COMI-HD — Curse of Monkey Island HD Upscale

![COMI-HD Screenshot](docs/screenshots/room9.png)
*Room 9 (Cannon Gallery) mit HD-Texturen — 4x Upscale*

---

## Überblick

COMI-HD ist ein **ScummVM Fork** der Curse of Monkey Island (COMI / SCUMM v8) in **4x HD** rendert. Der Fork lädt externe HD-Texturen (Backgrounds, Kostüme, Objekte, Fonts) aus einem `hd/` Verzeichnis und skaliert Koordinaten zur Laufzeit — kein Patchen der Original-Spiel-Dateien nötig.

### Features
- ⚡ **4x HD** (2560×1920) — KI-upscalte Texturen via RealESRGAN
- 🎭 **25.303 Kostüm-Frames** — HD-Charaktere in voller Pracht
- 🖼️ **81 HD-Backgrounds** — alle Räume in hochskalierter Qualität
- 🎬 **15 HD-Videos** — KI-upscalte Zwischensequenzen
- 🔧 **Kein Patchen** — Original-Spiel-Dateien bleiben unverändert

---

## Downloads

Das Release ist in **3 Teile** aufgeteilt:

| Teil | Inhalt | Größe | Quelle |
|------|--------|:-----:|:------:|
| 1. Game | COMI.LA0, LA1, LA2 | 82 MB | [GitHub Release](https://github.com/harrytyp/comiupscale/releases/tag/v1.0.2) |
| 2. HD Assets | Backgrounds, Videos, Kostüme, Objekte, Fonts | 8.8 GB | [MEGA](/comi_hd_v1.0.2/hd/) |
| 3. ScummVM Build | scummvm.exe, SDL2.dll, zlib1.dll, Scripts | 26 MB | [GitHub Release](https://github.com/harrytyp/comiupscale/releases/tag/v1.0.2) |

### 1. Game Files (`comi_hd_game.zip`)
Original Curse of Monkey Island Daten:
- `COMI.LA0`
- `COMI.LA1`
- `COMI.LA2`

→ In das `COMI/` Verzeichnis entpacken.

### 2. HD Assets (MEGA)
```
/comi_hd_v1.0.2/hd/
├── backgrounds/   (81 HD-Backgrounds, 2560×1920)
├── costumes/      (25.303 Kostüm-Frames)
├── videos/        (15 upscalte Zwischensequenzen)
├── objects/       (600 HD-Objekte)
├── fonts/         (5 HD-Fonts)
└── object_map.json
```
→ In das Spielverzeichnis entpacken (neben `game/hd/`).

### 3. ScummVM Build (`comi_hd_build.zip`)
| Datei | Beschreibung |
|-------|-------------|
| `scummvm.exe` | ScummVM v1.0.2 mit HD-Unterstützung (scumm_7_8 engine) |
| `SDL2.dll` | SDL2 Runtime |
| `zlib1.dll` | Zlib Runtime |
| `start_comi_hd.bat` | Windows Start-Script |
| `start_comi_hd.sh` | Linux Start-Script |
| `scummvm.ini` | Vorkonfigurierte ScummVM-INI |

---

## Installation

### Windows
1. `comi_hd_game.zip` → `COMI/` entpacken
2. `comi_hd_build.zip` → `comi_hd_v1.0.2/` entpacken
3. HD Assets von MEGA → `comi_hd_v1.0.2/hd/` entpacken
4. `start_comi_hd.bat` ausführen

### Linux
1. `comi_hd_game.zip` → `COMI/` entpacken
2. `comi_hd_build.zip` → `comi_hd_v1.0.2/` entpacken
3. HD Assets von MEGA → `comi_hd_v1.0.2/hd/` entpacken
4. `chmod +x scummvm start_comi_hd.sh`
5. `./start_comi_hd.sh` ausführen

---

## HD-Vergleich

![HD Background Room 9](docs/screenshots/hd_background_room9.png)
*HD Background Room 9 (2560×1920) — 4x Upscale*

---

## Technische Details

### ScummVM Fork
- **Basis:** ScummVM (eigener Fork)
- **HD Asset Manager:** Lädt externe Texturen aus `hd/` Verzeichnis
- **Coordinate Scaling:** Automatische Skalierung von SD→HD Koordinaten
- **Engine Support:** SCUMM v0-v6, v7 & v8 (COMI, Full Throttle, The Dig, etc.)
- **Build:** LLVM MinGW Cross-Compile (Windows) + GCC (Linux)

### HD Assets
- **Upscaling:** RealESRGAN `x4plus_anime_6B` Modell
- **Backgrounds:** Original ROOM/IMAG → PNG → 4x Upscale → PNG
- **Costumes:** AKOS → PNG Frames → 4x Upscale → PNG
- **Videos:** HNM → MP4 → 4x Upscale (Topaz) → MP4

---

## Changelog

### v1.0.2 (Current)
- ✅ scumm_7_8 engine aktiviert
- ✅ Room-Warp Debug entfernt
- ✅ Relativer Game-Pfad in start-comi_hd.bat
- ✅ SDL2.dll + zlib1.dll inkludiert

### v1.0.1
- HD Asset Pipeline stabilisiert
- Kostüm-Rendering optimiert

### v1.0.0
- Erstes Release mit HD-Backgrounds
- Grundlegende Kostüm-Unterstützung
