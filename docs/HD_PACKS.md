# HD-Packs: Manifest, Auswahl im ScummVM-Menü, Validierung

Spezifikation. Stand 2026-11-21. Nichts davon ist gebaut, das ist die Grundlage für die C++-Arbeit.

## Ziel

Der Spieler soll HD-Packs im normalen ScummVM-Menü sehen, umschalten und pruefen koennen, ohne
Dateien zu verschieben und ohne README zu lesen. Das Spiel soll ausserdem merken, wenn ein Pack
fehlt oder unvollstaendig ist, und das sagen statt still in 8 Bit zu fallen.

## Nicht-Ziele

- Kein Rust-Rewrite der Pipeline. Extraktion (NUTcracker) und Upscaling (RealESRGAN/torch) bleiben
  Python. Eine Neuimplementierung kostet Monate und aendert am Ergebnis nichts.
- Kein zweiter Updater. ScummVM ist die Oberflaeche, die der Spieler ohnehin sieht.
- Keine Aenderung an `comi-hd-final/` (ausgelieferte Assets) und kein Veroeffentlichen ohne Freigabe.

## Pack-Format

Ein Pack ist ein Verzeichnis mit `hd.json` und den Unterordnern `backgrounds/`, `objects/`,
`objects_layers/`, `costumes/`, `fonts/`, `videos/`.

```json
{
  "schema": 1,
  "name": "esrgan-anime",
  "title": "RealESRGAN Anime 4x",
  "version": "1.0.5",
  "engine_min": "2026.2.1",
  "scale": 4,
  "created": "2026-11-20",
  "rooms": 93,
  "objects": 982,
  "videos": { "langs": ["en", "de", "es"], "resolution": "3840x2160" },
  "checksums": { "backgrounds": "sha256:...", "objects": "sha256:..." }
}
```

Pflichtfelder fuer die Anzeige: `name`, `title`, `version`, `scale`. Alles andere ist optional und
wird, wenn vorhanden, geprueft. Ohne `hd.json` gilt ein Verzeichnis als "unbekannt" und wird
angeboten, aber markiert.

## Fundstellen und Vorrang

1. `--hd-pack=<name>` oder `[<domain>] hd_pack=<name>` (Name im Suchpfad)
2. `[<domain>] hd_path=<pfad>` (bestehend)
3. Pack-Verzeichnisse unter `<gamedir>/packs/*` und `~/.local/share/scummvm/packs/*`
4. Geschwisterverzeichnis `<gamedir>/../hd` (bestehendes Verhalten als Rueckfall)

## Fehler, der zuerst behoben werden muss

Gemessen am 2026-11-21: `hd_path` in der ini wird ignoriert, weil `ScummEngine::init()` den Pfad
aufloest, bevor die Config-Domain aktiv ist. Im Log stand `HD path from game-dir sibling: ./hd`,
obwohl die ini einen anderen Pfad nannte. Ein Pack-Umschalter kann ohne diesen Fix nicht wirken.

Loesung: Aufloesung spaeter, wenn der Raum zum ersten Mal geladen wird (in `room.cpp` vor
`hasBackground`), dort ist `ConfMan.getActiveDomainName()` gesetzt. Ergebnis cachen, bei
Raumwechsel nicht neu aufloesen. Alternativ in `loadGFX`, wenn die Domain sicher steht.

## Menue

Ort: bestehender Reiter "Graphics" in `gui/options.cpp`, `addGraphicControls()`. Nur
Standard-Widgets, damit keine Theme-Datei angefasst werden muss.

| Element | Typ | Config-Key | Wirkung |
|---|---|---|---|
| "HD assets" | Checkbox | `hd_enabled` | schaltet die HD-Schicht aus (reiner 8-Bit-Betrieb) |
| "HD pack" | Popup | `hd_pack` | Liste der gefundenen Packs mit Version |
| "Rescan packs" | Button | - | liest die Verzeichnisse neu ein |
| Statuszeile | StaticText | - | "esrgan-anime 1.0.5, 93 Raeume, 982 Objekte" oder Fehlertext |

Verhalten: Wechsel von `hd_pack` laedt beim naechsten Raumwechsel neu, kein Neustart. Ist
`hd_enabled` aus, wird keine HD-Textur geladen, das Spiel laeuft wie Original-ScummVM.

