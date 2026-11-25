# Asset-Pipeline: Stand je Plattform

Diese Datei ist die Checkliste für „from source" bei den Assets. Sie beschreibt, was ein Lauf
braucht und was davon tatsächlich belegt ist. Eine Zeile ohne Beleg ist keine Zusage.

## Was erzeugt wird

| Artefakt | Erzeugt von | Ergebnis |
|---|---|---|
| Hintergründe | `scripts/extract_all_raw.py` + Upscaler | `hd/backgrounds/*.png` |
| Objekte | dieselbe Extraktion, `upscale_objects.sh` | `hd/objects/*.png` |
| Layer | `fix_mask_alpha.py --layer` | `hd/objects_layers/*.png` |
| Kostüme | RealESRGAN-Batch | `hd/costumes/*.png` |
| Fonts | `scripts/` Font-Pipeline | `hd/fonts/` |
| Pack-Manifest | `scripts/pack_manifest.py` | `hd/hd.json` |
| Videos | **nicht im Repo** | `hd/videos/<SAN>.mp4` |
| Musik | **nicht im Repo** | `hd/audio/*.wav` |

Videos und Musik haben keinen Erzeugungsschritt. Sie werden abgelegt, und der Fork findet sie über
den SAN-Basisnamen beziehungsweise den Mixer-Pfad. Wer sie „from source" will, braucht eine
dokumentierte Quelle und einen Konvertierungsschritt; beides existiert heute nicht.

## Voraussetzungen je Plattform

| Baustein | Linux | macOS | Windows |
|---|---|---|---|
| Python 3 + numpy, Pillow, opencv | belegt | nicht geprüft | nicht geprüft |
| `parse`, `deal` (NUTcracker) | belegt | nicht geprüft | nicht geprüft |
| RealESRGAN (ncnn-vulkan) | belegt, Linux-Binary | nicht geprüft | Windows-Binary im Repo-Pfad erwartet |
| Vulkan-Treiber | vorhanden | nicht geprüft | nicht geprüft |
| bash-Skripte | belegt | nicht geprüft | nur unter MSYS2 denkbar |

## Was als Nächstes zu tun ist

1. `scripts/extract_all_raw.py` auf macOS und Windows/MSYS2 ausführen und Fehler beheben.
2. Prüfen, ob RealESRGAN auf beiden Plattformen startet und dieselben Ergebnisse liefert
   (Stichprobe: gleiche Datei, gleicher Hash).
3. Die bash-Skripte unter MSYS2 lauffähig machen oder durch Python ersetzen.
4. Ergebnis in die CI aufnehmen, damit ein Plattformbruch auffällt statt gemeldet zu werden.

Erst wenn 1 bis 3 belegt sind, darf „Assets from source auf allen Plattformen" irgendwo stehen.
