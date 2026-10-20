# Stand der Auslieferung (20.10.2026)

Geprueft mit `bash scripts/verify_release.sh`, Ergebnis: **bestanden**.

| Punkt | Ergebnis |
|-------|----------|
| Linux-Engine | `ScummVM 2026.2.1gitdirty (Oct 20 2026 08:44:40)` |
| Windows-Binary | `scummvm.exe`, 20.10.2026 10:29, juenger als die Quellen |
| HD-Assets | 26662 Dateien, Pruefsummen stimmen |
| Texture-Packs | jede Datei genau einmal, fehlt 0, doppelt 0, fremd 0 |
| Raumvergleich | 93 Raeume, Mittel 0,47 %, schlechtester 4,6 %, keiner ueber 10 % |

## Behoben in dieser Runde

1. **Kamerafenster senkrecht**: `_screenTop` statt `camera._cur.y` (Fenstermitte).
2. **8-Bit-Leseposition**: das Virtuellbild ist immer bildschirmbreit, `xstart` ist kein
   Quellversatz. Vorher wurden gescrollte Raeume an der falschen Stelle gelesen.
3. **Figuren unter grossen Kostuemen**: durchsichtige Kostuemflaechen holten den Hintergrund
   zurueck und loeschten die 8-Bit-Figur darunter (Raum 89).
4. **Objektsichtbarkeit**: das HD-Objekt wird mit dem 8-Bit-Bild abgeglichen. Passt es nicht
   zusammen, ist es im Original verdeckt und wird nicht gezeichnet (Raeume 25 und 41). Das
   ersetzt die alte Differenzheuristik, die stehende Objekte faelschlich ausgeblendet hat.
5. **Raumwechsel**: Raeume werden ueber Spielstand und `startScene` geladen, damit Raumskript
   und Oberflaechensperre laufen wie im Spiel.

## Reproduzierbarkeit

- `scripts/build_release_assets.sh` — Pipeline, Nacharbeiten, Packs neu bauen und pruefen,
  Pruefsummen. Ein Aufruf, Abbruch beim ersten Fehler.
- Gewichte der Hochskalierung mit SHA-256 festgeschrieben (`docs/ASSETS.md`).
- `docs/asset-manifest.txt` — Pfad, Groesse, SHA-256 aller 26662 Dateien, `--check` vergleicht.
- `scripts/install_build.sh` — uebernimmt beide Engines, alte Fassung bleibt als `.prev`.
- `scripts/install.sh`, `scripts/package_release.sh` — Installation und Pakete (Linux 22,3 MB,
  Windows 13,1 MB).
- `docs/VERIFY.md`, `docs/MODDING.md`, `scripts/validate_hd_mod.py` — Pruefung und eigene
  Upscales.

## Offen

Aus `docs/STATUS.md` (Stand 26.05.2026) stehen noch Punkte, die der Raumvergleich **nicht**
abdeckt, weil er nur Inhalt gegen Inhalt stellt:

- **HD-Videos (MP4)**: ffmpeg-Pipe, faellt auf 8-Bit zurueck
- **Schwert-Cursor im Schwierigkeitsdialog** (Raum 87): Bedienelement, kein Raumobjekt
- **Kostuem-Unterauswahl**: alle Kostueme auf sub=1
- **HD-Schriften**: global abgeschaltet
- **Flimmern** und **Zoom-Effekt im Schwierigkeitsdialog**

Diese fuenf sind die naechste Arbeitsliste. Der Objekt-Culling-Punkt aus dieser Liste ist mit
dem Sichtbarkeitsabgleich erledigt.

### Raum 87: Titel wird gezeichnet, obwohl das Original keinen zeigt

Der Ausschnitt (`harness/crop_pair.py 87 4_kostueme 200 110 340 200 2`) zeigt in der
HD-Fassung den Spieltitel ueber der Holzvertaefelung, im 8-Bit-Bild steht dort nur Holz.

Quelle laut Protokoll: `costume HIT: actor=32 costume=0016 cel=5` und `actor=31 costume=0016
cel=79`. Die Ueberlagerung kommt also nicht aus der UI-Schicht (`step2.6b ui-overlay:
pixels=0`), sondern aus der Kostümebene mit Kostüm 0016. Entweder ist der Cel-Index dort
veraltet (`_hdCurrentCel` gegen `a->_frame`), oder der Akteur ist im Original unsichtbar und
wird trotzdem gezeichnet.

Naechster Schritt: `_hdCurrentCel` und `a->_frame` je Bild vergleichen und die Abweichung
protokollieren; danach die Cel-Auswahl korrigieren.

Ausserdem: kein Neuaufbau von null in dieser Sitzung (Kette vollstaendig, aber nicht
durchgefahren), Windows-Binary nicht gestartet, Raeume 87 und 81 mit 4,6 Prozent nicht am Bild
angesehen.
