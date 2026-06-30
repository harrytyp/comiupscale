# COMI-Upscaled v1.0.2 — GPU-AI Upscaled HD Remaster

> **The Curse of Monkey Island** (LucasArts, 2000) — 4x AI-upscaled HD Texturen auf Basis eines modifizierten **ScummVM** Forks.

![Screenshot](https://github.com/harrytyp/comiupscale/releases/download/v1.0.1/screenshot_room9.png)

## 📦 Was ist enthalten?

| Komponente | Größe | Details |
|------------|-------|---------|
| **`scummvm`** (Linux Binary) | 25 MB | Modifizierter ScummVM mit HD-Overlay-Engine |
| **`hd/`** | 4,9 GB | 4x GPU-upscalte HD-Texturen (alle Kostüme, Objekte, Fonts, Hintergründe) |
| **README** | — | Diese Anleitung |

**Gesamtgröße: ~5 GB** (ohne Spieldaten, ohne 4K-Zwischensequenzen)

## ❌ Was ist NICHT enthalten (muss selbst besorgt werden)

### 1. Das Spiel "Curse of Monkey Island" (COMI)

Die Original-Spieldateien werden benötigt. Du kannst sie beziehen von:

| Quelle | Link | Hinweis |
|--------|------|---------|
| **archive.org** | https://archive.org/search?query=curse+of+monkey+island | Kostenlos, legal (Abandonware) |
| **Steam** | https://store.steampowered.com/app/730820/ | Ca. 5 € |
| **GOG** | https://www.gog.com/en/game/the_curse_of_monkey_island | Ca. 5 €, DRM-frei |

**Wichtig:** Du brauchst NUR die Spieldaten (COMI.LA0, COMI.LA1, COMI.LA2, RESOURCE/-Ordner), ~146 MB. Keine Installation nötig — einfach die Dateien in einen Ordner legen.

### 2. 4K-Zwischensequenzen (optional)

Falls du die Zwischensequenzen auch in 4K haben möchtest (zusätzliche ~6 GB):

📥 **Download:** https://archive.org/details/COMI_4k

Einfach in den `hd/videos/`-Ordner entpacken. Ohne diese Dateien laufen die Zwischensequenzen in Original-SD-Auflösung.

## 🚀 Installation

### Linux

```bash
# 1. Release entpacken
tar xf comi_hd_v1.0.2.tar.*
cd comi_hd_v1.0.2

# 2. Spieldaten (COMI.LA0, COMI.LA1, COMI.LA2, RESOURCE/) in einen Ordner kopieren
#    z.B. ~/games/comi/

# 3. scummvm.ini anpassen — path auf deinen Spielordner setzen:
#    [comi]
#    path=/home/deinuser/games/comi/
#    hd_path=./hd

# 4. Starten
./start_comi_hd.sh
```

### Windows

```bat
:: 1. Release entpacken
:: 2. Spieldaten in einen Ordner kopieren, z.B. C:\Spiele\COMI\
:: 3. scummvm.ini öffnen und path anpassen:
::    [comi]
;;    path=C:\Spiele\COMI\
;;    hd_path=.\hd
:: 4. start_comi_hd.bat ausführen
```

## 🎮 Steuerung

| Taste | Aktion |
|-------|--------|
| `F5` | Menü (Speichern/Laden) |
| `Strg` + `F5` | ScummVM-Menü |
| `Strg` + `d` | Debug-Konsole |
| `Alt` + `Enter` | Vollbild umschalten |
| `Esc` | Überspringen/Zurück |
| Maus | Klassischer Point-and-Click |

## ⚙️ Konfiguration

Die wichtigsten Optionen in `scummvm.ini` unter `[comi]`:

| Option | Standard | Beschreibung |
|--------|----------|-------------|
| `hd_path` | `./hd` | Pfad zu den HD-Texturen |
| `hd_enabled` | `true` | HD-Overlay ein/aus |
| `hd_trace` | `false` | Debug-Ausgabe (nur bei Fehlern aktivieren) |

## 🔧 Technische Details

- **Engine:** Modifizierter ScummVM (git 2026-02-01 + HD-Patches)
- **Upscaling-Modell:** RealESRGAN x4plus-anime (AMD RX 5700 XT)
- **Extraktion:** NUTcracker (AKOS/Kostüm-Dekodierung mit Room-Palette)
- **HD-Kostüme:** 25.302 Frames über 473 Kostüme
- **HD-Objekte:** 1.365 (Vordergrund) + 633 (Layer) über alle Räume
- **HD-Fonts:** 5 Schriftarten
- **HD-Hintergründe:** Alle Räume (CPU-vorgerechnet mit gleichem Modell)

## 📋 Systemvoraussetzungen

| | Minimum | Empfohlen |
|---|---------|-----------|
| **CPU** | 2 Kerne | 4+ Kerne |
| **RAM** | 2 GB | 4 GB |
| **GPU** | OpenGL 3.3+ | OpenGL 4.0+ (Software-Rendering via llvmpipe möglich) |
| **Speicher** | 5 GB frei | 12 GB (mit 4K-Videos) |
| **OS** | Linux (x86_64) / Windows 10 | |

## 📜 Lizenz

- **ScummVM:** GPLv2 — https://www.scummvm.org/
- **HD-Texturen:** Creative Commons BY-NC-SA 4.0
- **Spieldaten:** © LucasArts / Disney — nicht im Lieferumfang enthalten

## 🙏 Danksagung

- ScummVM Team für die großartige Engine
- NUTcracker (pycd02) für die Asset-Extraktion
- RealESRGAN (xinntao) für das Upscaling-Modell
- xinntao/Real-ESRGAN-ncnn-vulkan für die GPU-Inferenz

---

**COMI-Upscaled** — Ein Fan-Projekt. Nicht affililiert mit LucasArts, Disney oder ScummVM.