## Validierung

Beim Oeffnen des Menues und beim Laden eines Packs:

1. `hd.json` lesen. Fehlt sie, Status "unbekanntes Pack".
2. Pflichtordner zaehlen: `backgrounds` mindestens 1, `objects` mindestens 1.
3. `engine_min` gegen die laufende Version pruefen. Zu alt: Warnung, Laden verweigert.
4. Abdeckung: Zahl der Hintergruende gegen `rooms` vergleichen. Abweichung: Warnung.
5. Pruefsummen, falls vorhanden: nur ueber die Manifest-Datei selbst, nicht ueber 5 GB Assets.

Bei Fehler: Dialog mit Klartext und Pfad, kein stiller Rueckfall. Das ist die Klasse Fehler aus
Issue #32 (frisches Setup, unklare Versionen) und #25 (Raum ohne Hintergrund, keine Meldung).

## Videos

Aus dem Code (`hd_video_player.cpp`), nicht geraten: Videos werden ueber den **SAN-Basisnamen**
des Spiels gesucht, als `<SAN>.mp4` im Ordner `videos/` des Packs. Es gibt keine Sprachsuffixe;
Sprachfassungen unterscheiden sich ueber die Spieldaten, nicht ueber die Dateinamen. Gesucht wird
in drei Schreibweisen (Original, klein, gross), plus eine Umbenennungstabelle
(`SINKSHP` → `SINKSHIP`), weil manche archive.org-Dateien anders heissen.

Konsequenz fuer Manifest und Pruefung:

- Feld `videos.files` (Anzahl mp4) und `videos.naming: "san"`, keine Sprachliste. Die Sprachliste
  aus der ersten Fassung dieser Spec war falsch.
- Pruefung: Ordner `videos/` vorhanden, mindestens eine mp4, Dateinamen ohne Sprachsuffix
  (Muster wie `_de`, `-es` gelten als verdaechtig und werden gemeldet).
- Rueckfall: fehlt die passende mp4, spielt der Fork das Originalvideo. Das ist kein Fehler,
  sondern der Normalfall bei einem Pack ohne Videos.

Betrifft Issue #21 (spanische Fassung): dort fehlen schlicht die mp4s fuer die SAN-Namen dieser
Fassung, und der Rueckfall greift.

## Kommandozeile

`--hd-pack=<name>` und `--hd-path=<pfad>` fuer Skripte und Messlaeufe. Das brauchen die
Konformitaetslaeufe ohnehin, weil sie mit wechselnden Packs arbeiten.

## Testplan

1. Pack im Menue waehlen, Spiel starten, Konformitaetslauf gegen Pack: Kontrollraeume 47 und 52
   muessen pixelgenau bleiben.
2. Pack-Verzeichnis umbenennen: beim Start klare Meldung, Spiel laeuft in 8 Bit weiter.
3. `hd.json` mit falscher `engine_min`: Laden verweigert, Meldung nennt beide Versionen.
4. `hd_enabled` aus: keine HD-Textur geladen, Bild identisch zum Original.
5. Pack-Wechsel im Menue ohne Neustart: naechster Raum laedt aus dem neuen Pack (Logzeile mit
   Packname).

## Aufwand, grob

- Lazy-Pfadaufloesung: klein, eine Funktion, hoher Nutzen (blockiert alles andere).
- Manifest lesen und validieren: klein bis mittel.
- Menue-Reiter mit vier Widgets: mittel, ueberwiegend Copy-Paste-Muster aus `addGraphicControls`.
- Videos: mittel, weil Sprachzuordnung und Rueckfall geprueft werden muessen.
- Mehrere Packs parallel: faellt beim Manifest fast gratis ab, ist nur Verzeichnislogik.

## Reihenfolge

1. Lazy-Pfadaufloesung, damit `hd_path`/`hd_pack` ueberhaupt wirken.
2. Manifest und Validierung, ohne GUI (nur Log und Dialog beim Start).
3. Menue: Checkbox, Popup, Statuszeile.
4. Videos und Sprachrueckfall.
5. Pack-Verwaltung fuer mehrere Packs samt Rescan.
