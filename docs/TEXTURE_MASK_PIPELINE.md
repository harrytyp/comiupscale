# HD texture pipeline and the object mask

This page documents how the HD object textures are produced, where the object mask
comes from, and how a mask problem is fixed reproducibly. It exists because a
one-off colour filter once damaged textures (see Issue #22).

## Pipeline order

| Step | Script | Output |
|------|--------|--------|
| 1. Extract | `scripts/extract_all_raw.py` (NUTcracker) | 1x palette PNGs: backgrounds, objects, objects_layers, fonts, costumes |
| 2. Upscale | `scripts/upscale_esrgan.py` / RealESRGAN ncnn | 4x PNGs, RGB plus an alpha contour |
| 3. Alpha from source | `scripts/add_object_alpha_v6.py` (legacy) | alpha from the border dominant palette index |
| 3b. Alpha from mask | `scripts/fix_mask_alpha.py` (current) | alpha from the proven mask, magenta band filled |
| 4. Manifest | `scripts/hd_manifest_gen.py` | load list for the fork |
| 5. Package | `scripts/build_texture_pack.py` | release ZIPs |

The engine loads the result from `hd/objects` and `hd/objects_layers`
(`hd_object_manager.cpp`, path pattern `%04d_%s_%04d.png` = room, name, state).

## Where the mask lives

The extracted sources are 8-bit palette images with no transparency at all
(`info['transparency'] is None`). The mask is a palette entry. Its colour depends on
the room palette, and it is not always the same index:

| Source | Mask index | Palette colour | Area | Border share |
|--------|-----------|----------------|------|--------------|
| `0003_system-cursor-icon_0000` | 255 | (227,0,195) | 96.1% | 100% |
| `0003_lice-icon-object_0000` | 255 | (227,0,195) | 97.6% | 100% |
| `0003_inventory-bg-object_0000` | 255 | (227,0,195) | 14.4% | 76.5% |
| `0001_logo-logo-object_0000` | 33 (not a mask) | (203,0,223) | 14.9% | 0% |
| `0022_clring-a-balcony-door_0000` | none | - | - | - |

Because the mask colour equals a magenta in most room palettes, an upscaled texture
shows a magenta background where the mask was never turned into alpha. The same
magenta also appears blurred into the object edges, because the upscaler treats it
as image content.

## The rule that decides

`scripts/mask_index.py` returns a mask index only if **both** conditions hold:

1. the palette colour is in the magenta family (`r > 200`, `b > 150`, `g < 60`), and
2. the area of that index touches the image border (at least 10% of the border pixels).

A magenta area that sits entirely inside the image is artwork (the logo case), and a
texture whose palette has no magenta entry at all has no mask to remove (the room
object case). The rule reproduces the manual review outcome exactly.

## The step

`scripts/fix_mask_alpha.py --hd <folder> --src-zip comi-original-assets.zip --apply`

- mask from the 1x source, upscaled with NEAREST (the game mask is binary, a soft
  edge leaves semi transparent magenta pixels behind)
- alpha is only lowered, never raised
- RGB inside the mask and in the 2 px band just inside it is filled from the
  neighbouring pixels, but only where the colour is still in the magenta family;
  every other colour is artwork and stays untouched
- abort rule per file: if a changed pixel lies outside the 2 px dilated mask, the
  file is written unchanged and reported

`scripts/apply_mask_alpha_all.sh [BACKUP_DIR]` runs the step over all four texture
copies (linux release, game folder, windows release, fork) and can restore a known
state first. `scripts/restore_pristine_textures.sh` restores from the backups.

## Verification

- per file inside the step: change set must be a subset of the dilated mask
- per run outside the step: group the changed files by room and compare with the
  approved group, measure the residual magenta, expect zero aborts
- review sheets: `scripts/asset_review_sheets.py --before <backup> --after <hd> --out <dir>`
  writes before and after contact sheets per asset type

Last run: 366 of 600 object textures changed, all `0003_*` (room 3 system UI,
inventory background, inventory icons). Opaque magenta in those files went from
1,811,664 to 912 pixels. Logo and room objects untouched, object layers untouched,
0 aborts.

## Object layers (the second step)

`hd/objects_layers` is a different case and gets its own mode (`--layer --object-hd <hd>/objects`).

A layer is the object placed on a full screen canvas. It carries two masks:

1. the canvas mask: NUTcracker index 39, set by `resize_pil_image(*room_bg_image.size, 39, im, ...)`
   in the extraction. Its palette colour is an ordinary room colour (measured `(63,63,27)` for room 9,
   `(107,79,19)` for room 22), so a colour test is useless here.
2. the object's own mask inside that canvas.

The object area inside the canvas is an exact rectangle (checked on 14 sources, fill grade 1.000, and
its size matches the object source size, for example 176x152 for `0022_clring-a-balcony-door`), and
the corresponding object texture is already reviewed and shipped. So the layer step does not guess:

- find the object rectangle as the bounding box of the non index 39 area
- take the alpha of the sibling object texture (`<hd>/objects/<name>`) and place it at that rectangle
- everything outside stays transparent, alpha is only lowered

Result: the layer shows exactly the pixels the object texture shows. Verified on 14 files across 7
rooms: visible area of layer against object texture, deviation 0.000% in all 14 cases.

Runtime note: fill the visible rim only. Filling every transparent pixel of a 2560x1920 image cost
about 9 s per file, restricting the fill to the rim costs 0.9 s.

## Tools that must not be used

`scripts/add_object_alpha_v7.py` is deprecated. It decided by colour alone and
removed real violet from the logo and from room object textures.

## Open work

- Issue about the extraction: write the mask as alpha or as a `tRNS` chunk so the
  mask never enters the RGB pipeline, and pre-fill masked areas before upscaling.
- Issue about the object layers: they carry their mask through NUTcracker index 39
  (border share 100%), which is not a magenta entry, so `mask_index.py` skips them
  on purpose.

## Wurzelfix: die Maske entsteht bei der Extraktion (Issue #23)

Der Reparaturschritt oben arbeitet auf fertigen Assets. Die Ursache lag davor: die Extraktion
schrieb die Maske als Palettenindex ohne Transparenz, der Upscaler las das Bild als
undurchsichtiges RGB und skalierte die Maskenfarbe als Bildinhalt mit. Das ist jetzt an beiden
Stellen behoben.

**Extraktion** (`scripts/extract_all_raw.py`, Regel in `scripts/mask_detect.py`): Die Maske wird
als tRNS ins Paletten-PNG geschrieben, der Index aber nicht geraten, sondern je Raum gemessen:

- Der Maskeneintrag ist der Paletteneintrag, der mindestens 60 % der Randpixel und 15 % der
  Bildflaeche stellt.
- Er muss von mindestens 80 % der Objektbilder des Raums gestellt werden.
- Seine Farbe muss einer gemessenen Maskenfarbe entsprechen: (227,0,195) Magenta im Systemraum,
  (107,199,27) Gruen im Schiff, (141,47,255) Violett, (0,255,0) Gruen.
- Ohne diese Mehrheit passiert nichts. Eine falsch gesetzte Maske schneidet Grafik weg, das ist
  der teurere Fehler. Grund fuer die Farbsicherung: eine reine Randregel traefe den Logoraum,
  dessen blauer Rand Grafik ist.

Die Entscheidung je Raum landet in `mask_indices.json` neben den Rohbildern, mit Stimmenzahl.

**Upscaler** (`scripts/upscale_esrgan.py`): Maskierte Quellen bekommen die Maskenfarbe vor dem
Skalieren aus der Nachbarschaft ergaenzt (`cv2.inpaint`, 3 px), damit kein Saum ins Motiv gezogen
wird. Das Alpha wird danach binaer und kantentreu uebernommen (INTER_NEAREST), weil das Spiel nur
harte Masken kennt. Beide Wege werden unterstuetzt: cv2 liefert die tRNS als vierten Kanal, PIL
ueber den Palettenindex, damit die Stufe unabhaengig vom Leser funktioniert.

**Test** (`scripts/test_root_fix.py`, laeuft ohne GPU):

    python3 scripts/test_root_fix.py [--sheet /pfad/blatt.png]

Gemessen an den Rohbildern und den freigegebenen HD-Texturen:

- Maskenerkennung: Raum 3 Index 255 Magenta 60/60, Raum 39 Index 255 Violett 60/60,
  Raum 55 Index 5 Gruen 3/3, Logoraum ohne Mehrheit -> keine Maske.
- tRNS-Rundlauf: Transparenz gelesen, Maske korrekt.
- Abgleich mit den freigegebenen HD-Texturen in Raum 3: 60 Dateien, groesste Abweichung 0,089 %,
  also Reproduktion des freigegebenen Zustands.
- Fuellroutine: Magenta 3755 -> 0 und 3307 -> 0 Pixel.

Nicht in dieser Umgebung ausgefuehrt: `cv2.inpaint` und der ESRGAN-Schritt selbst, hier fehlen
cv2 und torch. Geprueft wurde die Fuellogik ueber die Referenzimplementierung, der GPU-Lauf
gehoert auf die Maschine mit dem Modell.

## Upscaler: Modellpfad und Herkunft (Nachtrag 25.09.)

Koljas Beobachtung, die Objekttexturen saehen nicht nach dem richtigen Upscaler aus, ist messbar.
Vergleich der ausgelieferten Textur gegen eine billige Lanczos-Vergroesserung, Abweichung und
Detailverhaeltnis (Laplace-Varianz, sichtbare Flaeche, Maskenrand 3 px ausgespart):

    0003_anchor-icon_0000.png          Abweichung 31,5/255   Detailverhaeltnis 31,3
    0003_system-cursor-icon_0000.png   Abweichung 38,9/255   Detailverhaeltnis 13,8
    0009_ramrod-object_0000.png        Abweichung  9,0/255   Detailverhaeltnis 34,8

Die Objekte sind also nicht einfach interpoliert, es lief ein Modell. Im direkten Bildvergleich
wirkt die ausgelieferte Fassung aber *weicher* als Lanczos, mit geglaetteten, teils
nachgezeichneten Strukturen. Das passt zu einem stark entrauschenden Modell, nicht zum
dokumentierten `x4plus_anime_6B`.

**Was gefehlt hat:** Aus einer PNG laesst sich nicht ablesen, womit sie erzeugt wurde. Der Pfad im
Skript zeigte auf `/tmp/RealESRGAN_x4plus_anime_6B.pth`, also auf ein Verzeichnis, das nach einem
Neustart leer ist (aktuell existiert dort keine `.pth`). Damit war der Lauf nicht reproduzierbar.

**Behoben in `scripts/upscale_esrgan.py`:**

- Der Modellpfad kommt aus dem Projekt: `models/<Modell>.pth`, uebersteuerbar mit
  `COMI_MODELS_DIR`, `COMI_UPSCALE_MODEL`, `COMI_MODEL_PATH`. Fehlt die Datei, bricht das Skript
  mit einer Anleitung ab statt mit einem torch-Fehler.
- Das Skript hat eine Kommandozeile: `--input`, `--output`, `--limit`, `--pattern`.
- Jeder Lauf schreibt `upscale_manifest.json` neben die Ergebnisse: Modellname, Pfad, SHA256 der
  Gewichte, Architekturparameter, Maskenbehandlung, Start und Ende, Dateizahl.

    python3 scripts/upscale_esrgan.py --input raw/objects --output hd/objects --limit 8

Fuer die bereits ausgelieferten Pakete gibt es keine Herkunftsangabe, sie entstanden vor dieser
Aenderung. Ein Neuaufbau mit dem dokumentierten Modell braucht die Gewichte und torch plus cv2,
beides ist in dieser Umgebung nicht vorhanden.

## Die Pipeline im Ueberblick (Stand 25.09.)

Alles liegt im Repo, nichts muss aus dem Gedaechtnis rekonstruiert werden:

| Stufe | Datei | Was sie tut |
|-------|-------|-------------|
| 1 Extraktion | `scripts/export_all.sh`, `scripts/extract_all_raw.py` | Rohbilder aus COMI.LA0/1/2, Maske als tRNS (siehe unten) |
| 2 Upscale Hintergruende | `config/upscale/batch_upscale.sh` | RealESRGAN-NCNN-Vulkan, Modell `realesrgan-x4plus-anime` |
| 3 Upscale Objekte und Ebenen | `config/upscale/upscale_objects.sh` | dieselbe Ablage und dasselbe Modell, 600 Objekte + 234 Ebenen |
| 4 Alpha und Maske | `scripts/add_object_alpha_v7.py` (historisch), jetzt Extraktion plus `scripts/fix_mask_alpha.py` | Maske reproduzierbar aus der Quelle |
| 5 Paket | `scripts/build_texture_pack.py` | ZIP fuer das Release, Tabelle in der Release-Notiz |
| 6 Orchestrierung | `scripts/full_pipeline.sh`, `setup_wizard/pipeline.py` | Extract, Upscale, Build, Platzieren in einem Lauf |

Das vorgeschriebene Modell ist `realesrgan-x4plus-anime` (so in `config/upscale/upscale_objects.sh`,
`config/upscale/batch_upscale.sh`, `scripts/full_pipeline.sh` und im README). Das ist die NCNN-Route,
nicht das PyTorch-Skript `scripts/upscale_esrgan.py`; das ist ein Ersatzweg und erwartet die Gewichte
in `models/`.

**Bekannte Luecke:** Die Tool-Binaries fehlen in einem frischen Klon, weil `.gitignore` sie
ausnimmt (`tools/realesrgan-ncnn-vulkan/`, `tools/nutcracker-Windows_X64/`). Auf diesem System
existiert kein NCNN-Binary und keine `.param`-Datei, die Stufe 2 und 3 sind hier also nicht
ausfuehrbar. `scripts/fetch_upscaler.sh` schliesst das: es holt `realesrgan-ncnn-vulkan` v0.2.0
fuer Windows oder Linux nach `tools/`, prueft die Pruefsumme gegen
`scripts/upscaler_checksum.txt` und listet die Modelle auf.

    bash scripts/fetch_upscaler.sh --windows
    bash scripts/fetch_upscaler.sh --linux
